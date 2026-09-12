"""
core/tools/weather.py — Open-Meteo weather (no API key required).

Geocodes a city name with the Open-Meteo geocoding API, then fetches current
conditions. Purely read-only and HTTP-based — safe to auto-fire.
"""

from __future__ import annotations

from typing import Any

import httpx

from core.tools.base import Tool, ToolError

_GEO = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST = "https://api.open-meteo.com/v1/forecast"


class WeatherTool(Tool):
    name = "weather"
    description = "Get the current weather for a city (Open-Meteo)."
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}}

    def __init__(self, timeout: float = 15.0, data_dir: Any | None = None, settings: Any | None = None) -> None:
        self.timeout = timeout

    async def run(self, **kwargs: Any) -> str:
        query = str(kwargs.get("query", "")).strip()
        if not query or query.startswith("!"):
            raise ToolError("no city given (try 'weather in Paris')")
        city = query.lower().replace("weather in", "").replace("weather", "").strip()
        if not city:
            raise ToolError("no city given")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                geo = await client.get(_GEO, params={"name": city, "count": 1})
                geo.raise_for_status()
                hits = geo.json().get("results")
                if not hits:
                    raise ToolError(f"no city found for {city!r}")
                loc = hits[0]
                current = await client.get(
                    _FORECAST,
                    params={
                        "latitude": loc["latitude"],
                        "longitude": loc["longitude"],
                        "current_weather": "true",
                        "timezone": "auto",
                    },
                )
                current.raise_for_status()
                w = current.json()["current_weather"]
                wmo = w.get("weathercode", 0)
                desc = _WMO.get(wmo, "Unknown")
                temp = w.get("temperature", 0.0)
                return f"{loc['name']}: {desc}, {temp:.1f}°C, wind {w.get('windspeed', 0)} km/h"
            except ToolError:
                raise
            except Exception as exc:
                raise ToolError(f"weather lookup failed: {exc}") from exc


_WMO: dict[int, str] = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Dense drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Light showers",
    81: "Showers", 82: "Violent showers", 95: "Thunderstorm",
}
