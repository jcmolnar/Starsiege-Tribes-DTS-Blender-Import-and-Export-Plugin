# Tribes DTS Blender Addon Refinement Plan

Address the coordinate system, winding order, normal encoding, string limit, and static mesh compatibility issues in the DTS importer, exporter, and parser.

## User Review Required

> [!WARNING]
> These changes will modify the way mesh winding orders, vertex normals, string limits, and coordinate axis conversions are handled when importing and exporting shapes. These fixes ensure compliance with the C++ Tribes engine specifications.

## Ghidra & RE Verification Summary

Based on reverse-engineering data from `T1Vista.exe` (Borland C++ 5.x build):
* **Class Registration**: In the compiled production client, the persistent mesh class is registered under the compiler RTTI name `TS::Shape::Mesh` (vtbl `0x00648154`), which corresponds to the concrete `CelAnimMesh` class (since the parent `Shape::Mesh` is pure virtual).
* **Frame Struct Layout**: `TS::Shape::Mesh::unpack` (`0x5ad2a8`) processes frame items in a loop using a stride of 28 bytes (`0x1c` in hex). This confirms that:
  - `fFirstVert` is at offset 0 (4 bytes).
  - `fScale` is at offset 4 (12 bytes).
  - `fOrigin` is at offset 16 (12 bytes).
* **Parser Resolution**: The parser (`dts.py`) must cleanly strip null terminators from classnames and map `TS::Shape::Mesh`, `TS::Mesh`, and `TS::CelAnimMesh` to the same mesh object parser class to ensure cross-version compatibility.

## Proposed Changes

Grouped by component: Importer, Exporter, and Parser.

---

### DTS Binary Parser Component

#### [MODIFY] [dts.py](file:///C:/Users/Joe/AppData/Roaming/Blender%20Foundation/Blender/5.0/scripts/addons/Tribes%20DTS%20Blender/dts.py)
* Refactor the persistent block class loader to split off trailing null padding and recognize `TS::Shape::Mesh` and `TS::Mesh` (static meshes) as `TsAnimmesh` (which maps to our internal mesh representation):
```python
            _on_clean = self.classname.split(b'\x00')[0]
            if _on_clean == b"TS::Shape":
                self.obj_data = Dts.TsShape(self._io, self, self._root)
            elif _on_clean in (b"TS::CelAnimMesh", b"TS::Mesh", b"TS::Shape::Mesh"):
                self.obj_data = Dts.TsAnimmesh(self._io, self, self._root)
```

---

### Addon Importer Component

#### [MODIFY] [main.py](file:///C:/Users/Joe/AppData/Roaming/Blender%20Foundation/Blender/5.0/scripts/addons/Tribes%20DTS%20Blender/main.py)
* Swap indices 1 and 2 for all faces on import to correctly convert CW winding (DTS standard) to CCW winding (Blender standard):
```diff
-                    array_val = [face.vip[0].vertex_index, face.vip[1].vertex_index, face.vip[2].vertex_index]
+                    array_val = [face.vip[0].vertex_index, face.vip[2].vertex_index, face.vip[1].vertex_index]
```
* Also swap texture UV mapping indices 1 and 2 to match the new face winding representation.

---

### Addon Exporter Component

#### [MODIFY] [export_dts.py](file:///C:/Users/Joe/AppData/Roaming/Blender%20Foundation/Blender/5.0/scripts/addons/Tribes%20DTS%20Blender/export_dts.py)
* **Static Normal Table**: Replace the generated golden-angle table `NORMAL_TABLE` with the exact 256 static `Point3F` vectors matching `fNormalTable` from `ts_vertex.cpp`.
* **Euclidean Normal Search**: Modify `find_closest_normal` to compute the minimum Euclidean distance instead of the maximum Dot Product.
* **Winding Order Swap**: Swap indices 1 and 2 for all faces to convert Blender's CCW winding back to the engine's CW winding.
* **Detail Level (LOD) Sorting**: Sort the `details` list in descending order of size (with negative sizes for collision/LOS placed at the end) before writing to `shape_data`.
* **TS::Mesh Support**: Check if a mesh is static (no shape keys or animations) and write its PERS header classname as `TS::Mesh` instead of forcing `TS::CelAnimMesh`.
* **Animation Framerate Divisor**: Change the FPS divisor from `24.0` to `30.0` to match the engine timing standard.
* **String Limit Truncation**:
  * Truncate object, sequence, and node names at 23 characters before padding to 24 bytes (ensuring null-termination).
  * Truncate material map filenames at 31 characters before padding to 32 bytes.
* **Axis Conversion for Skeletal Armatures**: Apply Y-up axis conversion to default node locations/rotations and animation keyframes if `convert_axes` is enabled. Conjugate local transforms with the conversion matrix `R @ M @ R_inv`.

---

## Verification Plan

### Manual Verification
1. Export a newly modeled object from Blender to DTS with and without animations, and verify correct rendering/lighting in the game client.
2. Verify that player footfall triggers and looping actions function correctly in-game.
3. Import a third-party DTS file containing static `TS::Mesh` or `TS::Shape::Mesh` structures to confirm it loads without parsing crashes.
