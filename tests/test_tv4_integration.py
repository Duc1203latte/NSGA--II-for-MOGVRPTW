"""Test việc gắn dp_split và adaptive_rates vào src/nsga2.py.

Mốc cờ-tắt (tests/fixtures/tv4_alloff_main.json) sinh từ nsga2.py CHƯA SỬA của commit main, KHÔNG
phải của branch này: `python -m scripts.make_tv4_fixture` lấy src/nsga2.py bằng
`git show <merge-base>:src/nsga2.py`, chạy với mọi cờ tắt, n_gen=10, seed 0 và 1 trên C102-25 và
R201-50. Hoán vị lưu nguyên, F lưu bằng float.hex nên so được từng bit.
"""
import copy
import json
import math

import numpy as np
import pytest

from src import nsga2
from src.improvements import adaptive as adaptive_mod
from src.improvements import dp_split as dp_mod
from src.improvements.dp_split import evaluate_dp, objective_scales
from src.instance import ROOT, load_config, load_instance

FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "tv4_alloff_main.json").read_text(encoding="utf-8"))


def make_cfg(n_gen, n_pop=None, **flags):
    cfg = copy.deepcopy(load_config())
    cfg["nsga2"]["n_gen"] = n_gen
    if n_pop is not None:
        cfg["nsga2"]["n_pop"] = n_pop
    dp_mode = flags.pop("dp_mode", "every_eval")   # config.yaml mặc định mode = polish; các test cũ kiểm every_eval
    for k in ("init_smart", "local_search", "diversity", "dp_split", "adaptive_rates"):
        cfg["improvements"][k] = flags.get(k, False)
    cfg["improvements"]["dp_split_params"]["mode"] = dp_mode
    return cfg


def split_key(key):
    inst_name, seed = key.split("/seed")
    name, n = inst_name.split("-")
    return name, int(n), int(seed)


# ---------------------------------------------------------------- cờ tắt == main
@pytest.mark.parametrize("key", sorted(FIXTURE["cases"]))
def test_flags_off_identical_to_main(key):
    name, n, seed = split_key(key)
    cfg = make_cfg(FIXTURE["n_gen"])
    assert cfg["nsga2"]["n_pop"] == FIXTURE["n_pop"]
    inst = load_instance(name, n, cfg)
    ref, res = FIXTURE["cases"][key], nsga2.run(inst, cfg, seed)
    assert res["pop"] == ref["pop"]
    # F so với dung sai 1e-12 (tương đối), KHÔNG so từng bit: fixture sinh trên Windows, còn libm/BLAS của Linux
    # (exp, sqrt, tổng nhiều số hạng) có thể lệch 1 ULP ở vài giá trị f2 dù hoán vị giống hệt. Hoán vị, CV, front
    # và n_evals vẫn so chính xác, nên mọi lệch hướng tiến hoá (khác RNG, khác thứ tự chọn) vẫn bị bắt.
    expected_F = np.array([[float.fromhex(x) for x in row] for row in ref["F_hex"]])
    assert np.allclose(res["F"], expected_F, rtol=1e-12, atol=0)
    assert [float(x) for x in res["CV"]] == ref["CV"]
    assert [int(i) for i in res["front"]] == ref["front"]
    assert res["n_evals"] == ref["n_evals"]
    # thông tin thêm của TV4 khi tắt cờ
    assert res["W"] is None and res["n_dp_calls"] == 0 and res["rate_log"] == []
    assert 0.0 <= res["feasible_frac_front"] <= 1.0 and 0.0 <= res["feasible_frac_pop"] <= 1.0
    assert res["wall_time_s"] > 0


def test_flags_off_calls_no_tv4_code(monkeypatch):
    """Cờ tắt: không bốc trọng số, không tính tỉ lệ, không scales (nên không RNG của TV4)."""
    def boom(*a, **k):
        raise AssertionError("code TV4 bị gọi khi cờ tắt")
    for mod, names in ((dp_mod, ("sample_weights", "child_weights", "evaluate_dp", "objective_scales")),
                       (adaptive_mod, ("adaptive_rates", "resolve_params"))):
        for nm in names:
            monkeypatch.setattr(mod, nm, boom)
    monkeypatch.setattr(adaptive_mod.StagnationTracker, "__init__", boom)
    cfg = make_cfg(3, n_pop=12)
    nsga2.run(load_instance("C102", 25, cfg), cfg, 0)


