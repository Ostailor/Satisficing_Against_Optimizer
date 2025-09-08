#!/usr/bin/env bash
set -euo pipefail

# Package release artifacts (manifests, analysis CSVs, figures) with checksums.
# Does not include raw per-run decision logs by default to keep size modest.

DIST=dist
rm -rf "$DIST"
mkdir -p "$DIST"

echo "[pack] Collecting manifests"
TMP_MAN=tmp_manifests
rm -rf "$TMP_MAN" && mkdir -p "$TMP_MAN"
find outputs -type f -path "*/exp_*_v4/*/manifest.json" -print0 | while IFS= read -r -d '' f; do
  rel="${f#outputs/}"
  dir="$(dirname "$rel")"
  mkdir -p "$TMP_MAN/$dir"
  cp "$f" "$TMP_MAN/$dir/"
done
tar -C "$TMP_MAN" -czf "$DIST/manifests_v4.tar.gz" .
rm -rf "$TMP_MAN"

echo "[pack] Collecting analysis CSVs"
TMP_AN=tmp_analysis
rm -rf "$TMP_AN" && mkdir -p "$TMP_AN"
rsync -a --include '*/' --include '*.csv' --exclude '*' outputs/analysis/ "$TMP_AN/" || true
tar -C "$TMP_AN" -czf "$DIST/analysis_v4.tar.gz" .
rm -rf "$TMP_AN"

echo "[pack] Collecting figures"
TMP_FIG=tmp_figs
rm -rf "$TMP_FIG" && mkdir -p "$TMP_FIG"
rsync -a --include '*/' --include '*.png' --exclude '*' outputs/analysis/figs_final/ "$TMP_FIG/" || true
tar -C "$TMP_FIG" -czf "$DIST/figures_v4.tar.gz" .
rm -rf "$TMP_FIG"

echo "[pack] Writing checksums"
(
  cd "$DIST"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum *.tar.gz > SHASUMS256.txt
  else
    shasum -a 256 *.tar.gz > SHASUMS256.txt
  fi
)

echo "[pack] Done. Artifacts in $DIST/"

