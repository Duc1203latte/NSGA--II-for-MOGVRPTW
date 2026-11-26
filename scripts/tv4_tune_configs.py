"""Các cấu hình tuning giai đoạn 3 của TV4: tên -> danh sách ghi đè `--set` của runner.

Tên động (đọc từ tên):
    adapt_v2_g<G>_b<B>   pc/pm cố định ở baseline + tăng pm khi trì trệ (stagnation_gens=G, boost=B)
    adapt_v3_g<G>_b<B>   khoảng pc/pm của v1 + tăng pm khi trì trệ
"""
from __future__ import annotations
import re

AP = "improvements.adaptive_params."
DPP = "improvements.dp_split_params."

# v1: khoảng đặt tâm ở baseline (pc 0.7, pm 0.1), chỉ mở rộng lên trên
V1_RANGES = [AP + "pc_min=0.7", AP + "pc_max=0.9", AP + "pm_min=0.1", AP + "pm_max=0.3"]
# v2: pc/pm cố định ở baseline; tran pm sau boost nâng lên 0.3 (nếu không boost bị chặn ở pm_max = 0.1)
V2_FIXED = [AP + "pc_min=0.7", AP + "pc_max=0.7", AP + "pm_min=0.1", AP + "pm_max=0.1",
            AP + "boost_pm_cap=0.3"]

STATIC = {
    "baseline": [],
    "baseline_g300": ["nsga2.n_gen=300"],   # đối chứng: baseline với ~1.5x thế hệ, cùng cỡ chi phí với polish
    "dp_every_eval": ["improvements.dp_split=true"],
    "dp_polish_k10": ["improvements.dp_split=true", DPP + "mode=polish", DPP + "polish_k=10"],
    "dp_polish_k30": ["improvements.dp_split=true", DPP + "mode=polish", DPP + "polish_k=30"],
    "adapt_v1": ["improvements.adaptive_rates=true", *V1_RANGES],
}
V2_GRID = [(g, b) for g in (10, 20) for b in (1.5, 2.0)]


def stag(g, b):
    return [AP + f"stagnation_gens={g}", AP + f"boost={b}"]


def overrides(name: str) -> list[str]:
    if name in STATIC:
        return STATIC[name]
    m = re.fullmatch(r"adapt_(v2|v3)_g(\d+)_b([\d.]+)", name)
    if not m:
        raise KeyError(name)
    kind, g, b = m.group(1), int(m.group(2)), float(m.group(3))
    base = V2_FIXED if kind == "v2" else V1_RANGES
    return ["improvements.adaptive_rates=true", *base, *stag(g, b)]


def v2_names() -> list[str]:
    return [f"adapt_v2_g{g}_b{b}" for g, b in V2_GRID]
