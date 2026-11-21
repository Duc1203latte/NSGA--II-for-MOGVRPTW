"""NSGA_II baseline cho MGVRPTW"""

from __future__ import annotations
import time
import numpy as np
from src.decoder import evaluate_detail
from src.instance import Instance

CROSSOVERS = ("ox", "obx")
MUTATIONS = ("standard", "always")

def evaluate_population(pop: list[np.ndarray], inst: Instance, W: np.ndarray | None = None,
                        scales: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    '''Trả về F (N x 3, cả ba cực tiểu) và CV (N,) = số xe vượt giới hạn.
    W (N x 3) khác None chỉ khi dp_split bật: chấm từng cá thể bằng evaluate_dp với trọng số của nó.'''
    F = np.empty((len(pop), 3))
    CV = np.zeros(len(pop))
    for i, perm in enumerate(pop):
        if W is None:
            d = evaluate_detail(perm.tolist(), inst)
        else:  # --- TV4 dp_split
            from src.improvements.dp_split import evaluate_dp
            d = evaluate_dp(perm.tolist(), inst, W[i], scales)
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
                   cfg: dict, pm: float, rng: np.random.Generator,
                   W: np.ndarray | None = None, rate_fn=None,
                   child_W_out: list | None = None) -> list[np.ndarray]:
    """W, rate_fn, child_W_out chỉ dùng khi bật cải tiến TV4; để mặc định thì đi đúng đường baseline.
    rate_fn(rank_p1, rank_p2) -> (pc, pm) cho mỗi cặp ghép (adaptive_rates).
    child_W_out: list nhận trọng số DP của từng con (cùng thứ tự với children)."""
    p = cfg["nsga2"]
    cross = ox if p["crossover"] == "ox" else obx
    children: list[np.ndarray] = []
    while len(children) < len(pop):
        i1 = tournament(rank, crowd, p["tournament_size"], rng)
        i2 = tournament(rank, crowd, p["tournament_size"], rng)
        p1, p2 = pop[i1], pop[i2]
        pc_pair, pm_pair = p["pc"], pm
        if rate_fn is not None:  # --- TV4 adaptive_rates
            pc_pair, pm_pair = rate_fn(rank[i1], rank[i2])
        if rng.random() < pc_pair:
            c1, c2 = cross(p1, p2, rng), cross(p2, p1, rng)
        else:
            c1, c2 = p1.copy(), p2.copy()
        for c in (c1, c2):
            mutate(c, pm_pair, p["mutation"], rng)
            if child_W_out is not None:  # --- TV4 dp_split: trọng số con, sau đột biến, trước LS/chấm
                from src.improvements.dp_split import child_weights
                child_W_out.append(child_weights(rng, W[i1], W[i2],
                                                 cfg["improvements"]["dp_split_params"]))
            children.append(c)
    if child_W_out is not None:
        del child_W_out[len(pop):]
    return children[: len(pop)]

def polish_front(pop: list[np.ndarray], F: np.ndarray, CV: np.ndarray, inst: Instance,
                 dp_params: dict) -> dict:
    """--- TV4 dp_split polish. Chấm lại từng hoán vị của quần thể cuối bằng evaluate_dp với K vector
    trọng số cố định (lưới simplex tất định, không RNG), gộp với quần thể cuối (hàng baseline đứng trước),
    bỏ hàng trùng vector mục tiêu và CV, rồi lấy tập không trội. Dùng chung cho lúc chạy (mode=polish) và
    cho polish ngoại tuyến trên kết quả đã lưu (scripts/tv4_polish_offline.py).
    Trả về pop, F, CV, W (NaN = chấm bằng split baseline), front, n_calls (số lời gọi evaluate_dp thêm)."""
    from src.improvements.dp_split import objective_scales, simplex_lattice
    scales = objective_scales(inst, dp_params["g3_scale"])
    lattice = simplex_lattice(dp_params["polish_k"])
    cand = [x for x in pop for _ in lattice]
    W_cand = np.tile(lattice, (len(pop), 1))
    F_c, CV_c = evaluate_population(cand, inst, W_cand, scales)
    pool_pop, pool_F, pool_CV = list(pop) + cand, np.vstack([F, F_c]), np.concatenate([CV, CV_c])
    pool_W = np.vstack([np.full((len(pop), 3), np.nan), W_cand])
    _, uniq = np.unique(np.column_stack([pool_F, pool_CV]), axis=0, return_index=True)
    uniq.sort()
    new_pop, new_F, new_CV, new_W = [pool_pop[i] for i in uniq], pool_F[uniq], pool_CV[uniq], pool_W[uniq]
    rank, _ = rank_and_crowding(new_F, new_CV)
    return {"pop": new_pop, "F": new_F, "CV": new_CV, "W": new_W,
            "front": np.flatnonzero(rank == 0), "n_calls": len(cand)}

def check_config(cfg: dict) -> None:
    p = cfg["nsga2"]
    if p["crossover"] not in CROSSOVERS:
        raise ValueError(f"crossover = {p['crossover']!r}, chỉ nhận {CROSSOVERS}")
    if p["mutation"] not in MUTATIONS:
        raise ValueError(f"mutation = {p['mutation']!r}, chỉ nhận {MUTATIONS}")

