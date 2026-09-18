# Large files

Generation outputs, model weights, and print PDFs are bulky. Choose a storage strategy deliberately.

## What git ignores by default

See `.gitignore`:

- `.env` and secrets
- `models/`, `*.safetensors`, `*.ckpt`, caches
- `generations/**/*.png` (and jpg/webp)
- `approved/**/*.png`
- `kdp/final/*.pdf`, interior/preview binaries
- `colab/outbound/`, `colab/inbound/`

Metadata JSON under `generations/<id>/record.json` can still be committed if you want an audit trail without binaries.

## Tradeoffs

### 1. Local only (default)

**Pros:** Small clone, no LFS complexity, secrets/models stay private.  
**Cons:** Teammates cannot see candidate PNGs; backups are your responsibility.  
**Use when:** Solo production, CI uses mock only, artists sync via drive/NAS.

### 2. Git LFS for selected finals

**Pros:** Versioned approved art with the repo; reproducible print builds.  
**Cons:** LFS quotas/bandwidth; slow clones; easy to accidentally track too much.  
**Use when:** Small set of **approved** page finals and locked references must travel with the repo. Track paths explicitly (e.g. `approved/*.png`, `characters/*/references/*.png`) — not entire `generations/`.

### 3. External object storage for candidates

**Pros:** Unlimited candidates; cheap lifecycle rules; share links for review.  
**Cons:** Extra tooling; links rot; need clear naming (`page_id`, seed, record id).  
**Use when:** High-volume iteration; keep git for code + JSON metadata only.

## Recommendation for this project

| Asset class | Suggested home |
|-------------|----------------|
| Code, configs, story JSON/MD | Git |
| Generation candidates | Local or external; **not** default git |
| Locked character references | Local → optional LFS once approved |
| Approved page art for PDF | Local → optional LFS for release tags |
| Diffusion weights | Local / HF cache only — never git |
| Final KDP PDF | Local artifact; attach to release if needed |

Never commit `.env` or raw model weights regardless of strategy.
