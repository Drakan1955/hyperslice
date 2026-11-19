# Changelog

## 1.0.0 — 2026-11-19
First public release.
- Public contact address and repository link in the manifest.

Since the 0.6 drafts:
- Presets: new thumbnail list with Séquin's 20 demos, 6 more sculptures and "My presets" (save/delete your own).
- Perforated lattice (Cells, Wire thickness), with a warning above 3000 cells (limit 6000).
- Stretch angle, overall Scale saved in `.sg1` (`size_scale`), UV map with tiles, Reflective surface.
- STL export with a chosen size in millimetres; overwrite warning on STL and `.sg1` saving.
- Edit Mode alert; shorter labels so they fit the default sidebar width.
- Fix: open edges on 5-branch towers with Taper (weld tolerance).
- Known, not fixed: small self-intersections on the axis of sculptures with 5–6 branches and a thick wall
  (reduce Thickness, e.g. 0.05, or widen the flange); see the manual.
- Licence: GPL-3.0-or-later.
