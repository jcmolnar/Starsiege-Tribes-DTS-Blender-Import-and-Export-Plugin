# Creating a New DTS Character Model for Starsiege: Tribes

This guide outlines all requirements for creating a new character model in Blender that exports correctly to DTS format.

---

## 1. Node Hierarchy (Required Structure)

The DTS engine expects a specific hierarchy of nodes. Each "node" in Blender is an **Empty** object.

```
bounds                      # Root bounding box (REQUIRED)
├── always                  # Always-visible root node
│   ├── dummyalways root    # Player root transform
│   └── dummyalways chasecam # Third-person camera attach point
│
├── mesh [DETAIL]           # Main mesh container per detail level
│   ├── VICON[DETAIL]       # Visibility control node (animation target)
│   ├── lowerback[DETAIL]   # Pelvis/root of skeleton
│   │   ├── thorax[DETAIL]  # Torso
│   │   │   ├── rhumerus[DETAIL]    # Right shoulder
│   │   │   │   ├── rradius[DETAIL] # Right elbow
│   │   │   │   │   └── dummy hand[DETAIL]  # RIGHT HAND (weapon mount)
│   │   │   ├── lhumerus[DETAIL]    # Left shoulder
│   │   │   │   ├── lradius[DETAIL] # Left elbow
│   │   │   ├── head[DETAIL]        # Head
│   │   │   │   └── dummy eye[DETAIL]  # Eye/camera node
│   │   │   ├── dummy lowback[DETAIL]  # Lower back mount (backpack alt)
│   │   │   └── dummy midback[DETAIL]  # Mid back mount (backpack)
│   │   │
│   │   ├── rfemur[DETAIL]  # Right hip
│   │   │   ├── rtibia[DETAIL]  # Right knee
│   │   │   │   └── rfoot[DETAIL]   # Right foot
│   │   └── lfemur[DETAIL]  # Left hip
│   │       ├── ltibia[DETAIL]  # Left knee
│   │       │   └── lfoot[DETAIL]   # Left foot
```

### Detail Level Suffixes
- `36` = Highest detail (close up)
- `10` = Medium detail  
- `2` = Lowest detail (far away)

Example: `dummy hand36`, `dummy hand10`, `dummy hand2`

---

## 2. Required Mount Points

| Mount Point | Node Name | Purpose |
|-------------|-----------|---------|
| `mountPoint = 0` | `dummy hand[DETAIL]` | Weapon (right hand) |
| `mountPoint = 1` | `dummy unused[DETAIL]` | Body/Skin attachment |
| `mountPoint = 2` | `dummy midback[DETAIL]` | Backpack |
| `mountPoint = 3` | `dummy lowback[DETAIL]` | Secondary back mount |

> **Critical:** The engine appends detail level suffix dynamically. Name your nodes exactly as shown.

---

## 3. Skeleton Bone Requirements

### Bone Hierarchy (as Empties with parent relationships)
```
lowerback     → Root of skeleton (pelvis)
  thorax      → Spine/chest
    head      → Neck attachment
    rhumerus  → Right upper arm
      rradius → Right forearm
    lhumerus  → Left upper arm
      lradius → Left forearm
  rfemur      → Right thigh
    rtibia    → Right shin
      rfoot   → Right foot
  lfemur      → Left thigh
    ltibia    → Left shin
      lfoot   → Left foot
```

### Transform Requirements
Each bone node stores:
- **Rotation** (quaternion, stored as 4 x 16-bit signed integers)
- **Translation** (3 x 32-bit floats, local to parent)

---

## 4. Mesh Requirements

### Mesh Naming Convention
```
mesh [DETAIL]           # Root mesh container
submesh_torso [DETAIL]  # Body part meshes
submesh_head [DETAIL]
submesh_rarm [DETAIL]
submesh_larm [DETAIL]
submesh_rbicep [DETAIL]
submesh_lbicep [DETAIL]
submesh_rthigh [DETAIL]
submesh_rleg [DETAIL]
submesh_rfoot [DETAIL]
submesh_lthigh [DETAIL]
submesh_lleg [DETAIL]
submesh_lfoot [DETAIL]
```

### Mesh Properties
- **Vertex Limit:** 256 vertices per mesh (packed as bytes)
- **Triangle/Face Limit:** No hard limit, but engine performance degrades
- **UV Mapping:** Required for textured materials
- **Vertex Groups:** Each mesh should be weighted to its parent bone

---

## 5. Detail Levels (LOD)

Three detail levels required:

| Detail | Suffix | Threshold | Usage |
|--------|--------|-----------|-------|
| High | `36` | 0-36 units | Close to camera |
| Medium | `10` | 36-100 units | Medium distance |
| Low | `2` | 100+ units | Far from camera |

Each detail level needs:
- Complete mesh set (all body parts)
- Complete bone hierarchy
- Identical node names with different suffix

---

## 6. Animation Sequences

### Required Sequences for Player Characters

