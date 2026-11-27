"""TV3: cơ chế giữ đa dạng.

Hai phần, bật bằng improvements.diversity:
  1. Độ đo mật độ thay crowding distance (diversity_params.density):
       knn : khoảng cách tới láng giềng gần thứ k
       sde : như knn nhưng trước khi đo, dịch q về phía p ở mục tiêu mà q tốt hơn p
             (shift-based density estimation, Li, Yang & Liu 2014). Cá thể chỉ giỏi một mục
             tiêu bị coi là đông đúc nên bị phạt.
     Điểm càng lớn càng thưa, dùng y như crowding (giải đấu và chọn sống sót).
     Khi phải cắt front cuối: bỏ dần từng cá thể đông nhất, mỗi lần bỏ thì tính lại mật độ.
  2. External archive (diversity_params.archive): giữ mọi lời giải không bị trội qua các thế hệ,
     tối đa archive_size; đầy thì bỏ dần cá thể đông nhất theo cùng độ đo.

Mọi phép đo làm trên mục tiêu đã chuẩn hoá min-max về [0, 1] của chính tập đang xét.
Module không dùng bộ sinh ngẫu nhiên.
"""
from __future__ import annotations
import numpy as np

DENSITIES = ("knn", "sde")

def normalize(F: np.ndarray) -> np.ndarray:
    F = np.asarray(F, dtype=float)
    lo, hi = F.min(axis=0), F.max(axis=0)
    return (F - lo) / np.where(hi > lo, hi - lo, 1.0)

def distance_matrix(F: np.ndarray, method: str) -> np.ndarray:
    """D[p, q] = khoảng cách từ p tới q (đã dịch nếu sde). Đường chéo = inf."""
    if method not in DENSITIES:
        raise ValueError(f"density = {method!r}, chỉ nhận {DENSITIES}")
    X = normalize(F)
    if method == "sde":
        # q' = max(q, p) theo từng mục tiêu: q tốt hơn p ở đâu thì kéo về bằng p ở đó
        diff = np.maximum(X[None, :, :], X[:, None, :]) - X[:, None, :]
    else:
        diff = X[None, :, :] - X[:, None, :]
    D = np.sqrt((diff ** 2).sum(axis=2))
    np.fill_diagonal(D, np.inf)
    return D

def kth_distance(D: np.ndarray, k: int) -> np.ndarray:
    m = len(D)
    if m <= k:
        return np.full(m, np.inf)
    return np.partition(D, k - 1, axis=1)[:, k - 1]

def density_score(F: np.ndarray, method: str, k: int) -> np.ndarray:
    """Điểm thưa của từng cá thể, lớn hơn là tốt hơn (thay crowding distance)."""
    if len(F) <= 1:
        return np.full(len(F), np.inf)
    return kth_distance(distance_matrix(F, method), k)

def truncate(F: np.ndarray, n_keep: int, method: str, k: int) -> np.ndarray:
    """Chỉ số n_keep cá thể giữ lại, bỏ dần từng cá thể đông nhất.
    Chuẩn hoá một lần theo cả tập ban đầu. Hoà thì so tới láng giềng thứ k+1, k+2...
    (như truncation của SPEA2), vẫn hoà nữa thì bỏ chỉ số nhỏ hơn."""
    alive = np.arange(len(F))
    if n_keep >= len(F):
        return alive
    D = distance_matrix(F, method)
    while len(alive) > n_keep:
        sub = np.sort(D[np.ix_(alive, alive)], axis=1)[:, k - 1:]   # láng giềng thứ k trở đi
        worst = np.lexsort(sub.T[::-1])[0]                          # nhỏ nhất theo thứ tự từ điển
        alive = np.delete(alive, worst)
    return alive

# --------------------------------------------------------------------------- archive

def pareto_mask(F: np.ndarray, CV: np.ndarray) -> np.ndarray:
    """True ở cá thể không bị ai trội (constrained domination như nsga2)."""
    from src.nsga2 import domination_matrix   # import muộn để tránh vòng import
    return ~domination_matrix(F, CV).any(axis=0)

def update_archive(arc_pop: list[np.ndarray], arc_F: np.ndarray, arc_CV: np.ndarray,
                   new_pop: list[np.ndarray], new_F: np.ndarray, new_CV: np.ndarray,
                   size: int, method: str, k: int):
    """Gộp archive với lời giải mới, giữ phần không bị trội, bỏ trùng vector mục tiêu,
    vượt size thì cắt theo mật độ. Trả về (pop, F, CV) của archive mới."""
    pop = arc_pop + new_pop
    F = np.vstack([arc_F, new_F]) if len(arc_pop) else np.asarray(new_F, dtype=float)
    CV = np.concatenate([arc_CV, new_CV]) if len(arc_pop) else np.asarray(new_CV, dtype=float)
    _, first = np.unique(F, axis=0, return_index=True)    # trùng mục tiêu: giữ bản đầu tiên
    idx = np.sort(first)
    idx = idx[pareto_mask(F[idx], CV[idx])]
    if len(idx) > size:
        idx = idx[truncate(F[idx], size, method, k)]
    return [pop[i] for i in idx], F[idx], CV[idx]

def check_params(dp: dict) -> None:
    if dp["density"] not in DENSITIES:
        raise ValueError(f"diversity_params.density = {dp['density']!r}, chỉ nhận {DENSITIES}")
    if dp["k"] < 1 or dp["archive_size"] < 1:
        raise ValueError("diversity_params.k và archive_size phải >= 1")


if __name__ == "__main__":
    # Tự kiểm nhanh: điểm giữa ba điểm gần nhau bị bỏ trước
    F = np.array([[0, 1, 0], [0.5, 0.5, 0], [0.51, 0.49, 0], [1, 0, 0]])
    assert set(truncate(F, 3, "knn", 1).tolist()) in ({0, 1, 3}, {0, 2, 3})
    print("ok")
