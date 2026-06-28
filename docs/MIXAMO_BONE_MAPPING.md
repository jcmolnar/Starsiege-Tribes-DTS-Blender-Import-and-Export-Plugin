# Mixamo to Tribes Bone Mapping

## Bone Name Mapping Table

| Mixamo Bone | Tribes Bone | Notes |
|-------------|-------------|-------|
| `mixamorig:Hips` | `lowerback` / `pelvis` | Root bone |
| `mixamorig:Spine` | `lowerback` | Lower spine |
| `mixamorig:Spine1` | `thorax` | Mid spine |
| `mixamorig:Spine2` | `thorax` | Upper spine |
| `mixamorig:Neck` | `head` (parent) | Neck joint |
| `mixamorig:Head` | `head` | Head bone |
| | | |
| **Left Arm** | | |
| `mixamorig:LeftShoulder` | `lhumerus` | Shoulder |
| `mixamorig:LeftArm` | `lhumerus` | Upper arm |
| `mixamorig:LeftForeArm` | `lradius` | Forearm |
| `mixamorig:LeftHand` | `dummy hand` | Hand |
| | | |
| **Right Arm** | | |
| `mixamorig:RightShoulder` | `rhumerus` | Shoulder |
| `mixamorig:RightArm` | `rhumerus` | Upper arm |
| `mixamorig:RightForeArm` | `rradius` | Forearm |
| `mixamorig:RightHand` | `dummy hand` | Hand |
| | | |
| **Left Leg** | | |
| `mixamorig:LeftUpLeg` | `lfemur` | Thigh |
| `mixamorig:LeftLeg` | `ltibia` | Shin |
| `mixamorig:LeftFoot` | `lfoot` | Foot |
| `mixamorig:LeftToeBase` | (none) | No toe in Tribes |
| | | |
| **Right Leg** | | |
| `mixamorig:RightUpLeg` | `rfemur` | Thigh |
| `mixamorig:RightLeg` | `rtibia` | Shin |
| `mixamorig:RightFoot` | `rfoot` | Foot |
| `mixamorig:RightToeBase` | (none) | No toe in Tribes |

---

## Tribes Bone Hierarchy (from rpgmalehuman.dts)

```
bounds
└── always
    └── dummyalways root
        └── dummyalways chasecam
            └── mesh 36
                └── VICON36
                    └── lowerback36
                        └── thorax36
                            ├── rhumerus36
                            │   └── rradius36
                            │       └── dummy hand36
                            │           ├── submesh_rarm 36
                            │           └── submesh_rbicep 36
                            ├── lhumerus36
                            │   └── lradius36
                            │       ├── submesh_larm 36
                            │       └── submesh_lbicep 36
                            ├── head36
                            │   └── dummy eye36
                            │       └── submesh_head 36
                            └── submesh_torso 36
                        └── dummy lowback36
                            └── submesh_pelvis 36
                                ├── rfemur36
                                │   └── rtibia36
                                │       └── rfoot36
                                │           └── submesh_rfoot 36
                                │       └── submesh_rleg 36
                                │   └── submesh_rthigh 36
                                └── lfemur36
                                    └── ltibia36
                                        └── lfoot36
                                            └── submesh_lfoot 36
                                        └── submesh_lleg 36
                                    └── submesh_lthigh 36
```

---

## Mixamo Standard Hierarchy

```
mixamorig:Hips
├── mixamorig:Spine
│   └── mixamorig:Spine1
│       └── mixamorig:Spine2
│           ├── mixamorig:Neck
│           │   └── mixamorig:Head
│           ├── mixamorig:LeftShoulder
│           │   └── mixamorig:LeftArm
│           │       └── mixamorig:LeftForeArm
│           │           └── mixamorig:LeftHand
│           └── mixamorig:RightShoulder
│               └── mixamorig:RightArm
│                   └── mixamorig:RightForeArm
│                       └── mixamorig:RightHand
├── mixamorig:LeftUpLeg
│   └── mixamorig:LeftLeg
│       └── mixamorig:LeftFoot
│           └── mixamorig:LeftToeBase
└── mixamorig:RightUpLeg
    └── mixamorig:RightLeg
        └── mixamorig:RightFoot
            └── mixamorig:RightToeBase
```

---

## Key Differences

1. **Tribes has LOD suffixes** - Bones are duplicated for each LOD level (36, 10, 2)
2. **Tribes has mesh nodes** - `submesh_` bones that hold geometry
3. **Mixamo has more spine bones** - Tribes uses simpler spine (lowerback → thorax)
4. **Mixamo has toes** - Tribes skeleton doesn't have toe bones
5. **Different hierarchy root** - Mixamo starts at Hips, Tribes has bounds/always/root wrapper
