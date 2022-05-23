import itertools
import logging

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import geopy.distance
import numpy as np

from .models.checkpoints import Checkpoints
from .conversion import from_latlon

logger = logging.getLogger(__name__)


def create_distance_matrix_wgs84(cps):
    def generate_distances(cps: Checkpoints):
        for cp_a, cp_b in itertools.combinations(cps, 2):
            d = geopy.distance.geodesic((cp_a.lat, cp_a.lng), (cp_b.lat, cp_b.lng)).m
            yield cps.index(cp_a), cps.index(cp_b), d

    logger.info("Build distance matrix (WGS84)")
    dists = [[0] * len(cps)] * len(cps)
    for a, b, d in generate_distances(cps):
        dists[a][b] = d
        dists[b][a] = d
    return dists


def create_distance_matrix_utm(cps):
    logger.info("Build distance matrix (UTM)")
    z = np.array([[complex(*(from_latlon(cp.lat, cp.lng)[:2])) for cp in cps]])
    distance_matrix_pre = abs(z.T - z)
    distance_matrix = np.floor(distance_matrix_pre).astype(int).tolist()
    return distance_matrix


def tsp(cps: Checkpoints):
    distance_matrix = create_distance_matrix_utm(cps)
    num_vehicles = 1
    depot = 0

    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), num_vehicles, depot)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    logger.info("Solve problem")
    solution = routing.SolveWithParameters(search_parameters)
    logger.info("Done")

    if not solution:
        logger.info("No solution found")
        return None

    index = routing.Start(0)
    route = [manager.IndexToNode(index)]
    route_distance = 0
    while not routing.IsEnd(index):
        previous_index = index
        index = solution.Value(routing.NextVar(index))
        route_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
        route.append(manager.IndexToNode(index))
    return route, route_distance
