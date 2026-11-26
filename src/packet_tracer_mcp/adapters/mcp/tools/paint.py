"""Create drawings as PNG/SVG files and optionally open them in Microsoft Paint."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ....infrastructure.paint.renderer import render_drawing
from ....shared.utils import reply_json, workdir_subdir


def register(mcp: FastMCP, _ctx) -> None:
    @mcp.tool()
    def paint_create_drawing(
        title: str,
        shapes_json: str,
        width: int = 1200,
        height: int = 800,
        background: str = "#FFFFFF",
        open_in_paint: bool = True,
        output_dir: str = "paint",
    ) -> str:
        """Create a drawing for Microsoft Paint and save both PNG and editable SVG.

        `shapes_json` must be a JSON array. Supported shapes:
        rectangle/ellipse: {type,x,y,width,height,fill,outline,outline_width};
        line: {type,x1,y1,x2,y2,color,width};
        text: {type,x,y,text,color,size};
        polygon: {type,points:[[x,y],...],fill,outline,outline_width}.
        Coordinates are pixels from the canvas top-left. Colors use #RGB or #RRGGBB.
        The files are saved in a safe subfolder under the MCP working directory.
        On Windows, open_in_paint starts Microsoft Paint with the PNG.
        """
        try:
            result = render_drawing(
                title=title,
                width=width,
                height=height,
                shapes_json=shapes_json,
                output_dir=workdir_subdir(output_dir, "paint"),
                background=background,
                open_in_paint=open_in_paint,
            )
            return reply_json(result)
        except (ValueError, RuntimeError, OSError) as exc:
            return reply_json({"status": "error", "message": str(exc)})
