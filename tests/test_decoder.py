"""Cổng kiểm tra decoder
Kiểm decoder đúng với MÔ HÌNH
Chạy: pytest tests/test_decoder.py -v"""

import random
import numpy as np
import pandas as pd
import pytest
import src.instance as instance_module
from src.instance import ROOT, Instance, euclidean_matrix, load_config, load_instance
from src.decoder import (
    emission_factor, evaluate, evaluate_detail, evaluate_routes_detail,
    satisfaction, split_capacity_time, split_greedy,
)

def make_toy(coords, demand, service, tw_expected, tw_specified,
             capacity = 400.0, fleet_size = None, **param_overrides) -> Instance:
    '''Dựng một instance nhỏ bằng tay để tính tay được. Dòng 0 là kho.
    Tham số chi phí và khí thải lấy từ config.yaml'''

    cfg = load_config()
    params = {
        "cost": cfg["cost"],
        "speed_kmh": cfg["speed_kmh"],
        "emission": cfg["emission"],
        "satisfaction_time": "arrival",
        "split_rule": "capacity_time",
    }
    params.update(param_overrides)
    coords = np.array(coords, dtype = float)
    return Instance(
        name="toy",
        n=len(coords) - 1,
        coords=coords,
        demand=np.array(demand, dtype=float),
        service_time=np.array(service, dtype=float),
        tw_expected=np.array(tw_expected, dtype=float),
        tw_specified=np.array(tw_specified, dtype=float),
        dist=euclidean_matrix(coords),
        capacity=capacity,
        fleet_size=fleet_size,
        depart_time=0.0,
        params=params,
    )

def toy_two_customers(**param_overrides) -> Instance:
    """Kho (0,0), khách 1 ở (10,0), khách 2 ở (20,0). 10 km mất 15 phút.
    Khách 1: 100 kg, dỡ 10 phút, khung kỳ vọng [30, 60], khung chấp nhận được [0, 90].
    Khách 2:  50 kg, dỡ 10 phút, khung kỳ vọng [20, 50], khung chấp nhận được [20, 80].
    """
    return make_toy(
        coords=[(0, 0), (10, 0), (20, 0)],
        demand=[0, 100, 50],
        service=[0, 10, 10],
        tw_expected=[(0, 1000), (30, 60), (20, 50)],
        tw_specified=[(0, 1000), (0, 90), (20, 80)],
        **param_overrides,
    )

def route_length(route: list[int], inst: Instance) -> float:
    '''Độ dài 1 tuyến 0 -> route -> 0'''
    stops = [0] + route + [0]
    return float(sum(inst.dist[a,b] for a, b in zip(stops, stops[1:])))

def load_fixture_routes() -> dict[int, list[list[int]]]:
    fx = pd.read_csv(ROOT / "data/paper/fixture_routes.csv")
    return {
        int(table): [[int(c) for c in str(s).split("-")] for s in g["sequence"]]
        for table, g in fx.groupby("table")
    }

'''Hàm hài lòng W'''
@pytest.mark.parametrize("t, expected", [
    (881, 0.0),        # trước ET
    (882, 0.0),        # đúng ET, đầu đoạn dốc lên
    (900, 60.0),       # giữa đoạn dốc lên: 100 * 18 / 30
    (912, 100.0),      # đúng ETa
    (967, 100.0),      # đúng LTb
    (990, 100 * 7 / 30),   # giữa đoạn dốc xuống
    (997, 0.0),        # đúng LT
    (998, 0.0),        # sau LT
])

def test_satisfaction_solomon_window(t, expected):
    # Khung kiểu Solomon: kỳ vọng [912, 967], chấp nhận được nới 30 phút mỗi đầu
    assert satisfaction(t, 882, 912, 967, 997) == pytest.approx(expected)

@pytest.mark.parametrize("t, expected", [(359, 0.0), (360, 100.0), (600, 100.0), (601, 0.0)])
def test_satisfaction_degenerate_window_no_division_by_zero(t, expected):
    # Kiểu case29: khung kỳ vọng trùng khung chấp nhận được
    assert satisfaction(t, 360, 360, 600, 600) == expected

'''Khí thải'''
def test_emission_factor_uses_v_squared():
    cfg = load_config()
    factor = emission_factor({"speed_kmh": cfg["speed_kmh"], "emission": cfg["emission"]})
    assert factor == pytest.approx(679.4376, abs=1e-3)

