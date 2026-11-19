# Hyperslice - (c) 2026 Costantino Vita ("Drakan"). SPDX-License-Identifier: GPL-3.0-or-later; see LICENSE.txt.
# Geometry ported from "Sculpture Generator 1" by Carlo H. Sequin (UC Berkeley),
# released under the GPL with his permission (e-mails of 2 and 18 November 2026). Not supported or endorsed by him.
bl_info = {
    "name": "Hyperslice",
    "author": "Drakan & Claude",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar (N) > Hyperslice  |  Add > Mesh",
    "description": "Scherk towers, saddle branches, twist and Collins toroidal closure, "
                   "inspired by Carlo Séquin's Sculpture Generator 1",
    "category": "Add Mesh",
}

import bpy
import bpy.utils.previews
import numpy as np
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty,
                       IntProperty, PointerProperty, StringProperty)
from bpy.app.handlers import persistent
from bpy.types import Menu, Operator, Panel, PropertyGroup

import math
import os
import random
import importlib
from . import sg1_core as core
from . import sg1_io
# Blender keeps the sub-modules in memory when an add-on is reinstalled without a restart: reload them
importlib.reload(core)
importlib.reload(sg1_io)
from . import presets_extra, translations_extra   # (translations_it reads them: reload them first)
importlib.reload(presets_extra)
importlib.reload(translations_extra)


# --------------------------------------------------------------------------
# traduzione: sorgente in inglese, italiano se Blender e' in italiano
# --------------------------------------------------------------------------
from . import translations_it
importlib.reload(translations_it)


def _rpt(msg, **kw):
    """Messaggio per i report, tradotto se la lingua di Blender e' l'italiano."""
    t = bpy.app.translations.pgettext_rpt(msg)
    return t.format(**kw) if kw else t


def _fmt(msg, **kw):
    """Testo dell'interfaccia con valori, tradotto se serve."""
    return bpy.app.translations.pgettext_iface(msg).format(**kw)

MAT_LABELS = ("side A", "side B", "rim", "top lid", "bottom lid")
MAT_PROPS = ("color_a", "color_b", "color_rim", "color_lid_up", "color_lid_down")
WELD_REL = 2e-6            # merge-by-distance tolerance relative to the size (must stay below the spacing near the saddle centres)
LIVE_FACE_LIMIT = 150000     # oltre questa soglia il live riduce il dettaglio


# --------------------------------------------------------------------------
# preset (parametri in unita' dell'originale; la dimensione si regola solo con scale)
# --------------------------------------------------------------------------
PRESETS = {
    "TORRE": ("Scherk tower",
              dict(branches=2, storeys=2, detail=8, height=1.5, flange=1.5,
                   thickness=0.15, rim_bulge=1.5, twist=0.0, warp=0.0, azimuth=0.0, scale=1.0)),
    "TORRE3": ("3-branch tower", dict(branches=3, storeys=3, detail=8, height=1.0, flange=1.2,
                                                 thickness=0.05, rim_bulge=1.0, twist=0.0, warp=0.0, azimuth=0.0, scale=0.8)),
    "RITORTA": ("Twisted tower", dict(branches=2, storeys=6, detail=8, height=1.0, flange=1.0,
                                       thickness=0.05, rim_bulge=1.0, twist=360.0, warp=0.0, azimuth=0.0, scale=0.6)),
    "ARCO": ("180° arch", dict(branches=2, storeys=3, detail=10, height=1.0, flange=1.0,
                                thickness=0.06, rim_bulge=1.0, twist=0.0, warp=180.0, azimuth=0.0, scale=0.9)),
    "FIG9": ("Toroidal closure",
             dict(branches=2, storeys=3, detail=16, height=4.5, flange=3.4, thickness=0.15,
                  rim_bulge=1.5, twist=270.0, warp=360.0, azimuth=0.0, scale=0.3)),
    "FIG10": ("Double closure",
              dict(branches=2, storeys=3, detail=16, height=3.4, flange=0.8, thickness=0.06,
                   rim_bulge=1.01, twist=270.0, warp=720.0, azimuth=5.0, scale=0.9)),
    "TRE_ANELLI": ("3-branch closure", dict(branches=3, storeys=3, detail=16, height=4.1, flange=1.5,
                                                thickness=0.07, rim_bulge=1.0, twist=180.0, warp=360.0, azimuth=0.0, scale=0.45)),
}
PRESET_GROUPS = {"classic": list(PRESETS.keys()), "demo": [], "more": []}
PRESET_DEMO_N = {}
from . import presets_extra
for _key, _group, _n, _name, _tr, _par in presets_extra.EXTRA:
    PRESETS[_key] = (_name, _par)
    PRESET_GROUPS[_group].append(_key)
    if _n:
        PRESET_DEMO_N[_key] = _n


# --------------------------------------------------------------------------
# generazione mesh
# --------------------------------------------------------------------------
def _params(props):
    return dict(branches=props.branches, storeys=props.storeys, detail=props.detail,
                height=props.height, flange=props.flange, thickness=props.thickness,
                rim_bulge=props.rim_bulge, twist=props.twist, warp=props.warp,
                azimuth=props.azimuth, scale=props.scale,
                detail_long=props.detail_long, taper=props.taper, swell=props.swell,
                stretch_x=props.stretch_x, stretch_y=props.stretch_y, stretch_z=props.stretch_z,
                stretch_angle=props.scale_angle, uv_map=props.uv_map, uv_tiles=props.uv_tiles)


def _set_mat_color(mat, col):
    mat.diffuse_color = col
    if mat.use_nodes and mat.node_tree is not None:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = col


def _set_mat_gloss(mat, reflective):
    """'Reflective' = environment_map_on of the original program: shiny, mirror-like surface."""
    if mat.use_nodes and mat.node_tree is not None:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Roughness"].default_value = 0.08 if reflective else 0.35
            bsdf.inputs["Metallic"].default_value = 0.4 if reflective else 0.0
    mat.roughness = 0.08 if reflective else 0.35
    mat.metallic = 0.4 if reflective else 0.0


def _ensure_materials(obj):
    """Cinque materiali propri dell'oggetto (uno per parte), colori dai cursori."""
    mesh = obj.data
    props = obj.sg1
    if len(mesh.materials) != len(MAT_LABELS):
        mesh.materials.clear()
        for label, pname in zip(MAT_LABELS, MAT_PROPS):
            m = bpy.data.materials.new(f"{obj.name} - {label}")
            m.use_nodes = True
            bsdf = m.node_tree.nodes.get("Principled BSDF")
            if bsdf is not None:
                bsdf.inputs["Roughness"].default_value = 0.35
            _set_mat_color(m, tuple(getattr(props, pname)))
            _set_mat_gloss(m, props.reflective)
            mesh.materials.append(m)


def _on_color(self, context):
    obj = self.id_data
    if not isinstance(obj, bpy.types.Object) or obj.type != "MESH":
        return
    mats = obj.data.materials
    if len(mats) == len(MAT_LABELS):
        for m, pname in zip(mats, MAT_PROPS):
            if m is not None:
                _set_mat_color(m, tuple(getattr(self, pname)))


