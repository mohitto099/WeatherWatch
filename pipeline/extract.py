"""
extract.py
----------
Stage 1 of the pipeline: EXTRACT + VALIDATE (merged, per the simplified 4-task DAG).

Responsibilities:
- Resolve a city name to lat/lon (Open-Meteo Geocoding API)
- Call Open-Meteo's forecast API for current weather at that location
- Validate the HTTP response and check required fields are present

Raises WeatherAPIError on any failure so the caller (run_pipeline.py / later,
the Airflow task) can catch it, log it, and stop the pipeline cleanly rather
than passing bad data downstream.
"""

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

REQUIRED_CURRENT_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "weather_code",
]


class WeatherAPIError(Exception):
    """Raised when the city can't be resolved or the weather API fails/returns bad data."""
    pass


def geocode_city(city_name: str) -> dict:
    """Resolve a city name to {name, country, latitude, longitude}."""
    resp = requests.get(GEOCODE_URL, params={"name": city_name, "count": 1}, timeout=10)

    if resp.status_code != 200:
        raise WeatherAPIError(f"Geocoding API returned HTTP {resp.status_code} for '{city_name}'")

    data = resp.json()
    results = data.get("results")
    if not results:
        raise WeatherAPIError(f"No location found for city '{city_name}'")

    top = results[0]
    return {
        "name": top["name"],
        "country": top.get("country", ""),
        "latitude": top["latitude"],
        "longitude": top["longitude"],
    }


def fetch_current_weather(latitude: float, longitude: float) -> dict:
    """Call Open-Meteo for current weather at a given lat/lon. Returns raw API JSON."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(REQUIRED_CURRENT_FIELDS),
        "timezone": "auto",
    }
    resp = requests.get(FORECAST_URL, params=params, timeout=10)

    if resp.status_code != 200:
        raise WeatherAPIError(f"Weather API returned HTTP {resp.status_code}")

    data = resp.json()
    current = data.get("current")
    if not current:
        raise WeatherAPIError("Weather API response missing 'current' block")

    missing = [f for f in REQUIRED_CURRENT_FIELDS if f not in current]
    if missing:
        raise WeatherAPIError(f"Weather API response missing fields: {missing}")

    return data


def extract(city_name: str) -> dict:
    """
    Full extract stage for one city.
    Returns a dict combining location info + raw current-weather API response.
    """
    location = geocode_city(city_name)
    raw_weather = fetch_current_weather(location["latitude"], location["longitude"])

    return {
        "location": location,
        "raw": raw_weather,
    }


if __name__ == "__main__":
    # Quick manual test: python extract.py
    import json
    result = extract("Mumbai")
    print(json.dumps(result, indent=2))
    