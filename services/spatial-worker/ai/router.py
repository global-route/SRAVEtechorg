from fastapi import APIRouter

router = APIRouter()


@router.post("/extract/{job_id}")
async def extract_footprints(job_id: str):
    # TODO: load YOLOv8 + SAM, tile GeoTIFF, run inference, write polygons to PostGIS
    return {"job_id": job_id, "status": "processing", "models": ["YOLOv8m-seg", "SAM-ViT-H"]}
