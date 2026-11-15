# Road Damage Dataset (RDD) & Custom Training Guide

This guide details the dataset acquisition, annotation formatting, and custom training pipeline for detecting road surface damages (potholes, longitudinal cracks, transverse cracks, and alligator cracking) using Ultralytics YOLO.

---

## 1. Standard Dataset: Road Damage Dataset (RDD2020 / RDD2022)

The system is standardized on the **Global Road Damage Detection Challenge (GRDDC)** taxonomy:

| Class Code | Damage Category | Description & Visual Characteristics |
| :--- | :--- | :--- |
| **D00** | `longitudinal_crack` | Linear crack running parallel to the direction of vehicle travel. |
| **D10** | `transverse_crack` | Linear crack running perpendicular to the direction of travel. |
| **D20** | `alligator_crack` | Interconnected fatigue cracking resembling reptile skin or mesh. |
| **D40** | `pothole` | Structural depression, pit, or cavity in the road surface. |

### Downloading the Official Dataset:
- RDD2020 / RDD2022 datasets can be obtained from the official Tokyo University / IEEE BigData challenge repository or Kaggle:
  - Kaggle: `kaggle datasets download -d chitholian/road-damage-dataset`
  - IEEE BigData RDD2022: `https://crddc2022.sekilab.global/`

---

## 2. Directory Layout for YOLO Training

Ultralytics YOLO requires datasets structured with separate `images` and `labels` directories:

```text
data/
└── road_damage/
    ├── train/
    │   ├── images/
    │   │   ├── damage_001.jpg
    │   │   └── ...
    │   └── labels/
    │       ├── damage_001.txt   # Class x_center y_center width height (normalized)
    │       └── ...
    └── val/
        ├── images/
        │   ├── damage_101.jpg
        │   └── ...
        └── labels/
            ├── damage_101.txt
            └── ...
```

---

## 3. YOLO Annotation Format

Each `.txt` label file contains one line per detected damage instance:
```text
<class_id> <x_center> <y_center> <width> <height>
```
Where coordinates are normalized between `0.0` and `1.0`.

Mapping:
- `0`: `longitudinal_crack` (D00)
- `1`: `transverse_crack` (D10)
- `2`: `alligator_crack` (D20)
- `3`: `pothole` (D40)

---

## 4. Automated Preparation Script

Use the automated preparation script in `scripts/prepare_rdd_dataset.py`:
- To convert official Pascal VOC XML annotations to YOLO format:
  ```powershell
  python scripts/prepare_rdd_dataset.py --source-xml C:/path/to/RDD/Annotations --source-img C:/path/to/RDD/JPEGImages
  ```
- To generate a verified synthetic training & validation set for offline development:
  ```powershell
  python scripts/prepare_rdd_dataset.py --generate-sample-dataset
  ```

---

## 5. Training the Custom Road Damage Model

Execute the training script:
```powershell
python scripts/train_road_damage.py --epochs 25 --imgsz 640 --batch 8
```
The script will output the optimized weights to:
`backend/models/road_damage_best.pt`
