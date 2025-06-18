import time
from gurobipy import *

class Para:
    """
    Parameter base class for problem settings.
    """
    def __init__(self, satellite_num, ground_station_num, city_num):
        self.satellite_num = satellite_num
        self.ground_station_num = ground_station_num
        self.city_num = city_num

class Heuristic(Para):
    """
    Heuristic and optimization class for satellite cache placement.
    """
    def __init__(self, satellite_num, ground_station_num, city_num):
        super().__init__(satellite_num, ground_station_num, city_num)
        self.name = "heuristic"

    def process(self, all_city_vis_mat, all_city_vis_list, all_gs_vis_mat, all_gs_vis_list, city_density_list, nearest_city_dc, deploy_num):
        """
        Prepare network state and solve the optimization.
        """
        self.get_network_state(
            all_city_vis_mat, all_city_vis_list,
            all_gs_vis_mat, all_gs_vis_list,
            city_density_list, nearest_city_dc, deploy_num
        )
        self.math_solution()

    def get_network_state(self, all_city_vis_mat, all_city_vis_list, all_gs_vis_mat, all_gs_vis_list, city_density_list, nearest_city_dc, deploy_num):
        """
        Store all problem instance parameters as class members.
        """
        self.all_city_vis_mat = all_city_vis_mat
        self.all_city_vis_list = all_city_vis_list
        self.all_gs_vis_mat = all_gs_vis_mat
        self.all_gs_vis_list = all_gs_vis_list
        self.city_density_list = city_density_list
        self.deploy_num = deploy_num
        self.visible_gs = self.deploy_num * len(self.all_city_vis_mat)
        self.x = [0 for _ in range(self.satellite_num)]
        self.y = [[[0 for _ in range(len(self.all_city_vis_mat))] for _ in range(self.city_num)] for _ in range(self.satellite_num)]
        self.x_map = []
        self.y_map = [[] for _ in range(len(self.all_city_vis_mat))]
        self.nearest_city_dc = nearest_city_dc
        self.satcap = 2000
        self.lambdaa = 0.01

    def get_variables(self, model):
        """
        Add Gurobi variables for the optimization problem.
        """
        x = model.addVars(self.satellite_num, lb=0, ub=1, vtype=GRB.CONTINUOUS, name="x")
        y = model.addVars(self.satellite_num, self.city_num, len(self.all_city_vis_mat), lb=0, ub=1, vtype=GRB.CONTINUOUS, name="y")
        d = model.addVar(vtype=GRB.CONTINUOUS, name="d")
        return x, y, d

    def math_solution(self):
        """
        Formulate and solve the cache placement problem using Gurobi.
        """
        try:
            model = Model(self.name)
            model.setParam('OutputFlag', False)
            model.setParam('TimeLimit', 180)

            x, y, d = self.get_variables(model)

            # Number of satellites deployed
            model.addConstr(quicksum(x[i] for i in range(self.satellite_num)) == self.deploy_num, name="deploy")

            # Coverage constraints
            model.addConstrs(
                (y[i, k, t] <= x[i] * self.all_city_vis_mat[t][k][i]
                 for i in range(self.satellite_num)
                 for k in range(self.city_num)
                 for t in range(len(self.all_city_vis_mat))),
                name='coverage'
            )

            # Satellite capacity constraints
            model.addConstrs(
                (quicksum(y[i, k, t] * self.city_density_list[k]
                          for k in range(self.city_num)) <= self.satcap
                 for i in range(self.satellite_num)
                 for t in range(len(self.all_city_vis_mat))),
                name='satcap'
            )

            # Objective constraint
            model.addConstrs(
                (quicksum(y[i, k, t] * self.city_density_list[k] for i in range(self.satellite_num) for k in range(self.city_num))
                 + self.lambdaa * quicksum(y[i, k, t] * self.city_density_list[k] * self.nearest_city_dc[k]
                                           for i in range(self.satellite_num) for k in range(self.city_num))
                 >= d
                 for t in range(len(self.all_city_vis_mat))),
                name='ddd'
            )

            # Maximize d
            model.setObjective(d, GRB.MAXIMIZE)
            model.update()

            self.opt_start_time = time.time()
            model.optimize()
            self.opt_end_time = time.time()
            status = model.status
            print(f"name: {self.name}, status = {status}")
            if status == 3:
                return

            print(f'The optimal objective is {model.objVal}\n')

            if status == GRB.Status.UNBOUNDED:
                print('The model cannot be solved because it is unbounded')
                return

            if status in (GRB.Status.OPTIMAL, GRB.Status.TIME_LIMIT):
                self.res = model.objVal
                self.d = [0 for _ in range(self.satellite_num)]
                self.cache_list = []
                for v in model.getVars():
                    if v.x == 0:
                        continue
                    varname = v.varName
                    if "d" in varname:
                        self.uvalue = v.x
                    elif "x" in varname:
                        idx = int(varname.replace("x[", "").replace("]", ""))
                        self.x[idx] = v.x
                        self.x_map.append((idx, v.x))
                        self.cache_list.append(idx)
                    elif "y" in varname:
                        parts = varname.replace("y[", "").replace("]", "").split(',')
                        sateid, cityid, timeid = map(int, parts)
                        self.y[sateid][cityid][timeid] = v.x
                        self.y_map[timeid].append((sateid, cityid, v.x))

            elif status not in (GRB.Status.INF_OR_UNBD, GRB.Status.INFEASIBLE):
                print(f'Optimization was stopped with status {status}')
        except GurobiError as e:
            print('Gurobi Error reported:', e)
