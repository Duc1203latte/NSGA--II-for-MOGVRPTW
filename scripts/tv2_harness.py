"""HARNESS NSGA-II TẠM THỜI CỦA TV2 - KHÔNG PHẢI BASELINE CỦA TV1.

Lý do tồn tại: tại commit 5197d65 (origin/main), ``src/nsga2.py``, ``src/metrics.py``,
``src/runner.py`` vẫn rỗng. Để kiểm thử tích hợp hook TV2 và chạy thí nghiệm sơ bộ, TV2 dùng một
NSGA-II chuẩn (Deb 2002) tối giản ở đây. Khi TV1 bàn giao ``src/nsga2.py``, mọi kết quả trong
``results/tv2/`` phải được chạy lại bằng baseline thật; số liệu từ harness này chỉ là sơ bộ.

Harness KHÔNG nằm trong ``src/`` và không được import bởi code sản phẩm.

Thiết kế (cố ý giống các bước README mô tả cho TV1):
* genome: hoán vị 1..n; khởi tạo baseline ``rng.permutation(np.arange(1, n+1))``;
* đánh giá: ``decoder.evaluate_detail`` (split theo ``split_rule`` trong config), mục tiêu
  tối thiểu hoá g = (f1, f2, 1 - f3);
* fast non-dominated sort + crowding distance; chọn cha mẹ bằng giải đấu nhị phân;
* lai ghép OX với xác suất pc (mỗi cặp), đột biến đảo đoạn (inversion) với xác suất pm (mỗi con);
* (mu + lambda) elitist; một ``np.random.Generator`` duy nhất theo seed.

Điểm gắn TV2 (chỉ khi cờ bật):
* khởi tạo: ``smart_initial_population``;
* sau đột biến, trước đánh giá: ``LocalSearchHook`` (tái dùng detail chính xác khi LS chạy).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from src.decoder import evaluate_detail
from src.improvements.local_search import to_min_vector
from src.instance import Instance


# --------------------------------------------------------------------------- NSGA-II cơ bản
def fast_non_dominated_sort(F: np.ndarray) -> list[np.ndarray]:
    n = len(F)
    le = np.all(F[:, None, :] <= F[None, :, :], axis=2)
    lt = np.any(F[:, None, :] < F[None, :, :], axis=2)
    dom = le & lt                                   # dom[i, j]: i trội j
    n_dom = dom.sum(axis=0)                         # số cá thể trội j
    fronts, current = [], np.flatnonzero(n_dom == 0)
    n_dom = n_dom.copy()
    while len(current):
        fronts.append(current)
        nxt = []
        for i in current:
            for j in np.flatnonzero(dom[i]):
                n_dom[j] -= 1
                if n_dom[j] == 0:
                    nxt.append(j)
        current = np.array(sorted(nxt), dtype=int)
    return fronts


def crowding_distance(F: np.ndarray) -> np.ndarray:
    n, m = F.shape
    d = np.zeros(n)
    if n <= 2:
        return np.full(n, np.inf)
    for k in range(m):
        order = np.argsort(F[:, k], kind="stable")
        lo, hi = F[order[0], k], F[order[-1], k]
        d[order[0]] = d[order[-1]] = np.inf
        if hi - lo <= 0:
            continue
        d[order[1:-1]] += (F[order[2:], k] - F[order[:-2], k]) / (hi - lo)
    return d


def rank_and_crowding(F: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rank = np.empty(len(F), dtype=int)
    crowd = np.empty(len(F))
    for r, idx in enumerate(fast_non_dominated_sort(F)):
        rank[idx] = r
        crowd[idx] = crowding_distance(F[idx])
    return rank, crowd


def ox_crossover(a: list[int], b: list[int], rng: np.random.Generator) -> tuple[list[int], list[int]]:
    n = len(a)
    if n < 2:
        return list(a), list(b)
    i, j = sorted(int(x) for x in rng.choice(n, 2, replace=False))

    def child(p, q):
        mid = p[i:j + 1]
        used = set(mid)
        rest = [c for c in q[j + 1:] + q[:j + 1] if c not in used]
        out = [0] * n
        out[i:j + 1] = mid
        pos = [(j + 1 + k) % n for k in range(n - (j - i + 1))]
        for k, c in zip(pos, rest):
            out[k] = c
        return out
    return child(a, b), child(b, a)


def inversion_mutation(p: list[int], rng: np.random.Generator) -> list[int]:
    n = len(p)
    if n < 2:
        return list(p)
    i, j = sorted(int(x) for x in rng.choice(n, 2, replace=False))
    q = list(p)
    q[i:j + 1] = q[i:j + 1][::-1]
    return q


def tournament(rank: np.ndarray, crowd: np.ndarray, rng: np.random.Generator) -> int:
    i, j = (int(x) for x in rng.integers(0, len(rank), 2))
    if rank[i] != rank[j]:
        return i if rank[i] < rank[j] else j
    if crowd[i] != crowd[j]:
        return i if crowd[i] > crowd[j] else j
    return i


# --------------------------------------------------------------------------- chạy
@dataclass
class RunResult:
    seed: int
    perms: list[list[int]]
    F: np.ndarray                            # (n_pop, 3) g = (f1, f2, 1 - f3) quần thể cuối
    fleet_ok: np.ndarray
    init_F: np.ndarray                       # quần thể ban đầu
    init_sources: list[str]
    history_front: list[np.ndarray] = field(default_factory=list)   # front 1 mỗi generation
    history_evals: list[int] = field(default_factory=list)
    n_evals: int = 0
    n_gen_done: int = 0
    elapsed_s: float = 0.0
    ls_counters: dict = field(default_factory=dict)
    rng_state_end: dict = field(default_factory=dict)

    def front_mask(self) -> np.ndarray:
        m = np.zeros(len(self.F), bool)
        m[fast_non_dominated_sort(self.F)[0]] = True
        return m


def run(inst: Instance, cfg: dict, seed: int, *, n_pop: int | None = None, n_gen: int | None = None,
        max_evals: int | None = None, record_history: bool = True) -> RunResult:
    """Một run NSGA-II. ``cfg`` là toàn bộ config đã đọc (cờ ở ``cfg['improvements']``)."""
    imp = cfg["improvements"]
    nsga = cfg["nsga2"]
    n_pop = n_pop or nsga["n_pop"]
    n_gen = nsga["n_gen"] if n_gen is None else n_gen
    pc = nsga["pc"]
    pm = nsga["pm"]["case29" if inst.name.startswith("case29") else "solomon"]
    n = inst.n
    rng = np.random.default_rng(seed)
    t0 = time.perf_counter()
    n_evals = 0

    def evaluate(p):
        nonlocal n_evals
        n_evals += 1
        return evaluate_detail(p, inst)

    ids = np.arange(1, n + 1)

    def baseline_factory(r):
        return r.permutation(ids).tolist()

    # ---- khởi tạo
    if imp.get("init_smart", False):
        from src.improvements.tv2_hooks import smart_initial_population
        perms, sources = smart_initial_population(imp, inst, n_pop, rng, baseline_factory)
    else:
        perms = [baseline_factory(rng) for _ in range(n_pop)]
        sources = ["random"] * n_pop

    ls = None
    if imp.get("local_search", False):
        from src.improvements.tv2_hooks import LocalSearchHook
        ls = LocalSearchHook.from_config(imp, inst, lambda p, m: evaluate(p),
                                         baseline_detail_fn=lambda p: evaluate_detail(p, inst))

    details = [evaluate(p) for p in perms]
    F = np.array([to_min_vector(d) for d in details])
    fleet = np.array([d["fleet_ok"] for d in details])
    init_F = F.copy()
    res = RunResult(seed, perms, F, fleet, init_F, list(sources))
    rank, crowd = rank_and_crowding(F)
    if record_history:
        res.history_front.append(F[rank == 0].copy())
        res.history_evals.append(n_evals)

    gen = 0
    while gen < n_gen and (max_evals is None or n_evals < max_evals):
        kids: list[list[int]] = []
        while len(kids) < n_pop:
            a = perms[tournament(rank, crowd, rng)]
            b = perms[tournament(rank, crowd, rng)]
            if rng.random() < pc:
                c1, c2 = ox_crossover(a, b, rng)
            else:
                c1, c2 = list(a), list(b)
            for c in (c1, c2):
                if rng.random() < pm:
                    c = inversion_mutation(c, rng)
                kids.append(c)
        kids = kids[:n_pop]
        kid_details = []
        for k, c in enumerate(kids):
            d = None
            if ls is not None:
                c, d = ls(c, rng, None)
                kids[k] = c
            kid_details.append(d if d is not None else evaluate(c))
        allp = perms + kids
        alld = details + kid_details
        allF = np.vstack([F, np.array([to_min_vector(d) for d in kid_details])])
        r_all, c_all = rank_and_crowding(allF)
        order = np.lexsort((-c_all, r_all))[:n_pop]
        perms = [allp[i] for i in order]
        details = [alld[i] for i in order]
        F = allF[order]
        rank, crowd = r_all[order], c_all[order]
        gen += 1
        if record_history:
            res.history_front.append(F[rank == 0].copy())
            res.history_evals.append(n_evals)

    res.perms, res.F = perms, F
    res.fleet_ok = np.array([d["fleet_ok"] for d in details])
    res.n_evals, res.n_gen_done = n_evals, gen
    res.elapsed_s = time.perf_counter() - t0
    if ls is not None:
        ls.counters.n_evals_total = n_evals
        res.ls_counters = ls.counters.as_dict()
    res.rng_state_end = rng.bit_generator.state
    return res


# --------------------------------------------------------------------------- chỉ số
def nondominated(F: np.ndarray) -> np.ndarray:
    F = np.unique(np.asarray(F, float), axis=0)
    return F[fast_non_dominated_sort(F)[0]] if len(F) else F


class Normalizer:
    """Min-max theo reference set chung (cố định cho mọi cấu hình/seed của một instance)."""

    def __init__(self, ref_set: np.ndarray):
        self.lo = ref_set.min(axis=0)
        self.hi = ref_set.max(axis=0)
        self.span = np.where(self.hi - self.lo > 0, self.hi - self.lo, 1.0)

    def __call__(self, F: np.ndarray) -> np.ndarray:
        return (np.asarray(F, float) - self.lo) / self.span


def hypervolume(Fn: np.ndarray, ref_point=(1.1, 1.1, 1.1)) -> float:
    from pymoo.indicators.hv import HV
    ref = np.asarray(ref_point, float)
    Fn = np.asarray(Fn, float)
    Fn = Fn[np.all(Fn < ref, axis=1)]
    if len(Fn) == 0:
        return 0.0
    return float(HV(ref_point=ref)(Fn))


def igd(Fn: np.ndarray, ref_n: np.ndarray) -> float:
    from pymoo.indicators.igd import IGD
    return float(IGD(np.asarray(ref_n, float))(np.asarray(Fn, float)))


def spacing(Fn: np.ndarray) -> float:
    """Schott spacing (L1 tới láng giềng gần nhất) trên mục tiêu đã chuẩn hoá. <2 điểm -> 0."""
    Fn = np.unique(np.asarray(Fn, float), axis=0)
    if len(Fn) < 2:
        return 0.0
    D = np.abs(Fn[:, None, :] - Fn[None, :, :]).sum(axis=2)
    np.fill_diagonal(D, np.inf)
    d = D.min(axis=1)
    return float(np.sqrt(((d - d.mean()) ** 2).sum() / (len(d) - 1)))
