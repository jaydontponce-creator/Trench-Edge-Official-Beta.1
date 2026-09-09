from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any
from .base import HTTPProvider

class OpenMeteoProvider(HTTPProvider):
    url = "https://api.open-meteo.com/v1/forecast"
    @property
    def ready(self): return True
    def game_weather(self, lat: float, lon: float, kickoff_iso: str, timezone: str="auto"):
        data = self.get_json(self.url, params={
            "latitude":lat,"longitude":lon,
            "hourly":"temperature_2m,precipitation_probability,precipitation,wind_speed_10m,wind_gusts_10m",
            "temperature_unit":"fahrenheit","wind_speed_unit":"mph","precipitation_unit":"inch",
            "timezone":timezone,"forecast_days":16
        })
        hourly=data.get("hourly",{}); times=hourly.get("time",[])
        if not times: return None
        target = datetime.fromisoformat(kickoff_iso.replace("Z","+00:00"))
        # Open-Meteo returns local naive timestamps when timezone=auto. Match by closest clock hour if offsets differ.
        best_i=min(range(len(times)), key=lambda i: abs((datetime.fromisoformat(times[i]).replace(tzinfo=None)-target.replace(tzinfo=None)).total_seconds()))
        return {
            "temperature_f": hourly.get("temperature_2m",[None]*len(times))[best_i],
            "precip_probability": hourly.get("precipitation_probability",[None]*len(times))[best_i],
            "precip_in": hourly.get("precipitation",[None]*len(times))[best_i],
            "wind_mph": hourly.get("wind_speed_10m",[None]*len(times))[best_i],
            "gust_mph": hourly.get("wind_gusts_10m",[None]*len(times))[best_i],
            "forecast_time": times[best_i], "source":"Open-Meteo"
        }
