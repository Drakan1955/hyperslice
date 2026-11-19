# Hyperslice - (c) 2026 Costantino Vita ("Drakan"). SPDX-License-Identifier: GPL-3.0-or-later; see LICENSE.txt.
# Geometry ported from "Sculpture Generator 1" by Carlo H. Sequin (UC Berkeley),
# released under the GPL with his permission (e-mails of 2 and 18 November 2026). Not supported or endorsed by him.
"""
sg1_io.py - lettura e scrittura dei file di parametri del Sculpture Generator 1.

Formato (testo, righe 'chiave = valore', fine riga CRLF, prima riga
'SCHERK-COLLINS SCULPTURE'). Le righe su texture, sfondo, mappa d'ambiente,
vista e rotazione automatica vengono ignorate in lettura; in scrittura si
mettono valori neutri, cosi' il programma originale puo' rileggere il file.
Le righe aggiuntive detail_axis, size_scale, taper, vase_swell, stretch_angle e perforated/perf_cells/perf_wire (estensioni di Hyperslice) si scrivono
in fondo al file: il programma originale le ignora solo li'.
Solo Python standard: nessuna dipendenza da Blender.
"""

HEADER = "SCHERK-COLLINS SCULPTURE"
EXT = ".sg1"

# chiave nel file -> (proprieta' dell'addon, tipo)
NUMERIC = {
    "branches": ("branches", int),
    "storeys": ("storeys", int),
    "height": ("height", float),
    "flange": ("flange", float),
    "thickness": ("thickness", float),
    "rim_bulge": ("rim_bulge", float),
    "warp": ("warp", float),
    "twist": ("twist", float),
    "azimuth": ("azimuth", float),
    "detail": ("detail", int),
    "scaleX": ("stretch_x", float),
    "scaleY": ("stretch_y", float),
    "scaleZ": ("stretch_z", float),
    # estensioni di Hyperslice: il programma originale le ignora SOLO se sono in fondo al file
    "detail_axis": ("detail_long", int),
    "size_scale": ("scale", float),
    "taper": ("taper", float),
    "vase_swell": ("swell", float),
    "stretch_angle": ("scale_angle", float),
    "texture_tiles": ("uv_tiles", int),
    "environment_map_on": ("reflective", int),   # on import: 'Reflective' option
    "perforated": ("perf_on", int),
    "perf_cells": ("perf_cells", int),
    "perf_wire": ("perf_wire", float),
}
COLORS = {
    "face1_color": "color_a",
    "face2_color": "color_b",
    "rim1_color": "color_rim",
    "rim2_color": "color_lid_up",
    "rim3_color": "color_lid_down",
}
IGNORED_PREFIXES = ("texture", "environment", "background", "auto_", "x_", "y_",
                    "scale_factor", "modelview")


def srgb_to_linear(c255):
    c = max(0.0, min(255.0, float(c255))) / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb255(x):
    x = max(0.0, min(1.0, float(x)))
    c = x * 12.92 if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    return int(round(c * 255.0))


class NotParamFile(ValueError):
    """La prima riga non e' l'intestazione dei file di parametri."""


def parse(path):
    """Ritorna (valori, colori, extra, ignorate).
    valori: nome proprieta' -> numero;  colori: nome proprieta' -> (r,g,b,1) lineare;
    extra: dict (oggi sempre vuoto; una riga 'scaleAngle' dei file di versioni recenti viene ignorata);  ignorate: numero di righe ignorate."""
    with open(path, "r", errors="replace") as f:
        lines = f.read().splitlines()
    if not lines or lines[0].strip() != HEADER:
        raise NotParamFile(HEADER)
    values, colors, extra = {}, {}, {}
    ignored = 0
    for ln in lines[1:]:
        if "=" not in ln:
            continue                      # righe di continuazione della matrice
        key, val = (s.strip() for s in ln.split("=", 1))
        try:
            if key in NUMERIC:
                prop, typ = NUMERIC[key]
                values[prop] = typ(float(val))
            elif key in COLORS:
                r, g, b = (float(x) for x in val.split()[:3])
                colors[COLORS[key]] = (srgb_to_linear(r), srgb_to_linear(g),
                                       srgb_to_linear(b), 1.0)
            elif key.startswith(IGNORED_PREFIXES):
                ignored += 1
        except ValueError:
            ignored += 1
    return values, colors, extra, ignored


