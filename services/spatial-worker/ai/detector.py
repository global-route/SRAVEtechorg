from __future__ import annotations
import os
import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.transform import Affine
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import torch

_yolo_model = None
_sam_predictor = None

PROPERTY_TYPE_MAP = {
    0: "residential_low",
    1: "residential_high",
    2: "commercial",
    3: "industrial",
}

TILE_SIZE  = int(os.getenv("TILE_SIZE_PX",  640))
OVERLAP_PX = int(os.getenv("TILE_OVERLAP_PX", 20))


def _load_yolo():
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO
        _yolo_model = YOLO("/models/yolov8m-seg.pt")
    return _yolo_model


def _load_sam():
    global _sam_predictor
    if _sam_predictor is None:
        from segment_anything import sam_model_registry, SamPredictor
        sam = sam_model_registry["vit_h"](checkpoint="/models/sam_vit_h_4b8939.pth")
        sam.to("cuda" if torch.cuda.is_available() else "cpu")
        _sam_predictor = SamPredictor(sam)
    return _sam_predictor


def _tile_image(img: np.ndarray, tile_size: int, overlap: int):
    """Yield (tile_array, row_offset, col_offset) for each patch."""
    h, w = img.shape[:2]
    stride = tile_size - overlap
    for row in range(0, h, stride):
        for col in range(0, w, stride):
            r_end = min(row + tile_size, h)
            c_end = min(col + tile_size, w)
            tile = img[row:r_end, col:c_end]
            # Pad to tile_size if at edge
            if tile.shape[0] < tile_size or tile.shape[1] < tile_size:
                pad = np.zeros((tile_size, tile_size, 3), dtype=img.dtype)
                pad[:tile.shape[0], :tile.shape[1]] = tile
                tile = pad
            yield tile, row, col


def _tile_transform(base_transform: Affine, row_off: int, col_off: int) -> Affine:
    """Shift the affine transform to the tile's origin."""
    x_off = base_transform.c + col_off * base_transform.a
    y_off = base_transform.f + row_off * base_transform.e
    return Affine(base_transform.a, base_transform.b, x_off,
                  base_transform.d, base_transform.e, y_off)


def detect_buildings(tif_path: str) -> list[dict]:
    """
    Tile GeoTIFF into TILE_SIZE x TILE_SIZE patches with OVERLAP_PX overlap,
    run YOLOv8 + SAM per tile, merge and deduplicate footprints.
    """
    model     = _load_yolo()
    predictor = _load_sam()

    with rasterio.open(tif_path) as src:
        img       = src.read([1, 2, 3]).transpose(1, 2, 0)   # HWC RGB
        transform = src.transform
        scan_date = src.tags().get("TIFFTAG_DATETIME", "")

    raw: list[dict] = []

    for tile, row_off, col_off in _tile_image(img, TILE_SIZE, OVERLAP_PX):
        tile_transform = _tile_transform(transform, row_off, col_off)
        detections = model.predict(tile, conf=0.45, iou=0.5, verbose=False)
        predictor.set_image(tile)

        for det in detections[0].boxes:
            box      = det.xyxy[0].cpu().numpy().astype(int)
            conf     = float(det.conf[0])
            cls      = int(det.cls[0])
            prop_type = PROPERTY_TYPE_MAP.get(cls, "residential_low")

            masks, _, _ = predictor.predict(box=box, multimask_output=False)
            mask = masks[0].astype(np.uint8)

            for geom, val in shapes(mask, transform=tile_transform):
                if val == 1:
                    poly = shape(geom).simplify(0.000005)
                    if not poly.is_valid or poly.is_empty:
                        continue
                    raw.append({
                        "poly":          poly,
                        "confidence":    conf,
                        "property_type": prop_type if conf >= 0.6 else "residential_low",
                        "needs_field_review": conf < 0.6,
                        "scan_date":     scan_date,
                    })

    # Deduplicate: merge polygons whose centroids are within 2m of each other
    results: list[dict] = []
    used = [False] * len(raw)
    for i, a in enumerate(raw):
        if used[i]:
            continue
        group = [a["poly"]]
        for j, b in enumerate(raw[i + 1:], start=i + 1):
            if not used[j] and a["poly"].centroid.distance(b["poly"].centroid) < 0.00002:
                group.append(b["poly"])
                used[j] = True
        merged = unary_union(group).simplify(0.000005)
        results.append({
            "footprint_geojson": mapping(merged),
            "confidence":        a["confidence"],
            "property_type":     a["property_type"],
            "needs_field_review": a["needs_field_review"],
            "scan_date":         a["scan_date"],
        })
        used[i] = True

    return results