def _on_reflective(self, context):
    obj = self.id_data
    if not isinstance(obj, bpy.types.Object) or obj.type != "MESH":
        return
    for m in obj.data.materials:
        if m is not None:
            _set_mat_gloss(m, self.reflective)


PERF_NAMES = ("SG1 Densify", "SG1 Triangulate", "SG1 Decimate", "SG1 Cells", "SG1 Wire", "SG1 Smooth")
PERF_GROUP = "Hyperslice_Dual"
PERF_CELLS_WARN = 3000      # above this the lattice gets slow and heavy; the slider stops at 6000


def _perf_group():
    """Geometry-nodes group: Dual Mesh (Voronoi-like cells) that keeps the material of each region
    (Dual Mesh alone resets all the material indices to 0)."""
    ng = bpy.data.node_groups.get(PERF_GROUP)
    if ng is not None:
        return ng
    ng = bpy.data.node_groups.new(PERF_GROUP, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    try:
        ng.is_modifier = True
    except Exception:
        pass
    N = ng.nodes
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    mi = N.new("GeometryNodeInputMaterialIndex")
    ev = N.new("GeometryNodeFieldOnDomain")
    ev.domain, ev.data_type = "POINT", "FLOAT"
    st = N.new("GeometryNodeStoreNamedAttribute")
    st.domain, st.data_type = "POINT", "FLOAT"
    st.inputs["Name"].default_value = "sg1_mat"
    du = N.new("GeometryNodeDualMesh")
    du.inputs["Keep Boundaries"].default_value = True
    na = N.new("GeometryNodeInputNamedAttribute")
    na.data_type = "FLOAT"
    na.inputs["Name"].default_value = "sg1_mat"
    rd = N.new("ShaderNodeMath")
    rd.operation = "ROUND"
    sm = N.new("GeometryNodeSetMaterialIndex")
    for n, x in ((gi, -900), (mi, -900), (ev, -700), (st, -500), (du, -300), (na, -300), (rd, -100),
                 (sm, 100), (go, 300)):
        n.location = (x, 0)
    L = ng.links.new
    L(mi.outputs[0], ev.inputs[0])
    L(gi.outputs[0], st.inputs["Geometry"])
    L(ev.outputs[0], st.inputs["Value"])
    L(st.outputs["Geometry"], du.inputs["Mesh"])
    L(du.outputs["Dual Mesh"], sm.inputs["Geometry"])
    L(na.outputs[0], rd.inputs[0])
    L(rd.outputs[0], sm.inputs["Material Index"])
    L(sm.outputs["Geometry"], go.inputs[0])
    return ng


def _update_perf(obj):
    """Adds, updates or removes the 'Perforated' modifiers: a simple subdivision gives enough triangles,
    Decimate leaves about 2 per cell, Dual Mesh makes the irregular cells, Wireframe the wires."""
    props = obj.sg1
    mods = obj.modifiers
    if not props.perf_on:
        for n in PERF_NAMES:
            if n in mods:
                mods.remove(mods[n])
        return
    nf = max(len(obj.data.polygons), 1)
    cells = props.perf_cells
    lev = 0
    while lev < 4 and nf * 4 ** lev * 2 < 8 * cells and nf * 4 ** (lev + 1) * 2 <= 1500000:
        lev += 1
    tris = nf * 4 ** lev * 2
    if any(n not in mods for n in PERF_NAMES):
        for n in PERF_NAMES:
            if n in mods:
                mods.remove(mods[n])
        m = mods.new("SG1 Densify", "SUBSURF")
        m.subdivision_type = "SIMPLE"
        mods.new("SG1 Triangulate", "TRIANGULATE")
        mods.new("SG1 Decimate", "DECIMATE")
        g = mods.new("SG1 Cells", "NODES")
        g.node_group = _perf_group()
        w = mods.new("SG1 Wire", "WIREFRAME")
        w.use_replace = True
        mods.new("SG1 Smooth", "SUBSURF")
    d = mods["SG1 Densify"]
    d.levels = d.render_levels = lev
    mods["SG1 Decimate"].ratio = min(1.0, 2.0 * cells / tris)
    w = mods["SG1 Wire"]
    w.thickness = props.perf_wire
    w.use_replace = True
    w.use_even_offset = True
    # Boundary wires together with even thickness throw single vertices hundreds of units away
    # on open meshes (e.g. when the ends of a ring do not match): never turn them on.
    w.use_boundary = False
    s = mods["SG1 Smooth"]
    s.levels = s.render_levels = 1


def _on_perf(self, context):
    obj = self.id_data
    if isinstance(obj, bpy.types.Object) and obj.type == "MESH" and self.is_sculpture:
        _update_perf(obj)


def regenerate(obj, force_full=False):
    """Ricostruisce la mesh dell'oggetto dai parametri. Ritorna il dettaglio usato."""
    import bmesh
    props = obj.sg1
    if obj.mode == "EDIT":          # in Edit Mode the generated mesh would be lost or mixed up: do nothing
        return props.last_detail
    p = _params(props)
    used_detail = p["detail"]
    if props.live_cap and not force_full:
        while used_detail > 2 and core.estimate_faces(dict(p, detail=used_detail)) > LIVE_FACE_LIMIT:
            used_detail -= 1
    p["detail"] = used_detail
    want_uv = bool(p.get("uv_map"))
    if want_uv:
        verts, quads, mats, uvs = core.generate(p, with_uv=True)
    else:
        verts, quads, mats = core.generate(p)
        uvs = None

    _ensure_materials(obj)      # prima della geometria: altrimenti gli indici si azzerano
    mesh = obj.data
    mesh.clear_geometry()
    nv, nf = len(verts), len(quads)
    try:
        mesh.vertices.add(nv)
        mesh.vertices.foreach_set("co", verts.astype(np.float32).ravel())
        mesh.loops.add(nf * 4)
        mesh.loops.foreach_set("vertex_index", quads.ravel())
        mesh.polygons.add(nf)
        mesh.polygons.foreach_set("loop_start", np.arange(0, nf * 4, 4, dtype=np.int32))
        mesh.polygons.foreach_set("material_index", mats)
        mesh.update(calc_edges=True)
    except Exception:
        mesh.clear_geometry()
        mesh.from_pydata(verts.tolist(), [], quads.tolist())
        mesh.polygons.foreach_set("material_index", mats)
        mesh.update()

    if uvs is not None:        # one UV per face corner, in the same order as the loops
        while len(mesh.uv_layers):
            mesh.uv_layers.remove(mesh.uv_layers[0])
        layer = mesh.uv_layers.new(name="UVMap")
        layer.data.foreach_set("uv", uvs[quads].astype(np.float32).ravel())

    # salda i bordi dei vari pezzi (stessa posizione => stessi vertici)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    ext = float(np.ptp(verts, axis=0).max()) if nv else 1.0
    tol = max(1e-6, min(WELD_REL * ext, 0.05 * max(props.thickness * props.scale, 1e-4)))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=tol)
    bm.to_mesh(mesh)
    bm.free()

    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), dtype=bool))
    mesh.update()

    props.last_detail = used_detail
    props.last_faces = len(mesh.polygons)
    if props.perf_on:
        _update_perf(obj)
    return used_detail


