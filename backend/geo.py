"""
geo.py
------
Resolves what the user typed ("Washington", "Jalna") to the canonical name the
pipeline stores ("Washington, D.C.", "Jalna" with the accent the geocoder uses).

Open-Meteo's geocoder always returns the same top match for the same query, and
the pipeline stores exactly that name, so resolving with the same call makes the
cache check and the /latest lookup find the stored row.

Successful lookups are remembered in memory, so each distinct spelling costs at
most one geocoding call per backend run. If the geocoder is unreachable or finds
nothing, the typed name is used unchanged (the pipeline will then report the error).
"""

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

_known: dict[str, str] = {}


def canonical_city(typed: str) -> str:
    typed = typed.strip()
    key = typed.lower()
    if key in _known:
        return _known[key]

    try:
        resp = requests.get(GEOCODE_URL, params={"name": typed, "count": 1}, timeout=5)
        results = resp.json().get("results") if resp.status_code == 200 else None
        if results:
            _known[key] = results[0]["name"]
            return _known[key]
    except (requests.RequestException, ValueError, KeyError):
        pass
    return typed
