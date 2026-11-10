"""Test split DP (Prins) trong src/improvements/dp_split.py."""
import dataclasses
import logging
import random

import numpy as np
import pytest

from src.decoder import evaluate_routes_detail, split_greedy
from src.instance import load_instance
from src.improvements import dp_split as dps
from src.improvements.dp_split import (
    _build_arcs, child_weights, evaluate_dp, objective_scales, route_cost_terms,
    sample_weights, split_dp,
)
from src.instance import load_config

DP_PARAMS = load_config()["improvements"]["dp_split_params"]


class CountingRng:
    """Boc np.random.Generator, dem so lan goi moi phuong thuc sinh so."""

    def __init__(self, seed):
        self.rng, self.calls = np.random.default_rng(seed), []

    def __getattr__(self, name):
        fn = getattr(self.rng, name)

        def wrapped(*a, **k):
            self.calls.append(name)
            return fn(*a, **k)
        return wrapped


def same_state(rng_a, rng_b):
    return rng_a.bit_generator.state == rng_b.bit_generator.state

CORNERS = [np.array(w, float) for w in ([1, 0, 0], [0, 1, 0], [0, 0, 1])]
G3_HEAVY = np.array([0.05, 0.05, 0.9])


def rand_perm(rng, n):
    return rng.permutation(np.arange(1, n + 1)).tolist()


def scalar(routes, inst, w, sc):
    """Chi phi vo huong tinh tu dau bang route_cost_terms (khong dung cong don cua DP)."""
    return sum(float(np.dot(w, np.array(route_cost_terms(r, inst)) / sc)) for r in routes)


def brute_force(perm, inst, w, sc, fleet=None):
    """Thu moi 2^(n-1) cach cat, bo cach khong kha thi (tai, so xe), tra ve chi phi nho nhat."""
    n, best = len(perm), float("inf")
    for mask in range(1 << (n - 1)):
        routes, cur = [], [perm[0]]
        for k in range(1, n):
            if mask >> (k - 1) & 1:
                routes.append(cur)
                cur = []
            cur.append(perm[k])
        routes.append(cur)
        if any(inst.demand[r].sum() > inst.capacity for r in routes):
            continue
        if fleet is not None and len(routes) > fleet:
            continue
        best = min(best, scalar(routes, inst, w, sc))
    return best


# ---------------------------------------------------------------- route_cost_terms
@pytest.mark.parametrize("name,n", [("C102", 25), ("case29", 29)])
def test_route_terms_match_evaluate(name, n):
    inst, rng = load_instance(name, n), np.random.default_rng(0)
    for _ in range(10):
        routes = split_greedy(rand_perm(rng, n), inst)
        d = evaluate_routes_detail(routes, inst)
        t = np.sum([route_cost_terms(r, inst) for r in routes], axis=0)
        assert np.allclose(t, [d["f1"], d["f2"], 1 - d["f3"]], rtol=1e-9, atol=1e-9)


@pytest.mark.parametrize("name,n", [("C102", 25), ("R201", 50), ("case29", 29)])
def test_arc_cost_incremental_equals_scratch(name, n):
    inst, rng = load_instance(name, n), np.random.default_rng(1)
    sc = objective_scales(inst)
    for w in CORNERS + [rng.dirichlet([1, 1, 1])]:
        perm = rand_perm(rng, n)
        for i, row in enumerate(_build_arcs(perm, inst, w, sc)):
            for j, cost in row:
                ref = float(np.dot(w, np.array(route_cost_terms(perm[i:j], inst)) / sc))
                assert cost == pytest.approx(ref, rel=1e-9, abs=1e-9)


# ---------------------------------------------------------------- toi uu
@pytest.mark.parametrize("name", ["C102", "R201", "RC202", "case29"])
@pytest.mark.parametrize("n", [6, 8])
def test_dp_equals_brute_force(name, n):
    inst, rng = load_instance(name, n), np.random.default_rng(2)
    sc = objective_scales(inst)
    for w in CORNERS + [rng.dirichlet([1, 1, 1]) for _ in range(3)]:
        perm = rand_perm(rng, n)
        got = scalar(split_dp(perm, inst, w, sc), inst, w, sc)
        assert got == pytest.approx(brute_force(perm, inst, w, sc), rel=1e-9, abs=1e-9)


