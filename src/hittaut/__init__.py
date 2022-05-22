import sys
from datetime import timedelta
import itertools
from typing import List

import requests
import requests_cache

import six

sys.modules["sklearn.externals.six"] = six
import mlrose
import numpy as np
import geopy.distance

from .models.checkpoints import Checkpoints
from .models.locations import Locations
from .conversion import from_latlon


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


def generate_distances(cps: Checkpoints):
    for cp_a, cp_b in itertools.combinations(cps, 2):
        d = geopy.distance.geodesic((cp_a.lat, cp_a.lng), (cp_b.lat, cp_b.lng)).m
        yield cps.index(cp_a), cps.index(cp_b), d


def opt(location, exclude: List[int], use_cache: bool):
    if use_cache:
        print("Setting up HTTP cache")
        requests_cache.install_cache("hittaut", expire_after=timedelta(days=1))

    locations = get_locations()

    filtered_locations = filter(lambda l: l.name.lower() == location.lower(), locations)
    filtered_locations = list(filtered_locations)
    if len(filtered_locations) != 1:
        locs = ", ".join([f"'{l.name}'" for l in locations])
        print(f"Didn't find any location. Choose from {locs}. Exiting.")
        return

    location = filtered_locations[0]
    print(f"Found location {location.name}")

    cps = list(get_checkpoints(location.id))
    print(f"Got {len(cps)} checkpoints")

    use_geodesic_dist = False
    if use_geodesic_dist:
        # This is suuuuuuuuuuuuuper slow in mlrose
        dist_list = list(generate_distances(cps))
        fitness_fn = mlrose.TravellingSales(distances=dist_list)
    else:
        # Convert WGS84 to UTM to allow mlrose to use np.linalg.norm to
        # evaluate fitness and still come close to the truth. Much faster.
        coords_list = [from_latlon(cp.lat, cp.lng)[0:2] for cp in cps]
        fitness_fn = mlrose.TravellingSales(coords=coords_list)

    print("Optimizing, this might take a while...")
    problem_fit = mlrose.TSPOpt(
        length=len(cps),
        fitness_fn=fitness_fn,
        maximize=False,
    )
    best_state, best_fitness = mlrose.genetic_alg(
        problem_fit,
        pop_size=600,
        mutation_prob=0.2,
        max_attempts=1000,
        # random_state=2,
    )

    optimally_sorted_cps = [cps[i] for i in best_state]
    print("Optimal path:")
    for cp in optimally_sorted_cps:
        print(f"- {cp.number}: {cp.short_description}")
    print(f"Distance to travel {best_fitness*1e-3} km")


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

    opt(args.location, args.exclude, args.cache)


if __name__ == "__main__":
    main()