# ---------------------------------------------------------------- dp_split
@pytest.mark.parametrize("name,n,n_pop", [("C102", 25, 20), ("R201", 50, 21), ("C102", 100, 10)])
@pytest.mark.parametrize("dups", [True, False])
def test_dp_split_on(name, n, n_pop, dups):
    cfg = make_cfg(4, n_pop=n_pop, dp_split=True)
    cfg["nsga2"]["eliminate_duplicates"] = dups
    inst = load_instance(name, n, cfg)
    res = nsga2.run(inst, cfg, 3)
    pop, W, F = res["pop"], res["W"], res["F"]
    assert W.shape == (len(pop), 3) == (n_pop, 3)
    assert np.all(W >= 0) and np.allclose(W.sum(axis=1), 1.0)
    scales = objective_scales(inst, cfg["improvements"]["dp_split_params"]["g3_scale"])
    for i, perm in enumerate(pop):
        d = evaluate_dp(perm, inst, W[i], scales)       # chấm lại bằng đúng trọng số của cá thể i
        assert sorted(c for r in d["routes"] for c in r) == list(range(1, n + 1))
        assert np.array_equal(F[i], [d["f1"], d["f2"], 1 - d["f3"]])  # W thẳng hàng với pop sau chọn lọc
        assert d["split"] == "dp" and np.array_equal(d["weights"], W[i])
        assert d["n_vehicles"] <= (inst.fleet_size or 10 ** 9) and d["fleet_ok"]
    assert np.all(res["CV"] == 0)
    assert res["feasible_frac_pop"] == res["feasible_frac_front"] == 1.0
    assert res["n_dp_calls"] == res["n_evals"] == n_pop * 5
    assert res["rate_log"] == []


def test_dp_split_initial_permutations_match_baseline():
    """Trọng số được bốc SAU hoán vị, nên quần thể ban đầu có cùng hoán vị với baseline."""
    base = nsga2.run(load_instance("C102", 25, make_cfg(0)), make_cfg(0), 5)
    cfg = make_cfg(0, dp_split=True)
    on = nsga2.run(load_instance("C102", 25, cfg), cfg, 5)
    assert on["pop"] == base["pop"]


def test_dp_split_weights_stay_with_their_perm():
    """Cá thể sống sót giữ trọng số gốc: trọng số bất kỳ ở thế hệ cuối xuất hiện ở thế hệ đầu hoặc là
    của con (bốc ngẫu nhiên); kiểm đơn giản: chế độ 'parent' thì mọi hàng W đều là hàng của quần thể đầu."""
    cfg = make_cfg(6, n_pop=16, dp_split=True)
    cfg["improvements"]["dp_split_params"]["weight_inherit"] = "parent"
    inst = load_instance("C102", 25, cfg)
    first = nsga2.run(inst, make_cfg(0, n_pop=16, dp_split=True), 2)["W"]
    last = nsga2.run(inst, cfg, 2)["W"]
    initial = {tuple(r) for r in first.tolist()}
    assert all(tuple(r) in initial for r in last.tolist())


# ---------------------------------------------------------------- adaptive_rates
def test_adaptive_on_rates_in_bounds_and_log():
    cfg = make_cfg(10, n_pop=40, adaptive_rates=True)
    inst = load_instance("C102", 25, cfg)
    res = nsga2.run(inst, cfg, 1)
    ap = adaptive_mod.resolve_params(cfg["improvements"]["adaptive_params"], cfg["nsga2"])
    log = res["rate_log"]
    assert len(log) == cfg["nsga2"]["n_gen"]
    assert res["W"] is None and res["n_dp_calls"] == 0
    rank_based = varied = 0
    for g in log:
        assert 0 < g["front1_fraction"] <= 1.0
        assert len(g["pc"]) == len(g["pm"]) == math.ceil(40 / 2)
        assert all(ap["pc_min"] - 1e-12 <= x <= ap["pc_max"] + 1e-12 for x in g["pc"])
        assert all(ap["pm_min"] - 1e-12 <= x <= ap["pm_max"] + 1e-12 for x in g["pm"])
        if g["front1_fraction"] < ap["single_front_threshold"]:
            rank_based += 1
            varied += len(set(g["pc"])) > 1
        else:
            assert set(g["pc"]) == {cfg["nsga2"]["pc"]}          # quần thể gần một front: pc gốc
    assert rank_based > 0 and varied > 0                          # nhánh theo hạng thật sự chạy


def test_adaptive_case29_uses_case29_bounds():
    cfg = make_cfg(3, n_pop=20, adaptive_rates=True)
    inst = load_instance("case29", 29, cfg)
    res = nsga2.run(inst, cfg, 0)
    lo, hi = cfg["improvements"]["adaptive_params"]["pm_case29"].values()
    assert all(lo - 1e-12 <= x <= hi + 1e-12 for g in res["rate_log"] for x in g["pm"])


