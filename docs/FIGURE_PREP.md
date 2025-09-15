# Figure Preparation (Springer Artwork Guidelines)

- Generator: all figures are produced by the analysis script using Python 3.11 and Matplotlib (v3.x).
- Types: line art and combination plots (lines with markers, labels, legends).
- Fonts: default sans serif (Matplotlib/DejaVu Sans). For production, Helvetica/Arial can be set if desired.

## Export formats
- Preferred: vector PDF/EPS for line art; TIFF (300 dpi) for halftones.
- This repo provides a helper to collect and rename figures as `Fig1..Fig6` under `docs/figs`:
  - `cd docs && make springer_figs`
- Optional conversion to EPS/TIFF (requires ImageMagick):
  - `cd docs && make springer_figs_convert`
  - Produces `FigN.eps` (600 dpi) and `FigN.tiff` (300 dpi) alongside PNGs.

## Lettering and lines
- Keep lettering 8–12 pt at final size; avoid faint lines; minimum 0.3 pt.
- Avoid outline/3D/shadow text; do not place titles inside the artwork.
- Use scale bars for magnified images (not applicable here).

## Numbering and captions
- Figures are numbered in the manuscript in Arabic numerals and cited in order.
- Captions are included in the LaTeX source (not embedded in figure files) and identify all plotted elements.

## Permissions
- No third‑party images are used. If adding external figures, obtain permission and cite the source in the caption.

