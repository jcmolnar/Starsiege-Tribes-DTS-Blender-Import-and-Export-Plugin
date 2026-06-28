# 📄 Tribes 1 / Darkstar DTS Master Reference

This document serves as the **single source of truth** for the DTS (Darkstar Transport System) file format and the supporting workflow for Tribes 1. It consolidates information from the 3DS Max exporter source, the Darkstar engine source, and exhaustive binary analysis.

---

## 🏗️ 1. Scene Hierarchy & Node Logic

The DTS format relies on a structured node hierarchy.

### Mandatory & Special Nodes
| Node Name | Purpose | Behavior |
| :--- | :--- | :--- |
| **`bounds`** | Bounding Box | **Mandatory.** Defines the shape's extents and global origin. Must be a mesh. |
| **`root`** | Hierarchy Root | The top-level parent for all bones and sequences. |
| **`always`** | Always Visible | Geometry attached is drawn regardless of detail level. |
| **`hide`** | Default Hidden | Node is invisible unless an active sequence explicitly shows it. |
| **`dummy`** | Placeholder | Geometry is ignored by the exporter; used for bone references only. |
| **`dummyalways`**| Combo | Combines `dummy` (no geo) and `always` (permanent node processing). |
| **`VICON`** | Motion Capture | Internal name for character root bones (Biped `Bip01` is remapped to this). |

### Detail Levels (LOD) & Collision
Detail levels are determined by naming top-level nodes (children of `root`).
- **Naming Pattern**: `[Name][Size]` (e.g., `Detail128`, `Mesh64`).
- **Mechanism**: The numeric suffix is the **Projected Pixel Size** trigger.
- **Collision Hulls**: 
  - Traditionally named `Collision-1`.
  - Stored with a **negative detail size** (usually -1).
  - This prevents the hull from rendering while allowing the physics engine to detect it.

### Node Remapping (3DS Max Legacy)
The exporter automatically renames certain prefixes to match engine expectations:
- `Bip01` ➡️ `VICON`
- `Bip01 <Name>` ➡️ `<Name>` (e.g., `Bip01 Spine` becomes `Spine`).

---

## 📐 2. Spatial & Coordinate System

Tribes uses a **Right-Handed, Y-Up** coordinate system.

### Coordinate Mapping (Blender to DTS)
To match the engine, Blender users must map axes as follows:
- **Blender X** ➡️ **DTS X**
- **Blender Z** ➡️ **DTS Y** (Engine UP)
- **Blender -Y** ➡️ **DTS Z** (Engine FORWARD)

### Scale Handling
- **Static Scale**: Scaled nodes in the hierarchy have their scale "multiplied" into the child meshes at export time.
- **Runtime Scale**: **NOT SUPPORTED.** Transforming scale in animations will not work in-game. The engine explicitly clears scale flags during animation to maintain consistency.

### Topology & TexCoords
- **V-Coordinate Inversion**: Darkstar inverts the V texture coordinate. To match, tools must use **`1.0 - v`**.
- **Face Winding**: Darkstar is **Clockwise (CW)** for front-facing polygons.
  - **Requirement**: Triangles must be stored with CW winding to produce correct "outward" normals in the engine's math routines (e.g., `m_normal` in `m_coll.h`).
  - **Tooling**: Since most modern tools (Blender, 3DS Max) are CCW by default, exporters must reverse the vertex order (e.g., swap indices 1 and 2).

---

## 🎬 3. Animation & Timing

### Timing Constants
- **Global Clock**: 4800 ticks per second.
- **Frame Rate**: At 30 FPS, one frame is **160 ticks**.
- **Normalized Time**: Keyframe positions are stored as floats from `0.0` (start) to `1.0` (end).

### Sequence Properties
- **Priority**: Stored as an integer (default `0x1000`/4096). **Highest priority (lowest number) wins.**
- **Blending**: There is **no additive blending**. The highest priority sequence completely replaces transforms for any bone it controls.
- **Cyclic**: If `TRUE`, the animation loops. If `FALSE`, it stalls at the last keyframe.