@pytest.mark.parametrize("name,n", [("C102", 25), ("R201", 50)])
def test_never_worse_than_greedy(name, n):
    inst, rng = load_instance(name, n), np.random.default_rng(3)
    sc = objective_scales(inst)
    for _ in range(50):
        perm, w = rand_perm(rng, n), rng.dirichlet([1, 1, 1])
        dp = scalar(split_dp(perm, inst, w, sc), inst, w, sc)
        gr = scalar(split_greedy(perm, inst), inst, w, sc)
        assert dp <= gr + 1e-9


# ---------------------------------------------------------------- fleet
@pytest.mark.parametrize("name", ["C102", "RC201"])
def test_fleet_respected_n100_g3_heavy(name):
    inst, rng = load_instance(name, 100), np.random.default_rng(4)
    assert inst.fleet_size == 25
    sc = objective_scales(inst)
    for _ in range(5):
        perm = rand_perm(rng, 100)
        routes = split_dp(perm, inst, G3_HEAVY, sc)
        assert len(routes) <= inst.fleet_size
        assert evaluate_dp(perm, inst, G3_HEAVY)["fleet_ok"]


@pytest.mark.parametrize("name", ["C102", "case29"])
@pytest.mark.parametrize("fleet", [2, 3])
def test_layered_dp_equals_brute_force_small_fleet(name, fleet):
    n, rng = 8, np.random.default_rng(5)
    inst = dataclasses.replace(load_instance(name, n), fleet_size=fleet)
    sc = objective_scales(inst)
    for w in CORNERS + [rng.dirichlet([1, 1, 1]) for _ in range(3)]:
        perm = rand_perm(rng, n)
        best = brute_force(perm, inst, w, sc, fleet)
        if best == float("inf"):
            continue  # khong kha thi: da co test fallback rieng
        routes = split_dp(perm, inst, w, sc)
        assert len(routes) <= fleet
        assert scalar(routes, inst, w, sc) == pytest.approx(best, rel=1e-9, abs=1e-9)


def test_fleet_binds_vs_unlimited():
    """Fleet nho phai thuc su gan cut: DP co fleet khong tot hon DP khong gioi han."""
    inst, rng = load_instance("C102", 25), np.random.default_rng(6)
    sc, w = objective_scales(inst), G3_HEAVY
    perm = rand_perm(rng, 25)
    free = split_dp(perm, inst, w, sc)
    tight = dataclasses.replace(inst, fleet_size=max(2, len(free) - 1))
    routes = split_dp(perm, tight, w, sc)
    assert len(routes) <= tight.fleet_size
    assert scalar(routes, inst, w, sc) >= scalar(free, inst, w, sc) - 1e-9


def test_infeasible_fleet_falls_back_to_greedy(monkeypatch, caplog):
    monkeypatch.setattr(dps, "_warned_infeasible", False)
    inst = dataclasses.replace(load_instance("C102", 25), fleet_size=1)  # tong demand > 400
    sc, perm = objective_scales(inst), list(range(1, 26))
    with caplog.at_level(logging.WARNING, logger=dps.__name__):
        r1 = split_dp(perm, inst, G3_HEAVY, sc)
        r2 = split_dp(perm, inst, G3_HEAVY, sc)
    assert r1 == r2 == split_greedy(perm, inst)
    assert len([m for m in caplog.records if m.levelno == logging.WARNING]) == 1  # chi canh bao 1 lan


# ---------------------------------------------------------------- hop le, tat dinh
@pytest.mark.parametrize("name,n", [("C102", 25), ("R201", 50), ("case29", 29)])
def test_valid_and_deterministic(name, n):
    inst, rng = load_instance(name, n), np.random.default_rng(7)
    sc = objective_scales(inst)
    for _ in range(10):
        perm, w = rand_perm(rng, n), rng.dirichlet([1, 1, 1])
        routes = split_dp(perm, inst, w, sc)
        assert [c for r in routes for c in r] == perm        # giu nguyen thu tu, moi khach 1 lan
        assert all(inst.demand[r].sum() <= inst.capacity for r in routes)
        assert split_dp(perm, inst, w, sc) == routes
        d1, d2 = evaluate_dp(perm, inst, w), evaluate_dp(perm, inst, w)
        assert d1["routes"] == d2["routes"] and d1["f1"] == d2["f1"]
        assert d1["split"] == "dp" and np.array_equal(d1["weights"], w)


