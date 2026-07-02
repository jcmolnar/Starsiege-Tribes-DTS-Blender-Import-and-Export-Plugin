"""DTS round-trip regression test.

Imports a .dts into Blender via this addon, exports it back out, then compares
the original and round-tripped files. Use it to prove a model still
round-trips before/after a change -- especially weapons, which regressed
historically.

Two tiers of checks:

  FAIL -- preservation invariants. Anything the engine depends on that a
    round-trip must keep: structural counts, node hierarchy, per-node bind
    (default) transforms, sequence names + cyclic flags, object->node
    bindings, per-mesh geometry (verts/faces/frames, per-frame decoded
    spatial bounds, face-material histograms, UV extents), and material
    map filenames.

  WARN -- printed but non-fatal. Differences a correct exporter may
    legitimately introduce: de-duplicated transforms/texverts/keyframes,
    regenerated subsequence layouts, small duration/priority drift.
    These never fail the test, so custom animations and new-model
    workflows don't produce false failures.

Numeric comparisons use tolerances matched to the format's quantization
(quat16 = 1/32767 steps; packed vertices = frame_scale-sized steps), so
legitimate re-quantization noise passes while real corruption fails.

Run (folder name has spaces, so run via Blender, not bare python):

    blender --background --factory-startup \
        --python tests/roundtrip_regression.py -- <input.dts> [output.dts]

Pass the input as an ABSOLUTE path (Blender resolves relative texture paths
against its own CWD). If output.dts is omitted, a temp file is used.
Exit code is non-zero on FAIL.

No .dts fixture is committed (test assets stay local). Point it at any local
DTS, e.g. the gitignored Axe.dts.
"""
import bpy, sys, os, re, tempfile, shutil, traceback

# --- locate the addon source (parent dir of tests/) and stage a temp package ---
ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _stage_package():
    """Copy the addon .py/.ksy into a temp package with an importable name.

    The installed folder is "Tribes DTS Blender" (spaces) which Python can't
    import directly, so we mirror the sources into tribes_dts_test/.
    """
    tmp = tempfile.mkdtemp(prefix="tribes_dts_test_")
    pkg = os.path.join(tmp, "tribes_dts_test")
    os.makedirs(pkg)
    for fn in os.listdir(ADDON_DIR):
        if fn.endswith(".py") or fn.endswith(".ksy"):
            shutil.copy(os.path.join(ADDON_DIR, fn), os.path.join(pkg, fn))
    sys.path.insert(0, tmp)
    return tmp, pkg

def _parse_args():
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    if not args:
        print("FAIL: no input .dts given. Pass it after '--'.")
        sys.exit(2)
    src = os.path.abspath(args[0])
    dst = os.path.abspath(args[1]) if len(args) > 1 else os.path.join(
        tempfile.gettempdir(), "dts_roundtrip_out.dts")
    return src, dst


# --- decoding helpers -------------------------------------------------------

def norm_name(n):
    """Normalize a DTS/Blender name for comparison.

    Strips the fixed-width null padding, lowercases, and drops a Blender
    .001-style duplicate suffix (the importer must rename colliding nodes,
    which would otherwise false-fail name-keyed comparisons).
    """
    if isinstance(n, bytes):
        n = n.split(b'\x00')[0].decode('ascii', 'ignore')
    n = n.split('\x00')[0].strip().lower()
    return re.sub(r'\.\d+$', '', n)

def _get(s, *names):
    """First non-empty attribute from a list of version-variant field names."""
    for nm in names:
        v = getattr(s, nm, None)
        if v:
            return v
    return []

def decode_quat(q):
    """quat16 -> normalized float tuple, sign-canonicalized (q == -q)."""
    x, y, z, w = q.x / 32767.0, q.y / 32767.0, q.z / 32767.0, q.w / 32767.0
    mag = (x * x + y * y + z * z + w * w) ** 0.5 or 1.0
    x, y, z, w = x / mag, y / mag, z / mag, w / mag
    # canonical sign: first nonzero component positive
    for c in (w, z, y, x):
        if abs(c) > 1e-6:
            if c < 0:
                x, y, z, w = -x, -y, -z, -w
            break
    return (x, y, z, w)

def transform_close(a, b, quat_tol=0.002, trans_tol=0.005):
    qa, ta = a
    qb, tb = b
    if max(abs(p - q) for p, q in zip(qa, qb)) > quat_tol:
        return False
    return max(abs(p - q) for p, q in zip(ta, tb)) <= trans_tol

