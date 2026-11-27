"""Test các chỉ số đánh giá trên những tập điểm nhỏ tính tay được.

Chạy: pytest tests/test_metrics.py -v
"""
import numpy as np
import pytest

from src.metrics import (
    dm, evaluate_front, hv, igd, non_dominated, normalization_bounds, normalize,
    reference_set, sc, sp,
)

# Cận chuẩn hoá [0, 1] ở mọi mục tiêu, nên chuẩn hoá không làm đổi điểm
UNIT = (np.zeros(3), np.ones(3))
REF = np.array([[0, 1, 1], [1, 0, 1], [1, 1, 0]], dtype=float)
REF_POINT = [1.1, 1.1, 1.1]


def test_non_dominated_drops_dominated_and_duplicates():
    F = np.array([[1, 1, 1], [1, 1, 1], [2, 2, 2], [0, 3, 3]], dtype=float)
    out = non_dominated(F)
    assert sorted(map(tuple, out)) == [(0, 3, 3), (1, 1, 1)]


def test_reference_set_merges_fronts():
    a = np.array([[1, 2, 0], [3, 3, 3]], dtype=float)
    b = np.array([[2, 1, 0]], dtype=float)
    assert sorted(map(tuple, reference_set([a, b]))) == [(1, 2, 0), (2, 1, 0)]


def test_normalization_bounds_use_all_points_not_only_reference_set():
    a = np.array([[1, 2, 0], [3, 3, 3]], dtype=float)     # (3, 3, 3) bị trội nhưng vẫn tính vào cận
    b = np.array([[2, 1, 0]], dtype=float)
    lo, hi = normalization_bounds([a, b])
    assert lo.tolist() == [1, 1, 0] and hi.tolist() == [3, 3, 3]


def test_normalize():
    bounds = (np.array([10.0, 0, 0]), np.array([20.0, 4, 0]))
    out = normalize(np.array([[15, 2, 0]]), bounds)
    assert out.tolist() == [[0.5, 0.5, 0.0]]       # mục tiêu 3 không đổi thì chia cho 1


def test_hv_single_point_is_a_box():
    # Một điểm (0, 0, 0): hộp tới điểm tham chiếu 1.1 mỗi cạnh
    assert hv(np.array([[0, 0, 0]]), UNIT, REF_POINT) == pytest.approx(1.1 ** 3)
    assert hv(np.array([[0.5, 0.5, 0.5]]), UNIT, REF_POINT) == pytest.approx(0.6 ** 3)


def test_hv_ignores_points_beyond_reference_point():
    assert hv(np.array([[2, 2, 2]]), UNIT, REF_POINT) == 0.0


def test_igd_zero_when_front_equals_reference():
    assert igd(REF, REF, UNIT) == pytest.approx(0.0)


def test_igd_hand_calculation():
    # Mọi điểm của REF cách (1, 1, 1) đúng 1, nên IGD = 1
    assert igd(np.array([[1, 1, 1]]), REF, UNIT) == pytest.approx(1.0)


def test_sp_evenly_spaced_is_zero():
    F = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]], dtype=float)
    assert sp(F) == pytest.approx(0.0)


def test_sp_hand_calculation():
    # Khoảng cách tới điểm gần nhất: 1, 1, 2. Trung bình 4/3.
    # Tổng bình phương lệch: (1/3)^2 + (1/3)^2 + (2/3)^2 = 6/9, chia (3 - 1), lấy căn
    F = np.array([[0, 0, 0], [1, 0, 0], [3, 0, 0]], dtype=float)
    assert sp(F) == pytest.approx(np.sqrt(1 / 3))


def test_sp_needs_two_points():
    assert np.isnan(sp(np.array([[0, 0, 0]])))


def test_sc_hand_calculation():
    A = np.array([[1, 1, 1]], dtype=float)
    B = np.array([[2, 2, 2],      # bị A trội
                  [0, 3, 3],      # không bị trội
                  [1, 1, 1]],     # bằng nhau thì không tính là trội
                 dtype=float)
    assert sc(A, B) == pytest.approx(1 / 3)
    assert sc(B, A) == pytest.approx(0.0)


def test_dm_full_spread_is_sqrt3():
    assert dm(REF, UNIT) == pytest.approx(np.sqrt(3))
    assert dm(np.array([[0.5, 0.5, 0.5]]), UNIT) == pytest.approx(0.0)   # một điểm thì không trải


def test_dm_never_exceeds_sqrt3_with_bounds_from_all_points():
    rng = np.random.default_rng(0)
    fronts = [rng.random((10, 3)) * 100 for _ in range(5)]
    bounds = normalization_bounds(fronts)
    assert all(dm(F, bounds) <= np.sqrt(3) + 1e-12 for F in fronts)


def test_evaluate_front_keys():
    out = evaluate_front(REF, REF, UNIT, REF_POINT)
    assert set(out) == {"HV", "IGD", "SP", "DM", "n_points"}
    assert out["n_points"] == 3 and out["IGD"] == pytest.approx(0.0)
