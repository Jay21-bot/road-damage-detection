#!/usr/bin/env python3
"""
Road Damage Dataset Preparation & VOC-to-YOLO Converter
Converts official RDD VOC XML annotations to YOLO format, and includes a procedural
synthetic road damage dataset generator for testing and training pipelines.
"""

import sys
import os
import random
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
import cv2
import numpy as np

# Standard RDD taxonomy to class IDs
RDD_CLASS_MAPPING = {
    "D00": 0,  # longitudinal_crack
    "longitudinal_crack": 0,
    "D10": 1,  # transverse_crack
    "transverse_crack": 1,
    "D20": 2,  # alligator_crack
    "alligator_crack": 2,
    "D40": 3,  # pothole
    "pothole": 3
}


def convert_voc_to_yolo(xml_file: Path, width: int, height: int) -> list:
    """Converts a single Pascal VOC XML file to YOLO normalized format."""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    yolo_boxes = []

    for obj in root.findall("object"):
        name = obj.find("name").text.strip()
        if name not in RDD_CLASS_MAPPING:
            continue
        cls_id = RDD_CLASS_MAPPING[name]

        bndbox = obj.find("bndbox")
        xmin = float(bndbox.find("xmin").text)
        ymin = float(bndbox.find("ymin").text)
        xmax = float(bndbox.find("xmax").text)
        ymax = float(bndbox.find("ymax").text)

        # Normalize to [0, 1]
        x_center = ((xmin + xmax) / 2.0) / width
        y_center = ((ymin + ymax) / 2.0) / height
        w = (xmax - xmin) / width
        h = (ymax - ymin) / height

        yolo_boxes.append(f"{cls_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")

    return yolo_boxes


