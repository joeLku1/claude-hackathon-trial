# Plotcraft v0.1.0

First hackathon release: a local chart design studio with Python/Matplotlib rendering and a browser-based editor.

- Seven live chart types, four themes, custom palettes, typography, axes, and plot layout.
- Draggable text annotations included in PNG, SVG, and PDF exports.
- Editable data, safe cell formulas, number formatting, and CSV import/export.
- Undo/redo, browser autosave, and portable JSON projects.
- MIT license, sample data, demo guide, and automated Python tests.

## Run

Requires Python 3.10+. Download and extract the source ZIP, then run:

```bash
python -m pip install -r requirements.txt
python -m plotcraft
```

Open http://127.0.0.1:8765. A virtual environment is recommended; see README for Windows/macOS/Linux setup. A wheel is also attached: install it with pip and run `plotcraft`.

This is a local app, not a hosted website. Scope: one chart per canvas, 200 rows, 12 columns, 20 annotations. Formula references are not rewritten after deleting rows or columns. See README for data conventions and limitations.
