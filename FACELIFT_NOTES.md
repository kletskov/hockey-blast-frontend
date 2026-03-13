# Hockey Blast Frontend — Sharks-Themed DaisyUI Facelift

## Summary

Applied a complete visual facelift replacing Bootstrap 4.5 with Tailwind CSS + DaisyUI, themed with San Jose Sharks colors.

## Color Palette

| Token | Value | Use |
|---|---|---|
| Primary (orange) | `#E57200` → `oklch(0.65 0.18 50)` | CTAs, active links, headings |
| Secondary (teal) | `#006272` → `oklch(0.42 0.09 210)` | Accents, navbar bg |
| Background | `#0d0d0d` → `oklch(0.12 0 0)` | Page bg |
| Surface | `#1a1a1a` → `oklch(0.16 0 0)` | Cards, tables |
| Elevated | `#242424` → `oklch(0.20 0 0)` | Table headers |
| Text | `#F0F0F0` → `oklch(0.93 0 0)` | Primary text |

## Changes Made

### Step 1: base.html (complete rewrite)
- DaisyUI CDN (`@5`) + Tailwind CDN
- Custom `sharks` DaisyUI theme via CSS variables in `<style>` block
- Sticky top navbar with 🏒 branding
- Responsive hamburger menu for mobile
- `max-w-6xl` content container
- Footer with Hockey B.L.A.S.T tagline
- Removed ALL Bootstrap CDN references

### Step 2: index.html (full rewrite)
- Card-wrapped search form with flex layout
- All tables → `table table-zebra table-sm` in card wrappers
- Section titles with `text-primary` styling
- Removed `style="color:black"` inline styles

### Step 3: Templates Updated (38 total)
All Bootstrap class replacements applied:
- `table table-striped` → `table table-zebra table-sm` + `overflow-x-auto` wrapper
- `form-control` inputs → `input input-bordered input-sm bg-base-200`
- `form-control` selects → `select select-bordered select-sm bg-base-200`
- `form-group` → `form-control mb-2`
- `alert-danger` → `alert-error`
- `card` → `card bg-base-200 shadow-md border border-base-content/5`
- `list-group` → `menu bg-base-200 rounded-box`
- `list-group-item` → `px-3 py-2 text-sm border-b border-base-content/5`
- `container` / `row` / `col-md-*` → flex/grid equivalents
- `<h5>` → `<h2 class="text-lg font-bold mt-6 mb-3 text-primary">`
- `<h6>` → `<h3 class="text-base font-semibold mt-4 mb-2 text-primary">`
- Removed `style="color:black"` and conflicting inline styles
- Plotly charts updated with dark theme (`paper_bgcolor`, `plot_bgcolor`, `font.color`)

**Templates converted to extend base.html (were standalone):**
- `players_per_season.html`
- `teams_per_season.html`
- `seasons.html`
- `version.html`
- `error.html`
- `ai_chat.html` (full dark theme UI)
- `ai_search.html`

**Templates not found (skipped):**
- `skater_performance_dropdowns.html`
- `goalie_performance_dropdowns.html`
- `referee_performance_dropdowns.html`
- `scorekeeper_performance_dropdowns.html`
- `team_division_skater_stats.html`
- `team_division_goalie_stats.html`

### Step 4: hockey-blast-predictions GameCard.vue
- Team names now clickable links to `hockey-blast.com/team_stats?team_id=...`
- "View on HB →" link in footer when `game.game_id` exists
- Both links use `@click.stop` to prevent card pick action from firing

## Bootstrap Remnants Check
`grep -r "bootstrapcdn|bootstrap.min.css|bootstrap.min.js" templates/` → **0 results** ✅

## Date
2026-03-13
