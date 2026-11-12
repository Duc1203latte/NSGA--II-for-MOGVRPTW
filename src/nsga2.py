"""NSGA_II baseline cho MGVRPTW"""

from __future__ import annotations
import numpy as np
from src.decoder import evaluate_detail
from src.instance import Instance

CROSSOVERS = ("ox", "obx")
MUTATIONS = ("standard", "always")

def evaluate_population(pop: list[np.ndarray], inst: Instance) -> tuple[np.ndarray, np.ndarray]:
    '''Trả về F (N x 3, cả ba cực tiểu) và CV (N,) = số xe vượt giới hạn'''
    F = np.empty((len(pop), 3))
    CV = np.zeros(len(pop))
    for i, perm in enumerate(pop):
        d = evaluate_detail(perm.tolist(), inst)
        F[i] = (d["f1"], d["f2"], 1.0 - d["f3"])
        if inst.fleet_size is not None:
            CV[i] = max(0, d["n_vehicles"] - inst.fleet_size)
    return F, CV

#Sắp xếp không trội
def domination_matrix(F: np.ndarray, CV: np.ndarray) -> np.ndarray:
    no_worse = np.all(F[:, None, :] <= F[None, :, :], axis=2)
    better = np.any(F[:, None, :] < F[None, :, :], axis=2)
    pareto = no_worse & better
    cv_i, cv_j = CV[:, None], CV[None, :]
    return (cv_i < cv_j) | ((cv_i == cv_j) & pareto)

def non_dominated_sort(F: np.ndarray, CV: np.ndarray) -> np.ndarray:
    D = domination_matrix(F, CV)
    n_dominators = D.sum(axis=0)              # số cá thể trội mình
    rank = np.full(len(F), -1)
    current = np.flatnonzero(n_dominators == 0)
    r = 0
    while current.size > 0:
        rank[current] = r
        n_dominators = n_dominators - D[current].sum(axis=0)   # bỏ front vừa xếp ra
        current = np.flatnonzero((n_dominators == 0) & (rank == -1))
        r += 1
    return rank

def crowding_distance(F: np.ndarray) -> np.ndarray:
    m = len(F)
    if m <= 2:
        return np.full(m, np.inf)
    dist = np.zeros(m)
    for j in range(F.shape[1]):
        order = np.argsort(F[:, j], kind="stable")
        lo, hi = F[order[0], j], F[order[-1], j]
        dist[order[0]] = dist[order[-1]] = np.inf
        if hi > lo:
            dist[order[1:-1]] += (F[order[2:], j] - F[order[:-2], j]) / (hi - lo)
    return dist