def generate_synthetic_road_damage_sample(sample_id: int, output_img_path: Path, output_lbl_path: Path):
    """
    Procedurally renders a synthetic asphalt pavement image containing
    realistic road damages (potholes, cracks) with ground-truth YOLO annotations.
    """
    w, h = 640, 640
    # Base asphalt texture with noise
    base_color = random.randint(40, 60)
    image = np.full((h, w, 3), base_color, dtype=np.uint8)
    noise = np.random.normal(0, 8, (h, w, 3)).astype(np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    annotations = []

    # Choose damage types to draw on this patch
    num_damages = random.randint(1, 3)

    for _ in range(num_damages):
        damage_type = random.choice([0, 1, 2, 3])  # 0: D00, 1: D10, 2: D20, 3: D40

        if damage_type == 0:  # Longitudinal Crack (Vertical-ish)
            x_start = random.randint(100, 540)
            y_start = random.randint(50, 200)
            length = random.randint(150, 350)
            points = [(x_start, y_start)]
            curr_x, curr_y = x_start, y_start

            for _ in range(random.randint(6, 12)):
                curr_x += random.randint(-12, 12)
                curr_y += length // 8
                curr_y = min(curr_y, h - 20)
                points.append((curr_x, curr_y))

            pts_arr = np.array(points, np.int32).reshape((-1, 1, 2))
            cv2.polylines(image, [pts_arr], isClosed=False, color=(15, 15, 15), thickness=random.randint(2, 4))

            # Bounding box
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            xmin, xmax = max(0, min(xs) - 8), min(w - 1, max(xs) + 8)
            ymin, ymax = max(0, min(ys) - 8), min(h - 1, max(ys) + 8)

        elif damage_type == 1:  # Transverse Crack (Horizontal-ish)
            x_start = random.randint(50, 150)
            y_start = random.randint(100, 540)
            length = random.randint(200, 450)
            points = [(x_start, y_start)]
            curr_x, curr_y = x_start, y_start

            for _ in range(random.randint(6, 12)):
                curr_x += length // 8
                curr_y += random.randint(-12, 12)
                curr_x = min(curr_x, w - 20)
                points.append((curr_x, curr_y))

            pts_arr = np.array(points, np.int32).reshape((-1, 1, 2))
            cv2.polylines(image, [pts_arr], isClosed=False, color=(15, 15, 15), thickness=random.randint(2, 4))

            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            xmin, xmax = max(0, min(xs) - 8), min(w - 1, max(xs) + 8)
            ymin, ymax = max(0, min(ys) - 8), min(h - 1, max(ys) + 8)

        elif damage_type == 2:  # Alligator Crack (Mesh pattern)
            cx = random.randint(150, 490)
            cy = random.randint(150, 490)
            patch_w = random.randint(80, 160)
            patch_h = random.randint(80, 160)

            # Draw interconnected lines
            for _ in range(random.randint(7, 14)):
                lx1 = cx - patch_w // 2 + random.randint(0, patch_w)
                ly1 = cy - patch_h // 2 + random.randint(0, patch_h)
                lx2 = cx - patch_w // 2 + random.randint(0, patch_w)
                ly2 = cy - patch_h // 2 + random.randint(0, patch_h)
                cv2.line(image, (lx1, ly1), (lx2, ly2), (18, 18, 18), 2)

            xmin = max(0, cx - patch_w // 2 - 5)
            xmax = min(w - 1, cx + patch_w // 2 + 5)
            ymin = max(0, cy - patch_h // 2 - 5)
            ymax = min(h - 1, cy + patch_h // 2 + 5)

        else:  # Pothole (D40)
            cx = random.randint(120, 520)
            cy = random.randint(120, 520)
            rx = random.randint(35, 75)
            ry = random.randint(25, 55)
            angle = random.randint(0, 180)

            # Draw deep black pit with darker core
            cv2.ellipse(image, (cx, cy), (rx, ry), angle, 0, 360, (20, 20, 20), -1)
            cv2.ellipse(image, (cx + 3, cy + 3), (rx - 6, ry - 6), angle, 0, 360, (8, 8, 8), -1)
            # Weathered edge
            cv2.ellipse(image, (cx, cy), (rx + 4, ry + 4), angle, 0, 360, (65, 65, 65), 2)

            xmin = max(0, cx - rx - 8)
            xmax = min(w - 1, cx + rx + 8)
            ymin = max(0, cy - ry - 8)
            ymax = min(h - 1, cy + ry + 8)

        # Calculate normalized YOLO bbox
        box_w = (xmax - xmin) / w
        box_h = (ymax - ymin) / h
        box_cx = ((xmin + xmax) / 2.0) / w
        box_cy = ((ymin + ymax) / 2.0) / h

        if box_w > 0.02 and box_h > 0.02:
            annotations.append(f"{damage_type} {box_cx:.6f} {box_cy:.6f} {box_w:.6f} {box_h:.6f}")

    # Save image and label
    cv2.imwrite(str(output_img_path), image)
    with open(output_lbl_path, "w", encoding="utf-8") as f:
        f.write("\n".join(annotations))


def build_sample_dataset(root_dir: Path, num_train: int = 40, num_val: int = 10):
    """Builds synthetic train and val directories with images and labels."""
    print(f"Creating sample road damage dataset in {root_dir}...")
    train_img_dir = root_dir / "train" / "images"
    train_lbl_dir = root_dir / "train" / "labels"
    val_img_dir = root_dir / "val" / "images"
    val_lbl_dir = root_dir / "val" / "labels"

    for d in [train_img_dir, train_lbl_dir, val_img_dir, val_lbl_dir]:
        d.mkdir(parents=True, exist_ok=True)

    print(f"Generating {num_train} synthetic training samples...")
    for i in range(num_train):
        img_p = train_img_dir / f"syn_damage_{i:04d}.jpg"
        lbl_p = train_lbl_dir / f"syn_damage_{i:04d}.txt"
        generate_synthetic_road_damage_sample(i, img_p, lbl_p)

    print(f"Generating {num_val} synthetic validation samples...")
    for i in range(num_val):
        img_p = val_img_dir / f"syn_val_damage_{i:04d}.jpg"
        lbl_p = val_lbl_dir / f"syn_val_damage_{i:04d}.txt"
        generate_synthetic_road_damage_sample(1000 + i, img_p, lbl_p)

    print(f"[SUCCESS] Sample dataset built at: {root_dir}")
    print(f"          - Train: {num_train} images")
    print(f"          - Val:   {num_val} images")


def main():
    parser = argparse.ArgumentParser(description="Prepare Road Damage Dataset for YOLO")
    parser.add_argument("--generate-sample-dataset", action="store_true", help="Generate procedural sample dataset")
    parser.add_argument("--output-dir", type=str, default="data/road_damage", help="Output dataset path")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    target_dir = project_root / args.output_dir

    if args.generate_sample_dataset or True:  # Default to building sample dataset if run directly
        build_sample_dataset(target_dir)


if __name__ == "__main__":
    main()
