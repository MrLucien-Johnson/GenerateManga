# KDP workflow

## Story page vs physical page

**Story page N is not always physical page N.**

`PhysicalPageMapper` applies:

1. Optional **front matter** pages (title, copyright, dedication, …)
2. Each illustrated story page
3. Optional **blank reverse** page after each illustration (default **on** for this coloring-book interior)

### Examples

`front_matter_pages=0`, `blank_reverse_pages=True`:

| Story | Physical art | Physical blank |
|-------|--------------|----------------|
| 1 | 1 | 2 |
| 2 | 3 | 4 |

`front_matter_pages=2`, `blank_reverse_pages=True`:

| Story | Physical art | Physical blank |
|-------|--------------|----------------|
| 1 | 3 | 4 |
| 2 | 5 | 6 |

`blank_reverse_pages=False`: story N → physical `(front_matter_pages + N)`.

## Trim size

Configured in `config/kdp.json`:

- Trim: **8.5 × 11** inches
- Bleed: **0.125** in each side → media box **8.75 × 11.25**
- DPI target: **300**
- `blank_reverse_pages: true`

Pixel guide for full-bleed pages:  
`(8.5 + 2×0.125) × 300` by `(11 + 2×0.125) × 300` → **2625 × 3375** (generation config may use slightly different working sizes; final print assets should match KDP expectations).

## Building the interior PDF

```python
from echo.publishing.kdp import build_kdp_pdf
from echo.publishing.preflight import run_preflight

report = run_preflight(root=root)
path = build_kdp_pdf(root=root, require_gates=True)
```

Rules:

- Only files under `approved/` are drawn.
- Filename stems should match page ids (`p1`, `p1_panel1`, …).
- Blank reverses are empty pages (optional faint page number via `page_number_on_blanks`).
- Front matter currently emits blank placeholders — replace with designed pages before final upload.
- `require_gates=True` enforces PDF readiness (Kaito + pilot + approved art).

## Never auto-publish

Building a PDF is **not** publishing. Upload to Amazon KDP (or any printer) is always a deliberate human action outside this toolkit. Git `auto_push` stays false by default.
