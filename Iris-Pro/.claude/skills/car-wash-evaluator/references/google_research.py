#!/usr/bin/env python3
"""
Car Wash Evaluator — Google Maps API Research Helper

Fetches competitor locations, driving distances, and a Street View photo
for a given address. Run this as Step 1 of any evaluation when a Google
Maps API key is available in car-wash-config.txt.

Usage:
    python3 google_research.py "1234 Peeples Valley Rd NW, Cartersville, GA"

Output:
    - Prints a JSON summary of geocode result, competitors, and distances
    - Saves a Street View image to /tmp/street_view_<address>.jpg

API key is read from:
    /sessions/magical-upbeat-wozniak/mnt/outputs/car-wash-config.txt
    Format: GOOGLE_MAPS_API_KEY=your_key_here

APIs used (all covered under $200/month free credit):
    - Geocoding API        (~$5 / 1,000 requests)
    - Places Nearby Search (~$32 / 1,000 requests)
    - Distance Matrix API  (~$5 / 1,000 requests)
    - Street View Static   (~$7 / 1,000 requests)

NOTE: This script requires outbound internet access. It works in Claude Code
(local) but NOT in the Cowork sandbox environment due to network restrictions.
"""

import sys
import json
import os
import urllib.request
import urllib.parse


# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATHS = [
    "/sessions/magical-upbeat-wozniak/mnt/outputs/car-wash-config.txt",
    os.path.expanduser("~/car-wash-config.txt"),
    os.path.join(os.path.dirname(__file__), "../../car-wash-config.txt"),
]

COMPETITOR_RADIUS_METERS = 8047  # 5 miles


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_api_key():
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GOOGLE_MAPS_API_KEY"):
                        return line.split("=", 1)[1].strip().strip("'\"")
    return None


def api_get(url):
    resp = urllib.request.urlopen(url, timeout=15)
    return json.loads(resp.read().decode("utf-8"))


# ── API Calls ─────────────────────────────────────────────────────────────────

def geocode(address, key):
    """Convert address to lat/lng and canonical formatted address."""
    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={urllib.parse.quote(address)}&key={key}"
    )
    data = api_get(url)
    if data["status"] == "OK":
        result = data["results"][0]
        loc = result["geometry"]["location"]
        return loc["lat"], loc["lng"], result["formatted_address"]
    print(f"  [geocode] Status: {data['status']}", file=sys.stderr)
    return None, None, None


def find_competitors(lat, lng, key):
    """
    Search for tunnel/express car washes within 5 miles.
    Uses two searches (keyword variations) and deduplicates by place_id.
    Self-serve bays and gas station washes are NOT real competition —
    only tunnel/express car washes count per the evaluation framework.
    """
    seen = {}
    searches = [
        "tunnel car wash",
        "express car wash",
    ]
    for keyword in searches:
        url = (
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            f"?location={lat},{lng}"
            f"&radius={COMPETITOR_RADIUS_METERS}"
            f"&type=car_wash"
            f"&keyword={urllib.parse.quote(keyword)}"
            f"&key={key}"
        )
        data = api_get(url)
        if data["status"] in ("OK", "ZERO_RESULTS"):
            for place in data.get("results", []):
                pid = place["place_id"]
                if pid not in seen:
                    seen[pid] = {
                        "name": place.get("name"),
                        "address": place.get("vicinity"),
                        "rating": place.get("rating"),
                        "review_count": place.get("user_ratings_total"),
                        "place_id": pid,
                        "lat": place["geometry"]["location"]["lat"],
                        "lng": place["geometry"]["location"]["lng"],
                        "distance_miles": None,
                        "drive_time_min": None,
                    }
    return list(seen.values())


def add_driving_distances(origin_lat, origin_lng, competitors, key):
    """Add exact driving distance (miles) and time (min) for each competitor."""
    if not competitors:
        return competitors
    destinations = "|".join(
        f"{c['lat']},{c['lng']}" for c in competitors
    )
    url = (
        "https://maps.googleapis.com/maps/api/distancematrix/json"
        f"?origins={origin_lat},{origin_lng}"
        f"&destinations={urllib.parse.quote(destinations)}"
        f"&mode=driving"
        f"&key={key}"
    )
    data = api_get(url)
    if data["status"] == "OK":
        elements = data["rows"][0]["elements"]
        for i, elem in enumerate(elements):
            if elem["status"] == "OK":
                competitors[i]["distance_miles"] = round(
                    elem["distance"]["value"] * 0.000621371, 1
                )
                competitors[i]["drive_time_min"] = round(
                    elem["duration"]["value"] / 60, 1
                )
    competitors.sort(key=lambda c: c.get("distance_miles") or 999)
    return competitors


def fetch_street_view(lat, lng, key, output_path):
    """
    Download a 640x400 Street View image of the site's road frontage.
    Tries multiple headings to find the best road-facing view.
    Returns the output path on success, None on failure.
    """
    # Try heading 0 first (north-facing); a smarter implementation could
    # derive the road heading from the geocode result's road geometry.
    url = (
        "https://maps.googleapis.com/maps/api/streetview"
        f"?size=640x400"
        f"&location={lat},{lng}"
        f"&fov=90"
        f"&heading=0"
        f"&pitch=0"
        f"&source=outdoor"
        f"&key={key}"
    )
    try:
        resp = urllib.request.urlopen(url, timeout=15)
        content = resp.read()
        # Street View returns a small grey placeholder if no imagery exists.
        # A real image is typically >5KB; placeholders are ~1.5KB.
        if len(content) < 3000:
            return None
        with open(output_path, "wb") as f:
            f.write(content)
        return output_path
    except Exception as e:
        print(f"  [street_view] Error: {e}", file=sys.stderr)
        return None


# ── Main ──────────────────────────────────────────────────────────────────────

def run(address):
    key = read_api_key()
    if not key:
        return {"error": "API key not found. Save key to car-wash-config.txt as GOOGLE_MAPS_API_KEY=your_key"}

    print(f"  Geocoding: {address}", file=sys.stderr)
    lat, lng, formatted_address = geocode(address, key)
    if lat is None:
        return {"error": f"Could not geocode address: {address}"}

    print(f"  Searching for competitors within 5 miles of {lat}, {lng}", file=sys.stderr)
    competitors = find_competitors(lat, lng, key)

    print(f"  Getting driving distances for {len(competitors)} competitors", file=sys.stderr)
    competitors = add_driving_distances(lat, lng, competitors, key)

    safe_addr = address.replace(" ", "_").replace(",", "")[:40]
    street_view_path = f"/tmp/street_view_{safe_addr}.jpg"
    print(f"  Fetching Street View image", file=sys.stderr)
    street_view_saved = fetch_street_view(lat, lng, key, street_view_path)

    return {
        "address": formatted_address,
        "lat": lat,
        "lng": lng,
        "street_view_image": street_view_saved,
        "competitors": competitors,
        "competitor_count": len(competitors),
        "note": (
            "Review competitor names carefully — filter out self-serve bays "
            "and gas station washes. Only tunnel/express car washes count as "
            "real competition per the evaluation framework."
        ),
    }


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 google_research.py "full address"')
        sys.exit(1)
    address = " ".join(sys.argv[1:])
    result = run(address)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
