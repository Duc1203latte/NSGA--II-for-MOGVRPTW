"""TV2 - local search trong từng tuyến (cờ ``improvements.local_search``).

Gọi SAU đột biến, TRƯỚC lần đánh giá chính thức của con. Hai toán tử nội tuyến:

* ``two_opt(route, i, j)``: đảo ``route[i:j+1]``.
* ``or_opt(route, start, length, insert_at)``: cắt khối ``route[start:start+length]`` (giữ thứ tự),
  chèn lại tại chỉ số ``insert_at`` tính trên mảng ĐÃ bỏ khối.

Nguồn sự thật duy nhất là ``decode_and_evaluate(perm, metadata) -> dict`` (đúng evaluator mà
NSGA-II dùng, phải trả ``routes``, ``f1``, ``f2``, ``f3``, ``fleet_ok``, ``n_vehicles``). Một bước đi
được đề xuất trên tuyến của nghiệm hiện tại, ghép lại thành hoán vị ứng viên rồi CHẤM LẠI bằng
evaluator đó. Khi ``require_same_routes`` (split tham lam / capacity_time), nếu evaluator cắt ứng viên
thành bộ tuyến khác bộ tuyến đã đề xuất (lệch biên tuyến) thì loại bước đi.

Mục tiêu tối thiểu hoá: ``g = (f1, f2, 1 - f3)``.

* ``acceptance='pareto'``  : nhận khi g_mới trội nghiêm ngặt g_cũ (có epsilon).
* ``acceptance='weighted'``: trọng số bốc MỘT lần mỗi lần gọi; nhận khi
  ``sum(w * g / scales)`` giảm hơn epsilon. ``scales`` cố định, dương, tính trước mỗi run.
  Đây KHÔNG phải cải thiện Pareto: từng mục tiêu có thể xấu đi.

RNG: chỉ dùng ``rng`` truyền vào. Hàm này không được gọi khi cờ tắt.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

import numpy as np

OPERATORS = ("two_opt", "or_opt")
ACCEPTANCE = ("weighted", "pareto")
WEIGHT_DISTS = ("dirichlet", "equal")
STRATEGIES = ("first", "best")
DRIFT_POLICIES = ("reject", "evaluate_actual")

Evaluator = Callable[[list[int], object], dict]


# --------------------------------------------------------------------------- toán tử
def two_opt(route: Sequence[int], i: int, j: int) -> list[int]:
    """Bản sao của route với đoạn [i..j] (gồm cả hai đầu) bị đảo. Cần 0 <= i < j < len."""
    m = len(route)
    if not (0 <= i < j < m):
        raise IndexError(f"two_opt cần 0 <= i < j < {m}, nhận i={i}, j={j}")
    r = list(route)
    r[i:j + 1] = r[i:j + 1][::-1]
    return r


def or_opt(route: Sequence[int], start: int, length: int, insert_at: int) -> list[int]:
    """Chuyển khối route[start:start+length] tới vị trí insert_at của mảng đã bỏ khối.
    Ví dụ (1,2,3,4,5,6), start=1, length=2, insert_at=3 -> [1,4,5,2,3,6].
    insert_at == start là no-op (trả bản sao y hệt)."""
    m = len(route)
    if length < 1 or start < 0 or start + length > m:
        raise IndexError(f"or_opt: khối [{start}, {start + length}) không nằm trong tuyến dài {m}")
    if not 0 <= insert_at <= m - length:
        raise IndexError(f"or_opt: insert_at phải trong [0, {m - length}], nhận {insert_at}")
    r = list(route)
    block = r[start:start + length]
    rest = r[:start] + r[start + length:]
    return rest[:insert_at] + block + rest[insert_at:]


def _sample_two_opt(m: int, rng: np.random.Generator) -> tuple[int, int] | None:
    if m < 2:
        return None
    i = int(rng.integers(0, m - 1))
    j = int(rng.integers(i + 1, m))
    return i, j


def _sample_or_opt(m: int, lengths: Sequence[int], rng: np.random.Generator
                   ) -> tuple[int, int, int] | None:
    ok = [L for L in lengths if L < m]          # cần ít nhất một vị trí khác để chèn
    if not ok:
        return None
    L = int(ok[int(rng.integers(len(ok)))])
    start = int(rng.integers(0, m - L + 1))
    ins = int(rng.integers(0, m - L))           # m-L vị trí khác start trong [0, m-L]
    if ins >= start:
        ins += 1
    return start, L, ins


# --------------------------------------------------------------------------- so sánh
def to_min_vector(detail: Mapping) -> np.ndarray:
    """(f1, f2, 1 - f3): ba mục tiêu cùng chiều tối thiểu hoá."""
    return np.array([float(detail["f1"]), float(detail["f2"]), 1.0 - float(detail["f3"])])


def dominates(a: Sequence[float], b: Sequence[float], eps: float = 0.0) -> bool:
    """a trội b (tối thiểu hoá): a_i <= b_i + eps mọi i và a_j < b_j - eps với ít nhất một j."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    return bool(np.all(a <= b + eps) and np.any(a < b - eps))


