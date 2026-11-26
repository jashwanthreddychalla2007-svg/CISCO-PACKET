"""Render safe, simple shape descriptions to SVG and PNG files."""

from __future__ import annotations

import html
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ...shared.utils import resolve_within, safe_name_component

MAX_SIDE = 4096
MAX_SHAPES = 200
MAX_COORD = 8192


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    value = float(value)
    if not 0 <= value <= MAX_COORD:
        raise ValueError(f"{field} must be between 0 and {MAX_COORD}")
    return value


def _color(value: Any, field: str = "color") -> str:
    if not isinstance(value, str) or not (
        len(value) in (4, 7) and value.startswith("#")
        and all(c in "0123456789abcdefABCDEF" for c in value[1:])
    ):
        raise ValueError(f"{field} must be a hex color such as #336699")
    return value


def _validate_shapes(shapes: list[dict[str, Any]], width: int, height: int) -> list[dict[str, Any]]:
    if not isinstance(shapes, list) or len(shapes) > MAX_SHAPES:
        raise ValueError(f"shapes must be a list with at most {MAX_SHAPES} items")
    clean: list[dict[str, Any]] = []
    for index, raw in enumerate(shapes):
        if not isinstance(raw, dict):
            raise ValueError(f"Shape {index + 1} must be an object")
        kind = raw.get("type")
        if kind not in {"rectangle", "ellipse", "line", "text", "polygon"}:
            raise ValueError(f"Shape {index + 1}: type must be rectangle, ellipse, line, text, or polygon")
        item: dict[str, Any] = {"type": kind}
        if kind in {"rectangle", "ellipse"}:
            for key in ("x", "y", "width", "height"):
                item[key] = _number(raw.get(key), f"shape {index + 1} {key}")
            if item["width"] == 0 or item["height"] == 0:
                raise ValueError(f"Shape {index + 1}: width and height must be positive")
            item["fill"] = _color(raw.get("fill", "#FFFFFF"), "fill")
            item["outline"] = _color(raw.get("outline", "#222222"), "outline")
            item["outline_width"] = _number(raw.get("outline_width", 2), "outline_width")
        elif kind == "line":
            for key in ("x1", "y1", "x2", "y2"):
                item[key] = _number(raw.get(key), f"shape {index + 1} {key}")
            item["color"] = _color(raw.get("color", "#222222"))
            item["width"] = max(1, _number(raw.get("width", 2), "line width"))
        elif kind == "text":
            if not isinstance(raw.get("text"), str) or len(raw["text"]) > 500:
                raise ValueError(f"Shape {index + 1}: text must be a string of at most 500 characters")
            item["x"] = _number(raw.get("x"), f"shape {index + 1} x")
            item["y"] = _number(raw.get("y"), f"shape {index + 1} y")
            item["text"] = raw["text"]
            item["color"] = _color(raw.get("color", "#222222"))
            item["size"] = max(1, _number(raw.get("size", 24), "text size"))
        else:
            points = raw.get("points")
            if not isinstance(points, list) or not 3 <= len(points) <= 100:
                raise ValueError(f"Shape {index + 1}: polygon needs 3 to 100 points")
            item["points"] = [
                [_number(p[0], "point x"), _number(p[1], "point y")]
                for p in points if isinstance(p, (list, tuple)) and len(p) == 2
            ]
            if len(item["points"]) != len(points):
                raise ValueError(f"Shape {index + 1}: each polygon point must be [x, y]")
            item["fill"] = _color(raw.get("fill", "#FFFFFF"), "fill")
            item["outline"] = _color(raw.get("outline", "#222222"), "outline")
            item["outline_width"] = _number(raw.get("outline_width", 2), "outline_width")
        clean.append(item)
    return clean


