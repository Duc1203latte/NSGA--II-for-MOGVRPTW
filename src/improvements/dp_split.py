"""Split toi uu (Prins) bang quy hoach dong, thay split_greedy khi co improvements.dp_split bat.

Moi tuyen xuat phat tu kho luc inst.depart_time va cac tuyen doc lap nhau, nen moi muc tieu
la tong dong gop tung tuyen. Tong co trong so cua cac dong gop da chuan hoa cung cong tinh
duoc theo tuyen, nen DP la chinh xac cho chi phi vo huong do.
"""

from __future__ import annotations
import logging
import numpy as np
from src.decoder import (
    MINUTES_PER_HOUR, emission_factor, evaluate_routes_detail, satisfaction, split_greedy,
)
from src.instance import Instance, load_config

log = logging.getLogger(__name__)

EPS = 1e-9                                   # san duoi cho he so chuan hoa
_scales_cache: dict[tuple[str, int], np.ndarray] = {}
_warned_infeasible = False                   # chi canh bao mot lan


class _RouteState:
    """Trang thai tuyen dang mo rong, cap nhat O(1) moi khach them vao."""

    def __init__(self, inst: Instance):
        p = inst.params
        self.inst = inst
        self.cost = p["cost"]
        self.v = p["speed_kmh"]
        self.slope = (self.cost["rho_star"] - self.cost["rho0"]) / inst.capacity
        self.k_emit = emission_factor(p) / p["emission"]["grams_per_kg"]
        self.reset()

    def reset(self) -> None:
        self.t = self.inst.depart_time   # gio roi diem hien tai
        self.prev = 0
        self.km_open = 0.0               # km cac chang chua tinh chang ve kho
        self.w = 0.0                     # tong d_m * tai_m, tai_m la tai truoc khi giao
        self.early = 0.0
        self.late = 0.0
        self.g3 = 0.0                    # tong (1 - W/100), chua chia n
        self.load = 0.0

    def append(self, c: int) -> None:
        inst = self.inst
        dn = inst.demand[c]
        # tai luc roi kho tang dn -> moi chang truoc tang slope*dn*km_open
        self.w += dn * self.km_open
        d = inst.dist[self.prev, c]
        self.km_open += d
        self.w += d * dn                 # chang vao c chi cho hang cua c (cac khach sau chua co)
        self.load += dn

        arrive = self.t + d / self.v * MINUTES_PER_HOUR
        et, lt = inst.tw_specified[c]
        eta, ltb = inst.tw_expected[c]
        self.early += max(eta - arrive, 0.0)
        self.late += max(arrive - ltb, 0.0)
        self.g3 += 1.0 - satisfaction(arrive, et, eta, ltb, lt) / 100.0
        self.t = max(arrive, eta) + inst.service_time[c]
        self.prev = c

    def terms(self) -> tuple[float, float, float]:
        inst, cost = self.inst, self.cost
        d_ret = inst.dist[self.prev, 0]
        km = self.km_open + d_ret
        fuel = cost["rho0"] * km + self.slope * self.w   # chang ve kho: xe rong
        f1 = (cost["sigma1"] * fuel + cost["sigma2"] + cost["sigma3"] * km
              + (cost["alpha"] * self.early + cost["beta"] * self.late) / MINUTES_PER_HOUR)
        f2 = self.k_emit * km
        return f1, f2, self.g3 / inst.n


def route_cost_terms(seq: list[int], inst: Instance) -> tuple[float, float, float]:
    """(f1_r, f2_r, g3_r) cua mot tuyen, khop dong gop cua tuyen do trong evaluate_routes_detail."""
    st = _RouteState(inst)
    for c in seq:
        st.append(c)
    return st.terms()


def sample_weights(rng, params: dict) -> np.ndarray:
    """Trong so (w1, w2, w3) cho mot ca the moi. Chi dung rng duoc truyen vao.
    dirichlet: 1 lan rng.dirichlet. onehot: 1 lan rng.integers(3)."""
    dist = params["weight_dist"]
    if dist == "dirichlet":
        return np.asarray(rng.dirichlet([1.0, 1.0, 1.0]), dtype=float)
    if dist == "onehot":
        w = np.zeros(3)
        w[int(rng.integers(3))] = 1.0
        return w
    raise ValueError(f"weight_dist = {dist!r} chua duoc ho tro")


def child_weights(rng, parent_a_weights, parent_b_weights, params: dict) -> np.ndarray:
    """Trong so cua con. fresh: boc moi (cung so lan rng nhu sample_weights).
    parent: sao chep trong so cua mot cha me chon ngau nhien (dung 1 lan rng.integers(2))."""
    mode = params["weight_inherit"]
    if mode == "fresh":
        return sample_weights(rng, params)
    if mode == "parent":
        src = parent_a_weights if int(rng.integers(2)) == 0 else parent_b_weights
        return np.array(src, dtype=float)
    raise ValueError(f"weight_inherit = {mode!r} chua duoc ho tro")