'''Tính tay trên toy'''
def test_toy_hand_calculation_arrival():
    d = evaluate_routes_detail([[1, 2]], toy_two_customers())

    assert d["route_lengths"] == [pytest.approx(40.0)]
    assert d["arrival_times"][1] == pytest.approx(15.0)
    assert d["arrival_times"][2] == pytest.approx(55.0)
    assert d["early_min"] == pytest.approx(15.0)
    assert d["late_min"] == pytest.approx(5.0)
    assert d["F1"] == pytest.approx(62.1)
    assert d["F2"] == pytest.approx(100.0)
    assert d["F3"] == pytest.approx(80.0)
    assert d["F4"] == pytest.approx(10.0)
    assert d["f1"] == pytest.approx(252.1)
    assert d["f2"] == pytest.approx(679.4376 * 40 / 1000, abs=1e-4)
    assert d["f3"] == pytest.approx((50 + 250 / 3) / 200)

def test_toy_hand_calculation_service_start():
    d = evaluate_routes_detail([[1, 2]], toy_two_customers(satisfaction_time="service_start"))
    assert d["f1"] == pytest.approx(252.1)
    assert d["f2"] == pytest.approx(679.4376 * 40 / 1000, abs=1e-4)
    assert d["f3"] == pytest.approx((100 + 250 / 3) / 200)

def test_heavy_first_is_cheaper():
    inst = make_toy(
        coords=[(0, 0), (10, 0), (0, 10)],
        demand=[0, 300, 50],
        service=[0, 0, 0],
        tw_expected=[(0, 1000)] * 3,
        tw_specified=[(0, 1000)] * 3,
    )
    heavy_first = evaluate_routes_detail([[1, 2]], inst)
    light_first = evaluate_routes_detail([[2, 1]], inst)
    assert heavy_first["total_km"] == pytest.approx(light_first["total_km"])
    assert heavy_first["F1"] < light_first["F1"]

'''Split'''
def split_toy(**kwargs) -> Instance:
    '''Ba khách thẳng hàng, khung rộng, chỉ để thử cắt theo tải'''
    defaults = dict(
        coords=[(0, 0), (1, 0), (2, 0), (3, 0)],
        demand=[0, 300, 200, 100],
        service=[0, 0, 0, 0],
        tw_expected=[(0, 1000)] * 4,
        tw_specified=[(0, 1000)] * 4,
    )
    defaults.update(kwargs)
    return make_toy(**defaults)


@pytest.mark.parametrize("perm, expected", [
    ([1, 2, 3], [[1], [2, 3]]),      # 300 + 200 > 400 nên cắt trước khách 2
    ([2, 3, 1], [[2, 3], [1]]),      # 200 + 100 = 300, thêm 300 thì vượt
    ([3, 2, 1], [[3, 2], [1]]),
])

def test_split_greedy_cuts_on_capacity(perm, expected):
    assert split_greedy(perm, split_toy()) == expected

def time_split_toy(fleet_size=None, demand=(0, 100, 100)) -> Instance:
    return make_toy(
        coords=[(0, 0), (10, 0), (20, 0)],
        demand=list(demand),
        service=[0, 10, 0],
        tw_expected=[(0, 1000), (0, 1000), (0, 30)],
        tw_specified=[(0, 1000), (0, 1000), (0, 35)],
        fleet_size=fleet_size,
    )

def test_split_capacity_time_cuts_when_too_late():
    assert split_capacity_time([1, 2], time_split_toy()) == [[1], [2]]


def test_split_capacity_time_no_time_cut_when_fleet_used_up():
    # Chỉ có 1 xe: không được mở xe mới vì giờ, đành chấp nhận đến muộn
    assert split_capacity_time([1, 2], time_split_toy(fleet_size=1)) == [[1, 2]]


def test_split_capacity_time_still_cuts_on_capacity_when_fleet_used_up():
    # Tải trọng là ràng buộc cứng: vượt tải thì vẫn cắt, dù vượt số xe
    inst = time_split_toy(fleet_size=1, demand=(0, 300, 200))
    routes = split_capacity_time([1, 2], inst)
    assert routes == [[1], [2]]
    assert evaluate_routes_detail(routes, inst)["fleet_ok"] is False

def test_split_rule_capacity_matches_split_greedy():
    inst = load_instance("C102", 25)
    inst.params["split_rule"] = "capacity"
    perm = list(range(1, 26))
    random.Random(0).shuffle(perm)
    assert evaluate_detail(perm, inst)["routes"] == split_greedy(perm, inst)

'''Bất biến trên dữ liệu thật'''
INSTANCES = [("C102", 25), ("R201", 50), ("RC201", 100), ("case29", 29)]