def _num(v, nd=2):
    s = f"{v:.{nd}f}"
    return s


def format_file(p, colors):
    """p: dict con le chiavi delle proprieta' dell'addon; colors: dict nome->(r,g,b,a) lineare."""
    def col(name):
        c = colors[name]
        return "%d %d %d" % (linear_to_srgb255(c[0]), linear_to_srgb255(c[1]), linear_to_srgb255(c[2]))

    rows = [
        HEADER,
        f"branches = {int(p['branches'])}",
        f"storeys = {int(p['storeys'])}",
        f"height = {_num(p['height'])}",
        f"flange = {_num(p['flange'])}",
        f"thickness = {_num(p['thickness'])}",
        f"rim_bulge = {_num(p['rim_bulge'])}",
        f"warp = {int(round(p['warp']))}",
        f"twist = {int(round(p['twist']))}",
        f"azimuth = {int(round(p['azimuth']))}",
        f"texture_tiles = {int(p.get('uv_tiles', 1))}",
        f"detail = {int(p['detail'])}",
    ]
    rows += [
        f"scaleX = {_num(p['stretch_x'], 3)}",
        f"scaleY = {_num(p['stretch_y'], 3)}",
        f"scaleZ = {_num(p['stretch_z'], 3)}",
        "texture_file = Images/marble2.ppm",
        "texture_on = 0",
        f"environment_map_on = {1 if p.get('reflective') else 0}",
        "background_file = Images/SculptStand.rgb",
        "background_on = 0",
        "background_color = 0 0 0",
        f"face1_color = {col('color_a')}",
        f"face2_color = {col('color_b')}",
        f"rim1_color = {col('color_rim')}",
        f"rim2_color = {col('color_lid_up')}",
        f"rim3_color = {col('color_lid_down')}",
        "auto_rotate_on = 0",
        "auto_wobble_on = 0",
        "x_rotation = 0.000",
        "y_rotation = 2.000",
        "scale_factor = 1.000",
        "x_translate = 0.000",
        "y_translate = 0.000",
        "modelview_matrix = 1.00000 0.00000 0.00000 0.00000",
        "                   0.00000 1.00000 0.00000 0.00000",
        "                   0.00000 0.00000 1.00000 0.00000",
        "                   0.00000 0.00000 0.00000 1.00000",
    ]
    # Estensioni di Hyperslice, solo se diverse dal neutro e SEMPRE in fondo: il lettore
    # del programma originale va per ordine e una riga in mezzo fa fallire il caricamento.
    if int(p.get("detail_long", 0)) != 0:
        rows.append(f"detail_axis = {int(p['detail_long'])}")
    if abs(p.get("scale", 1.0) - 1.0) > 1e-9:
        rows.append(f"size_scale = {_num(p['scale'], 3)}")
    if abs(p.get("taper", 0.0)) > 1e-9:
        rows.append(f"taper = {_num(p['taper'])}")
    if abs(p.get("swell", 0.0)) > 1e-9:
        rows.append(f"vase_swell = {_num(p['swell'])}")
    if abs(p.get("scale_angle", 0.0)) > 1e-9:
        rows.append(f"stretch_angle = {_num(p['scale_angle'], 1)}")
    if p.get("perf_on"):
        rows.append("perforated = 1")
        rows.append(f"perf_cells = {int(p.get('perf_cells', 800))}")
        rows.append(f"perf_wire = {_num(p.get('perf_wire', 0.07), 3)}")
    return "\r\n".join(rows) + "\r\n"