| Sequence Name | Description |
|---------------|-------------|
| `root` | Idle/standing pose |
| `run` | Running cycle |
| `back` | Running backwards |
| `side left` | Strafing left |
| `side right` | Strafing right |
| `fall` | Falling animation |
| `land` | Landing from fall |
| `jump` | Jump animation |
| `crouch root` | Crouching idle |
| `crouch forward` | Crouch walking |
| `crouch back` | Crouch walking backwards |
| `jet` | Jetpack flying |
| `diescream` | Death animation |
| `dying` | Post-death pose |
| `celwave` | Celebration wave |
| `celsalute` | Celebration salute |
| `pda` | Using PDA device |
| `sitting` | Sitting pose |
| `standjump` | Standing jump |
| `tumble` | Tumbling/rolling |

### Animation Data Structure
Each sequence contains:
- **SubSequences:** One per node that animates
- **Keyframes:** Transform indices at specific frames
- **Frame Count:** Total frames in sequence
- **Priority:** Controls animation blending

### Keyframe Format
```python
keyframe = {
    'position': float,      # 0.0 to 1.0 (normalized time)
    'transform_index': int, # Index into transform table
    'mat_index': int        # Material/visibility flags
}
```

---

## 7. Transform Table

All transforms (default poses + animation keyframes) stored in single table:
- **Stride:** 20 bytes (V8 format)
- **Format:** 
  - Bytes 0-7: Quaternion (4 x int16)
  - Bytes 8-19: Translation (3 x float32)

### Default Transforms
- Node 0 uses Transform 0 (etc.)
- Each node has a default transform index

### Keyframe Transforms  
- Indices 100+ typically used for animation keyframes
- Referenced by keyframe entries in sequences

---

## 8. Materials

### DTS Material Properties
```python
material = {
    'flags': int,           # Material type flags
    'alpha': int,           # Transparency (0-255)
    'index': int,           # Palette index
    'rgb': (r, g, b),       # Color values
    'filename': str         # Texture filename (*.bmp)
}
```

### Material Flags
- `0x0001` - Palette mapped
- `0x0003` - Textured
- `0x0100` - No shading
- `0x0200` - Flat shading
- `0x0400` - Smooth shading
- `0x1000` - Transparent
- `0x2000` - Translucent

---

## 9. Bounds and Visibility

### Required Metadata
```python
shape = {
    'radius': float,        # Bounding sphere radius
    'center': (x, y, z),    # Bounding sphere center
    'bounds_min': (x, y, z),# AABB minimum corner
    'bounds_max': (x, y, z) # AABB maximum corner
}
```

### Bounds Object
- Create an Empty named `bounds` at world origin
- Set as parent of entire hierarchy
- Defines overall model bounds for culling

---

## 10. Blender Setup Checklist

### Scene Setup
- [ ] Set units to Meters
- [ ] Origin at ground level (Z=0 = feet)
- [ ] Y-forward, Z-up coordinate system

### Hierarchy Setup
- [ ] Create `bounds` Empty at origin
- [ ] Create `always` child with mount points
- [ ] Create `mesh XX` containers for each detail level
- [ ] Create bone hierarchy under each mesh

### Mesh Setup
- [ ] Each body part as separate mesh object
- [ ] Parent to appropriate bone Empty
- [ ] Apply scale before export (Ctrl+A → Scale)
- [ ] UV unwrap for texturing

### Animation Setup
- [ ] Create Actions for each sequence
- [ ] Name actions exactly as required
- [ ] Set keyframes on bone Empties (not armature)
- [ ] Use Quaternion rotation mode

### Export Settings
- [ ] Provide `originalXXX.dts` for hybrid splicing
- [ ] Enable transform scaling if model is scaled
- [ ] Verify node names match expected patterns

---

## 11. File Structure Reference

```
mycharacter/
├── mycharacter.blend       # Blender source file
├── mycharacter.dts         # Exported DTS
├── originalmycharacter.dts # Reference file for splicing (optional)
└── textures/
    ├── body.bmp            # Body texture
    ├── head.bmp            # Head texture
    └── base.bmp            # Palette file
```

---

## 12. Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Weapon at feet | Transform table not scaled | Scale all 8670 transforms |
| Model invisible | Radius/bounds too small | Don't scale header bounds |
| Animations broken | Wrong keyframe indices | Verify transform references |
| Wrong mount point | Node name incorrect | Use exact naming convention |
| Mesh not attached | Wrong parent hierarchy | Check parent-child relations |
| Detail level wrong | Missing suffix | Add 36/10/2 to node names |

---

## 13. Testing Workflow

1. **Export** → Run Blender export
2. **Verify** → Use diagnostic scripts to check transforms
3. **Test in-game** → Spawn character, check animations
4. **Iterate** → Fix issues and re-export

### Diagnostic Commands
```powershell
# Trace hand hierarchy
python trace_mount_chain.py

# Compare transforms
python compare_headers.py

# Check for corruption
python check_transform_corruption.py
```
