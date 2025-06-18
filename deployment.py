import copy
import networkx as nx
import scipy.io as scio
from gurobi import *

interval = 60

def rounding_solution(x_map, deploy_num, user_density, all_sate_city_list):
    """
    Select cache satellites by greedy rounding.

    Args:
        x_map: List of (satellite, value) tuples (fractional result).
        deploy_num: Number of satellites to select.
        user_density: List of user density per city.
        all_sate_city_list: Time series of [satellite][city] visibility lists.

    Returns:
        List of selected satellite indices.
    """
    cache_satellite_list = []
    remain_sat = []
    deployed = [[] for _ in range(len(all_sate_city_list))]

    # Sort by value descending
    rounding_list = copy.deepcopy(x_map)
    rounding_list.sort(key=lambda t: t[1], reverse=True)
    for sat, _ in rounding_list:
        remain_sat.append(sat)

    for _ in range(deploy_num):
        potential_increase = []
        for sat in remain_sat:
            ideal = 0
            unique = 0
            for t in range(len(all_sate_city_list)):
                for city in all_sate_city_list[t][sat]:
                    ideal += user_density[city]
                    if city not in deployed[t]:
                        unique += user_density[city]
            potential_increase.append((sat, ideal, unique))
        # Prefer satellite with most unique coverage, then ideal
        potential_increase.sort(key=lambda x: (x[2], x[1]), reverse=True)
        selected_sat = potential_increase[0][0]
        cache_satellite_list.append(selected_sat)
        for t in range(len(all_sate_city_list)):
            deployed[t].extend(all_sate_city_list[t][selected_sat])
        remain_sat.remove(selected_sat)

    return cache_satellite_list

def placement(parameter, nearest_gs, nearest_dc, nearest_city_dc, user_density):
    """
    Main placement workflow for satellite cache/network simulation.

    Args:
        parameter: Constellation configuration list.
        nearest_gs: List of nearest GS for each city.
        nearest_dc: List of nearest DC for each GS.
        nearest_city_dc: List of nearest DC for each city.
        user_density: User density per city.
    """

    constellation_num = 1
    for constellation_index in range(constellation_num):
        constellation_name = parameter[0][constellation_index]
        satellite_num = int(parameter[1][constellation_index])
        cycle = int(parameter[2][constellation_index])
        bound = parameter[5][constellation_index]
        R = 6371 * 1000
        ground_station_num = 165
        city_num = 80

        all_city_vis_mat = []
        all_city_vis_list = []
        all_sate_city_list = []
        all_gs_vis_mat = []
        all_gs_vis_list = []
        all_sate_gs_list = []
        all_city_gs_list = []

        for time in range(1, cycle + 1, 1):
            if (time - 1) % interval != 0:
                continue
            print(time)
            G = nx.Graph()
            edge = []

            city_sat_vis_mat = [[0] * satellite_num for _ in range(city_num)]
            city_sat_vis_list = [[] for _ in range(city_num)]
            sat_city_vis_list = [[] for _ in range(satellite_num)]

            gs_sat_vis_mat = [[0] * satellite_num for _ in range(ground_station_num)]
            gs_sat_vis_list = [[] for _ in range(ground_station_num)]
            sat_gs_vis_list = [[] for _ in range(satellite_num)]

            path = f'satellite_data\\{constellation_name}\\delay\\{time}.mat'
            data = scio.loadmat(path)
            delay = data['delay']

            G.add_nodes_from(range(satellite_num + ground_station_num + city_num))

            # Build graph and visibility lists
            for i in range(satellite_num):
                for j in range(satellite_num, satellite_num + ground_station_num):
                    if delay[i][j] < bound:
                        edge.append((i, j, delay[i][j]))
                        gs_sat_vis_mat[j - satellite_num][i] = 1
                        gs_sat_vis_list[j - satellite_num].append(i)
                        sat_gs_vis_list[i].append(j - satellite_num)
                for j in range(satellite_num + ground_station_num, satellite_num + ground_station_num + city_num):
                    if delay[i][j] < bound:
                        edge.append((i, j, delay[i][j]))
                        city_sat_vis_mat[j - satellite_num - ground_station_num][i] = 1
                        city_sat_vis_list[j - satellite_num - ground_station_num].append(i)
                        sat_city_vis_list[i].append(j - satellite_num - ground_station_num)
            G.add_weighted_edges_from(edge)

            all_city_vis_mat.append(city_sat_vis_mat)
            all_city_vis_list.append(city_sat_vis_list)
            all_sate_city_list.append(sat_city_vis_list)
            all_gs_vis_mat.append(gs_sat_vis_mat)
            all_gs_vis_list.append(gs_sat_vis_list)
            all_sate_gs_list.append(sat_gs_vis_list)

            # City-to-GS latency information
            temp_save = []
            for ii, city_vis in enumerate(city_sat_vis_list):
                city_temp_list = []
                for satt in city_vis:
                    city_sat_latency = delay[satt][satellite_num + ground_station_num + ii]
                    if sat_gs_vis_list[satt]:
                        temp_latency_list = [
                            (gss, delay[satt][satellite_num + gss] + city_sat_latency)
                            for gss in sat_gs_vis_list[satt]
                        ]
                        city_temp_list.extend(temp_latency_list)
                city_temp_list.sort(key=lambda x: x[1])
                temp_save.append(city_temp_list)
            all_city_gs_list.append(temp_save)

        deploy_num = 44
        heuristic = Heuristic(satellite_num, ground_station_num, city_num)
        heuristic.process(
            all_city_vis_mat, all_city_vis_list,
            all_gs_vis_mat, all_gs_vis_list,
            user_density, nearest_city_dc, deploy_num
        )

        heuristic_cache_list = rounding_solution(
            heuristic.x_map, heuristic.deploy_num, user_density, all_sate_city_list
        )