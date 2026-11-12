"""TV2 - lớp dán mỏng để TV1 gắn ``init_smart`` và ``local_search`` vào ``nsga2.py``.

Quy tắc: CHỈ tạo/gọi các hook khi cờ tương ứng bật. Cờ tắt -> ``nsga2.py`` đi nguyên đường baseline,
không import-time side effect, không đọc RNG, không đọc params.

    imp = cfg["improvements"]
    if imp["init_smart"]:
        perms, sources = smart_initial_population(imp, inst, n_pop, rng, baseline_factory)
    else:
        perms = [<baseline>(rng) for _ in range(n_pop)]

    ls = LocalSearchHook.from_config(imp, inst, evaluator) if imp["local_search"] else None
    ...  # sau đột biến (và sau khi gán dp weights cho con, nếu có), trước khi đánh giá con:
    if ls is not None:
        child_perm, detail = ls(child_perm, rng, metadata)   # detail != None -> dùng lại, khỏi chấm
"""

from __future__ import annotations

from typing import Callable, Mapping, Sequence

import numpy as np

from src.improvements.init_smart import (
    make_initial_population, nearest_neighbor_order, parse_init_params, time_window_order,
)
from src.improvements.local_search import (
    LSCounters, LocalSearchResult, improve, parse_ls_params, to_min_vector,
)
from src.instance import Instance

DetailEvaluator = Callable[[list[int], object], dict]


def smart_initial_population(imp_cfg: Mapping, inst: Instance, n_pop: int,
                             rng: np.random.Generator, baseline_factory=None
                             ) -> tuple[list[list[int]], list[str]]:
    """Chỉ gọi khi ``imp_cfg['init_smart']`` là true."""
    if not imp_cfg.get("init_smart", False):
        raise RuntimeError("smart_initial_population chỉ được gọi khi init_smart bật")
    params = parse_init_params(imp_cfg["init_smart_params"])
    return make_initial_population(inst, n_pop, rng, params, baseline_factory)


def reference_scales(inst: Instance, evaluate_detail_fn: Callable[[list[int]], dict]) -> np.ndarray:
    """Hệ số chuẩn hoá cố định cho tổng có trọng số: (mean f1, mean f2, 1.0) trên 3 hoán vị tất định
    (thứ tự ID, NN, theo ETa) chấm bằng evaluator baseline. Không dùng RNG, không cache toàn cục;
    tính một lần cho mỗi run (mỗi LocalSearchHook). g3 = 1 - f3 đã nằm trong [0, 1] nên scale = 1."""
    perms = [list(range(1, inst.n + 1)), nearest_neighbor_order(inst), time_window_order(inst)]
    vals = np.array([[d["f1"], d["f2"]] for d in (evaluate_detail_fn(p) for p in perms)], float)
    return np.maximum(np.append(vals.mean(axis=0), 1.0), 1e-9)


class LocalSearchHook:
    """Gọi sau đột biến. Mỗi lần gọi: đúng 1 lần ``rng.random()`` để quyết định có chạy LS hay không.

    ``evaluator(perm, metadata) -> dict`` phải là CHÍNH evaluator mà NSGA-II dùng để chấm con
    (greedy/capacity_time: ``lambda p, m: evaluate_detail(p, inst)``; DP:
    ``lambda p, m: evaluate_dp(p, inst, m["dp_weights"], scales)``).
    """

    def __init__(self, params, inst: Instance, evaluator: DetailEvaluator, *,
                 scales: Sequence[float] | None = None, require_same_routes: bool = True):
        self.params = parse_ls_params(params)
        self.inst = inst
        self.evaluator = evaluator
        self.require_same_routes = require_same_routes
        self.counters = LSCounters()
        self.scales = None if scales is None else np.asarray(scales, float)
        if self.params.acceptance == "weighted" and self.scales is None:
            raise ValueError("acceptance='weighted' cần scales (dùng reference_scales)")
        self.last: LocalSearchResult | None = None

    @classmethod
    def from_config(cls, imp_cfg: Mapping, inst: Instance, evaluator: DetailEvaluator,
                    baseline_detail_fn: Callable[[list[int]], dict] | None = None
                    ) -> "LocalSearchHook":
        """``baseline_detail_fn(perm)`` dùng để tính scales; mặc định = ``evaluator(perm, None)``.
        Với DP split nên truyền evaluator greedy để scale không phụ thuộc trọng số."""
        if not imp_cfg.get("local_search", False):
            raise RuntimeError("LocalSearchHook chỉ được tạo khi local_search bật")
        params = parse_ls_params(imp_cfg["local_search_params"])
        dp = bool(imp_cfg.get("dp_split", False))
        scales = None
        if params.acceptance == "weighted":
            fn = baseline_detail_fn or (lambda p: evaluator(p, None))
            scales = reference_scales(inst, fn)
        return cls(params, inst, evaluator, scales=scales, require_same_routes=not dp)

    def __call__(self, perm: Sequence[int], rng: np.random.Generator, metadata=None
                 ) -> tuple[list[int], dict | None]:
        """Trả (hoán vị con, detail). detail là None khi LS không kích hoạt (caller tự chấm như cũ),
        ngược lại là kết quả evaluator CHÍNH XÁC cho hoán vị trả về với cùng metadata."""
        self.counters.n_ls_calls += 1
        self.last = None
        if rng.random() >= self.params.p_ls:
            return list(perm), None
        self.counters.n_ls_triggered += 1
        r = improve(perm, self.inst, rng, self.params, decode_and_evaluate=self.evaluator,
                    metadata=metadata, counters=self.counters, scales=self.scales,
                    require_same_routes=self.require_same_routes)
        self.last = r
        return r.perm, r.detail


__all__ = ["smart_initial_population", "reference_scales", "LocalSearchHook", "to_min_vector"]
