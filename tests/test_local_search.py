"""Test TV2: src/improvements/local_search.py và LocalSearchHook."""
import copy
import dataclasses

import numpy as np
import pytest

from src.decoder import evaluate_detail, split_greedy
from src.instance import load_config, load_instance
from src.improvements import local_search as lsm
from src.improvements.local_search import (
    LSCounters, dominates, improve, or_opt, parse_ls_params, to_min_vector, two_opt,
    weighted_score, _sample_or_opt, _sample_two_opt,
)
from src.improvements.tv2_hooks import LocalSearchHook, reference_scales

CFG = load_config()
LSP = CFG["improvements"]["local_search_params"]


class CountingRng:
    def __init__(self, seed):
        self.rng, self.calls = np.random.default_rng(seed), []

    def __getattr__(self, name):
        fn = getattr(self.rng, name)

        def w(*a, **k):
            self.calls.append(name)
            return fn(*a, **k)
        return w


def P(**kw):
    return {**LSP, **kw}


def is_perm(p, n):
    return len(p) == n and sorted(p) == list(range(1, n + 1))


def evaluator_for(inst, log=None):
    def ev(perm, meta):
        if log is not None:
            log.append((list(perm), meta))
        return evaluate_detail(perm, inst)
    return ev


def toy_capacity(demands, capacity, base=("C102", 25)):
    """Instance tự dựng cắt theo tải (split_rule=capacity), khách nằm trên một đường thẳng."""
    ref = load_instance(*base)
    n = len(demands)
    coords = np.c_[np.arange(n + 1, dtype=float), np.zeros(n + 1)]
    diff = coords[:, None, :] - coords[None, :, :]
    eta = np.zeros(n + 1)
    return dataclasses.replace(
        ref, name=f"toycap-{n}", n=n, coords=coords, demand=np.r_[0.0, demands].astype(float),
        service_time=np.zeros(n + 1), tw_expected=np.c_[eta, eta + 1e4],
        tw_specified=np.c_[eta, eta + 1e4 + 30], dist=np.hypot(diff[..., 0], diff[..., 1]),
        capacity=float(capacity), fleet_size=None,
        params={**ref.params, "split_rule": "capacity"})


INSTANCES = [("C102", 25), ("R201", 50), ("RC201", 100)]


# ------------------------------------------------------------------ toán tử
def test_two_opt_basic_and_no_mutation():
    r = [1, 2, 3, 4, 5, 6]
    assert two_opt(r, 1, 4) == [1, 5, 4, 3, 2, 6]
    assert two_opt(r, 0, 5) == [6, 5, 4, 3, 2, 1]
    assert two_opt([7, 8], 0, 1) == [8, 7]
    assert r == [1, 2, 3, 4, 5, 6]
    assert two_opt((1, 2, 3), 0, 1) == [2, 1, 3]


@pytest.mark.parametrize("route,i,j", [([], 0, 1), ([1], 0, 0), ([1, 2], 1, 1), ([1, 2], 1, 0),
                                       ([1, 2, 3], -1, 2), ([1, 2, 3], 0, 3)])
def test_two_opt_bounds(route, i, j):
    with pytest.raises(IndexError):
        two_opt(route, i, j)


def test_or_opt_spec_example_and_positions():
    r = [1, 2, 3, 4, 5, 6]
    assert or_opt(r, 1, 2, 3) == [1, 4, 5, 2, 3, 6]          # ví dụ trong đặc tả
    assert or_opt(r, 3, 1, 0) == [4, 1, 2, 3, 5, 6]          # chèn đầu
    assert or_opt(r, 0, 3, 3) == [4, 5, 6, 1, 2, 3]          # chèn cuối, L=3
    assert or_opt(r, 4, 2, 1) == [1, 5, 6, 2, 3, 4]          # chèn giữa, khối cuối
    assert or_opt(r, 2, 1, 2) == r                           # insert_at == start: no-op
    assert or_opt(r, 2, 3, 2) == r
    assert r == [1, 2, 3, 4, 5, 6]


@pytest.mark.parametrize("args", [(0, 0, 0), (5, 2, 0), (-1, 1, 0), (0, 2, 5), (0, 1, -1),
                                  (0, 7, 0)])