def test_adaptive_stagnation_boost_capped():
    cfg = make_cfg(8, n_pop=20, adaptive_rates=True)
    ap = cfg["improvements"]["adaptive_params"]
    ap["stagnation_gens"], ap["boost"] = 1, 100.0
    res = nsga2.run(load_instance("C102", 25, cfg), cfg, 0)
    assert all(x <= ap["pm_max"] + 1e-12 for g in res["rate_log"] for x in g["pm"])


# ---------------------------------------------------------------- cả hai
def test_both_on_runs_and_is_deterministic():
    cfg = make_cfg(5, n_pop=20, dp_split=True, adaptive_rates=True)
    inst = load_instance("R201", 25, cfg)
    a, b = nsga2.run(inst, cfg, 7), nsga2.run(inst, cfg, 7)
    assert a["pop"] == b["pop"] and np.array_equal(a["F"], b["F"]) and np.array_equal(a["W"], b["W"])
    assert a["rate_log"] == b["rate_log"] and len(a["rate_log"]) == 5
    assert a["n_dp_calls"] == a["n_evals"] and np.all(a["CV"] == 0)
    c = nsga2.run(inst, cfg, 8)
    assert c["pop"] != a["pop"]


# ---------------------------------------------------------------- dp_split mode "polish"
from src.decoder import evaluate_detail  # noqa: E402
from src.improvements.dp_split import simplex_lattice  # noqa: E402


@pytest.mark.parametrize("k", [1, 2, 3, 5, 10, 30])
def test_simplex_lattice(k):
    np.random.seed(0)
    state = np.random.get_state()
    lat = simplex_lattice(k)
    assert lat.shape == (k, 3) and np.all(lat >= 0) and np.allclose(lat.sum(axis=1), 1.0)
    assert len({tuple(r) for r in lat.round(12).tolist()}) == k           # không trùng
    assert np.array_equal(lat, simplex_lattice(k))                         # tất định
    if k >= 3:
        assert np.array_equal(lat[:3], np.eye(3))                          # luôn có ba cực
    assert np.array_equal(state[1], np.random.get_state()[1])              # không dùng RNG toàn cục
    if k == 10:                                                            # m = 3: đủ cả lưới
        assert {tuple(r) for r in (lat * 3).round().astype(int).tolist()} == {
            (i, j, 3 - i - j) for i in range(4) for j in range(4 - i)}


def polish_cfg(n_gen, n_pop, k):
    cfg = make_cfg(n_gen, n_pop=n_pop, dp_split=True)
    cfg["improvements"]["dp_split_params"].update(mode="polish", polish_k=k)
    return cfg


_REAL_DEFAULT_RNG = np.random.default_rng


class CountingRng:
    """Bọc Generator, ghi lại mọi lần gọi phương thức sinh số."""
    calls: list = []

    def __init__(self, seed):
        self._g = _REAL_DEFAULT_RNG(seed)

    def __getattr__(self, name):
        fn = getattr(self._g, name)

        def wrapped(*a, **k):
            CountingRng.calls.append(name)
            return fn(*a, **k)
        return wrapped


@pytest.mark.parametrize("name,n,k", [("C102", 25, 10), ("R201", 50, 30)])
def test_polish_final_population_equals_baseline_bit_for_bit(name, n, k, monkeypatch):
    n_pop, n_gen = 24, 8
    base_cfg, pol_cfg = make_cfg(n_gen, n_pop=n_pop), polish_cfg(n_gen, n_pop, k)
    inst = load_instance(name, n, base_cfg)
    seqs = {}
    for label, cfg in (("base", base_cfg), ("pol", pol_cfg)):
        CountingRng.calls = []
        monkeypatch.setattr(nsga2.np.random, "default_rng", CountingRng)
        seqs[label] = (nsga2.run(inst, cfg, 5), list(CountingRng.calls))
        monkeypatch.undo()
    base, pol = seqs["base"][0], seqs["pol"][0]
    pre = pol["pre_polish"]
    assert pre["pop"] == base["pop"]
    assert [[float(x).hex() for x in r] for r in pre["F"]] == [[float(x).hex() for x in r] for r in base["F"]]
    assert np.array_equal(pre["CV"], base["CV"]) and np.array_equal(pre["front"], base["front"])
    assert all(np.array_equal(a, b) for a, b in zip(pol["history"], base["history"]))
    assert seqs["pol"][1] == seqs["base"][1]            # cùng dãy gọi RNG: polish không bốc số ngẫu nhiên
    assert base["pre_polish"] is None and base["dp_mode"] is None
    # đếm lời gọi DP thêm: n_pop * K, tính vào cả n_evals lẫn n_dp_calls
    assert pol["n_dp_calls"] == n_pop * k and pol["n_evals"] == base["n_evals"] + n_pop * k
    assert pol["dp_mode"] == "polish"