def weighted_score(g: Sequence[float], weights: Sequence[float], scales: Sequence[float]) -> float:
    return float(np.dot(np.asarray(weights, float), np.asarray(g, float) / np.asarray(scales, float)))


# --------------------------------------------------------------------------- tham số
@dataclass(frozen=True)
class LocalSearchParams:
    p_ls: float = 0.2
    max_passes: int = 2
    max_candidate_evals: int = 40
    max_accepted_moves: int = 5
    operators: tuple[str, ...] = OPERATORS
    or_opt_lengths: tuple[int, ...] = (1, 2, 3)
    strategy: str = "first"
    acceptance: str = "weighted"
    weight_distribution: str = "dirichlet"
    improvement_epsilon: float = 1e-10
    split_drift_policy: str = "reject"


HARD_MAX_CANDIDATE_EVALS = 100_000


def parse_ls_params(raw: Mapping | LocalSearchParams) -> LocalSearchParams:
    """Kiểm tra ``improvements.local_search_params``. Sai thì ValueError rõ ràng."""
    if isinstance(raw, LocalSearchParams):
        return raw
    if not isinstance(raw, Mapping):
        raise ValueError("local_search_params phải là dict")
    known = set(LocalSearchParams.__dataclass_fields__)
    unknown = set(raw) - known
    if unknown:
        raise ValueError(f"local_search_params: khoá không hỗ trợ {sorted(unknown)}")
    d = {**LocalSearchParams().__dict__, **raw}

    p = d["p_ls"]
    if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError(f"p_ls phải trong [0, 1], nhận {p!r}")
    for k, lo in (("max_passes", 1), ("max_candidate_evals", 1), ("max_accepted_moves", 1)):
        v = d[k]
        if isinstance(v, bool) or not isinstance(v, int) or v < lo:
            raise ValueError(f"{k} phải là số nguyên >= {lo}, nhận {v!r}")
    if d["max_candidate_evals"] > HARD_MAX_CANDIDATE_EVALS:
        raise ValueError(f"max_candidate_evals vượt trần cứng {HARD_MAX_CANDIDATE_EVALS}")
    ops = tuple(d["operators"])
    if not ops or any(o not in OPERATORS for o in ops) or len(set(ops)) != len(ops):
        raise ValueError(f"operators phải là tập con khác rỗng, không lặp của {OPERATORS}, nhận {ops}")
    lens = tuple(d["or_opt_lengths"])
    if not lens or any(isinstance(L, bool) or not isinstance(L, int) or L not in (1, 2, 3)
                       for L in lens) or len(set(lens)) != len(lens):
        raise ValueError(f"or_opt_lengths phải là tập con khác rỗng của {{1, 2, 3}}, nhận {lens}")
    for k, allowed in (("strategy", STRATEGIES), ("acceptance", ACCEPTANCE),
                       ("weight_distribution", WEIGHT_DISTS), ("split_drift_policy", DRIFT_POLICIES)):
        if d[k] not in allowed:
            raise ValueError(f"{k} = {d[k]!r}, chỉ nhận {allowed}")
    eps = d["improvement_epsilon"]
    if isinstance(eps, bool) or not isinstance(eps, (int, float)) or not math.isfinite(eps) or eps < 0:
        raise ValueError(f"improvement_epsilon phải là số hữu hạn >= 0, nhận {eps!r}")
    return LocalSearchParams(float(p), d["max_passes"], d["max_candidate_evals"],
                             d["max_accepted_moves"], ops, lens, d["strategy"], d["acceptance"],
                             d["weight_distribution"], float(eps), d["split_drift_policy"])