def test_or_opt_bounds(args):
    with pytest.raises(IndexError):
        or_opt([1, 2, 3, 4, 5, 6], *args)


@pytest.mark.parametrize("m", range(0, 9))
def test_sampled_moves_valid_and_not_noop(m):
    rng = np.random.default_rng(m)
    route = list(range(10, 10 + m))
    for _ in range(300):
        mv = _sample_two_opt(m, rng)
        if m < 2:
            assert mv is None
        else:
            out = two_opt(route, *mv)
            assert sorted(out) == route and out != route
        mv = _sample_or_opt(m, (1, 2, 3), rng)
        if m < 2:
            assert mv is None
        else:
            s, L, ins = mv
            assert L < m and ins != s
            out = or_opt(route, s, L, ins)
            assert sorted(out) == route and out != route


# ------------------------------------------------------------------ so sánh
def test_dominates_with_eps():
    assert dominates([1, 1, 1], [1, 1, 2])
    assert not dominates([1, 1, 1], [1, 1, 1])
    assert not dominates([0, 2, 1], [1, 1, 1])
    assert not dominates([1, 1, 1 - 1e-12], [1, 1, 1], eps=1e-10)   # dưới epsilon: không tính
    assert dominates([1 + 1e-12, 1, 0.5], [1, 1, 1], eps=1e-10)     # lệch trong epsilon vẫn "<="


def test_f3_is_maximised():
    lo = {"f1": 10.0, "f2": 5.0, "f3": 0.4}
    hi = {"f1": 10.0, "f2": 5.0, "f3": 0.9}
    assert to_min_vector(hi)[2] == pytest.approx(0.1)
    assert dominates(to_min_vector(hi), to_min_vector(lo))          # hài lòng cao hơn = tốt hơn
    w, s = np.array([0.0, 0.0, 1.0]), np.ones(3)
    assert weighted_score(to_min_vector(hi), w, s) < weighted_score(to_min_vector(lo), w, s)


# ------------------------------------------------------------------ tham số
@pytest.mark.parametrize("bad", [
    {"p_ls": 1.5}, {"p_ls": -0.1}, {"p_ls": float("nan")}, {"max_passes": 0},
    {"max_candidate_evals": 0}, {"max_candidate_evals": 10**9}, {"max_accepted_moves": 1.5},
    {"or_opt_lengths": [4]}, {"or_opt_lengths": []}, {"or_opt_lengths": [1, 1]},
    {"operators": []}, {"operators": ["three_opt"]}, {"acceptance": "lexi"},
    {"weight_distribution": "beta"}, {"strategy": "random"}, {"improvement_epsilon": -1},
    {"split_drift_policy": "ignore"}, {"foo": 1},
])
def test_bad_params(bad):
    with pytest.raises(ValueError):
        parse_ls_params(P(**bad))


def test_config_defaults():
    assert CFG["improvements"]["local_search"] is False
    p = parse_ls_params(LSP)
    assert p.acceptance == "weighted" and p.split_drift_policy == "reject" and p.strategy == "first"


def test_weighted_requires_scales():
    inst = load_instance("C102", 25)
    with pytest.raises(ValueError):
        improve(list(range(1, 26)), inst, np.random.default_rng(0), P(),
                decode_and_evaluate=evaluator_for(inst))
    with pytest.raises(ValueError):
        improve(list(range(1, 26)), inst, np.random.default_rng(0), P(),
                decode_and_evaluate=evaluator_for(inst), scales=[1, 0, 1])
    with pytest.raises(ValueError):
        improve([1, 1] + list(range(3, 26)), inst, np.random.default_rng(0), P(acceptance="pareto"),
                decode_and_evaluate=evaluator_for(inst))


