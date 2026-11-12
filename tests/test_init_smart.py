"""Test TV2: src/improvements/init_smart.py."""
import copy
import dataclasses
import math

import numpy as np
import pytest

from src.instance import load_config, load_instance
from src.improvements import init_smart as ism
from src.improvements.init_smart import (
    FALLBACK_LABEL, allocate_quota, make_initial_population, make_initial_population_detailed,
    nearest_neighbor_order, parse_init_params, perturb_swaps, time_window_order,
)

CFG = load_config()
PARAMS = CFG["improvements"]["init_smart_params"]


def is_perm(p, n):
    return len(p) == n and sorted(p) == list(range(1, n + 1)) and 0 not in p


def toy(n, coords=None, eta=None, base=("C102", 25)):
    """Instance tự dựng: n khách, toạ độ/ETa cho trước, tham số mô hình lấy từ config."""
    ref = load_instance(*base)
    coords = np.asarray(coords if coords is not None else
                        np.c_[np.arange(n + 1), np.zeros(n + 1)], float)
    eta = np.asarray(eta if eta is not None else np.zeros(n + 1), float)
    tw_e = np.c_[eta, eta + 1000.0]
    tw_s = np.c_[np.maximum(0.0, eta - 30), eta + 1030.0]
    diff = coords[:, None, :] - coords[None, :, :]
    return dataclasses.replace(
        ref, name=f"toy-{n}", n=n, coords=coords, demand=np.r_[0.0, np.ones(n)],
        service_time=np.zeros(n + 1), tw_expected=tw_e, tw_specified=tw_s,
        dist=np.hypot(diff[..., 0], diff[..., 1]))


# ------------------------------------------------------------------ quota
def test_config_defaults_off_and_ratios():
    assert CFG["improvements"]["init_smart"] is False
    assert parse_init_params(PARAMS).ratios == {"nn": 0.2, "tw": 0.2, "random": 0.6}


def test_quota_80_is_16_16_48():
    assert allocate_quota(80, {"nn": 0.2, "tw": 0.2, "random": 0.6}) == {"nn": 16, "tw": 16, "random": 48}


@pytest.mark.parametrize("n_pop", [1, 2, 3, 5, 7, 11, 25, 79, 81, 101])
@pytest.mark.parametrize("ratios", [{"nn": 0.2, "tw": 0.2, "random": 0.6},
                                    {"nn": 1 / 3, "tw": 1 / 3, "random": 1 / 3},
                                    {"nn": 0.0, "tw": 0.5, "random": 0.5},
                                    {"nn": 0.15, "tw": 0.25, "random": 0.6}])
def test_quota_largest_remainder(n_pop, ratios):
    q = allocate_quota(n_pop, ratios)
    assert sum(q.values()) == n_pop
    for k, r in ratios.items():
        assert math.floor(n_pop * r + 1e-9) <= q[k] <= math.floor(n_pop * r + 1e-9) + 1
    if ratios["nn"] == 0.0:
        assert q["nn"] == 0


def test_quota_tie_break_order():
    # 1/3 mỗi nhóm, n_pop=4: floor 1/1/1, dư bằng nhau -> slot thừa vào nn
    assert allocate_quota(4, {"nn": 1 / 3, "tw": 1 / 3, "random": 1 / 3}) == {"nn": 2, "tw": 1, "random": 1}
    assert allocate_quota(5, {"nn": 1 / 3, "tw": 1 / 3, "random": 1 / 3}) == {"nn": 2, "tw": 2, "random": 1}
    # dư 0.5 / 0.5 / 0: nn và tw
    assert allocate_quota(3, {"nn": 0.5, "tw": 0.5, "random": 0.0}) == {"nn": 2, "tw": 1, "random": 0}