def sample_ls_weights(rng: np.random.Generator, dist: str) -> np.ndarray:
    """dirichlet: đúng 1 lần rng.dirichlet([1,1,1]). equal: (1/3,1/3,1/3), không dùng RNG."""
    if dist == "dirichlet":
        return np.asarray(rng.dirichlet([1.0, 1.0, 1.0]), dtype=float)
    if dist == "equal":
        return np.full(3, 1.0 / 3.0)
    raise ValueError(f"weight_distribution = {dist!r}")


# --------------------------------------------------------------------------- thống kê
@dataclass
class LSCounters:
    """Bộ đếm cộng dồn qua cả một run. Không ảnh hưởng luồng tính toán."""
    n_ls_calls: int = 0                 # số lần hook được gọi khi cờ bật
    n_ls_triggered: int = 0             # số lần rng.random() < p_ls
    n_ls_candidate_evals: int = 0       # số ứng viên đã chấm (gồm bị loại, gồm trúng cache)
    n_ls_accepted: int = 0
    n_ls_split_drift: int = 0           # evaluator cắt ứng viên khác bộ tuyến đề xuất
    n_ls_rejected_split: int = 0        # ... và bị loại vì split_drift_policy='reject'
    n_ls_rejected_feasibility: int = 0  # làm xấu ràng buộc số xe
    n_ls_rejected_no_improve: int = 0
    n_eval_requests: int = 0            # mọi yêu cầu chấm từ LS (gồm nghiệm ban đầu)
    n_real_model_evals: int = 0         # số lần thực sự gọi evaluator từ LS
    n_evals_total: int = 0              # do vòng lặp NSGA-II cập nhật: mọi lần gọi evaluator
    elapsed_s: float = 0.0              # thời gian trong LS (chỉ để báo cáo)

    def as_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class LocalSearchResult:
    perm: list[int]
    detail: dict                        # kết quả evaluator cho ``perm`` (chính xác, không ước lượng)
    attempts: int = 0
    accepted: int = 0
    evals: int = 0                      # số yêu cầu chấm (gồm nghiệm ban đầu)
    real_evals: int = 0
    passes: int = 0
    elapsed_s: float = 0.0
    weights: np.ndarray | None = None
    accepted_by: str = ""
    history: list[dict] = field(default_factory=list)   # audit: before/after từng bước được nhận


# --------------------------------------------------------------------------- chính
def _flatten(routes: Sequence[Sequence[int]]) -> list[int]:
    return [c for r in routes for c in r]


def _is_perm(perm: Sequence[int], n: int) -> bool:
    return len(perm) == n and sorted(perm) == list(range(1, n + 1))