# ------------------------------------------------------------------ đúng đắn trên instance thật
@pytest.mark.parametrize("name,n", INSTANCES)
@pytest.mark.parametrize("acceptance", ["weighted", "pareto"])
@pytest.mark.parametrize("policy", ["reject", "evaluate_actual"])
def test_improve_valid_monotone_and_exact(name, n, acceptance, policy):
    inst = load_instance(name, n)
    sc = reference_scales(inst, lambda p: evaluate_detail(p, inst))
    rng = np.random.default_rng(42)
    params = P(acceptance=acceptance, split_drift_policy=policy, max_candidate_evals=60,
               max_accepted_moves=10, max_passes=3)
    for _ in range(8):
        perm = rng.permutation(np.arange(1, n + 1)).tolist()
        orig = list(perm)
        d0 = evaluate_detail(perm, inst)
        r = improve(perm, inst, rng, params, decode_and_evaluate=evaluator_for(inst), scales=sc)
        assert perm == orig                                       # không sửa đầu vào
        assert is_perm(r.perm, n)
        fresh = evaluate_detail(r.perm, inst)                     # chấm lại độc lập
        for k in ("f1", "f2", "f3", "n_vehicles"):
            assert r.detail[k] == fresh[k]
        assert r.detail["routes"] == fresh["routes"]
        g0, g1 = to_min_vector(d0), to_min_vector(r.detail)
        if r.accepted == 0:
            assert r.perm == orig
        elif acceptance == "pareto":
            assert dominates(g1, g0)
        else:
            assert weighted_score(g1, r.weights, sc) < weighted_score(g0, r.weights, sc)
        for h in r.history:                                       # từng bước được nhận đều tốt hơn
            if acceptance == "pareto":
                assert dominates(h["after"], h["before"], params["improvement_epsilon"])
            else:
                assert (weighted_score(h["after"], r.weights, sc)
                        < weighted_score(h["before"], r.weights, sc))
            assert h["accepted_by"] == acceptance
        if d0["fleet_ok"]:
            assert r.detail["fleet_ok"]
        else:
            assert r.detail["n_vehicles"] <= d0["n_vehicles"]


def test_proposed_moves_keep_route_membership_and_are_single_route():
    """Mọi ứng viên = nghiệm hiện tại với ĐÚNG MỘT tuyến bị hoán đổi thứ tự nội bộ."""
    inst = load_instance("R201", 50)
    calls = []

    def frozen(perm, meta):                     # mục tiêu hằng: không bước nào được nhận
        calls.append(list(perm))
        d = evaluate_detail(perm, inst)
        return {**d, "f1": 1.0, "f2": 1.0, "f3": 0.5}

    rng = np.random.default_rng(3)
    for _ in range(5):
        calls.clear()
        perm = rng.permutation(np.arange(1, 51)).tolist()
        r = improve(perm, inst, rng, P(acceptance="pareto", max_candidate_evals=40, max_passes=3),
                    decode_and_evaluate=frozen)
        assert r.accepted == 0 and r.perm == perm
        routes = evaluate_detail(perm, inst)["routes"]
        bounds, k = [], 0
        for rt in routes:
            bounds.append((k, k + len(rt)))
            k += len(rt)
        for cand in calls[1:]:
            changed = [(a, b) for a, b in bounds if cand[a:b] != perm[a:b]]
            assert len(changed) == 1
            a, b = changed[0]
            assert sorted(cand[a:b]) == sorted(perm[a:b])


# ------------------------------------------------------------------ lệch biên tuyến (bắt buộc)
def test_boundary_drift_counterexample_rejected():
    """Tải 10. perm [1,2,3], demand 6,5,3 -> greedy: [1] | [2,3]. Đảo tuyến B -> [1,3,2]: greedy cắt
    lại thành [1,3] | [2] (khách đầu B lọt vào A). Bước đi phải bị loại, không được tính lợi ích."""
    inst = toy_capacity([6, 5, 3], 10)
    assert split_greedy([1, 2, 3], inst) == [[1], [2, 3]]
    assert split_greedy([1, 3, 2], inst) == [[1, 3], [2]]       # phản ví dụ thật
    log = []
    c = LSCounters()
    r = improve([1, 2, 3], inst, np.random.default_rng(0),
                P(acceptance="pareto", operators=["two_opt"], max_passes=3),
                decode_and_evaluate=evaluator_for(inst, log), counters=c)
    assert [1, 3, 2] in [p for p, _ in log]                     # ứng viên ĐÃ được chấm bằng decoder
    assert r.perm == [1, 2, 3] and r.accepted == 0
    assert c.n_ls_rejected_split >= 1 and c.n_ls_split_drift == c.n_ls_rejected_split
    assert c.n_ls_accepted == 0


