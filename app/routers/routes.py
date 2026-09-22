from __future__ import annotations

import asyncio
import math
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.dependencies import get_current_user
from app.schemas import RouteCalculateRequest, RouteCalculateResponse, RoutePoint


router = APIRouter(
    prefix="/routes",
    tags=["Rotas e geocodificação"],
    dependencies=[Depends(get_current_user)],
)

_geocode_cache: dict[str, tuple[float, RoutePoint]] = {}
_nominatim_lock = asyncio.Lock()
_last_nominatim_request = 0.0
CACHE_SECONDS = 60 * 60 * 24


def _cache_key(address: str) -> str:
    return " ".join(address.lower().strip().split())


def _parse_google_duration(value: str | None) -> int:
    if not value:
        return 0
    text = str(value).strip().lower().removesuffix("s")
    try:
        return int(round(float(text)))
    except ValueError:
        return 0


def _decode_google_polyline(encoded: str) -> list[list[float]]:
    if not encoded:
        return []
    coordinates: list[list[float]] = []
    index = 0
    latitude = 0
    longitude = 0
    length = len(encoded)

    while index < length:
        result = 0
        shift = 0
        while True:
            value = ord(encoded[index]) - 63
            index += 1
            result |= (value & 0x1F) << shift
            shift += 5
            if value < 0x20:
                break
        latitude += ~(result >> 1) if result & 1 else result >> 1

        result = 0
        shift = 0
        while True:
            value = ord(encoded[index]) - 63
            index += 1
            result |= (value & 0x1F) << shift
            shift += 5
            if value < 0x20:
                break
        longitude += ~(result >> 1) if result & 1 else result >> 1

        coordinates.append([latitude / 1e5, longitude / 1e5])

    return coordinates


async def _google_geocode(client: httpx.AsyncClient, address: str) -> RoutePoint:
    response = await client.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={
            "address": address,
            "key": settings.google_maps_api_key,
            "region": settings.route_country_code,
            "language": "pt-BR",
        },
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "OK" or not payload.get("results"):
        message = payload.get("error_message") or "Endereço não encontrado."
        raise HTTPException(status_code=422, detail=message)

    result = payload["results"][0]
    location = result["geometry"]["location"]
    return RoutePoint(
        input_address=address,
        formatted_address=result.get("formatted_address") or address,
        latitude=float(location["lat"]),
        longitude=float(location["lng"]),
    )


async def _google_route(payload: RouteCalculateRequest) -> RouteCalculateResponse:
    if not settings.google_maps_api_key:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_MAPS_API_KEY não está configurada.",
        )

    mode = payload.travel_mode.upper().strip()
    allowed = {"DRIVE", "WALK", "BICYCLE", "TRANSIT", "TWO_WHEELER"}
    if mode not in allowed:
        raise HTTPException(status_code=422, detail="Modo de transporte inválido.")

    timeout = httpx.Timeout(settings.route_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        origin, destination = await asyncio.gather(
            _google_geocode(client, payload.origin_address),
            _google_geocode(client, payload.destination_address),
        )

        body: dict[str, Any] = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": origin.latitude,
                        "longitude": origin.longitude,
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": destination.latitude,
                        "longitude": destination.longitude,
                    }
                }
            },
            "travelMode": mode,
            "computeAlternativeRoutes": False,
            "languageCode": "pt-BR",
            "units": "METRIC",
        }
        if mode in {"DRIVE", "TWO_WHEELER"}:
            body["routingPreference"] = "TRAFFIC_AWARE"

        response = await client.post(
            "https://routes.googleapis.com/directions/v2:computeRoutes",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": settings.google_maps_api_key,
                "X-Goog-FieldMask": (
                    "routes.duration,routes.distanceMeters,"
                    "routes.polyline.encodedPolyline"
                ),
            },
            json=body,
        )
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", {}).get("message")
            except Exception:
                detail = response.text
            raise HTTPException(
                status_code=502,
                detail=detail or "Não foi possível calcular a rota no Google Maps.",
            )

        data = response.json()
        routes = data.get("routes") or []
        if not routes:
            raise HTTPException(status_code=422, detail="Nenhuma rota encontrada.")

        route = routes[0]
        distance_meters = int(route.get("distanceMeters") or 0)
        duration_seconds = _parse_google_duration(route.get("duration"))
        encoded = (route.get("polyline") or {}).get("encodedPolyline") or ""
        coordinates = _decode_google_polyline(encoded)

    return RouteCalculateResponse(
        provider="Google Maps Routes API",
        travel_mode=mode,
        origin=origin,
        destination=destination,
        distance_meters=distance_meters,
        distance_km=round(distance_meters / 1000, 2),
        round_trip_distance_km=round(distance_meters / 500, 2),
        duration_seconds=duration_seconds,
        duration_minutes=max(1, math.ceil(duration_seconds / 60)),
        round_trip_duration_minutes=max(2, math.ceil(duration_seconds / 60) * 2),
        coordinates=coordinates,
        map_attribution="Google Maps para cálculo; mapa visual © OpenStreetMap contributors",
        warning="",
    )


