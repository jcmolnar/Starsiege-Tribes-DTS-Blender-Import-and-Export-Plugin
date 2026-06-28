# Custom DTS Character Model Workflow

Complete guide for replacing Tribes character geometry with custom high-poly models.

---

## Overview

This workflow replaces the geometry of `rpgmalehuman.dts` (the donor model) with your custom model while preserving the donor's skeleton, animations, and coordinate system.

**Scripts location:** `c:\Users\Joe\Tribes DTS Blender\`

---

## Prerequisites

1. **Custom model** - posed to match rpgmalehuman's bind pose
2. **Blender 5.0** with Tribes DTS Blender addon installed
3. **rpgmalehuman.dts** - the donor skeleton model

---

## Workflow Steps

### Phase 1: Prepare Your Model

#### Step 1: Slice Model into Body Parts
**Script:** `slice_mesh_to_body_parts.py`

Separates your unified model into 13 submesh parts matching the donor's structure:
- `submesh_head 36`
- `submesh_torso 36`
- `submesh_pelvis 36`
- `submesh_larm 36`, `submesh_rarm 36`
- `submesh_lbicep 36`, `submesh_rbicep 36`
- `submesh_lthigh 36`, `submesh_rthigh 36`
- `submesh_lleg 36`, `submesh_rleg 36`
- `submesh_lfoot 36`, `submesh_rfoot 36`

#### Step 2: Generate UVs (if needed)
**Script:** `smart_uv_project_all.py`

If your model doesn't have UVs, this creates automatic UV coordinates.

> **Note:** Smart UV Project creates a new layout that won't match existing textures. You'll need a new texture painted for your model's UVs.

#### Step 3: Cap Open Edges (optional)
**Script:** `cap_open_edges.py`

Fills holes at cut boundaries to make meshes solid.

#### Step 4: Export to OBJ
**Script:** `export_meshes_to_obj.py`

Exports each submesh as a separate OBJ file to `mesh_exports/` folder.

---

### Phase 2: Replace Donor Geometry

#### Step 5: Import Donor Model
1. **Open a FRESH Blender file**
2. Import `rpgmalehuman.dts`

> **Important:** Must be a fresh file - importing into existing scene causes conflicts.

#### Step 6: Replace Mesh Data
**Script:** `import_and_replace_meshes.py`

Imports OBJ files and copies geometry to donor meshes, transforming vertices to correct local space. Preserves donor's:
- Object transforms
- Parent hierarchy
- DTS metadata

#### Step 7: Center at Bone Pivots
**Script:** `center_meshes_at_bone_pivots.py`

**Critical for animations!** Centers each mesh's vertices at local origin (0,0,0) so bones rotate around correct pivot points.

#### Step 8: Fine-tune Positions (optional)
**Script:** `adjust_mesh_transforms.py`

Apply manual position/rotation offsets per mesh if alignment isn't perfect.

---

### Phase 3: Export

#### Step 9: Export DTS
1. File → Export → Tribes DTS
2. Save as your model name (e.g., `astronaut.dts`)
3. Copy to game folder

---

## Script Reference

| Script | Purpose | When to Run |
|--------|---------|-------------|
| `slice_mesh_to_body_parts.py` | Split model into 13 parts | Phase 1 |
| `smart_uv_project_all.py` | Generate automatic UVs | Phase 1 (if no UVs) |
| `cap_open_edges.py` | Fill cut holes | Phase 1 (optional) |
| `export_meshes_to_obj.py` | Export to OBJ files | Phase 1 |
| `import_and_replace_meshes.py` | Replace donor geometry | Phase 2 |
| `center_meshes_at_bone_pivots.py` | Fix animation pivots | Phase 2 |
| `adjust_mesh_transforms.py` | Manual position tweaks | Phase 2 (optional) |

---

## Troubleshooting

### Model "explodes" in-game
**Cause:** Geometry not centered at bone pivots  
**Fix:** Run `center_meshes_at_bone_pivots.py`

### Parts move wrong during animations
**Cause:** Same as above  
**Fix:** Run `center_meshes_at_bone_pivots.py`

### Textures look scrambled
**Cause:** UVs don't match texture layout  
**Fix:** Use Smart UV Project and create a new texture, OR manually UV unwrap to match existing texture

### Model imports exploded in Blender after export
**Cause:** Coordinate space issues in export  
**Fix:** Ensure full workflow was followed, especially centering step

---

## Texture Notes

The DTS references textures by material name. If material is `astronauttest3`, the game looks for `astronauttest3.bmp`.

**To use existing rpgmalehuman texture:**
- Your model's UVs must match the rpgmalehuman UV layout exactly

**To use a new texture:**
1. UV unwrap your model (Smart UV Project or manual)
2. Paint/bake a texture matching YOUR UV layout
3. Name it to match your material name