def match_multiset(orig_items, rt_items, close):
    """Greedy tolerant multiset match. Returns list of unmatched orig items."""
    remaining = list(rt_items)
    unmatched = []
    for o in orig_items:
        for i, r in enumerate(remaining):
            if close(o, r):
                del remaining[i]
                break
        else:
            unmatched.append(o)
    return unmatched


def summarize(path, Dts):
    d = Dts.from_file(path)
    s = d.shape.data.obj_data
    names = [n for n in s.names]

    # Strict structural counts (num_transforms/keyframes are WARN-tier:
    # a correct exporter may de-duplicate or re-lay-out those tables).
    strict_counts = {f: getattr(s, f, None) for f in (
        'num_nodes', 'num_names', 'num_objects', 'num_details', 'num_meshes')}
    warn_counts = {f: getattr(s, f, None) for f in (
        'num_transforms', 'num_seq', 'num_subseq', 'num_keyframes',
        'num_transitions', 'num_frametriggers')}

    nodes = _get(s, 'nodes', 'nodes_v7')
    transforms = _get(s, 'transforms', 'transforms_v7')
    objects = _get(s, 'objects', 'objects_v7')
    sequences = getattr(s, 'sequences', []) or []

    def node_name(i):
        if 0 <= i < len(nodes):
            return norm_name(names[nodes[i].name])
        return None

    # Node hierarchy as a (name, parent_name) multiset.
    hierarchy = sorted(
        (node_name(i), node_name(n.parent) if n.parent >= 0 else None)
        for i, n in enumerate(nodes))

    # Per-node bind pose: name -> list of (quat, translate). Engine poses the
    # rest skeleton from these; corruption here = deformed model in-game.
    bind = {}
    for i, n in enumerate(nodes):
        if 0 <= n.default_transform < len(transforms):
            t = transforms[n.default_transform]
            entry = (decode_quat(t.rotate),
                     (t.translate.x, t.translate.y, t.translate.z))
            bind.setdefault(node_name(i), []).append(entry)

    # Object -> node bindings (which mesh hangs off which bone).
    bindings = sorted(
        (norm_name(names[o.name]) if 0 <= o.name < len(names) else '?',
         node_name(o.node_index))
        for o in objects)

    # Sequence identity: names + cyclic flags are engine-facing (animations
    # are played BY NAME; cyclic controls looping). Durations/priorities are
    # WARN-tier -- the exporter intentionally normalizes some of those.
    seq_identity = sorted(
        (norm_name(names[q.name]) if 0 <= q.name < len(names) else '?',
         int(q.cyclic))
        for q in sequences)
    seq_timing = sorted(
        (norm_name(names[q.name]) if 0 <= q.name < len(names) else '?',
         round(q.duration, 3), int(q.priority))
        for q in sequences)

    meshes = []
    for m in d.meshes:
        verts = getattr(m, 'vertices', []) or []
        frames = _get(m, 'frames', 'frames_v2')
        nvpf = getattr(m, 'num_vertices_per_frame', 0) or 0

        # Decode EVERY frame with its own scale/origin (morph frames included).
        frame_bounds = []
        pack_step = 0.0
        for fr in frames:
            sc = getattr(fr, 'scale', None)
            og = getattr(fr, 'origin', None)
            if sc is None or og is None:   # v2 frames: scale lives on the mesh
                sc = getattr(m, 'scale_v2', None)
                og = getattr(m, 'origin_v2', None)
            first = getattr(fr, 'first_vert', 0)
            fverts = verts[first:first + nvpf] if nvpf else verts
            if not (sc and og and fverts):
                frame_bounds.append(None)
                continue
            pack_step = max(pack_step, abs(sc.x), abs(sc.y), abs(sc.z))
            xs = [v.x * sc.x + og.x for v in fverts]
            ys = [v.y * sc.y + og.y for v in fverts]
            zs = [v.z * sc.z + og.z for v in fverts]
            frame_bounds.append((round(min(xs), 3), round(max(xs), 3),
                                 round(min(ys), 3), round(max(ys), 3),
                                 round(min(zs), 3), round(max(zs), 3)))

        # Face-material histogram (order-independent: the exporter reverses
        # face order legitimately, but must not reroute faces to other
        # materials or change the face count per material).
        mat_hist = {}
        for f in getattr(m, 'faces', []) or []:
            mat_hist[f.material] = mat_hist.get(f.material, 0) + 1

        # UV extents (texvert COUNT may shrink via dedup; the extents of the
        # used UV space must survive -- catches flips/scaling/garbage UVs).
        # Only FACE-REFERENCED texverts count: some files carry hundreds of
        # thousands of orphan texverts (e.g. dragon_flyer: 322k total, 3.6k
        # referenced) which dedup legitimately drops.
        tvs = getattr(m, 'texture_vertices', []) or []
        used_tv = set()
        for f in getattr(m, 'faces', []) or []:
            for v in f.vip:
                if 0 <= v.texture_index < len(tvs):
                    used_tv.add(v.texture_index)
        if used_tv:
            uv_bbox = (round(min(tvs[i].x for i in used_tv), 3),
                       round(max(tvs[i].x for i in used_tv), 3),
                       round(min(tvs[i].y for i in used_tv), 3),
                       round(max(tvs[i].y for i in used_tv), 3))
        else:
            uv_bbox = None

        meshes.append({
            'nv': getattr(m, 'num_vertices', 0),
            'nvpf': nvpf,
            'nf': getattr(m, 'num_faces', 0),
            'ntv': getattr(m, 'num_texture_vertices', 0),
            'nframes': getattr(m, 'num_frames', 0),
            'frame_bounds': frame_bounds,
            # packed-vertex quantization step: legitimate re-pack noise is
            # at most ~1 step, so the drift tolerance scales with it.
            'tol': max(0.01, pack_step * 1.5),
            'mat_hist': mat_hist,
            'uv_bbox': uv_bbox,
        })

    # Material map filenames (texture preservation)
    mats = []
    try:
        if getattr(d, 'materials', None):
            for p in d.materials.params:
                mf = getattr(p, 'map_file', b'')
                if isinstance(mf, bytes):
                    mf = mf.split(b'\x00')[0].decode('ascii', 'ignore')
                else:
                    mf = mf.split('\x00')[0]
                mats.append(mf.lower())
    except Exception as e:
        mats = ['ERR %r' % e]

    return {'size': os.path.getsize(path),
            'strict_counts': strict_counts, 'warn_counts': warn_counts,
            'hierarchy': hierarchy, 'bind': bind, 'bindings': bindings,
            'seq_identity': seq_identity, 'seq_timing': seq_timing,
            'meshes': meshes, 'materials': mats}


