# File: backend/sketch_geometry.py
"""Read-only reference outlines using Shower Programmer's DXF preview rules.

Native DXF orientation and units are retained, including internal cuts. No CNC
rotation, hinge choice, or out-of-square correction is inferred by the scanner.
Unknown entities are rejected rather than silently drawing incomplete glass.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any


def read_reference_geometry(path: Path) -> dict[str, Any] | None:
    """Read bounded ASCII DXF geometry; return inch coordinates for validation."""
    if path.stat().st_size > 4_000_000:
        return None
    lines = path.read_text(encoding="latin1").splitlines()
    pairs = [(lines[i].strip(), lines[i + 1].strip()) for i in range(0, len(lines) - 1, 2)]
    units = 1.0  # Shower Programmer's legacy unitless exports are inches.
    for i, pair in enumerate(pairs):
        if pair == ("9", "$INSUNITS"):
            code = next((v for k, v in pairs[i + 1:i + 8] if k == "70"), "1")
            units = {"0": 1.0, "1": 1.0, "2": 12.0, "4": 1 / 25.4,
                     "5": 1 / 2.54, "6": 39.37007874015748}.get(code, 0)
            if not units:
                return None
            break
    entities: list[tuple[str, list[tuple[str, str]]]] = []
    active = False
    for code, value in pairs:
        if code == "2" and value == "ENTITIES":
            active = True
        elif active and code == "0":
            if value == "ENDSEC":
                break
            entities.append((value, []))
        elif active and entities:
            entities[-1][1].append((code, value))
    paths: list[list[tuple[float, float]]] = []
    poly: list[tuple[float, float, float]] | None = None
    poly_closed = False

    def arc(cx: float, cy: float, radius: float, start: float, sweep: float):
        if radius <= 0:
            raise ValueError("Invalid radius")
        steps = max(12, min(144, math.ceil(abs(sweep) / (math.pi / 36))))
        return [(cx + radius * math.cos(start + sweep * i / steps),
                 cy + radius * math.sin(start + sweep * i / steps)) for i in range(steps + 1)]

    def add_poly(vertices, closed):
        if len(vertices) < 2:
            return
        result = [(vertices[0][0], vertices[0][1])]
        following = vertices[1:] + ([vertices[0]] if closed else [])
        for (x, y, bulge), (ex, ey, _) in zip(vertices, following):
            if abs(bulge) > 1e-10:
                dx, dy = ex - x, ey - y
                chord = math.hypot(dx, dy)
                if not chord:
                    raise ValueError("Invalid arc")
                offset = chord * (1 - bulge * bulge) / (4 * bulge)
                cx, cy = (x + ex) / 2 - dy / chord * offset, (y + ey) / 2 + dx / chord * offset
                result.extend(arc(cx, cy, math.hypot(x - cx, y - cy), math.atan2(y - cy, x - cx), 4 * math.atan(bulge))[1:])
            else:
                result.append((ex, ey))
        paths.append(result)

    try:
        for kind, fields in entities:
            data = dict(fields)
            def number(key, default="0"):
                return float(data.get(key, default))
            # Reject non-planar/extruded coordinates rather than projecting them.
            if any(abs(number(k)) > 1e-8 for k in ("30", "31", "38", "210", "220")) or number("230", "1") != 1:
                return None
            if kind == "LINE":
                paths.append([(number("10"), number("20")), (number("11"), number("21"))])
            elif kind == "LWPOLYLINE":
                vertices = []
                for key, value in fields:
                    if key == "10": vertices.append([float(value), 0.0, 0.0])
                    elif key == "20" and vertices: vertices[-1][1] = float(value)
                    elif key == "42" and vertices: vertices[-1][2] = float(value)
                add_poly(vertices, bool(int(number("70")) & 1))
            elif kind == "POLYLINE":
                if int(number("70")) & ~1:
                    return None
                poly, poly_closed = [], bool(int(number("70")) & 1)
            elif kind == "VERTEX" and poly is not None:
                poly.append((number("10"), number("20"), number("42")))
            elif kind == "SEQEND" and poly is not None:
                add_poly(poly, poly_closed)
                poly = None
            elif kind in {"CIRCLE", "ARC"}:
                start = math.radians(number("50")) if kind == "ARC" else 0
                sweep = (math.radians(number("51")) - start) % math.tau if kind == "ARC" else math.tau
                paths.append(arc(number("10"), number("20"), number("40"), start, sweep or math.tau))
            elif kind == "ELLIPSE":
                cx, cy, ax, ay, ratio = number("10"), number("20"), number("11"), number("21"), number("40")
                start, end = number("41"), number("42", str(math.tau))
                if not 0 < ratio <= 1: return None
                sweep = (end - start) % math.tau or math.tau
                paths.append([(cx + ax * math.cos(t) - ay * ratio * math.sin(t),
                               cy + ay * math.cos(t) + ax * ratio * math.sin(t))
                              for t in [start + sweep * i / 144 for i in range(145)]])
            elif kind not in {"TEXT", "MTEXT", "DIMENSION", "POINT", "SEQEND"}:
                return None
        if poly is not None: return None
        scaled = [[(x * units, y * units) for x, y in p] for p in paths]
        points = [point for p in scaled for point in p]
        if not points or len(points) > 12000 or not all(math.isfinite(n) and abs(n) < 100000 for p in points for n in p):
            return None
        left, right = min(p[0] for p in points), max(p[0] for p in points)
        low, high = min(p[1] for p in points), max(p[1] for p in points)
        if right <= left or high <= low: return None
        return {"width": right - left, "height": high - low,
                "paths": [[[round(x - left, 5), round(high - y, 5)] for x, y in p] for p in scaled],
                "source": path.name, "units": "inches", "orientation": "source"}
    except (ValueError, OverflowError, ZeroDivisionError):
        return None