def test_objective_scales_no_rng(monkeypatch):
    inst = load_instance("C102", 25)
    monkeypatch.setattr(dps, "_scales_cache", {})  # bat buoc tinh lai

    def boom(*a, **k):
        raise AssertionError("objective_scales khong duoc dung RNG")

    monkeypatch.setattr(np.random, "default_rng", boom)
    monkeypatch.setattr(random, "random", boom)
    np.random.seed(123)
    state = np.random.get_state()
    s1 = objective_scales(inst)
    after = np.random.get_state()
    assert state[0] == after[0] and np.array_equal(state[1], after[1]) and state[2:] == after[2:]
    monkeypatch.setattr(dps, "_scales_cache", {})
    assert np.array_equal(s1, objective_scales(inst))  # tat dinh
    assert s1[2] == 1.0 and np.all(s1 >= dps.EPS)


# ---------------------------------------------------------------- trong so: boc va thua huong
def P_(**kw):
    return {**DP_PARAMS, **kw}


def test_sample_weights_dirichlet_on_simplex_and_deterministic():
    p = P_(weight_dist="dirichlet")
    rng = np.random.default_rng(0)
    for _ in range(200):
        w = sample_weights(rng, p)
        assert w.shape == (3,) and np.all(w >= 0) and w.sum() == pytest.approx(1.0)
    a = sample_weights(np.random.default_rng(42), p)
    b = sample_weights(np.random.default_rng(42), p)
    assert np.array_equal(a, b)


def test_sample_weights_onehot():
    p = P_(weight_dist="onehot")
    rng, seen = np.random.default_rng(0), set()
    for _ in range(100):
        w = sample_weights(rng, p)
        assert w.shape == (3,) and sorted(w.tolist()) == [0.0, 0.0, 1.0]
        seen.add(int(np.argmax(w)))
    assert seen == {0, 1, 2}
    assert np.array_equal(sample_weights(np.random.default_rng(7), p),
                          sample_weights(np.random.default_rng(7), p))


@pytest.mark.parametrize("dist,call", [("dirichlet", "dirichlet"), ("onehot", "integers")])
def test_sample_weights_exact_draws(dist, call):
    c = CountingRng(3)
    sample_weights(c, P_(weight_dist=dist))
    assert c.calls == [call]                        # dung 1 lan goi
    ref = np.random.default_rng(3)
    ref.dirichlet([1, 1, 1]) if dist == "dirichlet" else ref.integers(3)
    assert same_state(c.rng, ref)


@pytest.mark.parametrize("dist", ["dirichlet", "onehot"])
def test_child_weights_fresh(dist):
    p = P_(weight_dist=dist, weight_inherit="fresh")
    wa, wb = np.array([1.0, 0, 0]), np.array([0, 0, 1.0])
    c1, c2 = CountingRng(5), np.random.default_rng(5)
    w = child_weights(c1, wa, wb, p)
    assert np.array_equal(w, sample_weights(c2, p))       # cung dong so voi sample_weights
    assert len(c1.calls) == 1 and same_state(c1.rng, c2)
    assert w.sum() == pytest.approx(1.0)


def test_child_weights_parent():
    p = P_(weight_inherit="parent")
    wa, wb = np.array([0.2, 0.3, 0.5]), np.array([0.7, 0.2, 0.1])
    c = CountingRng(11)
    w = child_weights(c, wa, wb, p)
    assert c.calls == ["integers"]                        # dung 1 lan rng.integers(2)
    ref = np.random.default_rng(11)
    pick = int(ref.integers(2))
    assert same_state(c.rng, ref)
    assert np.array_equal(w, (wa, wb)[pick])
    w[0] = 99.0                                           # la ban sao, khong chung bo nho
    assert wa[0] == 0.2 and wb[0] == 0.7
    rng, picks = np.random.default_rng(0), set()
    for _ in range(50):
        picks.add(int(child_weights(rng, wa, wb, p)[0] == wb[0]))
    assert picks == {0, 1}                                # ca hai cha me deu duoc chon
    assert np.array_equal(child_weights(np.random.default_rng(1), wa, wb, p),
                          child_weights(np.random.default_rng(1), wa, wb, p))


def test_weight_modes_reject_unknown():
    with pytest.raises(ValueError):
        sample_weights(np.random.default_rng(0), P_(weight_dist="x"))
    with pytest.raises(ValueError):
        child_weights(np.random.default_rng(0), np.ones(3) / 3, np.ones(3) / 3,
                      P_(weight_inherit="x"))
