# Plotcraft

**Live data. Your design.** A small, local-first chart studio that combines spreadsheet-style recalculation with a presentation-style design canvas, powered by Python and Matplotlib.

[Demo guide](DEMO.md) · [MIT license](LICENSE)

## Start in two minutes

Requires **Python 3.10+**. Download and extract the release source ZIP, or clone this repository. In that folder:

```bash
python -m venv .venv
```

Activate it:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Then:

```bash
python -m pip install -r requirements.txt
python -m plotcraft
```

Open **http://127.0.0.1:8765** in your browser. Keep the terminal running; press Ctrl+C to stop. If the port is busy, use `python -m plotcraft --port 8766`.

Alternatively, install the release wheel with `python -m pip install path/to/plotcraft_studio-0.1.0-py3-none-any.whl`, then run `plotcraft`.

No API keys, Node build step, login, paid subscription, or internet connection at runtime. The first dependency installation requires internet access. This release runs on your computer; it is not a hosted web service or a standalone executable.

## What you can make

- **Seven chart types:** grouped bar, horizontal bar, stacked bar, line, area, scatter, and donut.
- **Live data:** edit cells or paste a tab-separated rectangle; recalculate dependencies and redraw after a short debounce. This means live editing, not a connection to an external streaming data source.
- **Design controls:** palettes, canvas and grid colors, fonts, title/subtitle, axes, number formats, legend, value labels, opacity, bar width, line weight, point size, tick rotation, axis limits, and plot position/size.
- **Text layers:** add, edit, recolor, resize, bold, drag, or keyboard-nudge annotations. All text layers are included in exports.
- **Four visual themes**, three canvas sizes, undo/redo, and a working sample.
- **Cell formatting:** currency, percentage, compact numbers, bold, and background color.
- **Portable projects:** browser autosave plus save/open `.plotcraft.json`; import and export CSV.
- **Consistent exports:** SVG and PDF vectors; PNG at 150 DPI (1.5× the logical canvas dimensions). The entire canvas is rendered by Matplotlib.

## Formulas and data conventions

Column A contains categories (numeric X values for scatter). Columns B onward contain series. Header labels are separate: the first **data** row is row 1.

| Example | Meaning |
| --- | --- |
| `=SUM(B1:B6)` | Sum a range |
| `=AVERAGE(B1:C3)` | Mean across a rectangular range |
| `=B1*1.2+C1/2` | Arithmetic with references |
| `=ROUND(B1/3,2)` | Round to two decimals |
| `=MIN(B1:B6)` / `=MAX(B1:B6)` | Range extrema |
| `=COUNT(B1:B6)` | Count numeric values |

Supported operators: `+ - * / %` (`%` means modulo, not percentage). Functions are case-insensitive. Ranges ignore text; blank cells become zero and count as numeric. Direct arithmetic on text is an error. Percent formatting expects a fraction: `0.25` becomes `25%`. Currency formatting uses USD/$.

Formulas use a bounded Python AST interpreter, **never `eval`**. Code, attributes, imports, exponentiation, file/network access, and arbitrary function calls are unsupported. Circular references, excessive depth, nonfinite numbers, and invalid expressions produce cell errors and pause export until corrected. Values are bounded to ±1e15.

**Deletion behavior:** deleting a row or column does not rewrite formula references. Check formulas afterwards or undo. This is deliberately a small chart editor, not a full Excel-compatible formula engine.

CSV has a header row and rectangular data. Formula strings are preserved on CSV export; Excel may interpret cells beginning with `=` when you open the file. Use project JSON to preserve charts, styles and annotations. CSV import replaces data but keeps your design.

## Scope of v0.1.0

One chart per canvas, up to 200 data rows, 12 columns (11 series), and 20 text annotations. Donut uses only the first selected series and requires nonnegative values with a positive total. Scatter requires numeric column A. Text is not automatically wrapped; keep labels short or insert line breaks in annotations. Font choices are the bundled DejaVu families; some languages may require additional glyph support.

There is no multi-page layout, arbitrary shapes, chart resizing by handles, Excel file import, collaboration, remote database connection, or hosted deployment yet. Plot position and size are controlled with sliders. Browser storage is local to the origin and browser; save a project file before clearing storage or changing ports.

## Architecture and development

The browser sends a JSON project to the bounded formula engine. Matplotlib renders the calculated values and design into an SVG preview or a PNG/PDF export.

The frontend is plain HTML/CSS/JavaScript. Python's standard-library HTTP server serves a fixed asset allowlist and stateless calculation/render endpoints. Matplotlib uses Agg and explicit Figure instances. A lock serializes rendering because Matplotlib is not thread-safe ([official guidance](https://matplotlib.org/stable/users/faq.html#work-with-threads)).

The server binds to `127.0.0.1` and rejects unrelated Host/Origin headers. This is a single-user local application, **not a production internet server**. Do not expose it through a public tunnel or reverse proxy without adding an appropriate server, authentication, rate limits, and deployment hardening.

```bash
python -m unittest discover -s tests -v
```

Tests cover dependency recalculation, cycles, unsupported expressions, bounds, all 21 chart/format combinations, export text, concurrent renders, CSV parsing, project roundtrips, and HTTP validation. `tests/browser_smoke.cjs` exercises the editor with Playwright (install Playwright and Chromium separately, start Plotcraft, then `node tests/browser_smoke.cjs`).

The included GitHub Actions workflow is configured to test Python 3.10 and 3.12, run the browser smoke flow, build a wheel/source archive, and publish the first v0.1.0 release only after the tests succeed. Later pushes do not overwrite that release.

## Verification and publishing status

The local Python suite passed all 15 tests, including all seven chart types in three export formats. A source-built wheel was checked for the editor assets. The sample PNG was visually inspected. Browser smoke automation is included but has **not yet run**: the build environment blocked the Chromium download. GitHub rejected repository writes with HTTP 403 (“Resource not accessible by integration”), so this package has not been pushed and no GitHub release has been published. See [PUBLISH.md](PUBLISH.md) to finish publishing after granting the connection access or using your own authenticated Git client.

## License

MIT. Python/Matplotlib and their dependencies retain their own licenses. Built as an independent hackathon prototype; not affiliated with Microsoft or Canva.