def test_boundary_drift_evaluate_actual_uses_real_routes():
    """Cùng phản ví dụ, policy evaluate_actual: chỉ nhận nếu decoder THẬT cho kết quả tốt hơn, và detail
    trả về là của bộ tuyến thật [1,3] | [2], không phải bộ tuyến đề xuất [1] | [3,2]."""
    inst = toy_capacity([6, 5, 3], 10)
    c = LSCounters()
    r = improve([1, 2, 3], inst, np.random.default_rng(0),
                P(acceptance="pareto", operators=["two_opt"], split_drift_policy="evaluate_actual"),
                decode_and_evaluate=evaluator_for(inst), counters=c)
    assert c.n_ls_split_drift >= 1 and c.n_ls_rejected_split == 0
    real = evaluate_detail(r.perm, inst)
    assert r.detail["routes"] == real["routes"] and r.detail["f1"] == real["f1"]
    if r.accepted:
        assert dominates(to_min_vector(real), to_min_vector(evaluate_detail([1, 2, 3], inst)))


def test_drift_rejected_on_capacity_time_split():
    """Với split mặc định capacity_time, các bước bị lệch biên bị loại và không bao giờ được nhận."""
    inst = load_instance("C102", 25)
    assert inst.params["split_rule"] == "capacity_time"
    c = LSCounters()
    rng = np.random.default_rng(9)
    sc = reference_scales(inst, lambda p: evaluate_detail(p, inst))
    for _ in range(20):
        perm = rng.permutation(np.arange(1, 26)).tolist()
        r = improve(perm, inst, rng, P(), decode_and_evaluate=evaluator_for(inst), counters=c,
                    scales=sc)
        assert r.detail["routes"] == evaluate_detail(r.perm, inst)["routes"]
    assert c.n_ls_rejected_split > 0


# ------------------------------------------------------------------ RNG, metadata, trọng số
def test_weights_sampled_once_per_invocation_and_metadata_passthrough():
    inst = load_instance("C102", 25)
    meta = {"dp_weights": np.array([0.2, 0.3, 0.5])}
    meta_copy = copy.deepcopy(meta)
    seen = []

    def ev(perm, m):
        seen.append(m)
        return evaluate_detail(perm, inst)

    sc = reference_scales(inst, lambda p: evaluate_detail(p, inst))
    crng = CountingRng(1)
    r = improve(list(range(1, 26)), inst, crng, P(max_candidate_evals=30), decode_and_evaluate=ev,
                metadata=meta, scales=sc)
    assert crng.calls.count("dirichlet") == 1
    assert crng.calls[0] == "dirichlet"
    assert all(m is meta for m in seen) and len(seen) == r.real_evals
    assert np.array_equal(meta["dp_weights"], meta_copy["dp_weights"])
    assert r.weights.shape == (3,) and r.weights.sum() == pytest.approx(1.0) and np.all(r.weights >= 0)


def test_equal_weights_use_no_rng_for_weights():
    inst = load_instance("C102", 25)
    sc = reference_scales(inst, lambda p: evaluate_detail(p, inst))
    crng = CountingRng(1)
    r = improve(list(range(1, 26)), inst, crng, P(weight_distribution="equal"),
                decode_and_evaluate=evaluator_for(inst), scales=sc)
    assert "dirichlet" not in crng.calls
    assert np.allclose(r.weights, 1 / 3)


def test_reproducible_same_seed():
    inst = load_instance("RC201", 100)
    sc = reference_scales(inst, lambda p: evaluate_detail(p, inst))
    perm = np.random.default_rng(0).permutation(np.arange(1, 101)).tolist()
    outs = []
    for _ in range(2):
        rng = np.random.default_rng(123)
        r = improve(perm, inst, rng, P(), decode_and_evaluate=evaluator_for(inst), scales=sc)
        outs.append((r.perm, r.detail["f1"], r.history, rng.bit_generator.state))
    assert outs[0][0] == outs[1][0] and outs[0][1] == outs[1][1]
    assert outs[0][2] == outs[1][2] and outs[0][3] == outs[1][3]


# ------------------------------------------------------------------ trần ngân sách
@pytest.mark.parametrize("cap_evals,cap_acc,cap_pass", [(1, 5, 2), (5, 1, 5), (40, 100, 1),
                                                        (200, 3, 50)])
