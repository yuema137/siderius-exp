# Tutorial illustrations

`tutorial-workflow.html` is the self-contained editable source for
`tutorial-workflow.svg`, which the repository README displays. The layout uses
the pastel cards, colored accents, sans-serif headings and connectors of the
infra paper figures; this is a tutorial diagram, not a reproduction of a paper
figure. No remote fonts, scripts or images are required.

`tutorial-sequence.html` is the editable source for `tutorial-sequence.svg`,
displayed by `tutorials/README.md`. It uses the same visual style while preserving
the tutorial index's horizontal five-step sequence. Its print size is
960 × 208 CSS pixels. Both README images use 80% width with automatic height.

Render with Chromium and Poppler, from the exp checkout:

```bash
export CHROME_BIN=/absolute/path/to/chromium
export FIGURE_BUILD_DIR=/absolute/path/to/temporary-figure-build
mkdir -p "$FIGURE_BUILD_DIR"
"$CHROME_BIN" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$FIGURE_BUILD_DIR/tutorial-workflow.pdf" \
  "file://$PWD/docs/assets/tutorial-workflow.html"
pdftocairo -svg "$FIGURE_BUILD_DIR/tutorial-workflow.pdf" \
  docs/assets/tutorial-workflow.svg
pdftoppm -scale-to-x 2880 -scale-to-y -1 -singlefile -png \
  "$FIGURE_BUILD_DIR/tutorial-workflow.pdf" "$FIGURE_BUILD_DIR/preview-3x"
```

To rebuild the tutorial index illustration, use `tutorial-sequence` in place
of `tutorial-workflow` in the input and output filenames above. Render and
inspect each changed illustration separately.

The HTML print size is 960 × 768 CSS pixels with zero page margins. The
intermediate PDF should contain exactly one vector page; the exported SVG uses
a proportional viewBox and needs no browser script support. Keep PDF and preview
PNGs in the temporary build directory. Use the 3× preview for visual review;
a screenshot at 960 pixels can look soft when enlarged. Verify the diagram at normal
README width and a narrow viewport before committing the source and SVG together.

The diagram owns only the beginner file flow. Task semantics, notebook saving,
launching and result rendering remain with their existing code and guides.