def _closure_hint(props):
    """None se le estremita' di un anello chiuso combaciano; altrimenti i due valori
    di torsione piu' vicini che le fanno combaciare."""
    if props.warp not in (360.0, 720.0, 1080.0):
        return None
    step = 360.0 / props.branches
    off = (180.0 / props.branches) if props.storeys % 2 else 0.0
    r = (props.twist + off) % step
    if min(r, step - r) < 0.5:
        return None
    base = (-off) % step
    low = base + math.floor((props.twist - base) / step) * step
    return (low, low + step)


def _taper_ring_problem(props):
    return props.warp in (360.0, 720.0, 1080.0) and abs(props.taper) > 1e-6


def _on_change(self, context):
    obj = self.id_data
    if isinstance(obj, bpy.types.Object) and self.is_sculpture and self.live:
        regenerate(obj)


_PREVIEWS = None          # bpy.utils.previews collection (thumbnails of the presets)


def _load_previews():
    global _PREVIEWS
    _PREVIEWS = bpy.utils.previews.new()
    folder = os.path.join(os.path.dirname(__file__), "thumbs")
    for key in PRESETS:
        path = os.path.join(folder, key + ".png")
        if os.path.isfile(path):
            _PREVIEWS.load(key, path, "IMAGE")


def _free_previews():
    global _PREVIEWS
    if _PREVIEWS is not None:
        bpy.utils.previews.remove(_PREVIEWS)
        _PREVIEWS = None


class SG1Props(PropertyGroup):
    is_sculpture: BoolProperty(default=False)
    live: BoolProperty(name="Live update", default=True,
                       description="Recompute the sculpture while you move the sliders")
    animate: BoolProperty(name="Animation", default=False,
                          description="Recompute the sculpture at every frame, so that animated sliders "
                                      "(keyframes or drivers) change its shape. Uses the full detail when rendering")
    live_cap: BoolProperty(name="Limit live detail", default=True,
                           description="If the mesh would be too heavy, temporarily lowers the "
                                       "detail; 'Regenerate' always uses the full value")
    branches: IntProperty(name="Saddle branches", default=2, min=1, max=10, update=_on_change,
                          description="Number of saddle branches (2 = classic Scherk, 3 = monkey saddle)")
    storeys: IntProperty(name="Storeys (holes)", default=2, min=1, max=20, update=_on_change)
    detail: IntProperty(name="Grid detail", default=8, min=1, max=20, update=_on_change)
    height: FloatProperty(name="Storey height", default=1.5, min=0.0, max=20.0, step=5,
                          precision=2, update=_on_change)
    flange: FloatProperty(name="Flange width", default=1.5, min=0.0, max=5.0, step=5,
                          precision=2, update=_on_change,
                          description="As in the original, values below 0.7 are raised to 0.7")
    thickness: FloatProperty(name="Thickness", default=0.15, min=0.0, max=1.0, step=1,
                             precision=3, update=_on_change,
                             description="0 = thin (open) surface")
    rim_bulge: FloatProperty(name="Rim bulge", default=1.5, min=-1.0, max=4.0, step=1,
                             precision=2, update=_on_change,
                             description="0 flat, up to 0.1 sharp edges, up to 1 triangular, above 1 elliptical")
    twist: FloatProperty(name="Total twist", default=0.0, min=-900.0, max=1100.0, step=100,
                         precision=1, update=_on_change,
                         description="Total axial twist in degrees, spread over the storeys")
    warp: FloatProperty(name="Arc bend", default=0.0, min=0.0, max=1800.0, step=100,
                        precision=1, update=_on_change,
                        description="Degrees of bending (360 = closed ring, 720 = double closure)")
    azimuth: FloatProperty(name="Rotation about the axis", default=0.0, min=-360.0, max=360.0,
                           step=100, precision=1, update=_on_change)
    scale: FloatProperty(name="Scale", default=1.0, min=0.01, max=10.0, precision=2, update=_on_change)
    detail_long: IntProperty(name="Detail along the axis", default=0, min=0, max=40, update=_on_change,
                             description="Points along the length of the sculpture; 0 = same as grid detail. "
                                         "Raise it for smoother rings")
    taper: FloatProperty(name="Taper", default=0.0, min=-0.9, max=3.0, step=5, precision=2,
                         update=_on_change,
                         description="Flange width at the top relative to the bottom: 1 = double, -0.5 = half. "
                                     "The flange never gets narrower than 1 (or than its own width, if smaller), "
                                     "otherwise the surfaces cross. Not compatible with closed rings")
    swell: FloatProperty(name="Vase swell", default=0.0, min=-0.9, max=3.0, step=5, precision=2,
                         update=_on_change,
                         description="Widens (positive) or narrows (negative) the flange at mid-height, "
                                     "like a vase; ends unchanged")
    stretch_x: FloatProperty(name="Stretch X", default=1.0, min=0.05, max=10.0, precision=2, update=_on_change)
    stretch_y: FloatProperty(name="Stretch Y", default=1.0, min=0.05, max=10.0, precision=2, update=_on_change)
    stretch_z: FloatProperty(name="Stretch Z", default=1.0, min=0.05, max=10.0, precision=2, update=_on_change)
    scale_angle: FloatProperty(name="Stretch angle", default=0.0, min=-360.0, max=360.0, precision=1,
                               update=_on_change,
                               description="Rotates the axes of Stretch X and Y about the sculpture's axis. "
                                           "Hyperslice extension, saved at the end of the parameter file")
    uv_map: BoolProperty(name="UV map", default=True, update=_on_change,
                         description="Creates a UV map: along the sculpture (U) and around it (V), "
                                     "one 0-1 space for each of the five materials")
    uv_tiles: IntProperty(name="UV tiles", default=1, min=1, max=50, update=_on_change,
                          description="Repeats the texture this many times (texture_tiles of the parameter file)")
    perf_on: BoolProperty(name="Perforated", default=False, update=_on_perf,
                          description="Turns the surface into an irregular, Voronoi-like lattice, with modifiers "
                                      "(turn it off to get the solid sculpture back). The UV map is lost")
    perf_cells: IntProperty(name="Cells", default=800, min=50, max=6000, soft_max=6000, update=_on_perf,
                            description="Approximate number of cells of the lattice")
    perf_wire: FloatProperty(name="Wire thickness", default=0.07, min=0.005, max=1.0, step=1, precision=3,
                             subtype="DISTANCE", update=_on_perf, description="Thickness of the lattice wires")
    color_a: FloatVectorProperty(name="Side A", subtype="COLOR", size=4, min=0.0, max=1.0,
                                 default=(0.80, 0.80, 0.82, 1.0), update=_on_color)
    color_b: FloatVectorProperty(name="Side B", subtype="COLOR", size=4, min=0.0, max=1.0,
                                 default=(0.85, 0.55, 0.30, 1.0), update=_on_color)
    color_rim: FloatVectorProperty(name="Rim", subtype="COLOR", size=4, min=0.0, max=1.0,
                                   default=(0.55, 0.60, 0.70, 1.0), update=_on_color)
    color_lid_up: FloatVectorProperty(name="Top lid", subtype="COLOR", size=4, min=0.0, max=1.0,
                                      default=(0.45, 0.70, 0.50, 1.0), update=_on_color)
    reflective: BoolProperty(name="Reflective", default=False, update=_on_reflective,
                             description="Shiny, mirror-like surface (the environment map of Sculpture Generator 1)")
    color_lid_down: FloatVectorProperty(name="Bottom lid", subtype="COLOR", size=4, min=0.0, max=1.0,
                                        default=(0.65, 0.50, 0.75, 1.0), update=_on_color)
    preset: EnumProperty(name="Preset", items=[(k, v[0], "") for k, v in PRESETS.items()])
    last_detail: IntProperty(default=0)
    last_faces: IntProperty(default=0)


