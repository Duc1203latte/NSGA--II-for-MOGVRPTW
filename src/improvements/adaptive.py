"""Pc/Pm thich nghi theo hang non-dominated (cai tien tach rieng khoi dp_split).

Ham thuan tuy, khong dung RNG. nsga2.py chi can:
    params = resolve_params(cfg["improvements"]["adaptive_params"], cfg["nsga2"], is_case29)
    pc, pm = adaptive_rates(rank_a, rank_b, max_rank, params, front1_fraction,
                            pm_boost=tracker.multiplier)
    tracker.update(front1_objectives)   # moi generation
"""

from __future__ import annotations
import numpy as np

DECIMALS = 9   # so sanh vector muc tieu lam tron toi 1e-9


def resolve_params(adaptive_params: dict, nsga2_cfg: dict, case29: bool = False) -> dict:
    """Gop cac khoang thanh dict phang, them pc/pm goc (baseline) lay tu nsga2 trong config.
    Case29 co khoang pm rieng de pm goc 0.2 nam trong khoang."""
    p = dict(adaptive_params)
    p["baseline_pc"] = nsga2_cfg["pc"]
    p["baseline_pm"] = nsga2_cfg["pm"]["case29" if case29 else "solomon"]
    if case29:
        p["pm_min"] = p["pm_case29"]["min"]
        p["pm_max"] = p["pm_case29"]["max"]
    p.pop("pm_case29", None)
    if not (p["pc_min"] <= p["pc_max"] and p["pm_min"] <= p["pm_max"]):
        raise ValueError("adaptive_params: can min <= max")
    if not (p["pc_min"] <= p["baseline_pc"] <= p["pc_max"]
            and p["pm_min"] <= p["baseline_pm"] <= p["pm_max"]):
        raise ValueError("adaptive_params: pc/pm goc phai nam trong khoang")
    if not 0.0 < p["single_front_threshold"] <= 1.0:
        raise ValueError("adaptive_params: single_front_threshold phai trong (0, 1]")
    return p


def adaptive_rates(rank_a: int, rank_b: int, max_rank: int, params: dict,
                   front1_fraction: float, pm_boost: float = 1.0) -> tuple[float, float]:
    """r = hang tot nhat cua hai cha me (0 = front 1). Hang cang tot thi lai/dot bien cang it.
    Neu gan ca quan the nam o front 1 (front1_fraction >= single_front_threshold) thi moi cap
    co r = 0 va thich nghi suy bien thanh pc_min/pm_min khong doi, nen tra ve pc, pm goc.
    pm_boost > 1 nhan pm khi quan the bi tri tre, nhung pm khong bao gio vuot pm_max."""
    if front1_fraction >= params["single_front_threshold"]:
        pc, pm = params["baseline_pc"], params["baseline_pm"]
    else:
        r = min(rank_a, rank_b)
        frac = min(r / max(max_rank, 1), 1.0)
        pc = params["pc_min"] + (params["pc_max"] - params["pc_min"]) * frac
        pm = params["pm_min"] + (params["pm_max"] - params["pm_min"]) * frac
    return pc, min(pm * pm_boost, params["pm_max"])


def rate_history(logs: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tu log moi generation tra ve (front1_fraction, pc trung binh, pm trung binh) de ve do thi.
    Moi phan tu cua logs la dict: {"front1_fraction": float, "pc": [pc moi cap], "pm": [pm moi cap]}.
    Generation khong co cap nao (list rong) cho nan."""
    frac = np.array([g["front1_fraction"] for g in logs], dtype=float)
    pc = np.array([np.mean(g["pc"]) if len(g["pc"]) else np.nan for g in logs], dtype=float)
    pm = np.array([np.mean(g["pm"]) if len(g["pm"]) else np.nan for g in logs], dtype=float)
    return frac, pc, pm


class StagnationTracker:
    """Dem so generation lien tiep front 1 khong doi. Doi = tap vector muc tieu khac nhau."""

    def __init__(self, stagnation_gens: int, boost: float):
        self.k = stagnation_gens     # 0 = tat
        self.boost = boost
        self._key = None
        self.unchanged = 0           # so generation lien tiep khong doi

    @property
    def multiplier(self) -> float:
        return self.boost if self.k > 0 and self.unchanged >= self.k else 1.0

    def update(self, front1_objectives) -> float:
        """Goi moi generation voi cac vector muc tieu cua front 1. Tra ve he so nhan pm."""
        arr = np.round(np.asarray(front1_objectives, dtype=float), DECIMALS)
        key = frozenset(map(tuple, arr.reshape(len(arr), -1).tolist()))
        if key == self._key:
            self.unchanged += 1
        else:
            self._key, self.unchanged = key, 0
        return self.multiplier