def _nearest_neighbor(inst: Instance) -> list[int]:
    left = set(range(1, inst.n + 1))
    cur, out = 0, []
    while left:
        nxt = min(left, key=lambda c: (inst.dist[cur, c], c))
        out.append(nxt)
        left.remove(nxt)
        cur = nxt
    return out


def objective_scales(inst: Instance) -> np.ndarray:
    """He so chuan hoa co dinh. f1, f2: trung binh tren 3 hoan vi tat dinh (greedy split).
    g3 da nam trong [0,1] nen he so lay tu config (g3_scale)."""
    key = (inst.name, inst.n)
    if key in _scales_cache:
        return _scales_cache[key]
    idx = np.arange(1, inst.n + 1)
    by_eta = sorted(idx.tolist(), key=lambda c: (inst.tw_expected[c, 0], inst.dist[0, c], c))
    perms = [idx.tolist(), by_eta, _nearest_neighbor(inst)]
    vals = []
    for p in perms:
        d = evaluate_routes_detail(split_greedy(p, inst), inst)
        vals.append((d["f1"], d["f2"]))
    g3_scale = load_config()["improvements"]["dp_split_params"]["g3_scale"]
    scales = np.maximum(np.append(np.mean(vals, axis=0), g3_scale), EPS)
    _scales_cache[key] = scales
    return scales


def _build_arcs(perm, inst: Instance, weights, scales) -> list[list[tuple[int, float]]]:
    """arcs[i] = [(j, cost)]: tuyen phuc vu perm[i..j-1], cost cong don O(1) moi lan them khach.
    Tach rieng de test doi chieu voi route_cost_terms."""
    w = np.asarray(weights, dtype=float) / np.asarray(scales, dtype=float)
    st = _RouteState(inst)
    arcs = []
    for i in range(len(perm)):
        st.reset()
        row = []
        for j in range(i + 1, len(perm) + 1):
            c = perm[j - 1]
            if st.load + inst.demand[c] > inst.capacity:
                break
            st.append(c)
            f1, f2, g3 = st.terms()
            row.append((j, w[0] * f1 + w[1] * f2 + w[2] * g3))
        arcs.append(row)
    return arcs


def split_dp(perm: list[int], inst: Instance, weights, scales) -> list[list[int]]:
    """Giu nguyen thu tu perm, chon cho cat de toi thieu tong dot(weights, terms_r / scales)."""
    global _warned_infeasible
    n = len(perm)
    arcs = _build_arcs(perm, inst, weights, scales)

    inf = float("inf")
    if inst.fleet_size is None:
        dp = [inf] * (n + 1)
        pred = [-1] * (n + 1)
        dp[0] = 0.0
        for i in range(n):
            if dp[i] == inf:
                continue
            for j, cst in arcs[i]:
                if dp[i] + cst < dp[j]:
                    dp[j], pred[j] = dp[i] + cst, i
        cuts = _backtrack_1d(pred, n)
    else:
        kmax = inst.fleet_size
        dp = [[inf] * (n + 1) for _ in range(kmax + 1)]
        pred = [[-1] * (n + 1) for _ in range(kmax + 1)]
        dp[0][0] = 0.0
        for k in range(kmax):
            for i in range(n):
                if dp[k][i] == inf:
                    continue
                for j, cst in arcs[i]:
                    if dp[k][i] + cst < dp[k + 1][j]:
                        dp[k + 1][j], pred[k + 1][j] = dp[k][i] + cst, i
        best_k = min(range(1, kmax + 1), key=lambda k: dp[k][n], default=None)
        if best_k is None or dp[best_k][n] == inf:
            if not _warned_infeasible:
                log.warning("split_dp: khong co cach cat trong gioi han %d xe, dung split_greedy",
                            kmax)
                _warned_infeasible = True
            return split_greedy(perm, inst)
        cuts, j = [], n
        for k in range(best_k, 0, -1):
            cuts.append(j)
            j = pred[k][j]
        cuts.append(0)
        cuts.reverse()

    return [list(perm[a:b]) for a, b in zip(cuts[:-1], cuts[1:])]


def _backtrack_1d(pred: list[int], n: int) -> list[int]:
    cuts, j = [n], n
    while j > 0:
        j = pred[j]
        cuts.append(j)
    cuts.reverse()
    return cuts


def evaluate_dp(perm: list[int], inst: Instance, weights, scales=None) -> dict:
    """Split DP roi di qua duong danh gia chinh thuc evaluate_routes_detail."""
    if scales is None:
        scales = objective_scales(inst)
    routes = split_dp(perm, inst, weights, scales)
    d = evaluate_routes_detail(routes, inst)
    d["weights"] = np.asarray(weights, dtype=float).copy()
    d["split"] = "dp"
    return d
