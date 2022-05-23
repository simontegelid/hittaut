from datetime import timedelta
from typing import List
import urllib.parse
import logging

import requests
import requests_cache


from .models.checkpoints import Checkpoints
from .models.locations import Locations
from .opt import tsp

logger = logging.getLogger(__name__)


def get_locations():
    LOCATIONS_URL = "https://www.orientering.se/api/v1/locations/"
    r = requests.get(LOCATIONS_URL)
    return Locations.parse_obj(r.json())


def get_checkpoints(location_id):
    CHECKPOINTS_URL = (
        "https://www.orientering.se/api/v1/locations/{location_id}/checkpoints/"
    )
    r = requests.get(CHECKPOINTS_URL.format(location_id=location_id))
    return Checkpoints.parse_obj(r.json())


def generate_google_maps_directions(cps):
    def chunks(lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    BASE_URL = "https://www.google.com/maps/dir/"
    LIMIT_WPS = 10  # Google maps seems to only allow 10 waypoints

    for part in chunks(cps, LIMIT_WPS):
        params = {
            "api": 1,
            "travelmode": "walking",
            "origin": f"{part[0].lat},{part[0].lng}",
            "origin_place_id": f"{part[0].number}: {part[0].short_description}",
            "destination": f"{part[-1].lat},{part[-1].lng}",
            "destination_place_id": f"{part[-1].number}: {part[-1].short_description}",
            "waypoints": "|".join(
                f"{part[i+1].lat},{part[i+1].lng}" for i in range(len(part) - 2)
            ),
            "waypoint_place_ids": "|".join(
                f"{part[i+1].number}: {part[i+1].short_description}"
                for i in range(len(part) - 2)
            ),
        }
        yield f"{BASE_URL}?{urllib.parse.urlencode(params)}"


def opt(location, exclude: List[int], use_cache: bool):
    if use_cache:
        logger.info("Setting up HTTP cache")
        requests_cache.install_cache("hittaut", expire_after=timedelta(days=1))

    locations = get_locations()

    filtered_locations = filter(lambda l: l.name.lower() == location.lower(), locations)
    filtered_locations = list(filtered_locations)
    if len(filtered_locations) != 1:
        locs = ", ".join([f"'{l.name}'" for l in locations])
        print(f"Didn't find any location. Choose from {locs}. Exiting.")
        return

    location = filtered_locations[0]
    logging.info(f"Found location {location.name}")

    cps = list(get_checkpoints(location.id))
    logging.info(f"Got {len(cps)} checkpoints")

    optimal_route_indices, route_distance = tsp(cps)
    if not optimal_route_indices:
        return

    optimally_sorted_cps = [cps[i] for i in optimal_route_indices]

    print("Optimal path:")
    for cp in optimally_sorted_cps:
        print(f"- {cp.number}: {cp.short_description}")

    print()
    for i, url in enumerate(generate_google_maps_directions(cps)):
        print(f"Google maps URL #{i+1}:")
        print(url)
    print()

    print(f"Distance to travel {route_distance*1e-3} km")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument(
        "location",
        help="The location of checkpoints. See hittaut.nu to find the location names.",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        nargs="*",
        default=None,
        type=int,
        help="Checkpoint IDs to exclude, eg. if you already have picked some checkpoints",
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        default=False,
        help="Cache HTTP requests, to avoid hammering hittaut.nu",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level="INFO",
        format="%(asctime)s.%(msecs)03d %(message)s",
        datefmt="%Y-%m-%d,%H:%M:%S",
    )

    opt(args.location, args.exclude, args.cache)


if __name__ == "__main__":
    main()
