"""Nhận một hoán vị, cắt thành các tuyến, đi dọc từng tuyế để 
tính giờ đến và tải trọng rồi ra3 mục tiêu"""

from __future__ import annotations
import numpy as np
from src.instance import Instance

MINUTES_PER_HOUR = 60.0

def evaluate(perm: list[int], inst: Instance) -> tuple[float, float, float]:
    d = evaluate_detail(perm, inst)
    return float(d["f1"]), float(d["f2"]), float(d["f3"])

def evaluate_detail(perm: list[int], inst: Instance) -> dict:
    return evaluate_routes_detail(split_greedy(perm, inst), inst)

def split_greedy(perm: list[int], inst: Instance) -> list[list[int]]:
    '''Đi dọc hoán vị, cộng dồn demand, quá tải trọng thì mở tuyến mới'''
    routes: list[list[int]] = []
    current: list[int] = []
    load = 0.0
    for c in perm:
        d = inst.demand[c]
        if current and load + d > inst.capacity:
            routes.append(current)
            current, load = [], 0.0
        current.append(c)
        load += d
    if current:
        routes.append(current)
    return routes

def emission_factor(params: dict) ->float:
    v = params["speed_kmh"]
    p, q = params["emission"]["phi"], params["emission"]["psi"]
    phi = p["c0"] + p["c1"] * v**3 + p["c2"] / v
    psi = q["d0"] + q["d1"] * v + q["d2"] * v**2 + q["d3"] / v
    return phi * psi

def satisfaction(t: float, et: float, eta: float, ltb: float, lt: float) -> float:
    '''Hàm hình thang W(t), thang 0 -100'''
    if t < et or t > lt:
        return 0.0
    if t < eta:
        return 100.0 * (t-et) / (eta - et)
    if t <= ltb:
        return 100.0
    return 100.0 * (lt - t) / (lt - ltb)

def _check_routes(routes: list[list[int]], inst: Instance) -> None:
    visited = sorted(c for r in routes for c in r)
    if visited != list(range(1, inst.n + 1)):
        raise ValueError("các tuyến phải phủ mỗi khách 1..n đúng 1 lần")
    for r in routes:
        if inst.demand[r].sum() > inst.capacity:
            raise ValueError(f"tuyến {r} vượt tải trọng {inst.capacity} kg")

def evaluate_routes_detail(routes: list[list[int]], inst: Instance) -> dict:
    '''Tính mọi thứ từ một bộ tuyến có sẵn. Mọi đường tính toán đều đi qua hàm này.'''
    _check_routes(routes, inst)
    cost = inst.params["cost"]
    v = inst.params["speed_kmh"]
    sat_at_arrival = inst.params["satisfaction_time"] == "arrival"
    fuel_slope = (cost["rho_star"] - cost["rho0"]) / inst.capacity  # L/km trên mỗi kg hàng

    fuel_l = 0.0       # tổng lít nhiên liệu, dùng cho F1
    total_km = 0.0     # tổng quãng đường, dùng cho F3 và f2
    early_min = 0.0    # tổng số phút đến sớm so với ETa, dùng cho F4
    late_min = 0.0     # tổng số phút đến muộn so với LTb, dùng cho F4
    sat_sum = 0.0      # tổng W của mọi khách, dùng cho f3
    arrival = np.full(inst.n + 1, np.nan)  # giờ đến từng khách, ô 0 (kho) để trống
    route_lengths, route_loads = [], []

    for route in routes:
        load = float(inst.demand[route].sum())  # xe rời kho chở đủ hàng cho cả tuyến
        route_loads.append(load)
        t = inst.depart_time                     # giờ xe rời điểm hiện tại
        prev = 0                                 # điểm hiện tại, bắt đầu từ kho
        length = 0.0

        for c in route:
            d = inst.dist[prev, c]
            length += d
            fuel_l += d * (cost["rho0"] + fuel_slope * load)   # tải tính trước khi giao cho c

            arrive = t + d / v * MINUTES_PER_HOUR               # v tính km/h, đổi ra phút
            arrival[c] = arrive
            et, lt = inst.tw_specified[c]
            eta, ltb = inst.tw_expected[c]

            early_min += max(eta - arrive, 0.0)
            late_min += max(arrive - ltb, 0.0)
            #sat_sum += satisfaction(arrive, et, eta, ltb, lt)  # W tính theo GIỜ ĐẾN (mục 4.1)

            #t = max(arrive, eta) + inst.service_time[c]         # đến sớm thì chờ tới ETa rồi mới dỡ hàng
            start = max(arrive, eta)
            t_sat = arrive if sat_at_arrival else start
            sat_sum += satisfaction(t_sat, et, eta, ltb, lt)
            t = start + inst.service_time[c]
            load -= inst.demand[c]
            prev = c

        d = inst.dist[prev, 0]                                   # chặng về kho, lúc này xe rỗng
        length += d
        fuel_l += d * (cost["rho0"] + fuel_slope * load)

        route_lengths.append(length)
        total_km += length

    F1 = cost["sigma1"] * fuel_l                 # tiền nhiên liệu
    F2 = cost["sigma2"] * len(routes)            # chi phí cố định mỗi xe
    F3 = cost["sigma3"] * total_km               # chi phí theo km
    F4 = (cost["alpha"] * early_min + cost["beta"] * late_min) / MINUTES_PER_HOUR  # phạt, phút -> giờ

    f1 = F1 + F2 + F3 + F4
    f2 = emission_factor(inst.params) * total_km / inst.params["emission"]["grams_per_kg"]  # g -> kg
    f3 = sat_sum / 100.0 / inst.n                # thang 0-1, chiều max

    return {
        "routes": routes,
        "route_lengths": route_lengths,
        "route_loads": route_loads,
        "arrival_times": arrival,
        "n_vehicles": len(routes),
        "satisfaction_time": inst.params["satisfaction_time"],
        "fleet_ok": inst.fleet_size is None or len(routes) <= inst.fleet_size,  # ràng buộc C5
        "total_km": total_km,
        "early_min": early_min,
        "late_min": late_min,
        "F1": F1, "F2": F2, "F3": F3, "F4": F4,
        "f1": f1, "f2": f2, "f3": f3,
    }