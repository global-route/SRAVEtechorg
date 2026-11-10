from __future__ import annotations
import numpy as np
import rasterio
from rasterio.transform import rowcol
from rasterio.features import shapes
from shapely.geometry import shape, mapping
import torch

_yolo_model = None
_sam_predictor = None

PROPERTY_TYPE_MAP = {
    0: "residential_low",
    1: "residential_high",
    2: "commercial",
    3: "industrial",
}


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


def detect_buildings(tif_path: str) -> list[dict]:
    """
    Run YOLOv8 + SAM on a GeoTIFF.
    Returns list of dicts: {footprint_geojson, confidence, property_type, scan_date}
    """
    results = []
    model = _load_yolo()
    predictor = _load_sam()

    with rasterio.open(tif_path) as src:
        img = src.read([1, 2, 3]).transpose(1, 2, 0)  # HWC RGB
        transform = src.transform
        scan_date = src.tags().get("TIFFTAG_DATETIME", "")

    detections = model.predict(img, conf=0.45, iou=0.5, verbose=False)
    predictor.set_image(img)

    for det in detections[0].boxes:
        box = det.xyxy[0].cpu().numpy().astype(int)
        conf = float(det.conf[0])
        cls = int(det.cls[0])
        prop_type = PROPERTY_TYPE_MAP.get(cls, "residential_low")

        # SAM mask from bounding box prompt
        masks, _, _ = predictor.predict(box=box, multimask_output=False)
        mask = masks[0].astype(np.uint8)

        # Convert mask to GeoJSON polygon
        for geom, val in shapes(mask, transform=transform):
            if val == 1:
                poly = shape(geom).simplify(0.000005)
                results.append({
                    "footprint_geojson": mapping(poly),
                    "confidence": conf,
                    "property_type": prop_type if conf >= 0.6 else "residential_low",
                    "needs_field_review": conf < 0.6,
                    "scan_date": scan_date,
                })
    return results