def test_hard_caps(cap_evals, cap_acc, cap_pass):
    inst = load_instance("RC201", 100)
    sc = reference_scales(inst, lambda p: evaluate_detail(p, inst))
    rng = np.random.default_rng(5)
    calls = []
    for _ in range(5):
        calls.clear()
        perm = rng.permutation(np.arange(1, 101)).tolist()
        r = improve(perm, inst, rng, P(max_candidate_evals=cap_evals, max_accepted_moves=cap_acc,
                                       max_passes=cap_pass, split_drift_policy="evaluate_actual"),
                    decode_and_evaluate=evaluator_for(inst, calls), scales=sc)
        assert r.attempts <= cap_evals and r.accepted <= cap_acc and r.passes <= cap_pass
        assert len(calls) == r.real_evals <= cap_evals + 1          # +1 = nghiệm ban đầu
        assert r.evals == r.attempts + 1


def test_initial_detail_reused_no_extra_eval():
    inst = load_instance("C102", 25)
    perm = list(range(1, 26))
    d = evaluate_detail(perm, inst)
    calls = []
    r = improve(perm, inst, np.random.default_rng(0), P(acceptance="pareto", max_candidate_evals=3),
                decode_and_evaluate=evaluator_for(inst, calls), initial_detail=d)
    assert [p for p, _ in calls].count(perm) == 0
    assert r.real_evals == len(calls) <= 3


# ------------------------------------------------------------------ biên
def test_all_single_customer_routes_no_move():
    inst = toy_capacity([5, 5, 5, 5], 5)                  # mỗi tuyến đúng 1 khách
    calls = []
    r = improve([2, 4, 1, 3], inst, np.random.default_rng(0), P(acceptance="pareto"),
                decode_and_evaluate=evaluator_for(inst, calls))
    assert r.perm == [2, 4, 1, 3] and r.attempts == 0 and r.accepted == 0 and len(calls) == 1


def test_n1_and_n2():
    inst1 = toy_capacity([1], 10)
    r = improve([1], inst1, np.random.default_rng(0), P(acceptance="pareto"),
                decode_and_evaluate=evaluator_for(inst1))
    assert r.perm == [1] and r.attempts == 0
    inst2 = toy_capacity([1, 1], 10)
    r = improve([2, 1], inst2, np.random.default_rng(0), P(acceptance="pareto", max_candidate_evals=7),
                decode_and_evaluate=evaluator_for(inst2))
    assert is_perm(r.perm, 2) and r.attempts <= 7


def test_duplicate_candidates_hit_cache_but_count_budget():
    inst = toy_capacity([1, 1], 10)                       # 1 tuyến 2 khách: chỉ có 1 bước đi khả dĩ
    calls = []

    def frozen(perm, m):
        calls.append(list(perm))
        return {**evaluate_detail(perm, inst), "f1": 1.0, "f2": 1.0, "f3": 0.5}
    r = improve([1, 2], inst, np.random.default_rng(0),
                P(acceptance="pareto", max_candidate_evals=10, max_passes=20),
                decode_and_evaluate=frozen)
    assert r.attempts == 10 and r.real_evals == len(calls) == 2   # [1,2] và [2,1], phần còn lại cache


def test_fleet_feasibility_policy():
    inst = load_instance("C102", 25)
    base = evaluate_detail(list(range(1, 26)), inst)
    assert base["fleet_ok"]

    def ev(perm, m):                 # mọi ứng viên khác nghiệm gốc giả lập vượt đội xe nhưng "tốt hơn"
        d = evaluate_detail(perm, inst)
        if perm != list(range(1, 26)):
            d = {**d, "fleet_ok": False, "f1": 0.0, "f2": 0.0, "f3": 1.0}
        return d
    c = LSCounters()
    r = improve(list(range(1, 26)), inst, np.random.default_rng(0), P(acceptance="pareto"),
                decode_and_evaluate=ev, counters=c)
    assert r.accepted == 0 and c.n_ls_rejected_feasibility > 0 and r.detail["fleet_ok"]


