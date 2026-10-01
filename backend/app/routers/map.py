import httpx
from fastapi import APIRouter, HTTPException
from ..config import settings

router = APIRouter(prefix="/map", tags=["Maps & Routing"])

@router.get("/route")
async def route(start_lat: float,start_lng: float,end_lat: float,end_lng: float):
    url=f"{settings.OSRM_URL}/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}"
    async with httpx.AsyncClient(timeout=10) as client:
        r=await client.get(url,params={"overview":"full","geometries":"geojson"})
    if r.status_code != 200: raise HTTPException(502,"Routing service unavailable")
    data=r.json()
    if not data.get("routes"): raise HTTPException(404,"No route found")
    rt=data["routes"][0]
    return {"distance_m":rt["distance"],"duration_s":rt["duration"],"geometry":rt["geometry"]}