# --------------------------------------------------------------------------
# operatori
# --------------------------------------------------------------------------
def _apply_preset(props, key):
    was_live = props.live
    props.live = False
    props.stretch_x = props.stretch_y = props.stretch_z = 1.0
    for cname in MAT_PROPS:                      # colors go back to the defaults unless the preset has its own
        setattr(props, cname, tuple(props.bl_rna.properties[cname].default_array))
    props.reflective = False
    props.perf_on = False
    props.perf_cells = 800
    props.perf_wire = 0.07
    for k, val in PRESETS[key][1].items():
        setattr(props, k, val)
    props.detail_long = 0
    props.taper = 0.0
    props.swell = 0.0
    props.scale_angle = 0.0
    props.live = was_live


def _new_sculpture(context, preset="TORRE"):
    mesh = bpy.data.meshes.new("Hyperslice")
    obj = bpy.data.objects.new("Hyperslice", mesh)
    context.collection.objects.link(obj)
    obj.location = context.scene.cursor.location
    obj.sg1.is_sculpture = True
    _apply_preset(obj.sg1, preset)
    regenerate(obj, force_full=True)
    for o in context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    return obj


class SG1_OT_add(Operator):
    bl_idname = "mesh.sg1_add"
    bl_label = "Hyperslice"
    bl_description = "Adds a Scherk/Collins sculpture"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        _new_sculpture(context)
        return {"FINISHED"}


class SG1_OT_regen(Operator):
    bl_idname = "mesh.sg1_regen"
    bl_label = "Regenerate (full detail)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        o = context.active_object
        return o is not None and o.type == "MESH" and o.sg1.is_sculpture

    def execute(self, context):
        regenerate(context.active_object, force_full=True)
        return {"FINISHED"}


class SG1_OT_preset(Operator):
    bl_idname = "mesh.sg1_preset"
    bl_label = "Apply preset"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        o = context.active_object
        return o is not None and o.type == "MESH" and o.sg1.is_sculpture

    def execute(self, context):
        o = context.active_object
        _apply_preset(o.sg1, o.sg1.preset)
        regenerate(o, force_full=False)
        return {"FINISHED"}


def _icon(key):
    return _PREVIEWS[key].icon_id if (_PREVIEWS is not None and key in _PREVIEWS) else 0


def _preset_name(key):
    return bpy.app.translations.pgettext_iface(PRESETS[key][0])


class SG1_OT_pick_preset(Operator):
    bl_idname = "mesh.sg1_pick_preset"
    bl_label = "Apply preset"
    bl_description = "Applies this preset"
    bl_options = {"REGISTER", "UNDO"}

    key: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    @classmethod
    def description(cls, context, properties):
        key = properties.key
        if key not in PRESETS:
            return cls.bl_description
        tip = bpy.app.translations.pgettext_tip
        pr = PRESETS[key][1]
        n = PRESET_DEMO_N.get(key)
        head = tip("Séquin's demo {n}").format(n=n) if n else tip(PRESETS[key][0])
        body = tip("{b} branches, {s} storeys, bend {w}°, twist {t}°").format(
            b=pr["branches"], s=pr["storeys"], w=int(round(pr["warp"])), t=int(round(pr["twist"])))
        return head + ": " + body

    def execute(self, context):
        if self.key not in PRESETS:
            return {"CANCELLED"}
        o = context.active_object
        if o is not None and o.type == "MESH" and o.sg1.is_sculpture:
            o.sg1.preset = self.key
            _apply_preset(o.sg1, self.key)
            regenerate(o, force_full=False)
        else:
            obj = _new_sculpture(context, self.key)
            obj.sg1.preset = self.key
        return {"FINISHED"}


PRESET_LABEL_WIDTH = 14     # names are padded to this width so that every column is as wide as a thumbnail
PRESET_ICON_SCALE = 6.0     # size of every thumbnail (all thumbnails are square and the same size)


