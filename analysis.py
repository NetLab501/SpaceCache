from geopy.distance import geodesic
from typing import List, Tuple
import deployment

def read_gateway(gw_file: str) -> Tuple[List[str], List[Tuple[float, float]]]:
    gs_num = []
    gs_loc = []
    with open(gw_file, "r") as file:
        for line in file:
            if '"town":' in line:
                town = line.split('"town": "')[1].split('",')[0]
                gs_num.append(town)
            elif '"lat":' in line:
                lat = float(line.split('"lat": ')[1].split(',')[0])
            elif '"lng":' in line:
                lng = float(line.split('"lng": ')[1].split(',')[0])
                gs_loc.append((lat, lng))

    return gs_num, gs_loc

def get_parameters(path: str) -> list:
    with open(path, "r") as f:
        lines = f.readlines()
    parameter = [[0 for _ in range(len(lines[0].strip('\n').split(',')))] for _ in range(6)]
    for row, line in enumerate(lines):
        values = line.strip('\n').split(',')
        for i in range(len(values)):
            if row != 0:
                parameter[row][i] = float(values[i])
            else:
                parameter[row][i] = values[i]
    return parameter

def get_density(city: str) -> Tuple[List[int], List[int]]:
    user_density = []
    user_type = []
    with open(city, "r") as f:
        for line in f:
            values = line.strip('\n').split('\t')
            user_density.append(int(int(values[-2]) / 1000))
            user_type.append(int(values[-1]))
    return user_density, user_type

def get_dc_hav(gs_loc: List[Tuple[float, float]], dc: str) -> List[Tuple[int, float, float]]:
    dc_lat_long = []
    nearest_dc = []
    speed = 299792.458  # km/ms

    with open(dc, "r") as f:
        for line in f:
            values = line.strip('\n').split('\t')
            dc_lat_long.append((float(values[-2]), float(values[-1])))

    for gs_num, (gs_lat, gs_long) in enumerate(gs_loc):
        distance_list = []
        for lat, long in dc_lat_long:
            distance = geodesic((gs_lat, gs_long), (lat, long)).km
            distance_list.append((gs_num, distance, distance / speed * 1000))
        distance_list.sort(key=lambda x: x[1])
        nearest_dc.append(distance_list[0])
    return nearest_dc

def get_distance_hav(gs_loc: List[Tuple[float, float]], city: str) -> List[int]:
    city_lat_long = []
    nearest_gs = []
    with open(city, "r") as f:
        for line in f:
            values = line.strip('\n').split('\t')
            city_lat_long.append((float(values[-4]), float(values[-3])))

    for city_num, (city_lat, city_long) in enumerate(city_lat_long):
        distance_list = []
        for gs_num, (gs_lat, gs_long) in enumerate(gs_loc):
            distance = geodesic((city_lat, city_long), (gs_lat, gs_long)).km
            distance_list.append((gs_num, distance))
        distance_list.sort(key=lambda x: x[1])
        nearest_gs.append(distance_list[0][0])
    return nearest_gs

def get_city_dc_hav(city: str, dc: str) -> List[int]:
    city_lat_long = []
    dc_lat_long = []
    nearest_city_dc = []
    with open(city, "r") as f:
        for line in f:
            values = line.strip('\n').split('\t')
            city_lat_long.append((float(values[-4]), float(values[-3])))
    with open(dc, "r") as f:
        for line in f:
            values = line.strip('\n').split('\t')
            dc_lat_long.append((float(values[-2]), float(values[-1])))
    for city_num, (city_lat, city_long) in enumerate(city_lat_long):
        distance_list = []
        for dc_num, (dc_lat, dc_long) in enumerate(dc_lat_long):
            distance = geodesic((city_lat, city_long), (dc_lat, dc_long)).km
            distance_list.append((dc_num, distance))
        distance_list.sort(key=lambda x: x[1])
        nearest_city_dc.append(distance_list[0][0])
    return nearest_city_dc

def perform_benchmark():
    # Use your specified file structure and names
    path = 'etc\\' + 'parameter.txt'
    gs = 'starlink_gateway\\' + 'gw.txt'
    dc = 'datacenters\\' + 'dcs.txt'
    city = 'popular_cities\\' + 'cities.txt'

    gs_name, gs_loc = read_gateway(gs)
    nearest_dc = get_dc_hav(gs_loc, dc)
    user_density, user_type = get_density(city)
    constellation_parameter = get_parameters(path)
    nearest_gs = get_distance_hav(gs_loc, city)
    nearest_city_dc = get_city_dc_hav(city, dc)

    # Call deployment's main placement function
    deployment.placement(
        constellation_parameter,
        nearest_gs,
        nearest_dc,
        nearest_city_dc,
        user_density
    )

if __name__ == '__main__':
    perform_benchmark()