def _svg(title: str, width: int, height: int, shapes: list[dict[str, Any]], background: str) -> str:
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<title>{html.escape(title)}</title>',
        f'<rect width="100%" height="100%" fill="{background}"/>',
    ]
    for s in shapes:
        if s["type"] == "rectangle":
            lines.append(f'<rect x="{s["x"]}" y="{s["y"]}" width="{s["width"]}" height="{s["height"]}" fill="{s["fill"]}" stroke="{s["outline"]}" stroke-width="{s["outline_width"]}"/>')
        elif s["type"] == "ellipse":
            lines.append(f'<ellipse cx="{s["x"] + s["width"] / 2}" cy="{s["y"] + s["height"] / 2}" rx="{s["width"] / 2}" ry="{s["height"] / 2}" fill="{s["fill"]}" stroke="{s["outline"]}" stroke-width="{s["outline_width"]}"/>')
        elif s["type"] == "line":
            lines.append(f'<line x1="{s["x1"]}" y1="{s["y1"]}" x2="{s["x2"]}" y2="{s["y2"]}" stroke="{s["color"]}" stroke-width="{s["width"]}"/>')
        elif s["type"] == "text":
            lines.append(f'<text x="{s["x"]}" y="{s["y"]}" fill="{s["color"]}" font-family="Arial,sans-serif" font-size="{s["size"]}">{html.escape(s["text"])}</text>')
        else:
            points = " ".join(f"{x},{y}" for x, y in s["points"])
            lines.append(f'<polygon points="{points}" fill="{s["fill"]}" stroke="{s["outline"]}" stroke-width="{s["outline_width"]}"/>')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def render_drawing(
    title: str, width: int, height: int, shapes_json: str,
    output_dir: Path, background: str = "#FFFFFF", open_in_paint: bool = True,
) -> dict[str, Any]:
    """Write an SVG source and Paint-compatible PNG into a contained output folder."""
    if (
        isinstance(width, bool) or not isinstance(width, int)
        or isinstance(height, bool) or not isinstance(height, int)
        or not (1 <= width <= MAX_SIDE and 1 <= height <= MAX_SIDE)
    ):
        raise ValueError(f"Canvas width and height must each be between 1 and {MAX_SIDE}")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a non-empty string")
    if not isinstance(shapes_json, str) or len(shapes_json) > 1_000_000:
        raise ValueError("shapes_json must be a string no larger than 1 MB")
    try:
        shapes = json.loads(shapes_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"shapes_json is not valid JSON: {exc}") from exc
    shapes = _validate_shapes(shapes, width, height)
    background = _color(background, "background")
    safe_title = safe_name_component(title, fallback="drawing")
    folder = resolve_within(output_dir, safe_title)
    folder.mkdir(parents=True, exist_ok=True)
    png_path = resolve_within(folder, f"{safe_title}.png")
    svg_path = resolve_within(folder, f"{safe_title}.svg")

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("PNG rendering requires Pillow. Install the package dependency with: pip install 'packet-tracer-mcp'") from exc

    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    for s in shapes:
        if s["type"] == "rectangle":
            box = (s["x"], s["y"], s["x"] + s["width"], s["y"] + s["height"])
            draw.rectangle(box, fill=s["fill"], outline=s["outline"], width=max(1, int(s["outline_width"])))
        elif s["type"] == "ellipse":
            box = (s["x"], s["y"], s["x"] + s["width"], s["y"] + s["height"])
            draw.ellipse(box, fill=s["fill"], outline=s["outline"], width=max(1, int(s["outline_width"])))
        elif s["type"] == "line":
            draw.line((s["x1"], s["y1"], s["x2"], s["y2"]), fill=s["color"], width=int(s["width"]))
        elif s["type"] == "text":
            try:
                font = ImageFont.truetype("arial.ttf", int(s["size"]))
            except OSError:
                font = ImageFont.load_default()
            draw.text((s["x"], s["y"]), s["text"], fill=s["color"], font=font)
        else:
            points = [tuple(p) for p in s["points"]]
            draw.polygon(points, fill=s["fill"])
            draw.line(points + [points[0]], fill=s["outline"], width=max(1, int(s["outline_width"])))
    image.save(png_path, format="PNG", optimize=True)
    svg_path.write_text(_svg(title, width, height, shapes, background), encoding="utf-8")

    opened = False
    open_message = ""
    if open_in_paint:
        if sys.platform == "win32":
            try:
                subprocess.Popen(["mspaint.exe", str(png_path)], close_fds=True)
                opened = True
            except OSError as exc:
                open_message = f"Created the files, but could not start Paint: {exc}"
        else:
            open_message = "Created the files. Paint is only available on Windows; open the PNG in an image editor."
    return {
        "status": "created",
        "png_path": str(png_path),
        "svg_path": str(svg_path),
        "canvas": {"width": width, "height": height},
        "shape_count": len(shapes),
        "opened_in_paint": opened,
        "message": open_message,
    }