### Keyframes & Interpolation
- **Rotation**: Stored as `Quat16` (signed 16-bit, scaled by 32767). Interpolated via **SLERP**.
- **Translation**: Stored as `Point3F`. Interpolated via **LERP**.
- **Visibility/Material**: Stored as boolean flags/indices. Transitions occur at the nearest keyframe proximity (0.5 threshold).

### Forward Kinematics (FK) vs. IK
- **Mechanism**: Tribes 1 uses **Forward Kinematics** (FK). Bone positions are pre-calculated during export based on parent rotations and stored in the DTS. 
- **No Automated IK**: There is no runtime Inverse Kinematics (IK) solver for foot-planting or procedural limb adjustment. Feet will clip or float on slopes unless the animation itself covers those poses.
- **Node Overrides**: The engine supports **Matrix Overrides** (`insertOverride`), allowing code to manually set a specific bone's transform (e.g., the `lowerback` node is overridden to align the torso with the player's view pitch).

---

## 🎨 4. Materials & Textures

### Binary Format (Version 3)
Materials are stored in 60-byte blocks within the `MaterialList`:
- `fFlags` (Int32), `fAlpha` (Float), `fRGB` (4 bytes), `fMapFile` (32 bytes), `fType` (Int32), `fElasticity`, `fFriction`.

### Texture Rules
- **Format**: 8-bit Paletted BMP (Microsoft DIB).
- **Transparency (@)**: Filenames starting with `@` (e.g., `@Skin.bmp`) treat **Palette Index 0** as transparent.
- **Translucency**: Filenames with `.tga` or `.png` in the source trigger the `TextureTranslucent` flag (Alpha blending).
- **Animated Materials**: Handled via `.ifl` (Image File List) files.

---

## 📂 5. DTS Binary Layout (v8)

Data is written as raw memory dumps of POD (Plain Old Data) structs.

| Block | Type | Count Header Field |
| :--- | :--- | :--- |
| **Header** | Int32[11], Float[4] | 15 fields | 60 bytes | Counts for subsequent vectors: `nNodes`, `nSequences`, `nSub`, `nKeys`, `nTrans`, `nNames`, `nObjects`, `nDetails`, `nMeshes`, `nTransitions`, `nTriggers`. Followed by `fRadius`, `fCenter` (P3F), `fBoundsMin` (P3F), `fBoundsMax` (P3F). |
| **Nodes** | `Node` | `nNodes` | 10 bytes | `fName`, `fParent`, `fnSub`, `fFirstSub`, `fDefTrans`. |
| **Sequences** | `Sequence` | `nSequences` | 32 bytes | Name, Cyclic, Duration, Priority, etc. |
| **SubSequences**| `SubSequence`| `nSubSequences`| 6 bytes | `fSeqIndex`, `fnKeys`, `fFirstKey`. |
| **Keyframes** | `Keyframe` | `nKeyframes` | 8 bytes | `fPos` (0-1), `fKeyValue`, `fMatIndex`. |
| **Transforms** | `Transform` | `nTransforms` | 20 bytes | `Quat16` (8b) + `Point3F` (12b). |
| **Names** | `char[24]` | `nNames` | 24 bytes | Null-padded string buffers. |
| **Objects** | `Object` | `nObjects` | 14+ bytes | Mesh links, Attachment point, Anim flags. |
| **Details** | `Detail` | `nDetails` | 8 bytes | `fRootNode`, `fSize` (LOD Trigger). |
| **Meshes** | `PERS` Block | `nMeshes` | Variable | The actual geometry data. |

### Critical Limits
- **Name Limit**: 23 characters (+1 null terminator) for Nodes/Sequences.
- **Texture Limit**: 31 characters (+1 null terminator).
- **Poly Compatibility**: Keep meshes under **5,000 polys** for guaranteed 1998-era performance.
- **Texture Geometry**: Textures should be Power-of-Two (e.g., 128x128, 256x256).

