# Hyperslice - (c) 2026 Costantino Vita ("Drakan"). SPDX-License-Identifier: GPL-3.0-or-later; see LICENSE.txt.
# Geometry ported from "Sculpture Generator 1" by Carlo H. Sequin (UC Berkeley),
# released under the GPL with his permission (e-mails of 2 and 18 November 2026). Not supported or endorsed by him.
"""
sg1_core.py - nucleo geometrico (solo numpy, nessuna dipendenza da Blender).

Porting in Python/numpy della costruzione geometrica di "Sculpture Generator 1"
di Carlo H. Séquin (UC Berkeley), file geom.c: torri di Scherk, rami a sella,
torsione per piano, profili del bordo, spessore, chiusura toroidale di Collins.

Convenzioni dell'originale mantenute:
  d  = detail,  D = d+1,  dd = 2d,  Dd = D+d,  DD = 2D
  indice i: 0 .. DD   (0 e DD sono i punti "rim", cioe' la direzione del bordo)
  indice j: 0 .. dd   (dal basso all'alto della "sella")
"""
import numpy as np
from math import pi, sqrt

KMID = 4
DMAX = 20

DEFAULTS = dict(
    branches=2, storeys=3, detail=6,
    height=1.0, flange=1.0, thickness=0.04, rim_bulge=0.0,
    twist=0.0, warp=0.0, azimuth=0.0, scale=1.0,
    stretch_x=1.0, stretch_y=1.0, stretch_z=1.0, stretch_angle=0.0,
    detail_long=0, taper=0.0, swell=0.0,
)