@pytest.mark.parametrize("name,n,k", [("C102", 25, 10), ("R201", 50, 10)])
def test_polish_front_weakly_dominates_baseline_front(name, n, k):
    cfg = polish_cfg(12, 30, k)
    inst = load_instance(name, n, cfg)
    base = nsga2.run(inst, make_cfg(12, n_pop=30), 2)
    pol = nsga2.run(inst, cfg, 2)
    assert np.all(base["CV"] == 0) and np.all(pol["CV"] == 0)
    bf, pf = base["F"][base["front"]], pol["F"][pol["front"]]
    for b in bf:
        assert np.any(np.all(pf <= b, axis=1)), "điểm baseline không được phủ yếu bởi front đã polish"
    assert len({tuple(r) for r in pf.tolist()}) == len(pf)          # không có điểm trùng vector mục tiêu
    # mỗi dòng chấm lại đúng bằng evaluator đã dùng: NaN = split baseline, còn lại = DP với trọng số đó
    from src.improvements.dp_split import evaluate_dp, objective_scales
    scales = objective_scales(inst, cfg["improvements"]["dp_split_params"]["g3_scale"])
    for i in pol["front"]:
        w = pol["W"][i]
        d = evaluate_detail(pol["pop"][i], inst) if np.isnan(w).all() else evaluate_dp(pol["pop"][i], inst, w, scales)
        assert np.array_equal(pol["F"][i], [d["f1"], d["f2"], 1 - d["f3"]])


def test_polish_is_deterministic_and_rejects_bad_mode():
    cfg = polish_cfg(5, 16, 10)
    inst = load_instance("C102", 25, cfg)
    a, b = nsga2.run(inst, cfg, 9), nsga2.run(inst, cfg, 9)
    assert a["pop"] == b["pop"] and np.array_equal(a["F"], b["F"]) and np.array_equal(a["front"], b["front"])
    assert np.array_equal(a["W"], b["W"], equal_nan=True)
    cfg["improvements"]["dp_split_params"]["mode"] = "nope"
    with pytest.raises(ValueError):
        nsga2.run(inst, cfg, 0)


# ---------------------------------------------------------------- polish + diversity (archive của TV3)
def _dominates_weakly(Fq, CVq, Fp, CVp):
    """q trội yếu p theo luật ràng buộc: CV nhỏ hơn, hoặc CV bằng nhau và mọi mục tiêu không lớn hơn."""
    return (CVq < CVp) | ((CVq == CVp) & np.all(Fq <= Fp, axis=1))


def test_polish_on_diversity_archive():
    """Có diversity + archive thì kết quả của tiến hoá là archive, và polish chạy trên archive đó."""
    cfg_pol = make_cfg(6, n_pop=16, dp_split=True, diversity=True, dp_mode="polish")
    cfg_div = make_cfg(6, n_pop=16, diversity=True)            # cùng diversity, không dp_split
    assert cfg_pol["improvements"]["diversity_params"]["archive"] is True
    k = cfg_pol["improvements"]["dp_split_params"]["polish_k"]
    inst = load_instance("C102", 25, cfg_pol)
    a, b = nsga2.run(inst, cfg_pol, 3), nsga2.run(inst, cfg_pol, 3)
    plain = nsga2.run(inst, cfg_div, 3)
    # tất định
    assert a["pop"] == b["pop"] and np.array_equal(a["F"], b["F"]) and np.array_equal(a["CV"], b["CV"])
    assert np.array_equal(a["front"], b["front"]) and np.array_equal(a["W"], b["W"], equal_nan=True)
    # polish không đụng tới tiến hoá: archive trước polish == kết quả chạy diversity thuần cùng seed
    pre = a["pre_polish"]
    assert pre["pop"] == plain["pop"] and np.array_equal(pre["F"], plain["F"])
    assert a["dp_mode"] == "polish" and a["n_dp_calls"] == len(pre["pop"]) * k
    assert a["n_evals"] == plain["n_evals"] + len(pre["pop"]) * k
    # front sau polish trội yếu archive trước polish: mọi điểm cũ bị một điểm front mới trội yếu (hoặc trùng)
    Fn, Cn = a["F"][a["front"]], a["CV"][a["front"]]
    for Fp, Cp in zip(pre["F"], pre["CV"]):
        assert np.any(_dominates_weakly(Fn, Cn, Fp[None, :], Cp)), (Fp, Cp)
    # các điểm front mới đều là điểm không trội trong tập đã polish
    assert len(a["front"]) >= 1 and a["feasible_frac_front"] >= 0.0