async def _respect_nominatim_rate_limit() -> None:
    global _last_nominatim_request
    async with _nominatim_lock:
        elapsed = time.monotonic() - _last_nominatim_request
        wait = max(0.0, 1.05 - elapsed)
        if wait:
            await asyncio.sleep(wait)
        _last_nominatim_request = time.monotonic()


async def _nominatim_geocode(client: httpx.AsyncClient, address: str) -> RoutePoint:
    key = _cache_key(address)
    cached = _geocode_cache.get(key)
    if cached and (time.monotonic() - cached[0]) < CACHE_SECONDS:
        return cached[1]

    await _respect_nominatim_rate_limit()
    user_agent = settings.route_user_agent
    if settings.route_contact_email:
        user_agent = f"{user_agent} ({settings.route_contact_email})"

    response = await client.get(
        f"{settings.nominatim_base_url.rstrip('/')}/search",
        headers={"User-Agent": user_agent},
        params={
            "q": address,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
            "countrycodes": settings.route_country_code,
        },
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        raise HTTPException(
            status_code=422,
            detail=f"Endereço não encontrado: {address}",
        )

    result = results[0]
    point = RoutePoint(
        input_address=address,
        formatted_address=result.get("display_name") or address,
        latitude=float(result["lat"]),
        longitude=float(result["lon"]),
    )
    _geocode_cache[key] = (time.monotonic(), point)
    return point


async def _osm_route(payload: RouteCalculateRequest) -> RouteCalculateResponse:
    mode = payload.travel_mode.upper().strip()
    if mode != "DRIVE":
        raise HTTPException(
            status_code=422,
            detail=(
                "Sem uma chave do Google Maps, o modo gratuito local calcula rotas de carro. "
                "Configure GOOGLE_MAPS_API_KEY para TRANSIT, WALK, BICYCLE ou TWO_WHEELER."
            ),
        )

    timeout = httpx.Timeout(settings.route_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        origin = await _nominatim_geocode(client, payload.origin_address)
        destination = await _nominatim_geocode(client, payload.destination_address)

        coordinate_pair = (
            f"{origin.longitude},{origin.latitude};"
            f"{destination.longitude},{destination.latitude}"
        )
        response = await client.get(
            f"{settings.osrm_base_url.rstrip('/')}/route/v1/driving/{coordinate_pair}",
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
                "alternatives": "false",
            },
        )
        response.raise_for_status()
        data = response.json()
        routes = data.get("routes") or []
        if data.get("code") != "Ok" or not routes:
            raise HTTPException(status_code=422, detail="Nenhuma rota rodoviária encontrada.")

        route = routes[0]
        distance_meters = int(round(float(route.get("distance") or 0)))
        duration_seconds = int(round(float(route.get("duration") or 0)))
        raw_coordinates = (route.get("geometry") or {}).get("coordinates") or []
        # GeoJSON do OSRM vem [longitude, latitude]; Leaflet usa [latitude, longitude].
        coordinates = [[float(lat), float(lon)] for lon, lat in raw_coordinates]

    return RouteCalculateResponse(
        provider="OpenStreetMap / Nominatim / OSRM",
        travel_mode=mode,
        origin=origin,
        destination=destination,
        distance_meters=distance_meters,
        distance_km=round(distance_meters / 1000, 2),
        round_trip_distance_km=round(distance_meters / 500, 2),
        duration_seconds=duration_seconds,
        duration_minutes=max(1, math.ceil(duration_seconds / 60)),
        round_trip_duration_minutes=max(2, math.ceil(duration_seconds / 60) * 2),
        coordinates=coordinates,
        map_attribution="© OpenStreetMap contributors · roteamento OSRM",
        warning=(
            "Modo de desenvolvimento sem SLA. Para uso comercial/produção, "
            "configure GOOGLE_MAPS_API_KEY e ROUTE_PROVIDER=google."
        ),
    )


@router.get("/provider")
def route_provider():
    configured = settings.route_provider.lower().strip()
    effective = (
        "google"
        if configured == "google"
        or (configured == "auto" and bool(settings.google_maps_api_key))
        else "osm"
    )
    return {
        "configured": configured,
        "effective": effective,
        "google_configured": bool(settings.google_maps_api_key),
    }


@router.post("/calculate", response_model=RouteCalculateResponse)
async def calculate_route(payload: RouteCalculateRequest):
    provider = settings.route_provider.lower().strip()
    use_google = provider == "google" or (
        provider == "auto" and bool(settings.google_maps_api_key)
    )

    try:
        if use_google:
            return await _google_route(payload)
        return await _osm_route(payload)
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="O serviço de mapas demorou demais para responder. Tente novamente.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail="O serviço externo de mapas retornou um erro.",
        ) from exc