def test_best_strategy_valid():
    inst = load_instance("R201", 50)
    sc = reference_scales(inst, lambda p: evaluate_detail(p, inst))
    rng = np.random.default_rng(1)
    for _ in range(5):
        perm = rng.permutation(np.arange(1, 51)).tolist()
        r = improve(perm, inst, rng, P(strategy="best"), decode_and_evaluate=evaluator_for(inst),
                    scales=sc)
        assert is_perm(r.perm, 50)
        assert r.detail["f1"] == evaluate_detail(r.perm, inst)["f1"]


# ------------------------------------------------------------------ evaluator được phép cắt lại (DP)
def test_resplitting_evaluator_same_metadata_and_real_routes():
    """Giả lập evaluator kiểu DP: cắt lại hoán vị thành các tuyến 2 khách, mục tiêu phụ thuộc trọng số
    cá thể trong metadata. LS không ép bộ tuyến, nhưng phải dùng cùng metadata và trả bộ tuyến thật."""
    inst = load_instance("C102", 25)
    meta = {"dp_weights": np.array([0.5, 0.25, 0.25])}

    def fake_dp(perm, m):
        assert m is meta
        routes = [list(perm[i:i + 2]) for i in range(0, len(perm), 2)]
        from src.decoder import evaluate_routes_detail
        d = evaluate_routes_detail(routes, inst)
        d["weights"] = np.asarray(m["dp_weights"]).copy()
        return d

    sc = reference_scales(inst, lambda p: evaluate_detail(p, inst))
    rng = np.random.default_rng(4)
    for _ in range(5):
        perm = rng.permutation(np.arange(1, 26)).tolist()
        r = improve(perm, inst, rng, P(max_candidate_evals=50), decode_and_evaluate=fake_dp,
                    metadata=meta, scales=sc, require_same_routes=False)
        again = fake_dp(r.perm, meta)
        assert r.detail["routes"] == again["routes"] and r.detail["f1"] == again["f1"]
        assert np.array_equal(r.detail["weights"], meta["dp_weights"])


# ------------------------------------------------------------------ hook
def test_hook_requires_flag_on():
    inst = load_instance("C102", 25)
    with pytest.raises(RuntimeError):
        LocalSearchHook.from_config(CFG["improvements"], inst, evaluator_for(inst))


def test_hook_p_ls_zero_one_draw_no_eval():
    inst = load_instance("C102", 25)
    imp = {**CFG["improvements"], "local_search": True,
           "local_search_params": P(p_ls=0.0)}
    calls = []
    hook = LocalSearchHook.from_config(imp, inst, evaluator_for(inst, calls))
    calls.clear()                                           # bỏ các lần chấm để tính scales
    crng = CountingRng(0)
    perm = list(range(25, 0, -1))
    out, detail = hook(perm, crng)
    assert out == perm and out is not perm and detail is None
    assert crng.calls == ["random"] and calls == []
    assert hook.counters.n_ls_calls == 1 and hook.counters.n_ls_triggered == 0


def test_hook_triggered_returns_exact_detail_and_counts():
    inst = load_instance("RC201", 100)
    imp = {**CFG["improvements"], "local_search": True, "local_search_params": P(p_ls=1.0)}
    hook = LocalSearchHook.from_config(imp, inst, evaluator_for(inst))
    rng = np.random.default_rng(0)
    for _ in range(10):
        perm = rng.permutation(np.arange(1, 101)).tolist()
        out, d = hook(perm, rng)
        assert d is not None and d["f1"] == evaluate_detail(out, inst)["f1"]
    c = hook.counters
    assert c.n_ls_calls == c.n_ls_triggered == 10
    assert c.n_ls_candidate_evals <= 10 * LSP["max_candidate_evals"]
    assert c.n_real_model_evals <= c.n_eval_requests
    assert c.n_ls_accepted + c.n_ls_rejected_split + c.n_ls_rejected_feasibility \
        + c.n_ls_rejected_no_improve == c.n_ls_candidate_evals


def test_reference_scales_deterministic_no_rng(monkeypatch):
    inst = load_instance("R201", 50)
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    s1 = reference_scales(inst, lambda p: evaluate_detail(p, inst))
    s2 = reference_scales(inst, lambda p: evaluate_detail(p, inst))
    assert np.array_equal(s1, s2) and s1.shape == (3,) and np.all(s1 > 0) and s1[2] == 1.0
    assert not hasattr(lsm, "random")
