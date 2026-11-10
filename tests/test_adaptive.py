"""Test Pc/Pm thich nghi (src/improvements/adaptive.py)."""
import numpy as np
import pytest

from src.instance import load_config
from src.improvements import adaptive as ad
from src.improvements.adaptive import StagnationTracker, adaptive_rates, resolve_params

CFG = load_config()["improvements"]
P = resolve_params(CFG["adaptive_params"])
P29 = resolve_params(CFG["adaptive_params"], case29=True)


def test_flag_default_off():
    assert CFG["adaptive_rates"] is False


def test_baseline_rates_inside_ranges():
    nsga = load_config()["nsga2"]
    assert P["pc_min"] <= nsga["pc"] <= P["pc_max"]
    assert P["pm_min"] <= nsga["pm"]["solomon"] <= P["pm_max"]
    assert P29["pm_min"] <= nsga["pm"]["case29"] <= P29["pm_max"]


@pytest.mark.parametrize("params", [P, P29])
def test_always_within_bounds(params):
    rng = np.random.default_rng(0)
    for _ in range(500):
        big = int(rng.integers(0, 12))
        a, b = int(rng.integers(0, big + 1)), int(rng.integers(0, big + 1))
        for boost in (1.0, 1.5, 10.0):
            pc, pm = adaptive_rates(a, b, big, params, boost)
            assert params["pc_min"] - 1e-12 <= pc <= params["pc_max"] + 1e-12
            assert params["pm_min"] - 1e-12 <= pm <= params["pm_max"] + 1e-12


def test_extremes():
    pc, pm = adaptive_rates(0, 5, 7, P)         # min(rank) = 0
    assert (pc, pm) == (P["pc_min"], P["pm_min"])
    pc, pm = adaptive_rates(7, 7, 7, P)         # rank = R
    assert pc == pytest.approx(P["pc_max"]) and pm == pytest.approx(P["pm_max"])
    assert adaptive_rates(0, 0, 0, P) == (P["pc_min"], P["pm_min"])   # max_rank = 0 khong chia 0


def test_monotonic_in_rank():
    prev = (-1.0, -1.0)
    for r in range(0, 9):
        cur = adaptive_rates(r, r + 3, 8, P)
        assert cur[0] >= prev[0] and cur[1] >= prev[1]
        prev = cur
    # chi phu thuoc hang tot hon cua hai cha me
    assert adaptive_rates(2, 6, 8, P) == adaptive_rates(6, 2, 8, P) == adaptive_rates(2, 2, 8, P)


def front(*rows):
    return np.array(rows, float)


def test_stagnation_triggers_exactly_after_k():
    k = 3
    t = StagnationTracker(k, 1.5)
    f = front([1, 2, 3], [2, 1, 3])
    assert t.update(f) == 1.0                    # generation dau chi ghi nhan
    for g in range(1, k):
        assert t.update(f.copy()) == 1.0, g      # chua du k generation khong doi
    assert t.update(f.copy()) == 1.5             # dung k generation khong doi
    assert t.update(f.copy()) == 1.5             # van tri tre thi giu boost
    assert t.multiplier == 1.5


def test_stagnation_resets_on_change():
    t = StagnationTracker(2, 1.5)
    f = front([1, 2, 3])
    for _ in range(3):
        t.update(f)
    assert t.multiplier == 1.5
    assert t.update(front([1, 2, 3], [0.5, 2, 3])) == 1.0   # front doi -> reset
    assert t.unchanged == 0
    assert t.update(front([1, 2, 3], [0.5, 2, 3])) == 1.0
    assert t.update(front([1, 2, 3], [0.5, 2, 3])) == 1.5


def test_change_detection_uses_1e9_rounding_and_set_semantics():
    t = StagnationTracker(1, 1.5)
    t.update(front([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]))
    # nhieu duoi 1e-9 va doi thu tu hang khong tinh la doi
    assert t.update(front([3.0, 2.0, 1.0 + 1e-12], [1.0, 2.0, 3.0])) == 1.5
    # lech 1e-6 thi la doi
    assert t.update(front([3.0, 2.0, 1.0 + 1e-6], [1.0, 2.0, 3.0])) == 1.0


def test_boost_never_exceeds_pm_max():
    t = StagnationTracker(1, 100.0)
    f = front([1, 1, 1])
    t.update(f)
    mult = t.update(f)
    assert mult == 100.0
    for r in range(0, 6):
        _, pm = adaptive_rates(r, r, 5, P, mult)
        assert pm <= P["pm_max"]
    assert adaptive_rates(5, 5, 5, P, mult)[1] == P["pm_max"]
    # boost nho: pm giua khoang tang dung he so, chua cham tran
    _, base = adaptive_rates(1, 1, 8, P)
    _, boosted = adaptive_rates(1, 1, 8, P, 1.5)
    assert boosted == pytest.approx(min(base * 1.5, P["pm_max"]))


def test_stagnation_gens_zero_never_boosts():
    t = StagnationTracker(0, 1.5)
    f = front([1, 2, 3])
    for _ in range(50):
        assert t.update(f) == 1.0
    assert t.multiplier == 1.0


def test_no_rng_used(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("adaptive.py khong duoc dung RNG")
    monkeypatch.setattr(np.random, "default_rng", boom)
    np.random.seed(5)
    state = np.random.get_state()
    t = StagnationTracker(1, 1.5)
    t.update(front([1, 2, 3]))
    adaptive_rates(1, 2, 3, P, t.update(front([1, 2, 3])))
    after = np.random.get_state()
    assert np.array_equal(state[1], after[1]) and state[2:] == after[2:]
    assert not hasattr(ad, "random")


def test_invalid_bounds_rejected():
    with pytest.raises(ValueError):
        resolve_params({**CFG["adaptive_params"], "pc_min": 0.95})
