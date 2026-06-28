# Mixamo Animation Retargeting Workflow

## Your Downloaded Animations → Tribes Names

| Mixamo File | Tribes Sequence Name | Status |
|-------------|---------------------|--------|
| `idle.fbx` | `root` | Ready |
| `running.fbx` | `run` | Ready |
| `Running Backward.fbx` | `runback` | Ready |
| `left strafe.fbx` | `side left` | Ready |
| `Crouching Idle.fbx` | `crouch root` | Ready |
| `jump.fbx` | `jump run` | Ready |
| `Flying.fbx` | `jet` | Ready |
| `Standing Death Forward.fbx` | `die forward` | Ready |
| `Standing React Death Backward.fbx` | `die back` | Ready |
| `Waving.fbx` | `wave` | Ready |
| `walking.fbx` | (unused - Tribes uses run) | Optional |
| `left strafe walking.fbx` | `crouch side left` | Optional |
| `Dancing Twerk.fbx` | `celebration 1` | Fun! |

## Not Yet Downloaded (Lower Priority)
- `fall`, `landing`
- `crouch forward`
- Death variants: `die chest`, `die head`, `die leg right/left`, `die left side`, `die right side`, `die spin`, `die forward kneel`, `die blown back`, `die grab back`, `crouch die`
- Signs: `sign over here`, `sign stop`, `sign point`, `sign salut`, `sign retreat`
- Others: `looks`, `crouch looks`, `pda access`, `celebration 2/3`, `taunt 1/2`, `pose kneel`, `pose stand`
- Vehicle: `apc root`, `apc pilot`, `flyer root`

---

## Retargeting Steps (For Each Animation)

### In Blender:

1. **Fresh scene** - Open new Blender file
2. **Import rpgmalehuman.dts** - This is your target skeleton
3. **Import Mixamo FBX** - e.g., `idle.fbx`
4. **Run `retarget_mixamo_to_tribes.py`** - Copies animation to Tribes skeleton
5. **Rename the action** - In Dope Sheet, rename action to Tribes name (e.g., "root")
6. **Repeat** for each animation
7. **Export DTS** - All animations in one file

---

## File Name → Tribes Name Mapping (for script)

```python
ANIMATION_MAPPING = {
    'idle.fbx': 'root',
    'running.fbx': 'run',
    'Running Backward.fbx': 'runback',
    'left strafe.fbx': 'side left',
    'Crouching Idle.fbx': 'crouch root',
    'jump.fbx': 'jump run',
    'Flying.fbx': 'jet',
    'Standing Death Forward.fbx': 'die forward',
    'Standing React Death Backward.fbx': 'die back',
    'Waving.fbx': 'wave',
    'Dancing Twerk.fbx': 'celebration 1',
}
```