# --------------------------------------------------------------------------
# utilita'
# --------------------------------------------------------------------------
def _rot_z(P, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    x, y = P[..., 0], P[..., 1]
    out = P.copy()
    out[..., 0] = x * c - y * s
    out[..., 1] = x * s + y * c
    return out


def _rot_y(P, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    x, z = P[..., 0], P[..., 2]
    out = P.copy()
    out[..., 0] = x * c - z * s
    out[..., 2] = x * s + z * c
    return out


def _normalize(A):
    mag = np.linalg.norm(A, axis=-1, keepdims=True)
    mag = np.where(mag == 0.0, 1.0, mag)
    return A / mag


# --------------------------------------------------------------------------
# profilo del bordo (rim)  -  come in basearray()
# --------------------------------------------------------------------------
def rim_profile(trim, thick, d):
    """Ritorna kmax, wbulge, tbulge, wrimnorm, trimnorm (array di kmax+1)."""
    if trim == 0.0:
        kmax = 1
        wb = [0.0, 0.0]
        tb = [0.0, -2.0 * thick]
        wn = [1.0, 1.0]
        tn = [0.0, 0.0]
    elif 0.0 < trim <= 0.1:
        kmax = 2
        wb = [0.0, thick * trim, 0.0]
        tb = [0.0, -1.0 * thick, -2.0 * thick]
        wn = [1.0 - trim, 1.0, 1.0 - trim]
        tn = [trim * trim * thick * trim, 0.0, -trim * trim * thick * trim]
    elif 0.0 < trim <= 1.0:
        kmax = 3   # punto doppio al centro: spigolo vivo
        wb = [0.0, thick * trim, thick * trim, 0.0]
        tb = [0.0, -0.98 * thick, -1.02 * thick, -2.0 * thick]
        wn = [1.0, 1.0, 1.0, 1.0]
        tn = [trim, trim, -trim, -trim]
    else:      # profilo semicircolare / ellittico
        if d <= 3:
            kmax = 3
        elif d >= 2 * KMID:
            kmax = 2 * KMID
        else:
            kmax = d
        k = np.arange(kmax + 1)
        kappa = k * pi / kmax
        wb = thick * trim * np.sin(kappa)
        tb = thick * (np.cos(kappa) - 1.0)
        wn = np.sin(kappa)
        tn = trim * np.cos(kappa)
    return (kmax, np.asarray(wb, float), np.asarray(tb, float),
            np.asarray(wn, float), np.asarray(tn, float))


# --------------------------------------------------------------------------
# basearray(): la "sella" modello, riusata per tutti i rami e piani
# --------------------------------------------------------------------------
def row_heights(branches, dj):
    """h[j] normalizzato (-1..1) lungo la sella; dj = righe per meta' sella."""
    j = np.arange(2 * dj + 1)
    if branches == 1:
        return (j - dj) / float(dj)
    return np.sin(0.5 * pi * (j - dj) / float(dj))


def base_array(branches, d, dj, height, flange_rows, twirl, thick, trim):
    """d = punti per meta' larghezza, dj = righe per meta' altezza della sella,
    flange_rows = larghezza dell'ala per ogni riga (array dd+1)."""
    D = d + 1
    dd = 2 * dj
    Dd = D + d
    DD = 2 * D

    h = row_heights(branches, dj)
    z = height * (1.0 + h)
    fr = np.asarray(flange_rows, float)

    v = np.zeros((DD + 1, dd + 1, 3))
    v[:, :, 2] = z[None, :]

    if branches == 1:
        # pannello piatto, piegato di 90 gradi (poi raddrizzato dallo "squash")
        rimx = fr + trim * thick * sqrt(0.5)
        v[0, :, 0] = rimx
        for i in range(1, D + 1):
            v[i, :, 0] = fr * (D - i) / float(d)
        v[0:D + 1, :, 1] = -v[0:D + 1, :, 0]
        for i in range(D + 1, DD):
            v[i, :, 0] = fr * (i - D) / float(d)
        v[DD, :, 0] = rimx
        v[D + 1:DD + 1, :, 1] = v[D + 1:DD + 1, :, 0]
    else:
        fl = (fr * sqrt(2.0))[None, :]                          # (1, dd+1)
        flt = ((fr + thick * trim) * sqrt(2.0))[None, :]
        fl2, flt2 = fl * fl, flt * flt
        r2 = np.maximum(1.0 - h * h, 0.0)[None, :]              # (1, dd+1)
        ii = np.arange(2, D + 1)
        mi = ((D - ii) / float(d))[:, None]                     # (n, 1)
        mi2 = mi * mi
        x = (-mi2 * fl + np.sqrt(mi2 * (fl2 - r2) + r2)) / (1.0 - mi2)
        y = mi * (x - fl)
        v[2:D + 1, :, 0] = x
        v[2:D + 1, :, 1] = y
        x1 = (fl2 + r2) / (2.0 * fl)
        v[1, :, 0] = x1[0]
        v[1, :, 1] = (x1 - fl)[0]
        x0 = (flt2 + r2) / (2.0 * flt)
        v[0, :, 0] = x0[0]
        v[0, :, 1] = (x0 - flt)[0]
        # specchia la meta' sinistra verso destra
        for i in range(D + 1, DD + 1):
            v[i, :, 0] = v[DD - i, :, 0]
            v[i, :, 1] = -v[DD - i, :, 1]

    # restringimento delle iperboli (rami multipli) e torsione per piano
    squash = 2.0 / float(branches) - 1.0
    with np.errstate(divide="ignore", invalid="ignore"):
        beta = np.degrees(np.arctan(v[:, :, 1] / v[:, :, 0]))
    beta = np.where(v[:, :, 0] == 0.0, 0.0, beta)
    alfa = twirl * 0.5 * (1.0 + h)                      # (dd+1,)
    gamma = beta * squash + alfa[None, :]
    v = _rot_z(v, gamma)

    # ---- normali (superficie "esterna") -------------------------------
    m = np.zeros_like(v)

    def cr(a, b):
        return np.cross(a, b)

    # punti interni: j = 1..dd-1,  i = 1..Dd
    V = v[1:Dd + 1, 1:dd]
    edown = v[1:Dd + 1, 0:dd - 1] - V
    eup = v[1:Dd + 1, 2:dd + 1] - V
    eleft = v[0:Dd, 1:dd] - V
    eright = v[2:Dd + 2, 1:dd] - V
    s = cr(eright, eup) + cr(eup, eleft) + cr(eleft, edown) + cr(edown, eright)
    m[1:Dd + 1, 1:dd] = _normalize(s)

    # bordo inferiore j = 0 e superiore j = dd (esclusa la sella i = D)
    iis = np.array([i for i in range(1, Dd + 1) if i != D])
    for jx, top in ((0, False), (dd, True)):
        V = v[iis, jx]
        eleft = v[iis - 1, jx] - V
        eright = v[iis + 1, jx] - V
        if top:
            edown = v[iis, jx - 1] - V
            s = cr(eleft, edown) + cr(edown, eright)
        else:
            eup = v[iis, jx + 1] - V
            s = cr(eright, eup) + cr(eup, eleft)
        m[iis, jx] = _normalize(s)

    # punti di sella
    if branches == 1:
        m[D, 0] = (1.0, 0.0, 0.0)
        t = _rot_z(np.array([1.0, 0.0, 0.0]), twirl)
        m[D, dd] = t
    else:
        m[D, 0] = (0.0, 0.0, -1.0)
        m[D, dd] = (0.0, 0.0, 1.0)

    # normali "rim" (direzione del bordo, entro la superficie)
    m[0, :] = _normalize(v[1, :] - v[2, :])
    m[DD, :] = _normalize(v[Dd, :] - v[DD - 2, :])

    return h, v, m


# --------------------------------------------------------------------------
# generazione completa
# --------------------------------------------------------------------------
def estimate_faces(p):
    d = int(p["detail"])
    dj = int(p.get("detail_long", 0)) or d
    kmax = rim_profile(p["rim_bulge"], p["thickness"], d)[0]
    full = 8 * d * dj + 8 * dj * kmax
    return int(p["branches"] * p["storeys"] * full)


def generate(p, with_uv=False):
    """Ritorna (verts[N,3], quads[M,4], mat[M]); i vertici NON sono ancora
    saldati tra patch adiacenti (lo fa il chiamante con una "merge by distance").
    mat: 0 = lato A, 1 = lato B, 2 = bordo, 3 = tappo alto, 4 = tappo basso.
    Con with_uv=True ritorna anche uv[N,2] (una per vertice, prima della saldatura): ogni materiale
    ha il proprio spazio 0..1 (u lungo la scultura, v attorno), moltiplicato per p["uv_tiles"]."""
    q = dict(DEFAULTS)
    q.update(p)
    p = q
    branches = int(p["branches"])
    S = int(p["storeys"])
    d = int(p["detail"])
    height = float(p["height"])
    thick = float(p["thickness"])
    trim = float(p["rim_bulge"])
    warp = float(p["warp"])
    twist = float(p["twist"])
    azimuth = float(p["azimuth"])
    scale = float(p["scale"])
    stretch = np.array([p["stretch_x"], p["stretch_y"], p["stretch_z"]], float)

    dj = int(p["detail_long"]) or d
    taper = max(float(p["taper"]), -0.9)
    swell = max(float(p["swell"]), -0.9)

    D = d + 1
    dd = 2 * dj
    Dd = D + d
    DD = 2 * D

    ring = warp != 0.0
    sheet = thick < 1e-4
    thwarp = warp / float(S)
    twirl = twist / float(S)
    ringrad = S * height / pi
    archrad = (360.0 * S * height / warp / pi) if ring else 1.0

    h = row_heights(branches, dj)
    kmax, wb, tb, wn, tn = rim_profile(trim, thick, d)

    closed_ring = warp in (360.0, 720.0, 1080.0)

    V_list, H_list, Q_list, M_list, UV_list = [], [], [], [], []
    nv = 0

    def add_group(P, Hn, quads, mat, uv=None):
        nonlocal nv
        UV_list.append(uv.reshape(-1, 2) if uv is not None else np.zeros((P.reshape(-1, 3).shape[0], 2)))
        V_list.append(P.reshape(-1, 3))
        H_list.append(Hn.reshape(-1, 3))
        Q_list.append(quads + nv)
        M_list.append(np.full(len(quads), mat, dtype=np.int32))
        nv += P.reshape(-1, 3).shape[0]

    def grid_quads(A, B, r0, r1):
        """quad su una griglia A x B (indice a*B+b), per b in [r0, r1)."""
        a = np.arange(A - 1)[:, None]
        b = np.arange(r0, r1)[None, :]
        i00 = a * B + b
        i10 = (a + 1) * B + b
        i11 = (a + 1) * B + b + 1
        i01 = a * B + b + 1
        return np.stack([i00, i10, i11, i01], axis=-1).reshape(-1, 4)

    # ---- 1) tutte le patch (stor, ramo): posizioni e normali nel mondo ------
    patches = []
    for stor in range(S + 1):
        odd = stor % 2 == 1
        do_upper = stor <= S - 1
        do_lower = stor > 0
        r0 = 0 if do_lower else dj
        r1 = dd if do_upper else dj

        # larghezza dell'ala lungo la scultura (rastremazione e rigonfiamento)
        u = np.clip((stor - 0.5 + 0.5 * (1.0 + h)) / S, 0.0, 1.0)
        fscale = (1.0 + taper) ** (u - 0.5) * np.maximum(1.0 + swell * np.sin(pi * u), 0.1)
        flange_rows = np.maximum(float(p["flange"]) * fscale, 0.7)
        if abs(taper) > 1e-9 or abs(swell) > 1e-9:
            # a flange narrower than about 1 makes the saddles of neighbouring branches cross each other
            flange_rows = np.maximum(flange_rows, min(float(p["flange"]), 1.0))
        h, v, m = base_array(branches, d, dj, height, flange_rows, twirl, thick, trim)

        azims = twirl * (stor - 0.5) + azimuth
        if odd:
            azims += 180.0 / branches
        thetab = warp * (stor - 0.5) / S
        zbase = 2.0 * height * (stor - 0.5) - height * S
        if warp <= 360.0:
            zoffset = -(360.0 - warp) * height * S / 360.0
        else:
            zoffset = 0.0

        for branch in range(branches):
            azimb = azims + 360.0 * branch / branches

            O = v.copy()
            O[..., 2] = 0.0
            O = _rot_z(O, azimb)
            N = _rot_z(m, azimb)
            if not ring:
                O[..., 2] = v[..., 2] + zbase
            else:
                thetaj = thwarp * 0.5 * (1.0 + h)          # (dd+1,)
                O[..., 0] += archrad
                with np.errstate(divide="ignore", invalid="ignore"):
                    sc = archrad / O[..., 0]
                sc = np.where(np.isfinite(sc), sc, 1.0)
                N = N.copy()
                N[..., 2] *= sc
                N = _normalize(N)
                ang = (thetab + thetaj)[None, :]
                O = _rot_y(O, ang)
                N = _rot_y(N, ang)
                O[..., 2] += zoffset
                if warp <= 360.0:
                    O[..., 0] += -archrad + ringrad * warp / 360.0
                else:
                    O[..., 0] += -archrad + ringrad * 360.0 / warp
            patches.append(dict(stor=stor, odd=odd, r0=r0, r1=r1, O=O, N=N, branch=branch,
                                gpos=np.clip((stor - 0.5 + 0.5 * (1.0 + h)) / S, 0.0, 1.0)))

    # ---- 2) con ala variabile le normali sulle cuciture dei piani non sono
    #         piu' simmetriche: le ricalcolo sulla superficie sottile saldata
    if (abs(taper) > 1e-9 or abs(swell) > 1e-9) and not sheet:
        _merged_normals(patches, Dd, dd)

    # ---- 3) facce -----------------------------------------------------------
    for pt in patches:
        stor, odd, r0, r1, O, N = (pt[k] for k in ("stor", "odd", "r0", "r1", "O", "N"))
        br, gp = pt["branch"], pt["gpos"]                    # branch index, position along the sculpture
        tfl = np.arange(Dd) / max(Dd - 1, 1)                 # across the flange
        if odd:
            tfl = 1.0 - tfl

        # superficie esterna: spostata lungo la normale
        Oout = O.copy()
        Oout[1:DD] += thick * N[1:DD]

        sgn = -1.0 if (sheet and odd) else 1.0
        mat_out = 1 if odd else 0
        mat_in = 0 if odd else 1

        # --- esterna
        Pout = Oout[1:Dd + 1]                           # (Dd, dd+1, 3)
        Nout = N[1:Dd + 1]
        uv_face = np.stack([np.broadcast_to(gp[None, :], (Dd, dd + 1)),
                            np.broadcast_to(((br + tfl) / branches)[:, None], (Dd, dd + 1))], axis=-1)
        add_group(Pout, sgn * Nout, grid_quads(Dd, dd + 1, r0, r1), mat_out, uv_face)

        if sheet:
            continue

        # --- bordi sinistro e destro
        for side, (ic, ir) in enumerate(((1, 0), (Dd, DD))):
            L = (Oout[ic][:, None, :]
                 + tb[None, :, None] * N[ic][:, None, :]
                 + wb[None, :, None] * N[ir][:, None, :])        # (dd+1, kmax+1, 3)
            NR = _normalize(tn[None, :, None] * N[ic][:, None, :]
                            + wn[None, :, None] * N[ir][:, None, :])
            kk = np.arange(kmax + 1) / max(kmax, 1)
            uv_rim = np.stack([np.broadcast_to(gp[:, None], (dd + 1, kmax + 1)),
                               np.broadcast_to((br + 0.5 * side + 0.5 * kk) / branches, (dd + 1, kmax + 1))], axis=-1)
            add_group(L, NR, grid_quads(dd + 1, kmax + 1, 0, kmax)[
                _row_filter(dd + 1, kmax, r0, r1)], 2, uv_rim)

        # --- tappi alle estremita' (solo se non e' un anello chiuso)
        if (not closed_ring) and (stor == S or stor == 0):
            lid = np.zeros((Dd, kmax + 1, 3))
            step = np.arange(kmax + 1) * 2.0 * thick / kmax
            for i in range(2, Dd):
                lid[i - 1] = Oout[i, dj][None, :] - step[:, None] * N[i, dj][None, :]
            for (ic, ir, slot) in ((1, 0, 0), (Dd, DD, Dd - 1)):
                lid[slot] = (Oout[ic, dj][None, :]
                             + tb[:, None] * N[ic, dj][None, :]
                             + wb[:, None] * N[ir, dj][None, :])
            if stor == 0:
                nl = Oout[1:Dd + 1, dj] - Oout[1:Dd + 1, dj + 1]
            else:
                nl = Oout[1:Dd + 1, dj] - Oout[1:Dd + 1, dj - 1]
            nl = _normalize(nl)
            Hn = np.repeat(nl[:, None, :], kmax + 1, axis=1)
            kk = np.arange(kmax + 1) / max(kmax, 1)
            uv_lid = np.stack([np.broadcast_to(tfl[:, None], (Dd, kmax + 1)),
                               np.broadcast_to((br + kk) / branches, (Dd, kmax + 1))], axis=-1)
            add_group(lid, Hn, grid_quads(Dd, kmax + 1, 0, kmax), 3 if stor == S else 4, uv_lid)

        # --- superficie interna
        Pin = Oout[1:Dd + 1] - 2.0 * thick * N[1:Dd + 1]
        add_group(Pin, -Nout, grid_quads(Dd, dd + 1, r0, r1), mat_in, uv_face)

    verts = np.concatenate(V_list)
    hints = np.concatenate(H_list)
    quads = np.concatenate(Q_list)
    mats = np.concatenate(M_list)
    uvs = np.concatenate(UV_list)

    # orientamento coerente delle facce rispetto alla normale-guida
    P0, P1, P2, P3 = (verts[quads[:, k]] for k in range(4))
    fn = np.cross(P2 - P0, P3 - P1)
    fh = hints[quads].sum(axis=1)
    flip = np.einsum("ij,ij->i", fn, fh) < 0.0
    quads[flip] = quads[flip][:, [0, 3, 2, 1]]

    # elimina vertici non usati
    used = np.zeros(len(verts), bool)
    used[quads.ravel()] = True
    remap = -np.ones(len(verts), np.int64)
    remap[used] = np.arange(used.sum())
    verts = verts[used]
    uvs = uvs[used] * float(p.get("uv_tiles", 1))
    ang = float(p.get("stretch_angle", 0.0))
    if ang != 0.0:                       # sperimentale: assi dello stretch ruotati attorno all'asse z
        verts = _rot_z(verts, -ang)
        verts = _rot_z(verts * (scale * stretch), ang)
    else:
        verts = verts * (scale * stretch)
    quads = remap[quads]
    if with_uv:
        return verts, quads.astype(np.int32), mats, uvs
    return verts, quads.astype(np.int32), mats


def _weld(points, tol):
    """Indice del vertice saldato per ogni punto (distanza < tol/2 => stesso indice).
    Usa 8 griglie sfalsate e propaga le etichette: nessun problema ai bordi delle celle."""
    n = len(points)
    labels = np.arange(n)
    keys = []
    for sx in (0.0, 0.5):
        for sy in (0.0, 0.5):
            for sz in (0.0, 0.5):
                k = np.floor(points / tol + np.array([sx, sy, sz])).astype(np.int64)
                _, inv = np.unique(k, axis=0, return_inverse=True)
                keys.append(inv.reshape(-1))
    for _ in range(8):
        old = labels.copy()
        for inv in keys:
            m = np.full(inv.max() + 1, n, dtype=np.int64)
            np.minimum.at(m, inv, labels)
            labels = m[inv]
        if np.array_equal(old, labels):
            break
    _, uid = np.unique(labels, return_inverse=True)
    return uid.reshape(-1)


def _merged_normals(patches, Dd, dd):
    """Sostituisce le normali interne (i=1..Dd) di ogni patch con quelle della
    superficie sottile saldata: coincidono sulle cuciture tra i piani, anche nelle
    chiusure con torsione (dove la superficie non e' orientabile)."""
    nrows = dd + 1
    per = Dd * nrows
    pts = np.concatenate([pt["O"][1:Dd + 1].reshape(-1, 3) for pt in patches])
    ext = float(np.ptp(pts, axis=0).max()) or 1.0
    uid = _weld(pts, 1e-5 * ext)
    nu = uid.max() + 1

    # normali di faccia, orientate verso l'esterno della propria patch
    faces = []
    for k, pt in enumerate(patches):
        base = k * per
        A = np.arange(Dd - 1)[:, None]
        B = np.arange(pt["r0"], pt["r1"])[None, :]
        q = np.stack([A * nrows + B, (A + 1) * nrows + B, (A + 1) * nrows + B + 1,
                      A * nrows + B + 1], axis=-1).reshape(-1, 4)
        P = pt["O"][1:Dd + 1].reshape(-1, 3)
        fn = np.cross(P[q[:, 2]] - P[q[:, 0]], P[q[:, 3]] - P[q[:, 1]])
        hint = pt["N"][1:Dd + 1].reshape(-1, 3)[q].sum(axis=1)
        fn = np.where((np.einsum("ij,ij->i", fn, hint) < 0.0)[:, None], -fn, fn)
        faces.append((uid[base + q], fn))

    # direzione di riferimento per ogni vertice saldato (un qualunque contributo)
    ref = np.zeros((nu, 3))
    for ids, fn in faces:
        for c in range(4):
            ref[ids[:, c]] = fn
    # somma allineata: sulle cuciture le due patch hanno normali opposte
    acc = np.zeros((nu, 3))
    for ids, fn in faces:
        for c in range(4):
            sgn = np.where(np.einsum("ij,ij->i", fn, ref[ids[:, c]]) < 0.0, -1.0, 1.0)
            np.add.at(acc, ids[:, c], fn * sgn[:, None])
    nv = _normalize(acc)

    for k, pt in enumerate(patches):
        nvp = nv[uid[k * per:(k + 1) * per]].reshape(Dd, nrows, 3)
        N = pt["N"]
        loc = N[1:Dd + 1]
        sgn = np.where(np.einsum("ijk,ijk->ij", nvp, loc) < 0.0, -1.0, 1.0)
        new = nvp * sgn[..., None]
        used = np.zeros(nrows, bool)
        used[pt["r0"]:pt["r1"] + 1] = True
        N[1:Dd + 1, used] = new[:, used]
        pt["N"] = N


def _row_filter(nrows, kmax, r0, r1):
    """Maschera per le quad di una griglia (nrows x kmax+1) costruita con
    grid_quads(nrows, kmax+1, 0, kmax): serve solo per tenere le righe j in
    [r0, r1). L'ordine di grid_quads e' (a, b) con a = riga j, b = k."""
    a = np.arange(nrows - 1)[:, None] * np.ones((1, kmax), int)
    return ((a >= r0) & (a < r1)).ravel()