def improve(
    perm: Sequence[int],
    inst,
    rng: np.random.Generator,
    params: Mapping | LocalSearchParams,
    *,
    decode_and_evaluate: Evaluator,
    metadata=None,
    counters: LSCounters | None = None,
    scales: Sequence[float] | None = None,
    require_same_routes: bool = True,
    initial_detail: dict | None = None,
) -> LocalSearchResult:
    """Cải thiện ``perm`` bằng 2-opt / Or-opt trong từng tuyến. Không sửa ``perm`` đầu vào.

    ``metadata`` được chuyển nguyên vẹn cho mọi lần gọi evaluator (vd ``{"dp_weights": w}``),
    không bao giờ bị bốc lại. ``scales`` bắt buộc khi ``acceptance='weighted'``.
    ``require_same_routes=False`` chỉ dùng cho evaluator được phép cắt lại (DP split).
    ``initial_detail``: kết quả evaluator đã có cho đúng ``perm`` + ``metadata`` (tuỳ chọn).
    """
    p = parse_ls_params(params)
    t0 = time.perf_counter()
    n = inst.n
    perm0 = list(perm)
    if not _is_perm(perm0, n):
        raise ValueError("improve: đầu vào không phải hoán vị 1..n")
    c = counters if counters is not None else LSCounters()
    eps = p.improvement_epsilon

    weights = None
    if p.acceptance == "weighted":
        if scales is None:
            raise ValueError("acceptance='weighted' cần scales cố định")
        scales = np.asarray(scales, dtype=float)
        if scales.shape != (3,) or not np.all(np.isfinite(scales)) or np.any(scales <= 0):
            raise ValueError(f"scales phải là 3 số dương hữu hạn, nhận {scales}")
        weights = sample_ls_weights(rng, p.weight_distribution)   # MỘT lần mỗi lần gọi

    cache: dict[tuple[int, ...], dict] = {}
    res = LocalSearchResult(perm0, {}, weights=weights, accepted_by=p.acceptance)

    def evaluate(cand: list[int]) -> dict:
        key = tuple(cand)
        res.evals += 1
        c.n_eval_requests += 1
        if key not in cache:
            d = decode_and_evaluate(list(cand), metadata)
            res.real_evals += 1
            c.n_real_model_evals += 1
            cache[key] = d
        return cache[key]

    def better(g_new: np.ndarray, g_old: np.ndarray) -> bool:
        if p.acceptance == "pareto":
            return dominates(g_new, g_old, eps)
        return weighted_score(g_new, weights, scales) < weighted_score(g_old, weights, scales) - eps

    def feasible_vs(new: dict, old: dict) -> bool:
        if old.get("fleet_ok", True):
            return bool(new.get("fleet_ok", True))
        return int(new["n_vehicles"]) <= int(old["n_vehicles"])   # đã vi phạm: không làm tệ hơn

    if initial_detail is not None:
        cache[tuple(perm0)] = initial_detail
        inc_detail = initial_detail
    else:
        inc_detail = evaluate(perm0)
    inc_perm = perm0
    inc_g = to_min_vector(inc_detail)
    budget_left = lambda: res.attempts < p.max_candidate_evals and res.accepted < p.max_accepted_moves  # noqa: E731

    for _ in range(p.max_passes):
        if not budget_left():
            break
        routes = [list(r) for r in inc_detail["routes"]]
        eligible = [k for k, r in enumerate(routes) if len(r) >= 2]
        if not eligible:
            break
        res.passes += 1
        order = [eligible[int(k)] for k in rng.permutation(len(eligible))]
        restart = False
        for ri in order:
            if not budget_left() or restart:
                break
            pending: list[tuple[np.ndarray, list[int], dict, list[list[int]], str]] = []
            for op in p.operators:
                if not budget_left():
                    break
                route = routes[ri]
                if op == "two_opt":
                    mv = _sample_two_opt(len(route), rng)
                    new_route = None if mv is None else two_opt(route, *mv)
                else:
                    mv = _sample_or_opt(len(route), p.or_opt_lengths, rng)
                    new_route = None if mv is None else or_opt(route, *mv)
                if new_route is None or new_route == route:
                    continue
                cand_routes = [list(r) for r in routes]
                cand_routes[ri] = new_route
                cand_perm = _flatten(cand_routes)
                assert _is_perm(cand_perm, n)
                res.attempts += 1
                c.n_ls_candidate_evals += 1
                d = evaluate(cand_perm)
                drifted = [list(r) for r in d["routes"]] != cand_routes
                if drifted and require_same_routes:
                    c.n_ls_split_drift += 1
                    if p.split_drift_policy == "reject":
                        c.n_ls_rejected_split += 1
                        continue
                    # evaluate_actual: d đã là kết quả THẬT của evaluator cho cand_perm (bộ tuyến
                    # thật = d["routes"]), nên vẫn so sánh trên d; bước đi không còn thuần nội tuyến.
                if not feasible_vs(d, inc_detail):
                    c.n_ls_rejected_feasibility += 1
                    continue
                g = to_min_vector(d)
                if not better(g, inc_g):
                    c.n_ls_rejected_no_improve += 1
                    continue
                pending.append((g, cand_perm, d, cand_routes, op))
                if p.strategy == "first":
                    break
            if not pending:
                continue
            if p.strategy == "best" and len(pending) > 1:
                key = ((lambda t: weighted_score(t[0], weights, scales)) if p.acceptance == "weighted"
                       else (lambda t: tuple(t[0])))
                pending.sort(key=key)
            g, cand_perm, d, cand_routes, op = pending[0]
            res.history.append({"op": op, "route": ri, "before": inc_g.tolist(), "after": g.tolist(),
                                "accepted_by": p.acceptance})
            inc_perm, inc_detail, inc_g = cand_perm, d, g
            res.accepted += 1
            c.n_ls_accepted += 1
            new_routes = [list(r) for r in d["routes"]]
            if new_routes != cand_routes:       # DP cắt lại, hoặc drift với policy evaluate_actual
                restart = True                  # bộ tuyến đổi: sang lượt mới với tuyến mới
            else:
                routes = cand_routes

    res.perm = list(inc_perm)
    res.detail = inc_detail
    res.elapsed_s = time.perf_counter() - t0
    c.elapsed_s += res.elapsed_s
    return res
