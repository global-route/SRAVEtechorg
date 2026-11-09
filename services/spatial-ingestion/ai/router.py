from fastapi import APIRouter

router = APIRouter()


@router.post("/extract/{job_id}")
async def extract_footprints(job_id: str):
    # TODO: run SAM + YOLOv8 on imagery from job_id, write polygons to detected_buildings
    return {"job_id": job_id, "status": "processing", "model": "YOLOv8+SAM"}
