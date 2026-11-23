"""Test cải tiến diversity (TV3): SDE / kNN density, cắt front, external archive.

Chạy: pytest tests/test_diversity.py -v
"""
import copy
import hashlib
import numpy as np
import pytest
from src.improvements.diversity import (
    density_score, distance_matrix, pareto_mask, truncate, update_archive)
from src.instance import load_config, load_instance
from src.nsga2 import run

# Hai cực biên A, B và một điểm cân bằng E (2 mục tiêu cho dễ tính tay, đã nằm trong [0, 1])
A, B, E = [0, 1], [1, 0], [0.4, 0.4]
F3 = np.array([A, B, E], dtype=float)

def test_knn_hand():
    # |A-E| = |B-E| = sqrt(0.16 + 0.36), |A-B| = sqrt(2)
    d = np.sqrt(0.52)
    assert np.allclose(density_score(F3, "knn", 1), [d, d, d])
    assert np.allclose(density_score(F3, "knn", 2), [np.sqrt(2), np.sqrt(2), d])

def test_sde_hand():
    # p = A: B dịch thành (1, 1) cách 1; E dịch thành (0.4, 1) cách 0.4  -> 0.4
    # p = E: A dịch thành (0.4, 1) cách 0.6; B dịch thành (1, 0.4) cách 0.6 -> 0.6
    assert np.allclose(density_score(F3, "sde", 1), [0.4, 0.4, 0.6])

def test_sde_shift_only_where_better():
    D = distance_matrix(F3, "sde")
    # Từ E nhìn A: A tốt hơn E ở mục tiêu 0 nên dịch về 0.4; ở mục tiêu 1 A tệ hơn, giữ nguyên
    assert D[2, 0] == pytest.approx(0.6)
    assert np.isinf(D.diagonal()).all()

def test_normalization_matters():
    # Mục tiêu 0 cỡ nghìn, mục tiêu 1 cỡ 0.1: sau chuẩn hoá phải ra như F3
    G = F3 * np.array([5000, 0.1]) + np.array([2000, 0])
    assert np.allclose(density_score(G, "sde", 1), density_score(F3, "sde", 1))

def test_density_small_sets():
    assert np.isinf(density_score(np.array([[1.0, 2.0]]), "sde", 1)).all()
    assert np.isinf(density_score(F3, "knn", 3)).all()      # ít hơn k + 1 điểm

def test_truncate_removes_crowded():
    # 1 và 2 gần như trùng nhau: phải bỏ một trong hai trước
    F = np.array([[0, 1], [0.5, 0.5], [0.51, 0.49], [1, 0]], dtype=float)
    for method in ("knn", "sde"):
        keep = set(truncate(F, 3, method, 1).tolist())
        assert keep in ({0, 1, 3}, {0, 2, 3})
    assert len(truncate(F, 2, "knn", 1)) == 2
    assert list(truncate(F, 10, "knn", 1)) == [0, 1, 2, 3]

def test_truncate_tie_break_second_neighbor():
    # 4 điểm cách đều trên đường thẳng: láng giềng 1 hoà hết, láng giềng 2 nhỏ nhất ở hai điểm giữa
    F = np.array([[0, 3], [1, 2], [2, 1], [3, 0]], dtype=float)
    keep = truncate(F, 3, "knn", 1).tolist()
    assert 0 in keep and 3 in keep

def test_pareto_mask_constraint():
    F = np.array([[1, 1, 1], [0, 0, 0], [2, 0, 1]], dtype=float)
    assert pareto_mask(F, np.zeros(3)).tolist() == [False, True, False]
    # cá thể 1 vi phạm nên bị mọi cá thể khả thi trội
    assert pareto_mask(F, np.array([0, 1, 0])).tolist() == [True, False, True]

def test_archive_nondominated_bounded_unique():
    rng = np.random.default_rng(0)
    pop, F, CV = [], np.empty((0, 3)), np.empty(0)
    for _ in range(20):
        new_F = rng.random((30, 3))
        new_F[:5] = new_F[5:10]                                 # cố tình có vector trùng
        new_pop = [np.array([i]) for i in range(30)]
        pop, F, CV = update_archive(pop, F, CV, new_pop, new_F, np.zeros(30), 25, "sde", 1)
        assert len(pop) == len(F) == len(CV) <= 25
        assert pareto_mask(F, CV).all()
        assert len(np.unique(F, axis=0)) == len(F)

def test_archive_keeps_extremes_when_truncating():
    # mặt phẳng f1 + f2 + f3 = 1: cực biên mỗi mục tiêu phải còn sau khi cắt bằng knn
    rng = np.random.default_rng(1)
    W = rng.dirichlet([1, 1, 1], size=200)
    W[:3] = np.eye(3)
    _, F, _ = update_archive([], np.empty((0, 3)), np.empty(0), [None] * 200, W,
                             np.zeros(200), 30, "knn", 1)
    for j in range(3):
        assert any(np.allclose(f, np.eye(3)[j]) for f in F)

# --------------------------------------------------------------------------- tích hợp nsga2

@pytest.fixture(scope="module")
def setup():
    cfg = load_config()
    cfg["nsga2"]["n_gen"] = 20
    return cfg, load_instance("C102", 25, cfg)

def sha(F):
    return hashlib.sha256(np.ascontiguousarray(F).tobytes()).hexdigest()[:16]

def test_flag_off_equals_main_baseline():
    # Mốc lấy từ main (commit f7e0ed3), config mặc định, 200 thế hệ
    cfg = load_config()
    res = run(load_instance("C102", 25, cfg), cfg, 0)
    assert sha(res["F"]) == "79ac59236c9e6fe0" and res["n_evals"] == 16080

def test_flag_off_ignores_params(setup):
    cfg, inst = setup
    other = copy.deepcopy(cfg)
    other["improvements"]["diversity_params"].update(density="knn", k=5, archive_size=3)
    a, b = run(inst, cfg, 7), run(inst, other, 7)
    assert np.array_equal(a["F"], b["F"])

@pytest.mark.parametrize("density", ["sde", "knn"])
@pytest.mark.parametrize("archive", [True, False])
def test_flag_on_runs(setup, density, archive):
    cfg, inst = setup
    cfg = copy.deepcopy(cfg)
    cfg["improvements"]["diversity"] = True
    cfg["improvements"]["diversity_params"].update(density=density, archive=archive)
    a, b = run(inst, cfg, 3), run(inst, cfg, 3)
    assert np.array_equal(a["F"], b["F"])                       # cùng seed, cùng kết quả
    front = a["F"][a["front"]]
    assert pareto_mask(front, a["CV"][a["front"]]).all()
    assert a["n_evals"] == cfg["nsga2"]["n_pop"] * (cfg["nsga2"]["n_gen"] + 1)  # không tốn thêm đánh giá
    assert len(a["history"]) == cfg["nsga2"]["n_gen"] + 1
    if archive:
        assert len(front) <= cfg["improvements"]["diversity_params"]["archive_size"]
        assert all(sorted(p) == list(range(1, inst.n + 1)) for p in a["pop"])
    else:
        assert len(a["pop"]) == cfg["nsga2"]["n_pop"]
