"""TV2 - khởi tạo quần thể thông minh (cờ ``improvements.init_smart``).

Sinh ``n_pop`` hoán vị 1..n theo ba nguồn:

* ``nn``     : nearest-neighbor xuất phát từ kho, hoà thì lấy ID nhỏ hơn;
* ``tw``     : sắp theo ETa (``tw_expected[:, 0]``), hoà thì gần khách trước đó (hoặc kho) hơn,
               vẫn hoà thì ID nhỏ hơn;
* ``random`` : đúng như baseline (``baseline_factory(rng)``, mặc định ``rng.permutation``).

Hai nguồn đầu tất định, nên biến thể được tạo bằng 1..k lần hoán đổi hai vị trí (vẫn là hoán vị).

Quy tắc RNG (minh bạch, tái lập):

* Module chỉ dùng ``rng`` được truyền vào, không tạo RNG riêng, không đọc config.
* Thứ tự sinh: toàn bộ nhóm ``nn`` -> nhóm ``tw`` -> nhóm ``random``. Không xáo thứ tự quần thể.
* Bản "thuần" (``keep_pure_seed``) của nn/tw không tiêu thụ RNG.
* Mỗi lần xáo: 1 lần ``rng.integers`` cho số lần hoán đổi, rồi mỗi lần hoán đổi
  1 lần ``rng.choice(n, 2, replace=False)``. Với n < 2 không xáo, không dùng RNG.
* Trùng lặp: thử lại tối đa ``dedup_max_attempts`` lần, hết thì sinh random dự phòng
  (nhãn ``random_fallback``). Khi không thể đủ hoán vị khác nhau (n! < n_pop) thì chấp nhận
  trùng, ghi lại trong ``n_duplicates``.

Khi cờ tắt, ``nsga2.py`` KHÔNG được gọi module này (xem docs/tv2_integration.md).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Mapping

import numpy as np

from src.instance import Instance

SOURCES: tuple[str, ...] = ("nn", "tw", "random")
FALLBACK_LABEL = "random_fallback"
RATIO_TOL = 1e-6

BaselineFactory = Callable[[np.random.Generator], "list[int]"]


# --------------------------------------------------------------------------- tham số
@dataclass(frozen=True)
class InitSmartParams:
    ratios: dict[str, float]
    perturb_swaps_min: int = 1
    perturb_swaps_max: int = 3
    keep_pure_seed: bool = True
    dedup_max_attempts: int = 50


def parse_init_params(raw: Mapping | InitSmartParams) -> InitSmartParams:
    """Kiểm tra và chuẩn hoá ``improvements.init_smart_params``. Sai thì ValueError rõ ràng."""
    if isinstance(raw, InitSmartParams):
        raw = raw.__dict__
    if not isinstance(raw, Mapping):
        raise ValueError("init_smart_params phải là dict")
    unknown = set(raw) - {"ratios", "perturb_swaps_min", "perturb_swaps_max",
                          "keep_pure_seed", "dedup_max_attempts"}
    if unknown:
        raise ValueError(f"init_smart_params: khoá không hỗ trợ {sorted(unknown)}")
    if "ratios" not in raw:
        raise ValueError("init_smart_params: thiếu 'ratios'")
    ratios = dict(raw["ratios"])
    if set(ratios) != set(SOURCES):
        raise ValueError(f"ratios phải có đúng các khoá {SOURCES}, nhận {sorted(ratios)}")
    for k, v in ratios.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f"ratios[{k!r}] = {v!r}: phải là số hữu hạn >= 0")
    total = sum(float(v) for v in ratios.values())
    if abs(total - 1.0) > RATIO_TOL:
        raise ValueError(f"tổng ratios = {total}, phải bằng 1 (sai số {RATIO_TOL})")

    kmin = raw.get("perturb_swaps_min", 1)
    kmax = raw.get("perturb_swaps_max", 3)
    for name, v in (("perturb_swaps_min", kmin), ("perturb_swaps_max", kmax)):
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError(f"{name} phải là số nguyên, nhận {v!r}")
    if not 1 <= kmin <= kmax:
        raise ValueError(f"cần 1 <= perturb_swaps_min <= perturb_swaps_max, nhận {kmin}, {kmax}")
    att = raw.get("dedup_max_attempts", 50)
    if isinstance(att, bool) or not isinstance(att, int) or att < 1:
        raise ValueError(f"dedup_max_attempts phải là số nguyên >= 1, nhận {att!r}")
    pure = raw.get("keep_pure_seed", True)
    if not isinstance(pure, bool):
        raise ValueError(f"keep_pure_seed phải là bool, nhận {pure!r}")
    return InitSmartParams({k: float(ratios[k]) for k in SOURCES}, kmin, kmax, pure, att)


def allocate_quota(n_pop: int, ratios: Mapping[str, float]) -> dict[str, int]:
    """Largest remainder: floor(n_pop*r), phát nốt slot theo phần dư lớn nhất.
    Hoà phần dư thì theo thứ tự nn, tw, random. Tổng luôn đúng n_pop."""
    if isinstance(n_pop, bool) or not isinstance(n_pop, (int, np.integer)) or n_pop <= 0:
        raise ValueError(f"n_pop phải là số nguyên > 0, nhận {n_pop!r}")
    n_pop = int(n_pop)
    exact = {k: n_pop * float(ratios[k]) for k in SOURCES}
    quota = {k: int(math.floor(exact[k] + 1e-9)) for k in SOURCES}
    rem = {k: exact[k] - quota[k] for k in SOURCES}
    left = n_pop - sum(quota.values())
    # sắp theo phần dư giảm dần; sorted ổn định nên hoà giữ thứ tự SOURCES
    for k in sorted(SOURCES, key=lambda s: -round(rem[s], 9))[:max(left, 0)]:
        quota[k] += 1
    assert sum(quota.values()) == n_pop
    return quota


# --------------------------------------------------------------------------- hoán vị gốc
def nearest_neighbor_order(inst: Instance) -> list[int]:
    """Từ kho, mỗi bước chọn khách chưa ghé có dist[cur, c] nhỏ nhất; hoà thì ID nhỏ hơn."""
    left = list(range(1, inst.n + 1))
    cur, out = 0, []
    while left:
        nxt = min(left, key=lambda c: (inst.dist[cur, c], c))
        out.append(nxt)
        left.remove(nxt)
        cur = nxt
    return out


def time_window_order(inst: Instance) -> list[int]:
    """Chọn tuần tự khách có ETa (tw_expected[c, 0]) nhỏ nhất; hoà ETa thì gần điểm trước đó
    (kho với khách đầu tiên) hơn; vẫn hoà thì ID nhỏ hơn. ETa, KHÔNG phải ET."""
    left = list(range(1, inst.n + 1))
    cur, out = 0, []
    eta = inst.tw_expected[:, 0]
    while left:
        nxt = min(left, key=lambda c: (eta[c], inst.dist[cur, c], c))
        out.append(nxt)
        left.remove(nxt)
        cur = nxt
    return out


def perturb_swaps(perm: list[int], rng: np.random.Generator, k_min: int, k_max: int) -> list[int]:
    """Bản sao của perm sau k ∈ [k_min, k_max] lần hoán đổi hai vị trí khác nhau.
    Giữ nguyên multiset. n < 2 thì trả bản sao, không dùng RNG."""
    out = list(perm)
    n = len(out)
    if n < 2:
        return out
    k = int(rng.integers(k_min, k_max + 1))
    for _ in range(k):
        i, j = (int(x) for x in rng.choice(n, 2, replace=False))
        out[i], out[j] = out[j], out[i]
    return out


def _default_factory(n: int) -> BaselineFactory:
    ids = np.arange(1, n + 1)
    return lambda rng: rng.permutation(ids).tolist()


# --------------------------------------------------------------------------- quần thể
@dataclass
class InitResult:
    population: list[list[int]]
    sources: list[str]
    quota: dict[str, int]
    effective_counts: dict[str, int]
    n_duplicates: int = 0
    n_dedup_retries: int = 0
    notes: list[str] = field(default_factory=list)


def _max_unique(n: int, cap: int) -> int:
    """min(n!, cap) không tính giai thừa lớn."""
    m = 1
    for k in range(2, n + 1):
        m *= k
        if m >= cap:
            return cap
    return min(m, cap)


def make_initial_population_detailed(
    inst: Instance,
    n_pop: int,
    rng: np.random.Generator,
    params: Mapping | InitSmartParams,
    baseline_factory: BaselineFactory | None = None,
) -> InitResult:
    """Như ``make_initial_population`` nhưng trả thêm quota/effective_counts/thống kê trùng."""
    p = parse_init_params(params)
    quota = allocate_quota(n_pop, p.ratios)
    n = inst.n
    factory = baseline_factory or _default_factory(n)
    n_unique_max = _max_unique(n, n_pop)          # min(n!, n_pop)
    can_be_unique = n_unique_max >= n_pop

    pop: list[list[int]] = []
    src: list[str] = []
    seen: set[tuple[int, ...]] = set()
    res = InitResult(pop, src, quota, {k: 0 for k in (*SOURCES, FALLBACK_LABEL)})
    if not can_be_unique:
        res.notes.append(f"n={n}: n! < n_pop={n_pop}, không thể khác nhau hết, chấp nhận trùng")

    def push(perm: list[int], label: str) -> None:
        t = tuple(perm)
        if t in seen:
            res.n_duplicates += 1
        seen.add(t)
        pop.append(list(perm))
        src.append(label)
        res.effective_counts[label] += 1

    def dedup_active() -> bool:
        # còn hoán vị chưa dùng thì còn khử trùng (kể cả khi n! < n_pop)
        return len(seen) < n_unique_max

    def fresh_random(label: str) -> None:
        perm = list(factory(rng))
        tries = 1
        while dedup_active() and tuple(perm) in seen and tries < p.dedup_max_attempts:
            res.n_dedup_retries += 1
            perm = list(factory(rng))
            tries += 1
        push(perm, label)

    bases = {"nn": nearest_neighbor_order(inst), "tw": time_window_order(inst)}
    for label in ("nn", "tw"):
        base = bases[label]
        for slot in range(quota[label]):
            if slot == 0 and p.keep_pure_seed:
                if tuple(base) not in seen or not dedup_active():
                    push(base, label)
                    continue
                # bản thuần trùng với nhóm trước (vd NN == TW): rơi xuống xáo như slot thường
            ok = False
            for _ in range(p.dedup_max_attempts):
                cand = perturb_swaps(base, rng, p.perturb_swaps_min, p.perturb_swaps_max)
                if not dedup_active() or tuple(cand) not in seen:
                    push(cand, label)
                    ok = True
                    break
                res.n_dedup_retries += 1
            if not ok:
                fresh_random(FALLBACK_LABEL)

    for _ in range(quota["random"]):
        fresh_random("random")

    if res.effective_counts[FALLBACK_LABEL]:
        res.notes.append(f"{res.effective_counts[FALLBACK_LABEL]} slot nn/tw hết lượt khử trùng, "
                         f"thay bằng random dự phòng")
    assert len(pop) == n_pop
    return res


def make_initial_population(
    inst: Instance,
    n_pop: int,
    rng: np.random.Generator,
    params: Mapping | InitSmartParams,
    baseline_factory: BaselineFactory | None = None,
) -> tuple[list[list[int]], list[str]]:
    """API cho TV1 gọi khi ``improvements.init_smart`` bật.

    Trả về (``n_pop`` hoán vị 1..n dạng ``list[int]``, nhãn nguồn tương ứng
    ``'nn' | 'tw' | 'random' | 'random_fallback'``). ``params`` =
    ``cfg["improvements"]["init_smart_params"]``; ``baseline_factory(rng) -> list[int]`` nên là
    đúng dòng sinh cá thể ngẫu nhiên của baseline để nhóm random giống baseline.
    """
    r = make_initial_population_detailed(inst, n_pop, rng, params, baseline_factory)
    return r.population, r.sources