---

## 🔊 6. Sound Triggers & Frame Events

The DTS format supports **FrameTriggers**, which are time-synced events baked into sequences.

### Player Footsteps (Hardcoded Values)
In the Tribes engine, `FrameTrigger` values **1** and **2** are reserved for player footfalls:
- **Value 1**: Right Foot Fall. Plays `rFootSounds` and adds a right footprint decal.
- **Value 2**: Left Foot Fall. Plays `lFootSounds` and adds a left footprint decal.

### Behavior & Direction
- **Synced Playback**: Triggers are evaluated during `findTriggerFrames` in each animation tick.
- **Directional Support**: The exporter negates the `fPosition` (normalized time) if the trigger is meant for reverse playback. The engine's `findTriggerFrames` handles this negation to ensure triggers only fire when the animation crosses the specific point in the correct direction.
- **Reverse Triggers**: If a trigger is at `0.0` but for a reverse sequence, it is stored as `-0.001f` to distinguish it from a forward start.

### Weapons & Other Items
Weapons and handheld items typically do **not** use DTS FrameTriggers for fire or reload sounds. Instead, they rely on a **State Machine** in the engine:
- **Sound Tags**: Defined in the item data blocks (`sfxFireTag`, `sfxReloadTag`, `sfxActivateTag`, etc.).
- **Sequence Names**: The engine looks for specific named sequences (`fire`, `reload`, `spin`, `ambient`) and plays the associated sound when that state is entered.

---

## 7. Binary Structure & Technical Specs

| Feature | Limit / Specification | Source |
| :--- | :--- | :--- |
| **DTS Version** | 8 (for Tribes: Starsiege) | `ts_shape.cpp` |
| **Max Nodes** | 64 | `ts_shapeInst.h` |
| **Max Name Length** | 24 characters (including null) | `ts_types.h` |
| **Max Detail Levels** | No hard limit (Int32 counter) | `ts_shape.h` |
| **Max Verts/Poly** | 64 (Clipping limit) | `ts_PointArray.cpp` |
| **Morph Frames** | Soft limit (Performance/Memory driven) | `ts_CelAnimMesh.cpp` |
| **Vertex Winding** | Clockwise (CW) | `MeshBuilder.cpp` |
| **Normal Encoding** | 8-bit index into 256-entry lookup table | `ts_vertex.cpp` |

---

## 8. Metadata & Summary of Research

### Verified Knowledge
- [x] **Vertex Winding**: Confirmed as Clockwise (CW). The exporter swaps indices 0 and 1.
- [x] **Scale Handling**: Runtime scale is supported via Node transforms; Blender exports should use 1.0 scale and bake deltas into the geometry if possible.
- [x] **Frame Triggers**: Hardcoded values 1 (Right Foot) and 2 (Left Foot) trigger sound/decals in `playerUpdate.cpp`.
- [x] **Morph Limits**: No hard engine limit; practical limit is 15-30 frames based on memory and CPU lerp overhead.
- [x] **Normal Encoding**: Confirmed as an 8-bit index into a 256-entry lookup table using nearest-neighbor Euclidean distance.

### Missing Information / Open Questions
- [ ] **Alpha/Translucency Sorting**: Exact behavior for overlapping translucent meshes (sorting is done by `MeshBuilder::sortPassKey`, but depth-sorting within a mesh is unclear).
- [x] **IK / Foot-planting**: Confirmed **Forward Kinematics (FK)** only. The engine lacks an automated IK solver; all limb placement is baked into 30 FPS animations. Node overrides (procedural matrix replacement) are used for aiming and head-tracking but do not involve kinematics solvers.


---
*Reference compiled from Darkstar Engine Source, 3DS Max Exporter Source, and Binary Analysis.*