def rank_and_crowding(F: np.ndarray, CV: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rank = non_dominated_sort(F, CV)
    crowd = np.zeros(len(F))
    for r in np.unique(rank):
        idx = np.flatnonzero(rank == r)
        crowd[idx] = crowding_distance(F[idx])
    return rank, crowd

def split_duplicates(pop: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Chia chỉ số quần thể thành bản gốc (lần đầu gặp) và bản sao (hoán vị đã gặp trước đó)"""
    seen: set[bytes] = set()
    first, dup = [], []
    for i, perm in enumerate(pop):
        key = perm.tobytes()
        (dup if key in seen else first).append(i)
        seen.add(key)
    return np.array(first, dtype=int), np.array(dup, dtype=int)


def select_survivors(pop: list[np.ndarray], F: np.ndarray, CV: np.ndarray,
                     n_keep: int, eliminate_duplicates: bool) -> np.ndarray:
    """Chọn n_keep cá thể sống sót. Nếu loại trùng: chỉ chọn trong các hoán vị khác nhau,
    bản sao chỉ dùng để lấp chỗ khi không đủ hoán vị khác nhau"""
    if not eliminate_duplicates:
        return environmental_selection(F, CV, n_keep)
    first, dup = split_duplicates(pop)
    if len(first) >= n_keep:
        return first[environmental_selection(F[first], CV[first], n_keep)]
    return np.concatenate([first, dup[: n_keep - len(first)]])

def environmental_selection(F: np.ndarray, CV: np.ndarray, n_keep: int) -> np.ndarray:
    rank, crowd = rank_and_crowding(F, CV)
    chosen: list[int] = []
    for r in np.unique(rank):
        idx = np.flatnonzero(rank == r)
        if len(chosen) + len(idx) <= n_keep:
            chosen.extend(idx.tolist())
        else:
            order = idx[np.argsort(-crowd[idx], kind="stable")]
            chosen.extend(order[: n_keep - len(chosen)].tolist())
            break
    return np.array(chosen)

#Chọn lọc
def tournament(rank: np.ndarray, crowd: np.ndarray, k: int, rng: np.random.Generator) -> int:
    cand = rng.choice(len(rank), size=k, replace=False)
    best = cand[0]
    for c in cand[1:]:
        if rank[c] < rank[best] or (rank[c] == rank[best] and crowd[c] > crowd[best]):
            best = c
    return int(best)

#Lai ghép
def ox(p1: np.ndarray, p2: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    n = len(p1)
    a, b = np.sort(rng.choice(n, size=2, replace=False))
    child = np.empty(n, dtype=p1.dtype)
    child[a:b + 1] = p1[a:b + 1]
    kept = set(p1[a:b + 1].tolist())
    p2_from_b = np.concatenate([p2[b + 1:], p2[:b + 1]])
    fill = [g for g in p2_from_b if g not in kept]
    positions = list(range(b + 1, n)) + list(range(0, a))
    child[positions] = fill
    return child

def obx_with_mask(p1: np.ndarray, p2: np.ndarray, mask: np.ndarray) -> np.ndarray:
    selected = p1[mask]                         # gen được chọn, theo thứ tự trong p1
    child = p2.copy()
    holes = np.isin(p2, selected)               # vị trí của các gen đó trong p2
    child[holes] = selected
    return child

def obx(p1: np.ndarray, p2: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    return obx_with_mask(p1, p2, rng.random(len(p1)) < 0.5)

#Đột biến
def inversion(perm: np.ndarray, rng: np.random.Generator) -> None:
    a, b = np.sort(rng.choice(len(perm), size=2, replace=False))
    perm[a:b + 1] = perm[a:b + 1][::-1]

def swap(perm: np.ndarray, rng: np.random.Generator) -> None:
    a, b = rng.choice(len(perm), size=2, replace=False)
    perm[a], perm[b] = perm[b], perm[a]

def mutate(perm: np.ndarray, pm: float, mode: str, rng: np.random.Generator) -> None:
    if mode == "standard":
        if rng.random() < pm:
            (inversion if rng.random() < 0.5 else swap)(perm, rng)
    else:  # "always"
        (inversion if rng.random() < pm else swap)(perm, rng)

#Vòng lặp chính
def mutation_rate(inst: Instance, cfg: dict) -> float:
    pm = cfg["nsga2"]["pm"]
    return pm["case29"] if inst.name.startswith("case29") else pm["solomon"]

def make_offspring(pop: list[np.ndarray], rank: np.ndarray, crowd: np.ndarray,
                   cfg: dict, pm: float, rng: np.random.Generator) -> list[np.ndarray]:
    p = cfg["nsga2"]
    cross = ox if p["crossover"] == "ox" else obx
    children: list[np.ndarray] = []
    while len(children) < len(pop):
        p1 = pop[tournament(rank, crowd, p["tournament_size"], rng)]
        p2 = pop[tournament(rank, crowd, p["tournament_size"], rng)]
        if rng.random() < p["pc"]:
            c1, c2 = cross(p1, p2, rng), cross(p2, p1, rng)
        else:
            c1, c2 = p1.copy(), p2.copy()
        for c in (c1, c2):
            mutate(c, pm, p["mutation"], rng)
            children.append(c)
    return children[: len(pop)]

def check_config(cfg: dict) -> None:
    p = cfg["nsga2"]
    if p["crossover"] not in CROSSOVERS:
        raise ValueError(f"crossover = {p['crossover']!r}, chỉ nhận {CROSSOVERS}")
    if p["mutation"] not in MUTATIONS:
        raise ValueError(f"mutation = {p['mutation']!r}, chỉ nhận {MUTATIONS}")

def run(inst: Instance, cfg: dict, seed: int) -> dict:
    '''Chạy NSGA-II một lần'''
    check_config(cfg)
    p = cfg["nsga2"]
    n_pop, n_gen = p["n_pop"], p["n_gen"]
    pm = mutation_rate(inst, cfg)
    rng = np.random.default_rng(seed)

    pop = [rng.permutation(np.arange(1, inst.n + 1)) for _ in range(n_pop)]
    F, CV = evaluate_population(pop, inst)
    n_evals = n_pop
    history = []

    for _ in range(n_gen):
        rank, crowd = rank_and_crowding(F, CV)
        history.append(F[rank == 0].copy())

        children = make_offspring(pop, rank, crowd, cfg, pm, rng)
        F_child, CV_child = evaluate_population(children, inst)
        n_evals += len(children)

        merged = pop + children
        F_all = np.vstack([F, F_child])
        CV_all = np.concatenate([CV, CV_child])
        keep = select_survivors(merged, F_all, CV_all, n_pop, p["eliminate_duplicates"])
        pop = [merged[i] for i in keep]
        F, CV = F_all[keep], CV_all[keep]

    rank, _ = rank_and_crowding(F, CV)
    history.append(F[rank == 0].copy())
    front = np.flatnonzero(rank == 0)
    return {
        "pop": [x.tolist() for x in pop],
        "F": F,                     # cực tiểu: (f1, f2, 1 - f3)
        "CV": CV,
        "front": front,             # chỉ số các cá thể ở front tốt nhất
        "history": history,         # front tốt nhất của từng thế hệ, n_gen + 1 phần tử
        "n_evals": n_evals,
        "seed": seed,
        "pm": pm,
    }
