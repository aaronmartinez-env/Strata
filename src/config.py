import os

BASE_PATH = os.path.join(os.path.dirname(__file__), "../data/")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "../outputs/")

POLLUTANTS = ["pm25", "pm10", "no2", "o3"]

WEIGHTS = {
    "pm25": 0.4,
    "pm10": 0.3,
    "no2": 0.2,
    "o3": 0.1
}

# Valencia bounding box (approx)
VALENCIA_BOUNDS = {
    "lat_min": 39.42,
    "lat_max": 39.52,
    "lon_min": -0.42,
    "lon_max": -0.33
}