@pytest.mark.parametrize("bad", [
    {"ratios": {"nn": 0.5, "tw": 0.5, "random": 0.5}},
    {"ratios": {"nn": -0.2, "tw": 0.6, "random": 0.6}},
    {"ratios": {"nn": float("nan"), "tw": 0.5, "random": 0.5}},
    {"ratios": {"nn": float("inf"), "tw": 0.5, "random": 0.5}},
    {"ratios": {"nn": 0.5, "random": 0.5}},
    {"ratios": {"nn": 0.2, "tw": 0.2, "random": 0.5, "x": 0.1}},
    {"ratios": {"nn": "0.2", "tw": 0.2, "random": 0.6}},
    {**PARAMS, "perturb_swaps_min": 0},
    {**PARAMS, "perturb_swaps_min": 4, "perturb_swaps_max": 3},
    {**PARAMS, "perturb_swaps_max": 2.5},
    {**PARAMS, "dedup_max_attempts": 0},
    {**PARAMS, "keep_pure_seed": "yes"},
    {**PARAMS, "unknown_key": 1},
    {"perturb_swaps_min": 1},
])
def test_bad_params_raise(bad):
    with pytest.raises(ValueError):
        parse_init_params(bad)


@pytest.mark.parametrize("n_pop", [0, -3, 2.5, True])
def test_bad_n_pop_raises(n_pop):
    with pytest.raises(ValueError):
        allocate_quota(n_pop, {"nn": 0.2, "tw": 0.2, "random": 0.6})


# ------------------------------------------------------------------ NN / TW tất định
def test_nn_tie_break_by_id():
    # kho tại 0; khách 1 và 2 cách kho bằng nhau (tại -1 và +1) -> chọn ID nhỏ (1)
    # từ 1 (x=-1): 2 cách 2, 3 (x=-3) cách 2 -> hoà -> chọn 2; từ 2 (x=1): còn 3 -> 3
    inst = toy(3, coords=[[0, 0], [-1, 0], [1, 0], [-3, 0]])
    assert nearest_neighbor_order(inst) == [1, 2, 3]


def test_nn_is_true_nearest_neighbor_ignoring_tw():
    # khách 3 gần kho nhất dù ETa muộn nhất -> NN vẫn chọn trước
    inst = toy(3, coords=[[0, 0], [5, 0], [6, 0], [1, 0]], eta=[0, 0, 10, 999])
    assert nearest_neighbor_order(inst) == [3, 1, 2]


def test_tw_sorted_by_eta_not_et():
    # ETa: c1=50, c2=10, c3=30. ET = ETa-30 nhưng clamp 0 -> nếu nhầm ET sẽ ra thứ tự khác
    inst = toy(3, coords=[[0, 0], [1, 0], [2, 0], [3, 0]], eta=[0, 50, 10, 30])
    inst.tw_specified[:, 0] = [0, 0, 0, 0]          # ET bằng nhau hết: dùng ET sẽ ra [1,2,3]
    assert time_window_order(inst) == [2, 3, 1]


def test_tw_tie_break_distance_from_previous_then_id():
    # ETa: c1=c2=c3=10, c4=0. Bắt đầu c4 (9,1). Từ c4: c3 (9,0) cách 1 gần nhất (c1, c2 cách
    # sqrt2), rồi từ c3: c1 (8,0) và c2 (10,0) cùng cách 1 -> ID nhỏ hơn (1), rồi 2.
    inst = toy(4, coords=[[0, 0], [8, 0], [10, 0], [9, 0], [9, 1]], eta=[0, 10, 10, 10, 0])
    assert time_window_order(inst) == [4, 3, 1, 2]
    # khách đầu tiên: hoà ETa thì gần KHO hơn
    inst2 = toy(2, coords=[[0, 0], [5, 0], [2, 0]], eta=[0, 7, 7])
    assert time_window_order(inst2) == [2, 1]


