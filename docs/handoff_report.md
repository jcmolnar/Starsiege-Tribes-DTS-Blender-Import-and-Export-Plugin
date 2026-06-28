# Handoff Report: DTS Export Crash Debugging

**Date:** 2026-01-02
**Target:** Tribes Torque Engine (old version)
**Objective:** Resolve client crashes/invisibility when equipping Blender-exported `axeorig.dts`.
**Strategy:** Achieve 1:1 Binary Parity with known-good `Axe.dts`.

## Current Status (Critical)
*   **Parity State:** We have achieved **Size Parity** (7122 bytes) and **Offset Alignment**.
*   **Verification:** `fc` (File Compare) fails starting at offset `0x109A` (Start of Face Data).
*   **Crash State:** "Invisible Weapon" or "Immediate Crash" depending on configuration.

## Identified Issues & Fixes So Far

### 1. Detail Level Struct Size (Major Invisibility Cause)
*   **Finding:** `Axe.dts` stores Detail Levels as **8 bytes** (`Name: u32`, `Size: f32`).
*   **Issue:** Standard Torque DTS (v8) usually expects 7 fields (28 bytes). My exporter was patching `dts.py` to match this, but writing 7 fields bloated the file +20 bytes/detail, shifting offsets and causing the engine to read Transition data as Mesh data -> Invisible.
*   **Current Fix:** `export_dts.py` reverted to write only `Name` and `Size`. This aligned the file size.

### 2. Face Index Swapping (Major Crash Cause)
*   **Finding:** The engine crashes reading indices. In `Axe.dts`, the **Middle Vertex Pair** of every face is stored as `(TextureIndex, VertexIndex)` instead of standard `(VertexIndex, TextureIndex)`.
*   **Evidence:** `Axe.dts` Face 0 middle vertex is `(285, 125)`.
    *   285 is a valid Texture Index.
    *   125 is a valid Vertex Index.
    *   If read as `(V=285, T=125)`, it crashes (285 > 132 verts).
*   **Current Hack:** `export_dts.py` manually swaps `u32` writes for the middle pair (`i == 1`).

### 3. Material Index
*   **Finding:** `CelAnimMesh` faces *do* appear to require the trailing 4-byte Material Index (or pad), contrary to my initial "strip it" theory. Removing it broke file alignment.
*   **Current State:** Material Index write is ENABLED.

## The Discrepancy (Where we are stuck)
The files align perfectly in headers and offsets, but the **content** of the Face Data (`0x109A` onwards) differs.
*   **Action Required:**
    1.  Dump the raw bytes of `Axe.dts` at `0x109A` (Face 0).
    2.  Dump the raw bytes of `axeorig.dts` at `0x109A` (Face 0).
    3.  Compare strictly.
    4.  Adjust `export_dts.py` loop to match the byte pattern of `Axe.dts`.
        *   Is `Axe.dts` writing `(T, V)` for *all* vertices?
        *   Is `Axe.dts` omitting the Material Index only for certain faces?
        *   Is there a subtle index offset?

## Files of Interest
*   `export_dts.py`: The exporter. Focus on `write_ts_animmesh` (lines 488+).
*   `compare_faces_skeleton.py`: For parsing face values.
*   `dump_range.py`: For raw hex verification. target `0x1090`.
*   `Axe.dts`: Reference.
*   `axeorig.dts`: Export.

## Immediate Next Steps
1.  Verify the byte pattern at `0x109A`.
2.  If `Axe.dts` data looks like standard `(V, T)` values (e.g. small ints), then my "Swap Hack" might be applying wrongly or redundantly.
3.  Once `0x109A` matches, the rest of the mesh data should align, and the crash will be gone.

## Debugging Script Inventory
We have created a suite of custom python scripts to inspect specific parts of the DTS file structure. All serve to compare `Axe.dts` (Reference) vs `axeorig.dts` (Export).

### 1. Structure & Layout
*   `compare_layout.py`: **Critical.** Scans the file for `PERS` blocks and prints their offsets and sizes. Used to verify structural alignment.
*   `inspect_tail.py`: Checks total file size and the last 32 bytes. Confirms footer alignment.
*   `splice_v2.py`: Utility to cut-and-paste headers or bodies between files to create "Hybrid" files for ensuring the crash comes from the body, not the header.

### 2. Mesh & Geometry Comparison
*   `compare_mesh_data.py`: **Critical.** Dumps `TsAnimMesh` headers (NumVerts, NumTVerts, NumFaces) and the first 10 faces/vertices. Primary tool for spotting index mismatches.
*   `compare_faces_skeleton.py`: Formats face data specifically to show `(VertexIndex, TextureIndex)` pairs. Used to visualize the "V/T Swap" issue.
*   `check_degenerate.py`: Scans entire mesh for indices that exceed `num_vertices`. Confirms if a crash is due to OOB access.
*   `compare_mesh_headers.py`: Compares primitive types and flags of meshes.
*   `inspect_counts.py`: Dumps raw hex at the Mesh Header Count offset to verify `num_vertices` at the binary level.

### 3. Detail Levels & Headers
*   `compare_details_v2.py`: **Critical.** Parses the `Detail Level` structs. Identified the major discrepancy where the exporter was writing 7 fields but the file expected 2.
*   `dump_details_hex.py`: Dumps raw hex of the Detail Level block.
*   `read_shape_bounds.py`: Compares the Shape Radius and Bounding Box floats.
*   `compare_transforms.py`: Compares Node rotation/translation lists.

### 4. Low-Level Inspection
*   `dump_range.py`: **Critical.** Dumps a 64-byte hex chunk at a hardcoded offset. Used to pinpoint exactly where binary divergence begins (currently `0x109A`).
*   `inspect_faces_offset.py`: Dumps bytes specifically around the calculated start of the Face Array.

### 5. Utilities
*   `force_copy.py`: Copies `export_dts.py` from the dev folder to the Blender Addons folder.
*   `dts.py`: The `Kaitai Struct` definition file. Modified during the session to support accurate parsing of `Detail` structs.
