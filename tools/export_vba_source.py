from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import shutil
import struct
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path


FREESECT = 0xFFFFFFFF
ENDOFCHAIN = 0xFFFFFFFE


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip()
    return cleaned or "unnamed"


@dataclass
class DirectoryEntry:
    index: int
    name: str
    object_type: int
    left_id: int
    right_id: int
    child_id: int
    start_sector: int
    stream_size: int
    path: str = ""


class CompoundFile:
    def __init__(self, data: bytes) -> None:
        self.data = data
        if data[:8] != bytes.fromhex("D0CF11E0A1B11AE1"):
            raise ValueError("Not an OLE compound file")

        self.sector_size = 1 << u16(data, 0x1E)
        self.mini_sector_size = 1 << u16(data, 0x20)
        self.num_fat_sectors = u32(data, 0x2C)
        self.first_dir_sector = u32(data, 0x30)
        self.mini_stream_cutoff = u32(data, 0x38)
        self.first_minifat_sector = u32(data, 0x3C)
        self.num_minifat_sectors = u32(data, 0x40)
        self.first_difat_sector = u32(data, 0x44)
        self.num_difat_sectors = u32(data, 0x48)

        self.difat = self._read_difat()
        self.fat = self._read_fat()
        self.directory_entries = self._read_directory()
        self._assign_paths()
        self.root_entry = next((e for e in self.directory_entries if e.object_type == 5), None)
        self.root_stream = self._read_regular_stream(self.root_entry) if self.root_entry else b""
        self.minifat = self._read_minifat()

    def _sector(self, sector_id: int) -> bytes:
        start = (sector_id + 1) * self.sector_size
        end = start + self.sector_size
        if start < 0 or end > len(self.data):
            raise ValueError(f"Sector {sector_id} is outside file bounds")
        return self.data[start:end]

    def _read_difat(self) -> list[int]:
        entries = []
        for i in range(109):
            value = u32(self.data, 0x4C + (i * 4))
            if value not in (FREESECT, ENDOFCHAIN):
                entries.append(value)

        next_sector = self.first_difat_sector
        sectors_read = 0
        while next_sector not in (FREESECT, ENDOFCHAIN) and sectors_read < self.num_difat_sectors:
            sector = self._sector(next_sector)
            count = (self.sector_size // 4) - 1
            for i in range(count):
                value = u32(sector, i * 4)
                if value not in (FREESECT, ENDOFCHAIN):
                    entries.append(value)
            next_sector = u32(sector, self.sector_size - 4)
            sectors_read += 1

        return entries[: self.num_fat_sectors]

    def _read_fat(self) -> list[int]:
        fat: list[int] = []
        for sector_id in self.difat:
            sector = self._sector(sector_id)
            fat.extend(u32(sector, i) for i in range(0, self.sector_size, 4))
        return fat

    def _chain(self, start_sector: int) -> list[int]:
        if start_sector in (FREESECT, ENDOFCHAIN):
            return []
        chain: list[int] = []
        seen: set[int] = set()
        sector = start_sector
        while sector not in (FREESECT, ENDOFCHAIN):
            if sector in seen:
                raise ValueError(f"Loop detected in sector chain at {sector}")
            if sector >= len(self.fat):
                raise ValueError(f"Sector chain references missing FAT entry {sector}")
            seen.add(sector)
            chain.append(sector)
            sector = self.fat[sector]
        return chain

    def _read_regular_stream(self, entry: DirectoryEntry | None) -> bytes:
        if entry is None or entry.start_sector in (FREESECT, ENDOFCHAIN):
            return b""
        chunks = [self._sector(sector_id) for sector_id in self._chain(entry.start_sector)]
        return b"".join(chunks)[: entry.stream_size]

    def _read_minifat(self) -> list[int]:
        if self.first_minifat_sector in (FREESECT, ENDOFCHAIN) or self.num_minifat_sectors == 0:
            return []
        chunks = [self._sector(sector_id) for sector_id in self._chain(self.first_minifat_sector)]
        data = b"".join(chunks)[: self.num_minifat_sectors * self.sector_size]
        return [u32(data, i) for i in range(0, len(data), 4)]

    def _mini_chain(self, start_sector: int) -> list[int]:
        if start_sector in (FREESECT, ENDOFCHAIN):
            return []
        chain: list[int] = []
        seen: set[int] = set()
        sector = start_sector
        while sector not in (FREESECT, ENDOFCHAIN):
            if sector in seen:
                raise ValueError(f"Loop detected in mini sector chain at {sector}")
            if sector >= len(self.minifat):
                raise ValueError(f"Mini sector chain references missing FAT entry {sector}")
            seen.add(sector)
            chain.append(sector)
            sector = self.minifat[sector]
        return chain

    def _read_mini_stream(self, entry: DirectoryEntry) -> bytes:
        chunks = []
        for mini_sector_id in self._mini_chain(entry.start_sector):
            start = mini_sector_id * self.mini_sector_size
            end = start + self.mini_sector_size
            chunks.append(self.root_stream[start:end])
        return b"".join(chunks)[: entry.stream_size]

    def read_stream(self, entry: DirectoryEntry) -> bytes:
        if entry.object_type == 5:
            return self._read_regular_stream(entry)
        if entry.stream_size < self.mini_stream_cutoff and self.root_stream:
            return self._read_mini_stream(entry)
        return self._read_regular_stream(entry)

    def _read_directory(self) -> list[DirectoryEntry]:
        fake_dir = DirectoryEntry(-1, "directory", 2, FREESECT, FREESECT, FREESECT, self.first_dir_sector, 0)
        chunks = [self._sector(sector_id) for sector_id in self._chain(fake_dir.start_sector)]
        directory = b"".join(chunks)
        entries: list[DirectoryEntry] = []
        for index in range(0, len(directory), 128):
            raw = directory[index : index + 128]
            if len(raw) < 128:
                continue
            name_len = u16(raw, 64)
            if name_len >= 2:
                name = raw[: name_len - 2].decode("utf-16le", errors="replace")
            else:
                name = ""
            object_type = raw[66]
            if object_type == 0:
                continue
            entries.append(
                DirectoryEntry(
                    index=index // 128,
                    name=name,
                    object_type=object_type,
                    left_id=u32(raw, 68),
                    right_id=u32(raw, 72),
                    child_id=u32(raw, 76),
                    start_sector=u32(raw, 116),
                    stream_size=u64(raw, 120),
                )
            )
        return entries

    def _entry_by_id(self, entry_id: int) -> DirectoryEntry | None:
        if entry_id in (FREESECT, ENDOFCHAIN):
            return None
        for entry in self.directory_entries:
            if entry.index == entry_id:
                return entry
        return None

    def _sibling_tree_ids(self, entry_id: int) -> list[int]:
        if entry_id in (FREESECT, ENDOFCHAIN):
            return []
        entry = self._entry_by_id(entry_id)
        if entry is None:
            return []
        return self._sibling_tree_ids(entry.left_id) + [entry.index] + self._sibling_tree_ids(entry.right_id)

    def _assign_paths(self) -> None:
        root = next((e for e in self.directory_entries if e.object_type == 5), None)
        if root is None:
            return
        root.path = root.name

        def walk(parent: DirectoryEntry, prefix: str) -> None:
            for child_id in self._sibling_tree_ids(parent.child_id):
                child = self._entry_by_id(child_id)
                if child is None:
                    continue
                child.path = f"{prefix}/{child.name}" if prefix else child.name
                if child.object_type in (1, 5):
                    walk(child, child.path)

        walk(root, "")

    def stream_entries(self) -> list[DirectoryEntry]:
        return [entry for entry in self.directory_entries if entry.object_type == 2]

    def find_stream(self, path_suffix: str) -> DirectoryEntry | None:
        normalized = path_suffix.replace("\\", "/").lower()
        for entry in self.stream_entries():
            if entry.path.lower().endswith(normalized):
                return entry
        return None


def decompress_vba_stream(data: bytes) -> bytes:
    if not data:
        return b""
    if data[0] != 0x01:
        return data

    pos = 1
    out = bytearray()
    while pos + 2 <= len(data):
        header_pos = pos
        header = u16(data, pos)
        pos += 2
        chunk_size = (header & 0x0FFF) + 3
        chunk_end = min(header_pos + chunk_size, len(data))
        compressed = (header & 0x8000) != 0

        if not compressed:
            out.extend(data[pos:chunk_end])
            pos = chunk_end
            continue

        chunk = bytearray()
        while pos < chunk_end:
            flags = data[pos]
            pos += 1
            for bit in range(8):
                if pos >= chunk_end:
                    break
                if flags & (1 << bit):
                    if pos + 2 > chunk_end:
                        pos = chunk_end
                        break
                    token = u16(data, pos)
                    pos += 2
                    bit_count = max(4, math.ceil(math.log2(max(len(chunk), 1))))
                    length_mask = 0xFFFF >> bit_count
                    offset_mask = 0xFFFF ^ length_mask
                    length = (token & length_mask) + 3
                    offset = ((token & offset_mask) >> (16 - bit_count)) + 1
                    for _ in range(length):
                        if offset <= len(chunk):
                            chunk.append(chunk[-offset])
                else:
                    chunk.append(data[pos])
                    pos += 1
        out.extend(chunk)
        pos = chunk_end

    return bytes(out)


@dataclass
class ModuleInfo:
    name: str
    stream_name: str
    source_offset: int
    module_type: str
    exported_file: str = ""
    source_length: int = 0


def decode_vba_bytes(data: bytes, codepage: int) -> str:
    encodings = [f"cp{codepage}", "cp1252", "latin1"]
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except LookupError:
            continue
        except UnicodeDecodeError:
            continue
    return data.decode("cp1252", errors="replace")


def parse_dir_stream(dir_data: bytes) -> tuple[int, list[ModuleInfo]]:
    decompressed = decompress_vba_stream(dir_data)
    pos = 0
    codepage = 1252
    modules: list[ModuleInfo] = []
    in_modules = False
    current: dict[str, object] | None = None

    while pos + 6 <= len(decompressed):
        rec_id = u16(decompressed, pos)
        rec_size = u32(decompressed, pos + 2)
        pos += 6
        payload = decompressed[pos : pos + rec_size]
        pos += rec_size
        # PROJECTVERSION stores VersionMajor after the 4-byte reserved field and
        # then VersionMinor as an extra UInt16. It is the one common record that
        # would otherwise knock the whole stream parser out of alignment.
        if rec_id == 0x0009 and pos + 2 <= len(decompressed):
            pos += 2

        if rec_id == 0x0003 and rec_size >= 2:
            codepage = u16(payload, 0)
        elif rec_id == 0x000F:
            in_modules = True
        elif in_modules and rec_id == 0x0019:
            if current and current.get("name") and current.get("stream_name"):
                modules.append(
                    ModuleInfo(
                        name=str(current.get("name")),
                        stream_name=str(current.get("stream_name")),
                        source_offset=int(current.get("source_offset") or 0),
                        module_type=str(current.get("module_type") or "unknown"),
                    )
                )
            current = {
                "name": decode_vba_bytes(payload, codepage).rstrip("\x00"),
                "stream_name": "",
                "source_offset": 0,
                "module_type": "unknown",
            }
        elif current is not None:
            if rec_id == 0x001A:
                current["stream_name"] = decode_vba_bytes(payload, codepage).rstrip("\x00")
            elif rec_id == 0x0031 and rec_size >= 4:
                current["source_offset"] = u32(payload, 0)
            elif rec_id == 0x0021:
                current["module_type"] = "procedural"
            elif rec_id == 0x0022:
                current["module_type"] = "document"
            elif rec_id == 0x002B:
                if current.get("name") and current.get("stream_name"):
                    modules.append(
                        ModuleInfo(
                            name=str(current.get("name")),
                            stream_name=str(current.get("stream_name")),
                            source_offset=int(current.get("source_offset") or 0),
                            module_type=str(current.get("module_type") or "unknown"),
                        )
                    )
                current = None

    if current and current.get("name") and current.get("stream_name"):
        modules.append(
            ModuleInfo(
                name=str(current.get("name")),
                stream_name=str(current.get("stream_name")),
                source_offset=int(current.get("source_offset") or 0),
                module_type=str(current.get("module_type") or "unknown"),
            )
        )

    return codepage, modules


def choose_extension(module: ModuleInfo, source: str) -> str:
    name = module.name.lower()
    if name.startswith("frm"):
        return ".frm"
    if module.module_type == "document":
        return ".cls"
    if 'Attribute VB_Base = "0{' in source:
        if name.startswith("sheet") or name == "thisworkbook":
            return ".cls"
        return ".frm"
    if "Attribute VB_PredeclaredId = True" in source and "Attribute VB_Creatable = False" in source:
        return ".cls"
    return ".bas"


def extract_vba_project(workbook_path: Path, output_root: Path) -> dict[str, object]:
    workbook_name = workbook_path.stem
    workbook_out = output_root / sanitize_filename(workbook_name)
    if workbook_out.exists():
        shutil.rmtree(workbook_out)
    workbook_out.mkdir(parents=True, exist_ok=True)
    metadata_dir = workbook_out / "_metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(workbook_path, "r") as zf:
        try:
            vba_bin = zf.read("xl/vbaProject.bin")
        except KeyError as exc:
            raise ValueError(f"{workbook_path.name} does not contain xl/vbaProject.bin") from exc

    (metadata_dir / "vbaProject.bin").write_bytes(vba_bin)
    cfb = CompoundFile(vba_bin)
    stream_manifest = [
        {
            "path": entry.path,
            "name": entry.name,
            "size": entry.stream_size,
            "start_sector": entry.start_sector,
        }
        for entry in sorted(cfb.stream_entries(), key=lambda e: e.path.lower())
    ]
    (metadata_dir / "cfb_streams.json").write_text(
        json.dumps(stream_manifest, indent=2),
        encoding="utf-8",
        newline="\n",
    )

    dir_entry = cfb.find_stream("VBA/dir")
    if dir_entry is None:
        raise ValueError(f"{workbook_path.name} VBA project does not contain a VBA/dir stream")

    codepage, modules = parse_dir_stream(cfb.read_stream(dir_entry))
    for module in modules:
        stream_entry = cfb.find_stream(f"VBA/{module.stream_name}")
        if stream_entry is None:
            continue
        stream_data = cfb.read_stream(stream_entry)
        compressed_source = stream_data[module.source_offset :]
        source_bytes = decompress_vba_stream(compressed_source)
        source = decode_vba_bytes(source_bytes, codepage).replace("\r\n", "\n").replace("\r", "\n")
        ext = choose_extension(module, source)
        out_file = workbook_out / f"{sanitize_filename(module.name)}{ext}"
        out_file.write_text(source, encoding="utf-8", newline="\n")
        module.exported_file = out_file.name
        module.source_length = len(source)

    project_manifest = {
        "workbook": str(workbook_path),
        "workbook_name": workbook_path.name,
        "exported_at": dt.datetime.now().isoformat(timespec="seconds"),
        "codepage": codepage,
        "module_count": len(modules),
        "modules": [asdict(module) for module in modules],
        "notes": [
            "Source was extracted directly from xl/vbaProject.bin.",
            "UserForm designer binary/state is preserved in _metadata/vbaProject.bin; exported .frm files contain the code stream and attributes.",
        ],
    }
    (metadata_dir / "modules.json").write_text(
        json.dumps(project_manifest, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return project_manifest


def write_readme(output_root: Path, manifests: list[dict[str, object]]) -> None:
    lines = [
        "# VBA Source",
        "",
        "This folder contains extracted VBA source for the active scanner system workbooks.",
        "",
        "## Workbooks exported",
        "",
    ]
    for manifest in manifests:
        lines.append(f"- {manifest['workbook_name']}: {manifest['module_count']} modules/forms/classes")
    lines.extend(
        [
            "",
            "## Workflow",
            "",
            "1. Export fresh source from the active workbooks before starting a change.",
            "2. Edit the `.bas`, `.cls`, and `.frm` source files here.",
            "3. Run the import tool in dry-run mode to confirm which modules will be touched.",
            "4. Import changed code back into the workbook after confirming the workbook is closed by other users.",
            "5. Test the workbook, then export source again so this folder matches the workbook.",
            "",
            "## Tools",
            "",
            "- `tools/export_vba_source.py` extracts readable VBA source from the `.xlsm` workbooks.",
            "- `tools/import_vba_source.ps1` imports source files back into a workbook through Excel automation.",
            "",
            "Example dry run:",
            "",
            "```powershell",
            '.\\tools\\import_vba_source.ps1 -ProjectRoot "I:\\BAREFOOT-INSTALL\\Glass Production\\Brandon\\Delivery List Scanning Project" -WorkbookName "Multi User Scanner Queue Testing (version 2).xlsm" -DryRun',
            "```",
            "",
            "Example dry run for only changed files:",
            "",
            "```powershell",
            '.\\tools\\import_vba_source.ps1 -ProjectRoot "I:\\BAREFOOT-INSTALL\\Glass Production\\Brandon\\Delivery List Scanning Project" -WorkbookName "Multi User Scanner Queue Testing (version 2).xlsm" -Files "modMasterQueueProcessor.bas","TemplateImporter.bas" -DryRun',
            "```",
            "",
            "Example real import:",
            "",
            "```powershell",
            '.\\tools\\import_vba_source.ps1 -ProjectRoot "I:\\BAREFOOT-INSTALL\\Glass Production\\Brandon\\Delivery List Scanning Project" -WorkbookName "Multi User Scanner Queue Testing (version 2).xlsm"',
            "```",
            "",
            'For a workbook that requires a password to open for editing, add `-WritePassword "..."`.',
            "",
            "## Notes",
            "",
            "- The `_metadata/vbaProject.bin` file is a raw copy of the workbook VBA project at export time.",
            "- The exported `.frm` files contain UserForm code/attributes. The import tool updates form code in the existing workbook component so the designer layout stays in the workbook.",
            "- Sheet modules and `ThisWorkbook` are updated in place so their workbook bindings are preserved.",
            "- Power Automate trigger URLs and other workbook secrets may appear in source files, so keep this folder in the same restricted location as the workbooks.",
            "",
        ]
    )
    (output_root / "README.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract VBA source from macro-enabled Excel workbooks.")
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--output", default="VBA Source", type=Path)
    parser.add_argument("workbooks", nargs="+", type=Path)
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    output_root = args.output
    if not output_root.is_absolute():
        output_root = project_root / output_root
    output_root.mkdir(parents=True, exist_ok=True)

    manifests = []
    for workbook in args.workbooks:
        workbook_path = workbook if workbook.is_absolute() else project_root / workbook
        manifests.append(extract_vba_project(workbook_path, output_root))

    write_readme(output_root, manifests)
    print(json.dumps({"output": str(output_root), "workbooks": len(manifests)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