@pytest.mark.parametrize("name,n", [("C102", 25), ("R201", 50), ("RC201", 100), ("case29", 29)])
def test_base_orders_are_permutations(name, n):
    inst = load_instance(name, n)
    nn, tw = nearest_neighbor_order(inst), time_window_order(inst)
    assert is_perm(nn, n) and is_perm(tw, n)
    eta = inst.tw_expected[:, 0]
    assert all(eta[a] <= eta[b] for a, b in zip(tw, tw[1:]))     # ETa không giảm


# ------------------------------------------------------------------ perturb
def test_perturb_keeps_multiset_and_input():
    rng = np.random.default_rng(0)
    base = list(range(1, 31))
    orig = list(base)
    for _ in range(200):
        out = perturb_swaps(base, rng, 1, 3)
        assert sorted(out) == orig and out is not base
    assert base == orig


def test_perturb_draw_count():
    class Counting:
        def __init__(self, seed):
            self.rng, self.calls = np.random.default_rng(seed), []

        def __getattr__(self, name):
            fn = getattr(self.rng, name)

            def w(*a, **k):
                self.calls.append(name)
                return fn(*a, **k)
            return w

    c = Counting(1)
    perturb_swaps(list(range(1, 11)), c, 2, 2)
    assert c.calls == ["integers", "choice", "choice"]
    c2 = Counting(1)
    assert perturb_swaps([7], c2, 1, 3) == [7] and c2.calls == []   # n<2: không dùng RNG


# ------------------------------------------------------------------ quần thể
@pytest.mark.parametrize("name,n", [("C102", 25), ("R201", 50), ("RC201", 100), ("case29", 29)])
def test_population_valid_quota_unique(name, n):
    inst = load_instance(name, n)
    r = make_initial_population_detailed(inst, 80, np.random.default_rng(0), PARAMS)
    assert len(r.population) == 80 == len(r.sources)
    assert all(is_perm(p, n) for p in r.population)
    assert r.quota == {"nn": 16, "tw": 16, "random": 48}
    assert r.effective_counts == {"nn": 16, "tw": 16, "random": 48, FALLBACK_LABEL: 0}
    assert [s for s in r.sources] == ["nn"] * 16 + ["tw"] * 16 + ["random"] * 48
    assert len({tuple(p) for p in r.population}) == 80          # không trùng
    assert r.population[0] == nearest_neighbor_order(inst)      # bản thuần
    assert r.population[16] == time_window_order(inst)
    assert len({tuple(p) for p in r.population[:16]}) == 16     # 16 bản NN khác nhau


@pytest.mark.parametrize("n_pop", [1, 3, 7, 33, 81])
def test_odd_pop_sizes(n_pop):
    inst = load_instance("C102", 25)
    pop, src = make_initial_population(inst, n_pop, np.random.default_rng(3), PARAMS)
    q = allocate_quota(n_pop, PARAMS["ratios"])
    assert len(pop) == n_pop and all(is_perm(p, 25) for p in pop)
    assert {k: src.count(k) for k in ("nn", "tw", "random")} == q


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_tiny_n_does_not_hang_and_is_graceful(n):
    inst = toy(n)
    r = make_initial_population_detailed(inst, 80, np.random.default_rng(0), PARAMS)
    assert len(r.population) == 80 and all(is_perm(p, n) for p in r.population)
    uniq = len({tuple(p) for p in r.population})
    assert r.n_duplicates == 80 - uniq
    if math.factorial(n) < 80:
        assert uniq <= math.factorial(n) and r.notes
        if n <= 3:
            assert uniq == math.factorial(n)        # n! nhỏ: khử trùng phủ hết
    else:
        assert uniq == 80 and r.n_duplicates == 0


