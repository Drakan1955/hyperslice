# Changelog

## 1.0.1 — 2026-11-21
Changes requested in the extensions.blender.org review.
- The per-frame handler has been removed: the add-on no longer registers any frame-change or render handler.
- The "Animation" checkbox is replaced by a **Bake animation** button: it calculates the shape at every frame of a
  range (Start, End, Step) from the animated parameters and stores it as shape keys on a new plain mesh named
  "<name>_baked". The original sculpture is left untouched and is hidden in the viewport (still in the Outliner). Integer parameters (branches, storeys, detail) cannot be baked: the operation stops
  with a message that names the frame.
- Manifest: the only tag is now "Add Mesh".
- Manuals and panel pictures updated.

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
