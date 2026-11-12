"""Chỉ số đánh giá tập Pareto
HV, IGD, SP, DM tính trên mục tiêu đã chuẩn hoá về [0, 1]. Cận chuẩn hoá lấy min-max của
MỌI điểm trong mọi front (mọi cấu hình, mọi run trên cùng instance), không chỉ reference set,
để front nào cũng nằm trong [0, 1]. SC chỉ so trội nên không cần chuẩn hoá.
"""

from __future__ import annotations
import numpy as np
from pymoo.indicators.hv import HV
from pymoo.indicators.igd import IGD
from src.nsga2 import domination_matrix

def non_dominated(F: np.ndarray) -> np.ndarray:
    #Bỏ điểm trùng nhau và điểm bị trội, giữ lại phần không bị trội
    F = np.unique(np.asarray(F, dtype=float), axis=0)
    D = domination_matrix(F, np.zeros(len(F)))
    return F[~D.any(axis=0)]                   # cột j không có ai trội

def reference_set(fronts: list[np.ndarray]) -> np.ndarray:
    #Gộp front của mọi thuật toán, mọi run trên cùng một instance, rồi lọc phần không bị trội
    return non_dominated(np.vstack(fronts))

def normalization_bounds(fronts: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Min và max từng mục tiêu trên mọi điểm của mọi front"""
    allF = np.vstack(fronts)
    return allF.min(axis=0), allF.max(axis=0)

def normalize(F: np.ndarray, bounds: tuple[np.ndarray, np.ndarray]) -> np.ndarray:
    """Chuẩn hoá min-max. Mục tiêu nào không đổi thì chia cho 1"""
    lo, hi = bounds
    span = np.where(hi > lo, hi - lo, 1.0)
    return (np.asarray(F, dtype=float) - lo) / span

#Các chỉ số
def hv(F: np.ndarray, bounds: tuple[np.ndarray, np.ndarray], ref_point: list[float]) -> float:
    return float(HV(ref_point=np.asarray(ref_point, dtype=float))(normalize(F, bounds)))

def igd(F: np.ndarray, ref_set: np.ndarray, bounds: tuple[np.ndarray, np.ndarray]) -> float:
    return float(IGD(normalize(ref_set, bounds))(normalize(F, bounds)))

def sp(F: np.ndarray) -> float:
    F = np.asarray(F, dtype=float)
    if len(F) < 2:
        return float("nan")
    dist = np.linalg.norm(F[:, None, :] - F[None, :, :], axis=2)
    np.fill_diagonal(dist, np.inf)
    d = dist.min(axis=1)
    return float(np.sqrt(((d.mean() - d) ** 2).sum() / (len(F) - 1)))

def sc(A: np.ndarray, B: np.ndarray) -> float:
    """Set coverage (31): tỉ lệ điểm của B bị ít nhất một điểm của A trội.
    SC(A, B) = 1 nghĩa là A phủ hết B. Phải xét cả SC(A, B) lẫn SC(B, A)."""
    A, B = np.asarray(A, dtype=float), np.asarray(B, dtype=float)
    no_worse = np.all(A[:, None, :] <= B[None, :, :], axis=2)
    better = np.any(A[:, None, :] < B[None, :, :], axis=2)
    covered = (no_worse & better).any(axis=0)  # điểm j của B bị ai đó trong A trội
    return float(covered.mean())

def dm(F: np.ndarray, bounds: tuple[np.ndarray, np.ndarray]) -> float:
    spread = np.ptp(normalize(F, bounds), axis=0)
    return float(np.sqrt((spread ** 2).sum()))

def evaluate_front(F: np.ndarray, ref_set: np.ndarray, bounds: tuple[np.ndarray, np.ndarray],
                   ref_point: list[float]) -> dict:
    F = non_dominated(F)
    return {
        "HV": hv(F, bounds, ref_point),
        "IGD": igd(F, ref_set, bounds),
        "SP": sp(normalize(F, bounds)),
        "DM": dm(F, bounds),
        "n_points": len(F),
    }

def hv_history(history: list[np.ndarray], bounds: tuple[np.ndarray, np.ndarray],
               ref_point: list[float]) -> np.ndarray:
    return np.array([hv(non_dominated(F), bounds, ref_point) for F in history])