def test_fallback_when_dedup_exhausted():
    # n=6 (720 hoán vị), toàn bộ là nn: NN + đúng 1 swap chỉ cho 1 + 15 hoán vị khác nhau,
    # nên với 60 slot phải rơi về random dự phòng, có nhãn rõ ràng
    inst = toy(6)
    p = {"ratios": {"nn": 1.0, "tw": 0.0, "random": 0.0}, "perturb_swaps_min": 1,
         "perturb_swaps_max": 1, "dedup_max_attempts": 3, "keep_pure_seed": True}
    r = make_initial_population_detailed(inst, 60, np.random.default_rng(0), p)
    assert r.effective_counts["nn"] <= 16 and r.effective_counts[FALLBACK_LABEL] >= 44
    assert r.effective_counts["nn"] + r.effective_counts[FALLBACK_LABEL] == 60
    assert r.sources.count(FALLBACK_LABEL) == r.effective_counts[FALLBACK_LABEL]
    assert len({tuple(x) for x in r.population}) == 60
    assert any("dự phòng" in s for s in r.notes)


def test_reproducible_and_seed_sensitive():
    inst = load_instance("R201", 50)
    a = make_initial_population(inst, 80, np.random.default_rng(7), PARAMS)
    b = make_initial_population(inst, 80, np.random.default_rng(7), PARAMS)
    c = make_initial_population(inst, 80, np.random.default_rng(8), PARAMS)
    assert a == b
    assert a[0] != c[0]
    r1, r2 = np.random.default_rng(7), np.random.default_rng(7)
    make_initial_population(inst, 80, r1, PARAMS)
    make_initial_population(inst, 80, r2, PARAMS)
    assert r1.bit_generator.state == r2.bit_generator.state


def test_no_mutation_of_inputs_and_uses_caller_rng():
    inst = load_instance("C102", 25)
    snap = copy.deepcopy(inst)
    params = copy.deepcopy(PARAMS)
    cfg_before = copy.deepcopy(CFG)
    rng = np.random.default_rng(11)
    state0 = copy.deepcopy(rng.bit_generator.state)
    make_initial_population(inst, 80, rng, params)
    for f in dataclasses.fields(inst):
        a, b = getattr(inst, f.name), getattr(snap, f.name)
        assert (np.array_equal(a, b) if isinstance(a, np.ndarray) else a == b), f.name
    assert params == PARAMS and CFG == cfg_before
    assert rng.bit_generator.state != state0              # dùng đúng rng của caller
    assert not hasattr(ism, "random")                     # không import thư viện random


def test_no_global_numpy_rng(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("init_smart không được tự tạo RNG")
    monkeypatch.setattr(np.random, "default_rng", boom)
    np.random.seed(1)
    st = np.random.get_state()
    make_initial_population(load_instance("C102", 25), 20, np.random.Generator(np.random.PCG64(0)),
                            PARAMS)
    after = np.random.get_state()
    assert np.array_equal(st[1], after[1]) and st[2:] == after[2:]


def test_random_group_equals_baseline_stream():
    """ratios = 100% random với cùng factory baseline -> đúng dãy hoán vị và trạng thái RNG
    như vòng sinh baseline (khi không có trùng, điển hình n >= 5)."""
    inst = load_instance("C102", 25)
    ids = np.arange(1, 26)
    factory = lambda r: r.permutation(ids).tolist()  # noqa: E731
    p = {**PARAMS, "ratios": {"nn": 0.0, "tw": 0.0, "random": 1.0}}
    r_smart, r_base = np.random.default_rng(5), np.random.default_rng(5)
    pop, src = make_initial_population(inst, 80, r_smart, p, baseline_factory=factory)
    base = [factory(r_base) for _ in range(80)]
    assert pop == base and set(src) == {"random"}
    assert r_smart.bit_generator.state == r_base.bit_generator.state


def test_baseline_factory_is_used():
    inst = load_instance("C102", 25)
    calls = []

    def factory(r):
        calls.append(1)
        return r.permutation(np.arange(1, 26)).tolist()
    make_initial_population(inst, 10, np.random.default_rng(0), PARAMS, baseline_factory=factory)
    assert len(calls) == allocate_quota(10, PARAMS["ratios"])["random"]