def run(inst: Instance, cfg: dict, seed: int) -> dict:
    '''Chạy NSGA-II một lần'''
    t_start = time.perf_counter()
    check_config(cfg)
    p = cfg["nsga2"]
    n_pop, n_gen = p["n_pop"], p["n_gen"]
    pm = mutation_rate(inst, cfg)
    rng = np.random.default_rng(seed)
    imp = cfg.get("improvements", {})
    use_dp, use_adaptive = bool(imp.get("dp_split", False)), bool(imp.get("adaptive_rates", False))
    # --- TV4 dp_split có hai chế độ: every_eval (chấm mọi cá thể bằng DP) và polish (chỉ sau thế hệ cuối)
    use_polish = False
    if use_dp:
        dp_mode = imp["dp_split_params"].get("mode", "every_eval")
        if dp_mode not in ("every_eval", "polish"):
            raise ValueError(f"dp_split_params.mode = {dp_mode!r}, chỉ nhận every_eval | polish")
        use_polish, use_dp = dp_mode == "polish", dp_mode == "every_eval"   # polish: tiến hoá như baseline

    pop = [rng.permutation(np.arange(1, inst.n + 1)) for _ in range(n_pop)]
    # --- TV4 dp_split: trọng số khởi tạo, bốc SAU các hoán vị để dãy hoán vị giống baseline.
    # W song song với pop (N x 3): đi theo pop qua khởi tạo, con cái, merged và chỉ số keep.
    W = scales = None
    n_dp_calls = 0
    if use_dp:
        from src.improvements.dp_split import objective_scales, sample_weights
        dp_params = imp["dp_split_params"]
        W = np.array([sample_weights(rng, dp_params) for _ in range(n_pop)])
        scales = objective_scales(inst, dp_params["g3_scale"])   # một lần mỗi run
        n_dp_calls += n_pop
    # --- TV4 adaptive_rates: tham số và tracker, một lần mỗi run
    rate_log = []
    if use_adaptive:
        from src.improvements.adaptive import StagnationTracker, adaptive_rates, resolve_params
        ad_params = resolve_params(imp["adaptive_params"], p, case29=inst.name.startswith("case29"))
        tracker = StagnationTracker(ad_params["stagnation_gens"], ad_params["boost"])
    F, CV = evaluate_population(pop, inst, W, scales)
    n_evals = n_pop
    history = []

    for _ in range(n_gen):
        rank, crowd = rank_and_crowding(F, CV)
        history.append(F[rank == 0].copy())

        rate_fn, pcs, pms = None, [], []
        if use_adaptive:  # --- TV4 adaptive_rates: pc/pm theo hạng cha mẹ từng cặp
            front1_fraction = float(np.mean(rank == 0))
            boost = tracker.update(F[rank == 0])
            max_rank = int(rank.max())

            def rate_fn(rank_a, rank_b):
                pc_, pm_ = adaptive_rates(rank_a, rank_b, max_rank, ad_params, front1_fraction, boost)
                pcs.append(pc_)
                pms.append(pm_)
                return pc_, pm_

        child_W = [] if use_dp else None
        children = make_offspring(pop, rank, crowd, cfg, pm, rng, W, rate_fn, child_W)
        W_child = np.array(child_W) if use_dp else None
        F_child, CV_child = evaluate_population(children, inst, W_child, scales)
        n_evals += len(children)
        if use_dp:
            n_dp_calls += len(children)
        if use_adaptive:
            rate_log.append({"front1_fraction": front1_fraction, "pc": pcs, "pm": pms})

        merged = pop + children
        F_all = np.vstack([F, F_child])
        CV_all = np.concatenate([CV, CV_child])
        # Loại trùng chỉ so byte của hoán vị: cùng hoán vị khác trọng số DP vẫn tính là trùng.
        keep = select_survivors(merged, F_all, CV_all, n_pop, p["eliminate_duplicates"])
        pop = [merged[i] for i in keep]
        F, CV = F_all[keep], CV_all[keep]
        if use_dp:  # --- TV4 dp_split: W đi theo keep, luôn thẳng hàng với pop
            W = np.vstack([W, W_child])[keep]

    rank, _ = rank_and_crowding(F, CV)
    history.append(F[rank == 0].copy())
    front = np.flatnonzero(rank == 0)
    pre_polish = None
    if use_polish:  # --- TV4 dp_split polish: DP với K trọng số cố định cho từng hoán vị cuối, không RNG
        pre_polish = {"pop": [x.tolist() for x in pop], "F": F.copy(), "CV": CV.copy(), "front": front.copy()}
        pol = polish_front(pop, F, CV, inst, imp["dp_split_params"])
        pop, F, CV, W, front = pol["pop"], pol["F"], pol["CV"], pol["W"], pol["front"]
        n_evals += pol["n_calls"]
        n_dp_calls += pol["n_calls"]
    return {
        "pop": [x.tolist() for x in pop],
        "F": F,                     # cực tiểu: (f1, f2, 1 - f3)
        "CV": CV,
        "front": front,             # chỉ số các cá thể ở front tốt nhất
        "history": history,         # front tốt nhất của từng thế hệ, n_gen + 1 phần tử
        "n_evals": n_evals,
        "seed": seed,
        "pm": pm,
        # --- TV4: thông tin thêm, không ảnh hưởng thuật toán
        "W": W,                     # trọng số DP (N x 3) thẳng hàng với pop; None khi dp_split tắt
        "n_dp_calls": n_dp_calls,
        "rate_log": rate_log,       # mỗi thế hệ {"front1_fraction", "pc": [...], "pm": [...]}
        "feasible_frac_pop": float(np.mean(CV == 0)),     # tỉ lệ nghiệm không vượt đội xe
        "feasible_frac_front": float(np.mean(CV[front] == 0)),
        "wall_time_s": time.perf_counter() - t_start,
        "dp_mode": "polish" if use_polish else ("every_eval" if use_dp else None),
        "pre_polish": pre_polish,   # polish: quần thể/F/CV/front trước khi polish (bằng baseline cùng seed)
    }