def compare(orig, rt):
    """Return (fail_issues, warnings). Empty fail_issues == PASS."""
    issues = []
    warns = []

    # --- strict structural counts ---
    for k, ov in orig['strict_counts'].items():
        rv = rt['strict_counts'].get(k)
        if ov != rv:
            issues.append(f"count {k}: {ov} -> {rv}")

    # --- warn-tier counts (dedup / re-layout is legitimate) ---
    for k, ov in orig['warn_counts'].items():
        rv = rt['warn_counts'].get(k)
        if ov != rv:
            warns.append(f"count {k}: {ov} -> {rv} (dedup/re-layout is legal)")

    # --- node hierarchy ---
    if orig['hierarchy'] != rt['hierarchy']:
        o_set, r_set = set(orig['hierarchy']), set(rt['hierarchy'])
        for miss in sorted(o_set - r_set):
            issues.append(f"hierarchy lost: {miss[0]} (parent {miss[1]})")
        for extra in sorted(r_set - o_set):
            issues.append(f"hierarchy gained: {extra[0]} (parent {extra[1]})")

    # --- per-node bind transforms (tolerant of quat16/repack quantization) ---
    for name, o_entries in orig['bind'].items():
        r_entries = rt['bind'].get(name)
        if r_entries is None:
            issues.append(f"bind transform lost for node '{name}'")
            continue
        unmatched = match_multiset(o_entries, r_entries, transform_close)
        for q, t in unmatched:
            issues.append(
                f"bind transform drift on '{name}': no match for "
                f"q=({q[0]:.4f},{q[1]:.4f},{q[2]:.4f},{q[3]:.4f}) "
                f"t=({t[0]:.4f},{t[1]:.4f},{t[2]:.4f})")

    # --- object -> node bindings ---
    if orig['bindings'] != rt['bindings']:
        issues.append(f"object/node bindings: {orig['bindings']} -> {rt['bindings']}")

    # --- sequences ---
    if orig['seq_identity'] != rt['seq_identity']:
        issues.append(
            f"sequence names/cyclic: {orig['seq_identity']} -> {rt['seq_identity']}")
    if orig['seq_timing'] != rt['seq_timing']:
        warns.append(
            f"sequence duration/priority: {orig['seq_timing']} -> {rt['seq_timing']}")

    # --- meshes ---
    if len(orig['meshes']) != len(rt['meshes']):
        issues.append(f"mesh count: {len(orig['meshes'])} -> {len(rt['meshes'])}")
    else:
        for i, (om, rm) in enumerate(zip(orig['meshes'], rt['meshes'])):
            for f in ('nv', 'nvpf', 'nf', 'nframes'):
                if om[f] != rm[f]:
                    issues.append(f"mesh{i} {f}: {om[f]} -> {rm[f]}")
            # Texture vertices: dedup may shrink, must not vanish or inflate.
            otv, rtv = om['ntv'], rm['ntv']
            if otv > 0 and rtv == 0:
                issues.append(f"mesh{i} texverts lost: {otv} -> 0")
            elif rtv > otv:
                issues.append(f"mesh{i} texverts inflated: {otv} -> {rtv}")
            elif rtv < otv:
                warns.append(f"mesh{i} texverts deduped: {otv} -> {rtv}")
            # Per-frame decoded bounds, tolerance scaled to packing step.
            tol = max(om['tol'], rm['tol'])
            for fi, (ob, rb) in enumerate(zip(om['frame_bounds'],
                                              rm['frame_bounds'])):
                if ob and rb:
                    drift = max(abs(a - b) for a, b in zip(ob, rb))
                    if drift > tol:
                        issues.append(
                            f"mesh{i} frame{fi} bounds drift {drift:.3f} "
                            f"(tol {tol:.3f}): {ob} -> {rb}")
                elif bool(ob) != bool(rb):
                    issues.append(f"mesh{i} frame{fi}: bounds "
                                  f"{'lost' if ob else 'gained'}")
            # Face-material histogram.
            if om['mat_hist'] != rm['mat_hist']:
                issues.append(
                    f"mesh{i} face materials: {om['mat_hist']} -> {rm['mat_hist']}")
            # UV extents.
            if om['uv_bbox'] and rm['uv_bbox']:
                uv_drift = max(abs(a - b) for a, b in
                               zip(om['uv_bbox'], rm['uv_bbox']))
                if uv_drift > 0.002:
                    issues.append(
                        f"mesh{i} UV extents drift {uv_drift:.4f}: "
                        f"{om['uv_bbox']} -> {rm['uv_bbox']}")
            elif bool(om['uv_bbox']) != bool(rm['uv_bbox']):
                issues.append(f"mesh{i} UVs "
                              f"{'lost' if om['uv_bbox'] else 'gained'}")

    # --- materials / texture filenames must be preserved exactly ---
    if orig.get('materials') != rt.get('materials'):
        issues.append(
            f"materials: {orig.get('materials')} -> {rt.get('materials')}")

    return issues, warns


