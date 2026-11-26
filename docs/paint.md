# Microsoft Paint drawings

The MCP server includes `paint_create_drawing`. It turns a structured drawing description into a PNG that opens in Microsoft Paint on Windows, plus an SVG source file for editing in a vector editor. The drawing files are written below the server's working directory in a safe output folder (by default, `paint/<drawing-name>/`).

## Example

Ask the connected AI client: “Draw a simple network diagram in Paint with three blue router boxes connected in a row, one green PC below each router, and labels R1–R3 and PC1–PC3.” The client calls `paint_create_drawing` with a shape list similar to:

```json
[
  {"type":"rectangle","x":80,"y":80,"width":150,"height":70,"fill":"#DCEBFF","outline":"#2457A7","outline_width":3},
  {"type":"text","x":110,"y":125,"text":"Router R1","color":"#16345F","size":22},
  {"type":"line","x1":230,"y1":115,"x2":390,"y2":115,"color":"#333333","width":4},
  {"type":"ellipse","x":390,"y":80,"width":150,"height":70,"fill":"#E0F5E9","outline":"#22834A","outline_width":3},
  {"type":"text","x":425,"y":125,"text":"Router R2","color":"#165A31","size":22}
]
```

Coordinates use pixels from the top-left of the canvas. Shapes are drawn in list order, so later shapes appear on top. Supported shape types are `rectangle`, `ellipse`, `line`, `text`, and `polygon`. Colors must use `#RGB` or `#RRGGBB` notation. The canvas can be up to 4096×4096 pixels and each drawing can contain up to 200 shapes.

Set `open_in_paint` to `false` to only save the files. On non-Windows systems the PNG and SVG are still created, but Microsoft Paint is not launched.

This feature creates finished image files; it does not automate Paint's freehand brush or edit Paint's internal canvas objects.
