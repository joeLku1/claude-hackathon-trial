# A 90-second Plotcraft demo

## The idea

“Data should stay live while you design. Plotcraft is a free, open-source chart canvas: edit numbers like a spreadsheet, then style the story like a slide.”

## Demo sequence

1. Start `python -m plotcraft`, open the local URL, and load the sample.
2. Click **B4** and change `62` to `100`. The June value in **B6** is `=SUM(B4:B5)/2+20`; it updates from 88 to 107 automatically.
3. Switch to **Line**, turn on **Data labels**, and choose **After hours**.
4. Add a text annotation: “A community, growing together.” Drag it into position and change its color/size.
5. Switch to a square canvas, adjust plot size if necessary, and export an SVG or PNG.
6. Save the project, reopen it, and change another number. The design remains editable.
7. Show the repository's MIT license and the release assets.

## Honest positioning for the NUS Hackers track

The target workflow is chart creation and presentation styling across spreadsheet and design tools. This implementation independently recreates the visible data-edit → calculate → chart → style → export workflow. It does not claim to reverse engineer proprietary binaries, file formats, or internal algorithms.

The key observation is that data and visual design can live in one portable JSON document. A single Matplotlib render path keeps preview and exported text layers consistent. Local execution avoids a mandatory subscription or rendering service. The software price is $0; users still supply a computer and installation time. Optional future hosting would have infrastructure costs.

Before presenting quantified savings or market reach, collect current official pricing and adoption sources for the exact Excel/Microsoft 365 or Canva plan you compare against. Do not claim all charting alternatives are paid: free tools exist. The useful differentiation to demonstrate is customizable, live Matplotlib charts with a simple design interface and an openly licensed, editable project format.

## Known boundaries to state if asked

One chart per canvas; basic formulas rather than Excel compatibility; no live external feed, team editing, hosted service, or arbitrary diagram shapes. The demo data is fictional.