def _draw_grid(layout, keys, columns):
    """Preset grid: a column_flow whose cells are filled column by column, so that the
    items read row by row. Empty cells get an invisible icon of the same size, otherwise
    they would be shorter and shift the real cells."""
    rows = -(-len(keys) // columns)
    cells = list(keys) + [None] * (rows * columns - len(keys))
    flow = layout.column_flow(columns=columns, align=False)
    for c in range(columns):
        for r in range(rows):
            key = cells[r * columns + c]
            cell = flow.column(align=True)
            if key is None:
                cell.template_icon(icon_value=0, scale=PRESET_ICON_SCALE)
                cell.label(text=" ")
                continue
            cell.template_icon(icon_value=_icon(key), scale=PRESET_ICON_SCALE)
            cell.operator("mesh.sg1_pick_preset", text=_preset_name(key).center(PRESET_LABEL_WIDTH, "\u2002")).key = key


PRESET_SECTIONS = (("classic", "Classic sculptures", 4), ("demo", "Séquin's demos", 5), ("more", "More sculptures", 3), ("mine", "My presets", 5))


class SG1_OT_save_my_preset(Operator):
    bl_idname = "mesh.sg1_save_my_preset"
    bl_label = "Save as my preset"
    bl_description = ("Saves the current sculpture (parameters and colours) with a small picture in the list "
                      "'My presets'. A preset with the same name is replaced")
    bl_options = {"REGISTER"}

    name: StringProperty(name="Name", default="")

    @classmethod
    def poll(cls, context):
        o = context.active_object
        return o is not None and o.type == "MESH" and o.sg1.is_sculpture and o.mode == "OBJECT"

    def invoke(self, context, event):
        names = set(_my_names())
        n = 1
        while f"My sculpture {n}" in names:
            n += 1
        self.name = f"My sculpture {n}"
        return context.window_manager.invoke_props_dialog(self, width=320)

    def draw(self, context):
        self.layout.prop(self, "name")

    def execute(self, context):
        name = _clean_name(self.name)
        if not name:
            self.report({"ERROR"}, _rpt("Type a name for the preset"))
            return {"CANCELLED"}
        obj = context.active_object
        base = os.path.join(_my_dir(), name)
        try:
            with open(base + ".sg1", "w", newline="") as f:
                f.write(_param_text(obj.sg1))
        except OSError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        try:
            _render_thumbnail(obj, base + ".png")
        except Exception as e:
            self.report({"WARNING"}, _rpt("Preset saved, but the picture could not be made: {e}", e=e))
        else:
            self.report({"INFO"}, _rpt("Saved preset {name}", name=name))
        _refresh_my_previews()
        context.window_manager.sg1_open = "mine"
        return {"FINISHED"}


class SG1_OT_pick_mine(Operator):
    bl_idname = "mesh.sg1_pick_mine"
    bl_label = "Apply my preset"
    bl_description = "Applies this saved preset"
    bl_options = {"REGISTER", "UNDO"}

    name: StringProperty()

    def execute(self, context):
        path = os.path.join(_my_dir(), self.name + ".sg1")
        level, msg, _obj = _apply_param_file(context, path)
        if level == "ERROR":
            self.report({"ERROR"}, msg)
            return {"CANCELLED"}
        return {"FINISHED"}


class SG1_OT_delete_my_preset(Operator):
    bl_idname = "mesh.sg1_delete_my_preset"
    bl_label = "Delete this preset"
    bl_description = "Deletes this saved preset (the parameter file and its picture)"
    bl_options = {"REGISTER"}

    name: StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        base = os.path.join(_my_dir(), self.name)
        for ext in (".sg1", ".png"):
            try:
                os.remove(base + ext)
            except OSError:
                pass
        if _MY_PREVIEWS is not None and self.name in _MY_PREVIEWS:
            pass            # the picture stays in memory until Blender is closed; it is just no longer shown
        self.report({"INFO"}, _rpt("Preset {name} deleted", name=self.name))
        return {"FINISHED"}


def _draw_mine(layout, columns=5):
    names = _my_names()
    if not names:
        layout.label(text="No saved presets yet: use \"Save as my preset\" in the panel.")
        return
    rows = -(-len(names) // columns)
    cells = names + [None] * (rows * columns - len(names))
    flow = layout.column_flow(columns=columns, align=False)
    for c in range(columns):
        for r in range(rows):
            n = cells[r * columns + c]
            cell = flow.column(align=True)
            if n is None:
                cell.template_icon(icon_value=0, scale=PRESET_ICON_SCALE)
                cell.label(text=" ")
                continue
            cell.template_icon(icon_value=_my_icon(n), scale=PRESET_ICON_SCALE)
            row = cell.row(align=True)
            row.operator("mesh.sg1_pick_mine", text=n.center(PRESET_LABEL_WIDTH - 3, "\u2002")).name = n
            row.operator("mesh.sg1_delete_my_preset", text="", icon="TRASH").name = n


class SG1_PT_presets(Panel):
    """Preset picker, shown as a popover (not a menu): in a menu Blender keeps the last button highlighted
    when the cursor moves over a non-button area, so a click on a thumbnail could trigger the wrong preset.
    Only one of the three sections is open at a time (wm.sg1_open)."""
    bl_label = "Preset"
    bl_idname = "SG1_PT_presets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"
    bl_ui_units_x = 40

    def draw(self, context):
        lay = self.layout
        wm = context.window_manager
        lay.label(text="Preset")
        for gid, label, columns in PRESET_SECTIONS:
            is_open = wm.sg1_open == gid
            lay.prop_enum(wm, "sg1_open", gid, text=label, icon="TRIA_DOWN" if is_open else "TRIA_RIGHT")
            if is_open:
                if gid == "mine":
                    _draw_mine(lay, columns)
                else:
                    _draw_grid(lay, PRESET_GROUPS[gid], columns)


class SG1_OT_open_presets(Operator):
    bl_idname = "mesh.sg1_open_presets"
    bl_label = "Preset"
    bl_description = "Choose a preset"

    def execute(self, context):
        _refresh_my_previews()
        context.window_manager.sg1_open = "classic"      # always start from the classic sculptures
        bpy.ops.wm.call_panel("INVOKE_DEFAULT", name="SG1_PT_presets", keep_open=True)
        return {"FINISHED"}


def _open_edges(obj):
    """Open or non-manifold edges of the mesh as it will be exported (modifiers applied)."""
    import bmesh
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    try:
        bm = bmesh.new()
        bm.from_mesh(me)
        bad = sum(1 for e in bm.edges if len(e.link_faces) != 2)
        bm.free()
    finally:
        ev.to_mesh_clear()
    return bad


class SG1_OT_export_stl(Operator):
    bl_idname = "mesh.sg1_export_stl"
    bl_label = "Export STL (for 3D printing)"
    bl_description = ("Exports the active mesh as a binary STL, scaled so that its largest dimension is the "
                      "chosen size in millimetres (STL files have no units: slicers read the numbers as mm)")
    bl_options = {"REGISTER"}

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.stl", options={"HIDDEN"})
    check_existing: BoolProperty(default=True, options={"HIDDEN"})   # red file name + warning if the file exists
    size_mm: FloatProperty(name="Largest dimension (mm)", default=100.0, min=0.0, max=10000.0, precision=1,
                           description="Size of the printed sculpture. 0 = no scaling (1 Blender unit = 1 mm)")

    @classmethod
    def poll(cls, context):
        o = context.active_object
        return o is not None and o.type == "MESH" and o.mode == "OBJECT"

    def invoke(self, context, event):
        self.filepath = context.active_object.name.replace(" ", "_") + ".stl"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def draw(self, context):
        self.layout.prop(self, "size_mm")

    def execute(self, context):
        import bmesh
        obj = context.active_object
        if not hasattr(bpy.ops.wm, "stl_export"):
            self.report({"ERROR"}, _rpt("This Blender version has no STL exporter"))
            return {"CANCELLED"}
        path = bpy.path.ensure_ext(self.filepath, ".stl")
        biggest = max(obj.dimensions) if len(obj.data.vertices) else 0.0
        scale = (self.size_mm / biggest) if (self.size_mm > 0.0 and biggest > 0.0) else 1.0
        bad = _open_edges(obj)
        sel = [o for o in context.view_layer.objects if o.select_get()]
        try:
            for o in sel:
                o.select_set(False)
            obj.select_set(True)
            bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, global_scale=scale,
                                  use_scene_unit=False, ascii_format=False, apply_modifiers=True)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        finally:
            obj.select_set(False)
            for o in sel:
                o.select_set(True)
        msg = _rpt("Exported {name}", name=os.path.basename(path))
        if self.size_mm > 0.0:
            msg += _rpt(": largest dimension {mm} mm", mm=round(self.size_mm, 1))
        if bad:
            self.report({"WARNING"}, msg + " - " + _rpt("{n} open edges (mesh is not watertight)", n=bad))
        else:
            self.report({"INFO"}, msg)
        return {"FINISHED"}


class SG1_OT_freeze(Operator):
    bl_idname = "mesh.sg1_freeze"
    bl_label = "Freeze (plain mesh)"
    bl_description = "Regenerates at full detail and turns the mesh into an ordinary editable / exportable mesh"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        o = context.active_object
        return o is not None and o.type == "MESH" and o.sg1.is_sculpture

    def execute(self, context):
        o = context.active_object
        regenerate(o, force_full=True)
        o.sg1.is_sculpture = False
        self.report({"INFO"}, _rpt("Sculpture frozen: it is now a plain mesh"))
        return {"FINISHED"}


class SG1_OT_check(Operator):
    bl_idname = "mesh.sg1_check"
    bl_label = "Check watertightness (for 3D printing)"
    bl_description = "Counts open or non-manifold edges of the mesh"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        o = context.active_object
        return o is not None and o.type == "MESH"

    def execute(self, context):
        import bmesh
        bad = _open_edges(context.active_object)
        if bad:
            self.report({"WARNING"}, _rpt("{n} open edges (mesh is not watertight)", n=bad))
        else:
            self.report({"INFO"}, _rpt("Mesh is closed and manifold: ready for STL export"))
        return {"FINISHED"}


# --------------------------------------------------------------------------
# pannello
# --------------------------------------------------------------------------
PARAM_KEYS = ("branches", "storeys", "height", "flange", "thickness", "rim_bulge", "warp", "twist",
              "azimuth", "detail", "scale", "stretch_x", "stretch_y", "stretch_z", "detail_long", "taper", "swell",
              "scale_angle", "reflective", "uv_tiles", "perf_on", "perf_cells", "perf_wire")


def _param_text(p):
    colors = {n: tuple(getattr(p, n)) for n in MAT_PROPS}
    return sg1_io.format_file({k: getattr(p, k) for k in PARAM_KEYS}, colors)


def _apply_param_file(context, path):
    """Reads a parameter file into the active sculpture (or a new one). Returns (level, message, obj)."""
    try:
        values, colors, extra, ignored = sg1_io.parse(path)
    except sg1_io.NotParamFile:
        return ("ERROR", os.path.basename(path) + ": " +
                _rpt("not a Sculpture Generator parameter file (first line '{header}' missing)",
                     header=sg1_io.HEADER), None)
    except (OSError, ValueError) as e:
        return "ERROR", f"{os.path.basename(path)}: {e}", None
    o = context.active_object
    if o is not None and o.type == "MESH" and o.sg1.is_sculpture:
        obj = o
    else:
        obj = _new_sculpture(context)
        obj.name = os.path.splitext(os.path.basename(path))[0]
    p = obj.sg1
    was_live = p.live
    p.live = False
    clamped = []
    p.detail_long = 0
    p.scale = 1.0
    p.taper = 0.0
    p.swell = 0.0
    p.scale_angle = 0.0
    p.perf_on = False
    p.perf_cells = 800
    p.perf_wire = 0.07
    for name, val in values.items():
        rna = p.bl_rna.properties[name]
        if rna.type == "BOOLEAN":
            setattr(p, name, bool(val))
            continue
        lo, hi = rna.hard_min, rna.hard_max
        v = min(max(val, lo), hi)
        if v != val:
            clamped.append(f"{name} {val:g} -> {v:g}")
        setattr(p, name, v)
    for name, col in colors.items():
        setattr(p, name, col)
    p.live = was_live
    regenerate(obj, force_full=True)
    msg = _rpt("Read {name}", name=os.path.basename(path))
    if ignored:
        msg += " " + _rpt("({n} texture/background/view lines ignored)", n=ignored)
    if clamped:
        msg += "; " + _rpt("values brought within limits:") + " " + ", ".join(clamped)
    return ("WARNING" if clamped else "INFO"), msg, obj


# --------------------------------------------------------------------------
# my presets: files in the user's config folder, so that they survive reinstalling the add-on
# --------------------------------------------------------------------------
_MY_PREVIEWS = None


def _my_dir():
    pkg = __package__ or ""
    if pkg.startswith("bl_ext."):       # installed as an extension: its own user folder, kept when updating
        return bpy.utils.extension_path_user(pkg, path="presets", create=True)
    return bpy.utils.user_resource("CONFIG", path="sculpture_sg1", create=True)


def _my_names():
    try:
        return sorted((f[:-4] for f in os.listdir(_my_dir()) if f.lower().endswith(".sg1")), key=str.lower)
    except OSError:
        return []


def _refresh_my_previews():
    if _MY_PREVIEWS is None:
        return
    _MY_PREVIEWS.clear()          # load() raises KeyError if a name is already there: reload everything
    d = _my_dir()
    for n in _my_names():
        png = os.path.join(d, n + ".png")
        if os.path.isfile(png):
            _MY_PREVIEWS.load(n, png, "IMAGE", force_reload=True)


def _my_icon(name):
    return _MY_PREVIEWS[name].icon_id if (_MY_PREVIEWS is not None and name in _MY_PREVIEWS) else 0


def _clean_name(name):
    import re
    name = re.sub(r'[\\/:*?"<>|]', "", name).strip().strip(".")
    return name[:40]


def _render_thumbnail(obj, path, size=192):
    """Small colour picture of the sculpture, made in a temporary scene (the user's scene is not touched)."""
    from mathutils import Vector
    scene = bpy.data.scenes.new("sg1_thumb")
    cam_data = bpy.data.cameras.new("sg1_thumb")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("sg1_thumb", cam_data)
    world = bpy.data.worlds.new("sg1_thumb")
    try:
        scene.collection.objects.link(obj)
        scene.collection.objects.link(cam)
        scene.camera = cam
        scene.world = world
        world.color = (0.945, 0.935, 0.915)
        r = scene.render
        r.engine = "BLENDER_WORKBENCH"
        r.resolution_x = r.resolution_y = size
        r.resolution_percentage = 100
        r.image_settings.file_format = "PNG"
        r.image_settings.color_mode = "RGB"
        r.filepath = path
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
        scene.display.render_aa = "8"
        scene.view_settings.view_transform = "Standard"
        corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        center = sum(corners, Vector()) / 8.0
        radius = max((c - center).length for c in corners) or 1.0
        d = Vector((0.8, -1.0, 0.45)).normalized()
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        cam.location = center + d * radius * 4.0
        m = cam.rotation_euler.to_matrix()
        right, up = m.col[0], m.col[1]
        ext = max(max(abs((c - center).dot(right)), abs((c - center).dot(up))) for c in corners)
        cam_data.ortho_scale = ext * 2.0 * 1.12
        cam_data.clip_end = radius * 20.0
        bpy.ops.render.render(write_still=True, scene=scene.name)
    finally:
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(cam)
        bpy.data.cameras.remove(cam_data)
        bpy.data.worlds.remove(world)


class SG1_OT_import(Operator):
    bl_idname = "mesh.sg1_import_params"
    bl_label = "Import parameters"
    bl_description = ("Reads a Sculpture Generator parameter file (.sg1 or .txt). "
                      "If a sculpture is selected it modifies it, otherwise it creates a new one")
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.sg1;*.txt", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        level, msg, _obj = _apply_param_file(context, self.filepath)
        self.report({level}, msg)
        return {"FINISHED"} if level != "ERROR" else {"CANCELLED"}


class SG1_OT_export(Operator):
    bl_idname = "mesh.sg1_export_params"
    bl_label = "Save parameters"
    bl_description = ("Writes the parameters in the Sculpture Generator format. If you give "
                      "no extension, .sg1 is added (for the original program type it "
                      "yourself in the name, e.g. .txt or .sg1)")
    bl_options = {"REGISTER"}

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.sg1;*.txt", options={"HIDDEN"})
    check_existing: BoolProperty(default=True, options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        o = context.active_object
        return o is not None and o.type == "MESH" and o.sg1.is_sculpture

    def invoke(self, context, event):
        o = context.active_object
        self.filepath = o.name.replace(" ", "_") + sg1_io.EXT
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        p = context.active_object.sg1
        path = self.filepath
        if not os.path.splitext(path)[1]:
            path += sg1_io.EXT
        text = _param_text(p)
        try:
            with open(path, "w", newline="") as f:
                f.write(text)
        except OSError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, _rpt("Saved {name}", name=os.path.basename(path)))
        return {"FINISHED"}



def _open_edges(obj):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    n = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    bm.free()
    return n


def _valid_twist(rng, branches, storeys, lo=-360.0, hi=720.0):
    step = 360.0 / branches
    off = (180.0 / branches) if storeys % 2 else 0.0
    base = (-off) % step
    k0 = math.ceil((lo - base) / step)
    k1 = math.floor((hi - base) / step)
    return base + rng.randint(k0, k1) * step


class SG1_OT_variant(Operator):
    bl_idname = "mesh.sg1_variant"
    bl_label = "Random variant"
    bl_description = ("Proposes new parameters (New) or small variations of the current ones (Tweak). "
                      "Discards combinations that do not close by itself. Undo with Ctrl+Z")
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(name="Type", items=[("NUOVA", "New", "Completely new parameters"),
                                            ("RITOCCO", "Tweak", "Small variations of the current values")],
                       default="NUOVA")
    seed: IntProperty(name="Seed", default=0,
                      description="0 = random; the same seed repeats the same variant")

    @classmethod
    def poll(cls, context):
        o = context.active_object
        return o is not None and o.type == "MESH" and o.sg1.is_sculpture

    def _clip(self, v, lo, hi):
        return max(lo, min(hi, v))

    def _propose(self, p, rng):
        if self.mode == "NUOVA":
            p.branches = rng.choice([2, 2, 2, 3, 3, 4])
            p.storeys = rng.choice([2, 3, 3, 4, 5, 6])
            p.warp = rng.choice([0, 0, 180, 360, 360, 360, 720])
            p.height = round(rng.uniform(0.8, 3.5), 2)
            p.flange = round(self._clip(rng.uniform(0.6, 1.1) * p.height, 0.8, 4.0), 2)
            p.thickness = round(rng.uniform(0.04, 0.15), 2)
            p.rim_bulge = round(rng.choice([0.0, 1.0, 1.5, 2.0, rng.uniform(0.3, 2.5)]), 2)
            if p.warp in (360, 720, 1080):
                p.twist = _valid_twist(rng, p.branches, p.storeys)
            else:
                p.twist = float(rng.choice([0, 0, 90, 180, 270, 360, 540]))
            p.azimuth = float(rng.randrange(-180, 181, 5))
            p.taper = round(rng.uniform(-0.5, 1.0), 2) if (p.warp == 0 and rng.random() < 0.3) else 0.0
            p.swell = round(rng.uniform(-0.4, 1.2), 2) if rng.random() < 0.3 else 0.0
        else:
            p.height = round(self._clip(p.height * rng.uniform(0.9, 1.1), 0.1, 20.0), 2)
            p.flange = round(self._clip(p.flange * rng.uniform(0.9, 1.1), 0.0, 5.0), 2)
            p.thickness = round(self._clip(p.thickness * rng.uniform(0.9, 1.1), 0.0, 1.0), 3)
            p.rim_bulge = round(self._clip(p.rim_bulge + rng.uniform(-0.2, 0.2), -1.0, 4.0), 2)
            p.azimuth = float(self._clip(p.azimuth + rng.uniform(-15, 15), -360, 360))
            if p.warp in (360.0, 720.0, 1080.0):
                step = 360.0 / p.branches
                p.twist = float(self._clip(p.twist + rng.choice([-step, 0.0, 0.0, step]), -900, 1100))
            else:
                p.twist = float(self._clip(p.twist + rng.uniform(-30, 30), -900, 1100))
                if abs(p.taper) > 0:
                    p.taper = round(self._clip(p.taper + rng.uniform(-0.1, 0.1), -0.9, 3.0), 2)
            p.swell = round(self._clip(p.swell + rng.uniform(-0.1, 0.1), -0.9, 3.0), 2)

    def execute(self, context):
        obj = context.active_object
        p = obj.sg1
        rng = random.Random(self.seed or None)
        was_live = p.live
        p.live = False
        keys = ("branches", "storeys", "warp", "height", "flange", "thickness", "rim_bulge",
                "twist", "azimuth", "taper", "swell")
        saved = {k: getattr(p, k) for k in keys}
        ok = False
        for _ in range(15):
            self._propose(p, rng)
            regenerate(obj, force_full=False)
            if p.thickness < 1e-4 or _open_edges(obj) == 0:
                ok = True
                break
        if not ok:
            for k, v in saved.items():
                setattr(p, k, v)
            regenerate(obj, force_full=False)
            self.report({"WARNING"}, _rpt("No valid variant found: I left the previous values"))
        p.live = was_live
        return {"FINISHED"}


class SG1_PT_panel(Panel):
    bl_label = "Hyperslice"
    bl_idname = "SG1_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Hyperslice"

    def draw(self, context):
        lay = self.layout
        o = context.active_object
        if context.mode == "EDIT_MESH":
            b = lay.box()
            b.alert = True
            b.label(text="Edit Mode: parameters off", icon="ERROR")
            b.label(text="Go back to Object Mode.")
            lay = lay.column()
            lay.enabled = False
        lay.operator("mesh.sg1_add", icon="MESH_TORUS")
        if o is None or o.type != "MESH" or not o.sg1.is_sculpture:
            lay.label(text="Select a sculpture to edit it.")
            lay.operator("mesh.sg1_open_presets", text="Add from preset", icon="PRESET")
            lay.operator("mesh.sg1_import_params", icon="IMPORT")
            if o is not None and o.type == "MESH":      # shown only when there is a mesh to check
                lay.operator("mesh.sg1_check", icon="CHECKMARK")
                lay.operator("mesh.sg1_export_stl", icon="EXPORT")
            return
        p = o.sg1
        cur = p.preset if p.preset in PRESETS else "TORRE"
        lay.operator("mesh.sg1_open_presets", text=_preset_name(cur), icon_value=_icon(cur))
        lay.operator("mesh.sg1_save_my_preset", icon="ADD")
        col = lay.column(align=True)
        col.prop(p, "branches")
        col.prop(p, "storeys")
        col.prop(p, "detail")
        col = lay.column(align=True)
        col.prop(p, "height")
        col.prop(p, "flange")
        col.prop(p, "thickness")
        col.prop(p, "rim_bulge")
        col = lay.column(align=True)
        col.prop(p, "twist")
        col.prop(p, "warp")
        col.prop(p, "azimuth")
        col.prop(p, "scale")
        hint = _closure_hint(p)
        if hint:
            b = lay.box()
            b.alert = True
            b.label(text="The ends do not match.", icon="ERROR")
            b.label(text=_fmt("Twist that closes: {a:g} or {b:g}", a=hint[0], b=hint[1]))
        if _taper_ring_problem(p):
            b = lay.box()
            b.alert = True
            b.label(text="Taper and closed ring:", icon="ERROR")
            b.label(text="the ends cannot match")
        col = lay.column(align=True)
        col.prop(p, "detail_long")
        col.prop(p, "taper")
        col.prop(p, "swell")
        col = lay.column(align=True)
        col.prop(p, "stretch_x")
        col.prop(p, "stretch_y")
        col.prop(p, "stretch_z")
        col.prop(p, "scale_angle")
        box = lay.box()
        box.label(text="Colors")
        for pname in MAT_PROPS:
            box.prop(p, pname)
        box.prop(p, "reflective")
        box = lay.box()
        box.prop(p, "perf_on")
        if p.perf_on:
            col = box.column(align=True)
            col.prop(p, "perf_cells")
            col.prop(p, "perf_wire")
            if p.perf_cells > PERF_CELLS_WARN:
                box.label(text="Many cells: slow and heavy", icon="ERROR")
                box.label(text="Turn on Perforated last")
        row = lay.row(align=True)
        row.enabled = not p.perf_on
        row.prop(p, "uv_map")
        sub = row.row(align=True)
        sub.enabled = p.uv_map
        sub.prop(p, "uv_tiles", text="Tiles")
        if p.perf_on:
            lay.label(text="UV map: lost with Perforated", icon="INFO")
        lay.separator()
        lay.prop(p, "live")
        lay.prop(p, "live_cap")
        lay.prop(p, "animate")
        if p.live_cap and p.last_detail and p.last_detail < p.detail:
            lay.label(text=_fmt("Preview at detail {d}: press Regenerate", d=p.last_detail), icon="INFO")
        lay.label(text=_fmt("Faces: {n}", n=p.last_faces))
        lay.operator("mesh.sg1_regen", icon="FILE_REFRESH")
        lay.operator("mesh.sg1_check", icon="CHECKMARK")
        lay.operator("mesh.sg1_export_stl", icon="EXPORT")
        lay.operator("mesh.sg1_freeze", icon="FREEZE")
        row = lay.row(align=True)
        op = row.operator("mesh.sg1_variant", text="Random variant", icon="FILE_REFRESH")
        op.mode = "NUOVA"
        op.seed = 0
        op = row.operator("mesh.sg1_variant", text="Tweak")
        op.mode = "RITOCCO"
        op.seed = 0
        row = lay.row(align=True)
        row.operator("mesh.sg1_import_params", text="Import .sg1", icon="IMPORT")
        row.operator("mesh.sg1_export_params", text="Save .sg1", icon="EXPORT")


def _menu_add(self, context):
    self.layout.operator("mesh.sg1_add", text="Hyperslice", icon="MESH_TORUS")


classes = (SG1Props, SG1_OT_add, SG1_OT_regen, SG1_OT_preset, SG1_OT_pick_preset,
           SG1_OT_save_my_preset, SG1_OT_pick_mine, SG1_OT_delete_my_preset, SG1_OT_open_presets, SG1_PT_presets, SG1_OT_export_stl, SG1_OT_freeze,
           SG1_OT_check, SG1_OT_import, SG1_OT_export, SG1_OT_variant, SG1_PT_panel)


# ----- Animazione: ricalcolo a ogni fotogramma -----------------------------
_RENDERING = False
_SIGS = {}


def _signature(obj, full):
    p = _params(obj.sg1)
    return (full,) + tuple(round(float(v), 6) for v in p.values())


@persistent
def _on_frame_change(scene, depsgraph=None):
    """Ricalcola le sculture con 'Animazione' attiva e parametri cambiati rispetto all'ultimo calcolo."""
    for obj in scene.objects:
        if obj.type != 'MESH' or obj.animation_data is None:
            continue
        props = obj.sg1
        if not (props.is_sculpture and props.animate):
            continue
        sig = _signature(obj, _RENDERING)
        key = obj.name_full
        if _SIGS.get(key) == sig:
            continue
        regenerate(obj, force_full=_RENDERING)
        _SIGS[key] = sig


@persistent
def _on_render_init(*args):
    global _RENDERING
    _RENDERING = True
    _SIGS.clear()


@persistent
def _on_render_end(*args):
    global _RENDERING
    _RENDERING = False
    _SIGS.clear()


@persistent
def _on_load(*args):
    _SIGS.clear()


_HANDLERS = (("frame_change_post", _on_frame_change), ("render_init", _on_render_init),
             ("render_post", _on_render_end), ("render_cancel", _on_render_end),
             ("render_complete", _on_render_end), ("load_post", _on_load))


def register():
    global _MY_PREVIEWS
    _load_previews()
    _MY_PREVIEWS = bpy.utils.previews.new()
    _refresh_my_previews()
    for name, fn in _HANDLERS:
        getattr(bpy.app.handlers, name).append(fn)
    bpy.app.translations.register(__name__, translations_it.TRANSLATIONS)
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Object.sg1 = PointerProperty(type=SG1Props)
    bpy.types.WindowManager.sg1_open = EnumProperty(
        items=[(g, l, "") for g, l, _c in PRESET_SECTIONS], default="classic", options={"SKIP_SAVE"})
    bpy.types.VIEW3D_MT_mesh_add.append(_menu_add)


def unregister():
    for name, fn in _HANDLERS:
        lst = getattr(bpy.app.handlers, name)
        while fn in lst:
            lst.remove(fn)
    bpy.types.VIEW3D_MT_mesh_add.remove(_menu_add)
    del bpy.types.Object.sg1
    del bpy.types.WindowManager.sg1_open
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.app.translations.unregister(__name__)
    _free_previews()
    global _MY_PREVIEWS
    if _MY_PREVIEWS is not None:
        bpy.utils.previews.remove(_MY_PREVIEWS)
        _MY_PREVIEWS = None


if __name__ == "__main__":
    register()
