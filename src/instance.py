"""Đọc instance, đổi đơn vị, sinh 2 khung giờ"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
import vrplib
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
SATISFACTION_TIMES = ("arrival", "service_start")

@dataclass
class Instance:
    name: str 
    n: int #số khách, không tính kho
    coords: np.ndarray #(n+1,2) km, dòng 0 là kho
    demand: np.ndarray #(n+1), kg
    service_time: np.ndarray #(n+1,) phút
    tw_expected: np.ndarray # (n+1, 2) phut, cot 0 = ETa, cot 1 = LTb
    tw_specified: np.ndarray # (n+1, 2) phut, cot 0 = ET,  cot 1 = LT
    dist: np.ndarray # (n+1, n+1) km
    capacity: float # kg
    fleet_size: int | None # so xe toi da, None = khong gioi han
    depart_time: float # phut, gio xe roi kho
    params: dict # tham so mo hinh: cost, speed_kmh, emission

def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def euclidean_matrix(coords: np.ndarray) -> np.ndarray:
    diff = coords[:, None, :] - coords[None, :, :]
    return np.hypot(diff[...,0], diff[...,1])

def load_instance(name: str, n: int) -> Instance:
    cfg = load_config()
    if name.lower() == "case29":
        inst = _load_case29(n, cfg)
    else:
        inst = _load_solomon(name, n, cfg)
    _check_instance(inst)
    return inst

def _model_params(cfg: dict) -> dict:
    sat_time = cfg["satisfaction_time"]
    if sat_time not in SATISFACTION_TIMES:
        raise ValueError(f"satisfaction_time = {sat_time!r}, chỉ nhận {SATISFACTION_TIMES}")
    return {
        "cost": cfg["cost"],
        "speed_kmh": cfg["speed_kmh"],
        "emission": cfg["emission"],
        "satisfaction_time": sat_time,
    }

def _depart_time(mode: str, tw_expected: np.ndarray) -> float:
    if mode != "depot_open":
        raise ValueError(f"depart = {mode!r} chưa được hỗ trợ")
    return float(tw_expected[0,0])

def _load_solomon(name: str, n: int, cfg: dict) -> Instance:
    sc = cfg["solomon"]
    raw = vrplib.read_instance(str(ROOT / sc["dir"] / f"{name}.txt"),instance_format="solomon")
    n_max = len(raw["demand"]) - 1
    if not 1 <= n <= n_max:
        raise ValueError(f"{name}: n phai trong [1, {n_max}], nhan {n}")
    k = n+1 #kho +n khách đầu tiên

    coords = raw["node_coord"][:k].astype(float)
    tw_expected = raw["time_window"][:k].astype(float)
    slack = sc["tw_slack_min"]
    tw_specified = np.column_stack([
        np.maximum(0.0, tw_expected[:, 0] - slack),
        tw_expected[:, 1] + slack,
    ])

    return Instance(
        name=f"{name}-{n}",
        n=n,
        coords=coords,
        demand=raw["demand"][:k].astype(float),
        service_time=raw["service_time"][:k].astype(float),
        tw_expected=tw_expected,
        tw_specified=tw_specified,
        dist=euclidean_matrix(coords),
        capacity=float(sc["capacity_kg"]),
        fleet_size=sc["fleet_size"],
        depart_time=_depart_time(sc["depart"], tw_expected),
        params=_model_params(cfg),
    )

def _load_case29(n: int, cfg: dict) -> Instance:
    cc = cfg["case29"]
    df = pd.read_csv(ROOT / cc["file"]).sort_values("id").reset_index(drop=True)

    n_max = len(df) - 1
    if not 1 <= n <= n_max:
        raise ValueError(f"case29: n phải trong [1, {n_max}], nhan {n}")
    df = df.iloc[: n + 1]
    if not np.array_equal(df["id"].to_numpy(), np.arange(n + 1)):
        raise ValueError("case29.csv: cot id phai la 0, 1, 2, ... liên tiếp")

    coords = df[["x", "y"]].to_numpy(float)
    # tan -> kg. Lam tron de 1.08 * 1000 ra dung 1080, khong ra 1080.0000000000002
    demand = np.round(df["demand_ton"].to_numpy(float) * cc["ton_to_kg"], 6)
    # gio -> phut
    tw_specified = df[["tw_start_h", "tw_end_h"]].to_numpy(float) * cc["hour_to_min"]

    if cc["expected_window"] != "same_as_specified":
        raise ValueError(f"expected_window = {cc['expected_window']!r} chưa được hỗ trợ")
    tw_expected = tw_specified.copy()

    return Instance(
        name=f"case29-{n}",
        n=n,
        coords=coords,
        demand=demand,
        service_time=df["service_min"].to_numpy(float),
        tw_expected=tw_expected,
        tw_specified=tw_specified,
        dist=euclidean_matrix(coords),
        capacity=float(cc["capacity_kg"]),
        fleet_size=cc["fleet_size"],
        depart_time=_depart_time(cc["depart"], tw_expected),
        params=_model_params(cfg),
    )

def _check_instance(inst: Instance) -> None:
    if inst.demand[1:].max() > inst.capacity:
        raise ValueError(f"{inst.name}: có khách cần nhiều hàng hơn tải trọng xe")
    et, eta = inst.tw_specified[:, 0], inst.tw_expected[:, 0]
    ltb, lt = inst.tw_expected[:, 1], inst.tw_specified[:, 1]
    if not np.all((et <= eta) & (eta <= ltb) & (ltb <= lt)):
        raise ValueError(f"{inst.name}: hai khung giờ lồng nhau ET <= ETa <= LTb <= LT")