@pytest.mark.parametrize("name, n", INSTANCES)
@pytest.mark.parametrize("split_rule", ["capacity", "capacity_time"])
def test_invariants_on_random_permutations(name, n, split_rule):
    inst = load_instance(name, n)
    inst.params["split_rule"] = split_rule
    cost = inst.params["cost"]
    factor = emission_factor(inst.params)
    rng = random.Random(123)

    for _ in range(50):
        perm = list(range(1, n + 1))
        rng.shuffle(perm)
        d = evaluate_detail(perm, inst)

        # Mỗi khách đúng một lần, không tuyến rỗng, không tuyến vượt tải
        assert sorted(c for r in d["routes"] for c in r) == list(range(1, n + 1))
        assert all(len(r) > 0 for r in d["routes"])
        assert all(inst.demand[r].sum() <= inst.capacity for r in d["routes"])

        # Các thành phần cộng lại đúng
        assert d["f1"] == pytest.approx(d["F1"] + d["F2"] + d["F3"] + d["F4"])
        assert d["F2"] == pytest.approx(cost["sigma2"] * d["n_vehicles"])
        assert d["F3"] == pytest.approx(cost["sigma3"] * d["total_km"])
        assert d["total_km"] == pytest.approx(sum(d["route_lengths"]))
        assert d["f2"] == pytest.approx(factor * d["total_km"] / 1000)
        assert 0.0 <= d["f3"] <= 1.0

        # evaluate và evaluate_detail cho cùng một kết quả
        assert evaluate(perm, inst) == (d["f1"], d["f2"], d["f3"])

@pytest.mark.parametrize("bad_routes", [
    [[1], [2]],             # thiếu khách 3
    [[1, 2], [2, 3]],       # khách 2 lặp lại
    [[1, 2, 3]],            # 300 + 200 + 100 > 400
])

def test_invalid_routes_raise(bad_routes):
    with pytest.raises(ValueError):
        evaluate_routes_detail(bad_routes, split_toy())

'''Đọc dữ liệu'''

def test_solomon_windows_and_cut():
    inst = load_instance("C102", 25)
    full = load_instance("C102", 100)
    assert inst.n == 25 and len(inst.demand) == 26
    assert np.array_equal(inst.coords, full.coords[:26])     # 25 khách đầu của bản 100

    eta, ltb = inst.tw_expected[:, 0], inst.tw_expected[:, 1]
    assert np.allclose(inst.tw_specified[:, 0], np.maximum(0, eta - 30))
    assert np.allclose(inst.tw_specified[:, 1], ltb + 30)
    assert inst.depart_time == 0.0


def test_case29_units():
    inst = load_instance("case29", 29)
    assert inst.demand[1] == 1080.0                          # 1.08 tấn
    assert inst.demand.sum() == pytest.approx(31320.0)
    assert list(inst.tw_specified[1]) == [420.0, 600.0]      # 7h - 10h
    assert np.array_equal(inst.tw_expected, inst.tw_specified)
    assert inst.depart_time == 360.0                         # 6:00
    assert inst.capacity == 4000.0

@pytest.mark.parametrize("key, bad_value", [
    ("satisfaction_time", "service-start"),
    ("split_rule", "time"),
])
def test_invalid_config_value_raises(monkeypatch, key, bad_value):
    cfg = load_config()
    cfg[key] = bad_value
    monkeypatch.setattr(instance_module, "load_config", lambda: cfg)
    with pytest.raises(ValueError):
        load_instance("C102", 25)

'''Ba bộ tuyến của bài báo'''
def test_fixture_route_lengths_match_paper():
    inst = load_instance("case29", 29)
    fx = pd.read_csv(ROOT / "data/paper/fixture_routes.csv")
    for _, row in fx.iterrows():
        route = [int(c) for c in str(row["sequence"]).split("-")]
        assert route_length(route, inst) == pytest.approx(row["length_km"], rel=1e-3)   # sai số dưới 0.1%

@pytest.mark.parametrize("table, f1, f2, f3_arrival", [
    (11, 2589.68, 250.95, 0.8276),
    (12, 2465.46, 229.03, 0.7586),
    (13, 2807.02, 278.31, 0.7931),
])

def test_fixture_objectives_regression(table, f1, f2, f3_arrival):
    routes = load_fixture_routes()[table]
    inst = load_instance("case29", 29)
    inst.params["satisfaction_time"] = "arrival"
    d = evaluate_routes_detail(routes, inst)
    assert d["f1"] == pytest.approx(f1, abs=0.01)
    assert d["f2"] == pytest.approx(f2, abs=0.01)
    assert d["f3"] == pytest.approx(f3_arrival, abs=1e-4)
    inst.params["satisfaction_time"] = "service_start"
    assert evaluate_routes_detail(routes, inst)["f3"] == pytest.approx(1.0)