def main():
    src, dst = _parse_args()
    tmp, pkg = _stage_package()
    try:
        import tribes_dts_test as addon
        from tribes_dts_test.dts import Dts
        addon.register()

        bpy.ops.wm.read_factory_settings(use_empty=True)
        print(f"=== IMPORT {src} ===")
        bpy.ops.dynamix.dts(filepath=src)
        print("objects:", [o.name for o in bpy.data.objects])

        bpy.ops.object.select_all(action='SELECT')
        if bpy.data.objects:
            bpy.context.view_layer.objects.active = bpy.data.objects[0]

        print(f"=== EXPORT {dst} ===")
        # Do NOT pass original_dts_path: that activates donor skeleton-sync
        # (vertex reprojection). A normal round-trip relies on the importer's
        # collection prop (dts_source_file) for header splicing only.
        bpy.ops.export_mesh.dts(filepath=dst)

        orig = summarize(src, Dts)
        rt = summarize(dst, Dts)
        for label, d_ in (("ORIGINAL ", orig), ("ROUNDTRIP", rt)):
            print(f"\n{label}: {d_['size']} bytes  "
                  f"{d_['strict_counts']}  {d_['warn_counts']}")
            print(f"  sequences: {d_['seq_identity']}")
            for i, m in enumerate(d_['meshes']):
                print(f"  mesh{i}: nv={m['nv']} nvpf={m['nvpf']} nf={m['nf']} "
                      f"ntv={m['ntv']} frames={m['nframes']} "
                      f"mats={m['mat_hist']} uv={m['uv_bbox']}")
                print(f"    frame0 bounds: "
                      f"{m['frame_bounds'][0] if m['frame_bounds'] else None}")
            print(f"  materials: {d_['materials']}")

        issues, warns = compare(orig, rt)
        print("\n" + "=" * 50)
        if warns:
            print("WARNINGS (non-fatal):")
            for w in warns:
                print("  ~ " + w)
        if issues:
            print("RESULT: FAIL")
            for it in issues:
                print("  - " + it)
            sys.exit(1)
        print("RESULT: PASS (structure, skeleton, animation identity, "
              "geometry, materials preserved)")
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(3)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

main()
