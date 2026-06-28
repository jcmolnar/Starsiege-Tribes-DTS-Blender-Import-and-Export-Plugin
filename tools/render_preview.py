"""Render a posed Tribes character .blend to PNGs for visual review.

The submesh_* objects are rigidly parented to the node-empties, so rendering the
mesh shows the retargeted pose. Renders front (+Y) and side views at a few
frames, LOD36 only (other LODs overlap in place).

    blender --background --factory-startup \
        --python tools/render_preview.py -- <posed.blend> <tag> [out_dir]

Outputs <out_dir>/<tag>_{front,side}_fNNN.png. Default out_dir = ./renders.
"""
import bpy, os, sys, math
from mathutils import Vector

def _args():
    argv = sys.argv
    a = argv[argv.index("--") + 1:] if "--" in argv else []
    if len(a) < 2:
        print("usage: -- <blend> <tag> [out_dir]"); sys.exit(2)
    blend, tag = a[0], a[1]
    out = a[2] if len(a) > 2 else os.path.join(os.getcwd(), "renders")
    return blend, tag, out

def main():
    blend, tag, outdir = _args()
    os.makedirs(outdir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x = 420; sc.render.resolution_y = 520

    # LOD36 only (other LODs overlap in place)
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.hide_render = not o.name.rstrip().endswith("36")

    mins = Vector((1e9,) * 3); maxs = Vector((-1e9,) * 3)
    for o in bpy.data.objects:
        if o.type == 'MESH' and not o.hide_render and len(o.data.vertices) > 2:
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                for i in range(3):
                    mins[i] = min(mins[i], w[i]); maxs[i] = max(maxs[i], w[i])
    ctr = (mins + maxs) / 2; size = max((maxs - mins))

    def cam(name, dv):
        c = bpy.data.cameras.new(name); ob = bpy.data.objects.new(name, c)
        sc.collection.objects.link(ob)
        ob.location = ctr + dv.normalized() * size * 2.6
        ob.rotation_euler = (ctr - ob.location).normalized().to_track_quat('-Z', 'Y').to_euler()
        return ob
    front = cam("front", Vector((0, 1, 0.15)))   # Tribes character faces +Y
    side = cam("side", Vector((-1, 0, 0.15)))

    li = bpy.data.lights.new("sun", 'SUN'); lo = bpy.data.objects.new("sun", li)
    sc.collection.objects.link(lo); lo.rotation_euler = (math.radians(55), 0, math.radians(30))

    nf = sc.frame_end
    for f in sorted(set([sc.frame_start, int(nf * 0.25), int(nf * 0.5), int(nf * 0.75), nf])):
        sc.frame_set(f)
        for nm, c in (("front", front), ("side", side)):
            sc.camera = c
            sc.render.filepath = os.path.join(outdir, f"{tag}_{nm}_f{f:03}.png")
            bpy.ops.render.render(write_still=True)
    print(f"RENDERED {tag} -> {outdir}")

main()
