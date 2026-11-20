#!/usr/bin/env bash
# Download YOLOv8 and SAM model checkpoints to /models volume.
# Run as an init container or manually before first ingest.
set -euo pipefail

MODELS_DIR="${MODELS_DIR:-/models}"
mkdir -p "$MODELS_DIR"

YOLO_URL="https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8m-seg.pt"
YOLO_PATH="$MODELS_DIR/yolov8m-seg.pt"
SAM_URL="https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"
SAM_PATH="$MODELS_DIR/sam_vit_h_4b8939.pth"

download_if_missing() {
  local url="$1" path="$2" name="$3"
  if [ -f "$path" ]; then
    echo "$name already present at $path"
    return
  fi
  echo "Downloading $name..."
  curl -fL --progress-bar -o "$path" "$url"
  echo "$name downloaded: $(du -sh "$path" | cut -f1)"
}

download_if_missing "$YOLO_URL" "$YOLO_PATH" "YOLOv8m-seg"
download_if_missing "$SAM_URL"  "$SAM_PATH"  "SAM ViT-H"

echo "All models ready in $MODELS_DIR"
ls -lh "$MODELS_DIR"
