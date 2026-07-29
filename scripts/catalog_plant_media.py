from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def image_month(path: Path) -> str:
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            timestamp = exif.get(36867) or exif.get(306)
            if timestamp:
                return str(timestamp)[:7].replace(":", "-")
    except Exception:
        return "unreadable"
    return "undated"


def make_contact_page(
    items: list[Path], output_path: Path, title: str, columns: int = 6
) -> None:
    thumb_width = 220
    thumb_height = 150
    label_height = 34
    title_height = 48
    rows = (len(items) + columns - 1) // columns
    canvas = Image.new(
        "RGB",
        (columns * thumb_width, title_height + rows * (thumb_height + label_height)),
        (24, 27, 31),
    )
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 14), title, fill=(245, 247, 250))

    for index, path in enumerate(items):
        x = (index % columns) * thumb_width
        y = title_height + (index // columns) * (thumb_height + label_height)
        try:
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((thumb_width - 8, thumb_height - 8))
                canvas.paste(
                    image,
                    (
                        x + (thumb_width - image.width) // 2,
                        y + (thumb_height - image.height) // 2,
                    ),
                )
        except Exception:
            draw.rectangle(
                (x + 8, y + 8, x + thumb_width - 8, y + thumb_height - 8),
                outline=(210, 70, 70),
                width=3,
            )

        label = path.name
        if len(label) > 31:
            label = label[:28] + "..."
        draw.text((x + 6, y + thumb_height + 5), label, fill=(225, 229, 235))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, quality=88)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--media-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    files = sorted(
        path
        for path in args.media_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
        and "POWERPOINT PLANT PROGRESS" not in path.parts
    )

    groups: dict[str, list[Path]] = defaultdict(list)
    records: list[tuple[Path, str]] = []
    for path in files:
        month = image_month(path)
        groups[month].append(path)
        records.append((path, month))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "image-manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["relative_path", "month"])
        for path, month in records:
            writer.writerow([path.relative_to(args.media_root), month])

    page_size = 36
    for month in sorted(groups):
        month_files = groups[month]
        for page_number, start in enumerate(range(0, len(month_files), page_size), 1):
            page_items = month_files[start : start + page_size]
            output_path = args.output_dir / (
                f"{month}-page-{page_number:02d}.jpg"
            )
            make_contact_page(
                page_items,
                output_path,
                f"{month} | {start + 1}-{start + len(page_items)} of {len(month_files)}",
            )

    print(f"IMAGES={len(files)}")
    print(f"GROUPS={len(groups)}")
    print(f"MANIFEST={manifest_path}")


if __name__ == "__main__":
    main()
