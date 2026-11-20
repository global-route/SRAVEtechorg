import os
import ee
import httpx


def init_gee() -> None:
    credentials = ee.ServiceAccountCredentials(
        email=os.getenv("GEE_SERVICE_ACCOUNT"),
        key_file=os.getenv("GEE_KEY_FILE"),
    )
    ee.Initialize(credentials)


def fetch_imagery(bbox: list[float], max_cloud_pct: float = 20.0, source: str = "sentinel2") -> ee.Image | None:
    """
    Pull imagery for a bounding box.
    source: "sentinel2" (default, via GEE) | "planetscope" (via Planet API, 3m resolution)
    """
    if source == "planetscope":
        return None  # PlanetScope path handled by export_geotiff_planet
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
    Export Sentinel-2 image to GeoTIFF in /tmp and return file path.
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


async def export_geotiff_planet(bbox: list[float], job_id: str) -> str:
    """
    Download a PlanetScope GeoTIFF via the Planet API (3m resolution).
    Requires PLANET_API_KEY env var.
    Returns local /tmp path.
    """
    api_key = os.getenv("PLANET_API_KEY", "")
    if not api_key:
        raise RuntimeError("PLANET_API_KEY not set")

    min_lon, min_lat, max_lon, max_lat = bbox
    geometry = {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat], [max_lon, min_lat],
            [max_lon, max_lat], [min_lon, max_lat],
            [min_lon, min_lat],
        ]],
    }

    # Quick search for most recent PSScene with <10% cloud cover
    search_payload = {
        "item_types": ["PSScene"],
        "filter": {
            "type": "AndFilter",
            "config": [
                {"type": "GeometryFilter", "field_name": "geometry", "config": geometry},
                {"type": "RangeFilter", "field_name": "cloud_cover", "config": {"lte": 0.1}},
                {"type": "StringInFilter", "field_name": "item_type", "config": ["PSScene"]},
            ],
        },
    }

    async with httpx.AsyncClient(auth=(api_key, ""), timeout=60.0) as client:
        search_res = await client.post(
            "https://api.planet.com/data/v1/quick-search",
            json=search_payload,
        )
        search_res.raise_for_status()
        features = search_res.json().get("features", [])
        if not features:
            raise RuntimeError("No PlanetScope scenes found for bbox")

        item_id = features[0]["id"]
        item_type = features[0]["properties"]["item_type"]

        # Activate analytic_sr asset
        activate_url = f"https://api.planet.com/data/v1/item-types/{item_type}/items/{item_id}/assets"
        assets_res = await client.get(activate_url)
        assets_res.raise_for_status()
        asset = assets_res.json().get("ortho_analytic_4b_sr") or assets_res.json().get("analytic_sr")
        if not asset:
            raise RuntimeError("analytic_sr asset not available for this scene")

        if asset["status"] != "active":
            await client.get(asset["_links"]["activate"])
            raise RuntimeError("PlanetScope asset activating — retry in 60s")

        # Download
        dl_res = await client.get(asset["location"])
        dl_res.raise_for_status()

    path = f"/tmp/{job_id}_planet.tif"
    with open(path, "wb") as f:
        f.write(dl_res.content)
    return path
