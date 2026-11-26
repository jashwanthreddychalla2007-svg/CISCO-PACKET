"""Tests for Paint-compatible drawing exports."""

from __future__ import annotations

import json

from PIL import Image

from src.packet_tracer_mcp.infrastructure.paint.renderer import render_drawing


def test_renders_png_and_svg_with_shapes(tmp_path):
    shapes = [
        {"type": "rectangle", "x": 10, "y": 10, "width": 80, "height": 50, "fill": "#FF0000"},
        {"type": "ellipse", "x": 120, "y": 10, "width": 50, "height": 50, "fill": "#00FF00"},
        {"type": "line", "x1": 10, "y1": 100, "x2": 180, "y2": 100, "color": "#0000FF"},
        {"type": "text", "x": 10, "y": 130, "text": "Paint test", "size": 18},
        {"type": "polygon", "points": [[200, 10], [260, 10], [230, 60]], "fill": "#FFFF00"},
    ]

    result = render_drawing(
        "hello drawing", 300, 180, json.dumps(shapes), tmp_path, open_in_paint=False,
    )

    png = Image.open(result["png_path"])
    assert png.format == "PNG"
    assert png.size == (300, 180)
    assert png.getpixel((20, 20)) == (255, 0, 0)
    assert "Paint test" in open(result["svg_path"], encoding="utf-8").read()
    assert result["shape_count"] == 5
    assert not result["opened_in_paint"]


def test_rejects_unsafe_colors_and_path_names(tmp_path):
    import pytest

    safe_result = render_drawing("../escape", 100, 100, "[]", tmp_path, open_in_paint=False)
    assert safe_result["png_path"].startswith(str(tmp_path.resolve()))

    # Invalid values are rejected before any files are created.
    with pytest.raises(ValueError, match="hex color"):
        render_drawing(
            "valid-name", 100, 100,
            json.dumps([{"type": "rectangle", "x": 0, "y": 0, "width": 10, "height": 10, "fill": "red"}]),
            tmp_path, open_in_paint=False,
        )


def test_bounds_and_svg_text_are_safe(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="width and height"):
        render_drawing("bad", 5000, 20, "[]", tmp_path, open_in_paint=False)

    result = render_drawing(
        "<title>", 100, 80,
        json.dumps([{"type": "text", "x": 1, "y": 24, "text": "<script>&"}]),
        tmp_path, open_in_paint=False,
    )
    svg = open(result["svg_path"], encoding="utf-8").read()
    assert "&lt;title&gt;" in svg
    assert "&lt;script&gt;&amp;" in svg
