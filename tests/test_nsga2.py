"""Test các thành phần của NSGA-II trên dữ liệu nhỏ tự dựng.

Chạy: pytest tests/test_nsga2.py -v
"""
import copy
import numpy as np
import pytest
from src.instance import load_config, load_instance
from src.nsga2 import (
    crowding_distance, domination_matrix, environmental_selection, inversion, mutate,
    non_dominated_sort, obx, obx_with_mask, ox, run, select_survivors, split_duplicates, swap,)

def is_permutation(x, n) -> bool:
    return sorted(np.asarray(x).tolist()) == list(range(1, n + 1))

# =========================================================================== trội và sắp xếp

def test_domination_pareto():
    F = np.array([[1, 1, 1],     # 0 trội 1 và 2
                  [2, 2, 2],
                  [1, 2, 1],     # 2 trội 1, không trội 0
                  [0, 5, 5]])    # 3 không so được với 0
    D = domination_matrix(F, np.zeros(4))
    assert D[0, 1] and D[0, 2] and D[2, 1]
    assert not D[2, 0] and not D[0, 3] and not D[3, 0]
    assert not D.diagonal().any()                    # không ai tự trội mình


def test_domination_constraint_first():
    # Cá thể 1 tốt hơn hẳn về mục tiêu nhưng vi phạm nhiều xe hơn, nên vẫn bị 0 trội
    F = np.array([[9, 9, 9], [1, 1, 1]])
    D = domination_matrix(F, np.array([0, 2]))
    assert D[0, 1] and not D[1, 0]


def test_non_dominated_sort_ranks():
    F = np.array([[1, 5, 0], [5, 1, 0],             # front 0
                  [2, 6, 0], [6, 2, 0],             # front 1
                  [7, 7, 0]])                       # front 2
    assert non_dominated_sort(F, np.zeros(5)).tolist() == [0, 0, 1, 1, 2]


def test_crowding_distance_hand_calculation():
    # 4 điểm trên một đường, mục tiêu 2 ngược chiều mục tiêu 1, mục tiêu 3 bằng nhau
    F = np.array([[0, 3, 0], [1, 2, 0], [2, 1, 0], [3, 0, 0]], dtype=float)
    d = crowding_distance(F)
    assert np.isinf(d[0]) and np.isinf(d[3])
    # điểm giữa: (2 - 0) / 3 cho mục tiêu 1, (3 - 1) / 3 cho mục tiêu 2
    assert d[1] == pytest.approx(4 / 3)
    assert d[2] == pytest.approx(4 / 3)


def test_environmental_selection_keeps_best_front():
    F = np.array([[1, 5, 0], [5, 1, 0], [2, 6, 0], [6, 2, 0], [7, 7, 0]], dtype=float)
    keep = environmental_selection(F, np.zeros(5), 3)
    assert {0, 1} <= set(keep.tolist()) and len(keep) == 3

# =========================================================================== loại cá thể trùng

def test_split_duplicates():
    pop = [np.array([1, 2, 3]), np.array([2, 1, 3]), np.array([1, 2, 3]), np.array([1, 2, 3])]
    first, dup = split_duplicates(pop)
    assert first.tolist() == [0, 1] and dup.tolist() == [2, 3]

def test_select_survivors_prefers_distinct_permutations():
    # Cá thể 2 là bản sao của cá thể 0 (cùng hoán vị, cùng mục tiêu, cùng tốt nhất)
    pop = [np.array([1, 2, 3]), np.array([2, 1, 3]), np.array([1, 2, 3]), np.array([3, 2, 1])]
    F = np.array([[1, 1, 0], [2, 2, 0], [1, 1, 0], [3, 3, 0]], dtype=float)
    CV = np.zeros(4)
    assert sorted(select_survivors(pop, F, CV, 2, True).tolist()) == [0, 1]
    assert sorted(select_survivors(pop, F, CV, 2, False).tolist()) == [0, 2]   # không loại thì giữ cả bản sao

def test_select_survivors_fills_with_duplicates_when_needed():
    pop = [np.array([1, 2, 3])] * 3
    F = np.ones((3, 3))
    assert select_survivors(pop, F, np.zeros(3), 2, True).tolist() == [0, 1]

# =========================================================================== toán tử

def test_obx_example_from_paper():
    # Hình 3 bài báo: chọn gen 7, 5, 4 của p1
    p1 = np.array([2, 7, 1, 5, 9, 3, 6, 4, 8])
    p2 = np.array([3, 5, 2, 6, 4, 1, 8, 9, 7])
    mask = np.isin(p1, [7, 5, 4])
    assert obx_with_mask(p1, p2, mask).tolist() == [3, 7, 2, 6, 5, 1, 8, 9, 4]


@pytest.mark.parametrize("cross", [ox, obx])
def test_crossover_gives_permutation(cross):
    rng = np.random.default_rng(0)
    for _ in range(200):
        p1, p2 = rng.permutation(np.arange(1, 21)), rng.permutation(np.arange(1, 21))
        assert is_permutation(cross(p1, p2, rng), 20)


def test_ox_keeps_a_segment_of_parent1():
    rng = np.random.default_rng(1)
    p1, p2 = np.arange(1, 11), np.arange(10, 0, -1)
    child = ox(p1, p2, rng)
    same = child == p1
    first, last = np.flatnonzero(same)[[0, -1]]
    assert same[first:last + 1].all()               # các vị trí giống p1 là một đoạn liền


@pytest.mark.parametrize("op", [inversion, swap])
def test_mutation_operators_give_permutation(op):
    rng = np.random.default_rng(2)
    perm = np.arange(1, 16)
    for _ in range(200):
        op(perm, rng)
        assert is_permutation(perm, 15)


def test_mutate_standard_respects_pm_zero():
    rng = np.random.default_rng(3)
    perm = np.arange(1, 11)
    for _ in range(100):
        mutate(perm, 0.0, "standard", rng)
    assert perm.tolist() == list(range(1, 11))      # pm = 0 thì không bao giờ đột biến


# =========================================================================== chạy cả thuật toán

def small_config(**nsga2_overrides) -> dict:
    cfg = copy.deepcopy(load_config())
    cfg["nsga2"].update(n_pop=20, n_gen=15, **nsga2_overrides)
    return cfg


def test_run_same_seed_same_result():
    inst = load_instance("C102", 25)
    a = run(inst, small_config(), seed=7)
    b = run(inst, small_config(), seed=7)
    assert a["pop"] == b["pop"]
    assert np.array_equal(a["F"], b["F"])


def test_run_output_is_valid_and_improves():
    inst = load_instance("C102", 25)
    res = run(inst, small_config(), seed=0)
    assert len(res["pop"]) == 20
    assert all(is_permutation(x, 25) for x in res["pop"])
    assert len({tuple(x) for x in res["pop"]}) == 20          # bật loại trùng: không có bản sao
    assert res["n_evals"] == 20 * (15 + 1)
    assert len(res["history"]) == 15 + 1
    # chi phí nhỏ nhất trên front cuối không tệ hơn thế hệ đầu (elitism)
    assert res["history"][-1][:, 0].min() <= res["history"][0][:, 0].min()

@pytest.mark.parametrize("key, bad", [("crossover", "pmx"), ("mutation", "sometimes")])
def test_run_rejects_unknown_operator(key, bad):
    with pytest.raises(ValueError):
        run(load_instance("C102", 25), small_config(**{key: bad}), seed=0)
