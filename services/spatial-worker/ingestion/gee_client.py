import os
import ee


def init_gee() -> None:
    credentials = ee.ServiceAccountCredentials(
        email=os.getenv("GEE_SERVICE_ACCOUNT"),
        key_file=os.getenv("GEE_KEY_FILE"),
    )
    ee.Initialize(credentials)


def fetch_imagery(bbox: list[float], max_cloud_pct: float = 20.0) -> ee.Image:
    """
    Pull least-cloudy Sentinel-2 composite within the last 90 days for a bounding box.
    bbox: [min_lon, min_lat, max_lon, max_lat]
    """
    region = ee.Geometry.Rectangle(bbox)
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(
            ee.Date(ee.Date.now().advance(-90, "day")),
            ee.Date.now(),
        )
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_pct))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )
    image = collection.first().clip(region)
    return image


def export_geotiff(image: ee.Image, bbox: list[float], job_id: str, resolution_m: float = 10.0) -> str:
    """
    Export image to GeoTIFF in /tmp and return file path.
    Uses ee.data.getPixels for small LGA tiles.
    """
    import tempfile, json
    region = ee.Geometry.Rectangle(bbox)
    params = {
        "expression": image.select(["B4", "B3", "B2"]),
        "fileFormat": "GEO_TIFF",
        "grid": {
            "dimensions": {"width": 2048, "height": 2048},
            "affineTransform": {},
            "crsCode": "EPSG:4326",
        },
        "region": json.loads(region.toGeoJSONString()),
    }
    pixels = ee.data.getPixels(params)
    path = f"/tmp/{job_id}.tif"
    with open(path, "wb") as f:
        f.write(pixels)
    return path
