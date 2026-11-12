"""Test tích hợp TV2 qua HARNESS NSGA-II tạm (scripts/tv2_harness.py).

Lưu ý: src/nsga2.py của TV1 chưa có (rỗng tại 5197d65). Các test này chứng minh hook TV2 đúng
hợp đồng trên một NSGA-II chuẩn; tích hợp vào nsga2.py thật vẫn là việc chờ TV1.
"""
import copy
import sys

import numpy as np
import pytest

from scripts import tv2_harness as H
from scripts.tv2_regression_snapshot import CASES, N_GEN, N_POP, all_off_cfg, load_fixture, snapshot
from src.decoder import evaluate_detail
from src.improvements.local_search import to_min_vector
from src.instance import load_config, load_instance

CFG = load_config()


def cfg_with(**flags):
    c = all_off_cfg()
    c["improvements"].update(flags)
    return c


def is_perm(p, n):
    return sorted(p) == list(range(1, n + 1))


# ------------------------------------------------------------------ mặc định & hồi quy all-off
def test_all_flags_default_off():
    imp = CFG["improvements"]
    for f in ("init_smart", "local_search", "diversity", "dp_split"):
        assert imp[f] is False, f
    assert "init_smart_params" in imp and "local_search_params" in imp


def test_alloff_regression_exact_vs_saved_snapshot():
    """Tắt hết cờ: hoán vị, mục tiêu (từng bit qua float.hex), số lần đánh giá và trạng thái RNG cuối
    trùng khớp mốc đã lưu (mốc được chụp khi các module TV2 bị chặn import)."""
    assert snapshot() == load_fixture()


def test_alloff_never_touches_tv2_modules(monkeypatch):
    """Chặn import module TV2: đường all-off vẫn chạy và ra đúng kết quả như khi không chặn."""
    inst = load_instance("C102", 25)
    ref = H.run(inst, all_off_cfg(), 3, n_pop=16, n_gen=4, record_history=False)
    for mod in ("src.improvements.tv2_hooks", "src.improvements.init_smart"):
        monkeypatch.setitem(sys.modules, mod, None)
    got = H.run(inst, all_off_cfg(), 3, n_pop=16, n_gen=4, record_history=False)
    assert got.perms == ref.perms and np.array_equal(got.F, ref.F)
    assert got.rng_state_end == ref.rng_state_end and got.n_evals == ref.n_evals


def test_flags_on_with_zero_effect_still_isolated():
    """ls bật nhưng p_ls = 0: mỗi con tiêu thụ đúng 1 lần rng.random() nên dãy RNG KHÁC baseline
    (đúng như thiết kế: chỉ đường cờ TẮT mới phải trùng baseline)."""
    inst = load_instance("C102", 25)
    c = cfg_with(local_search=True)
    c["improvements"]["local_search_params"] = {**c["improvements"]["local_search_params"], "p_ls": 0.0}
    a = H.run(inst, c, 0, n_pop=16, n_gen=3, record_history=False)
    b = H.run(inst, all_off_cfg(), 0, n_pop=16, n_gen=3, record_history=False)
    assert a.ls_counters["n_ls_triggered"] == 0 and a.ls_counters["n_ls_calls"] == 16 * 3
    assert a.n_evals == b.n_evals                       # không có đánh giá thừa
    assert a.rng_state_end != b.rng_state_end


# ------------------------------------------------------------------ 4 cấu hình
CONFIGS = {
    "off": {},
    "init_only": {"init_smart": True},
    "ls_only": {"local_search": True},
    "both": {"init_smart": True, "local_search": True},
}


@pytest.mark.parametrize("name,n", CASES)
@pytest.mark.parametrize("label", list(CONFIGS))
def test_configs_valid_exact_and_reproducible(name, n, label):
    inst = load_instance(name, n)
    c = cfg_with(**CONFIGS[label])
    r1 = H.run(inst, c, 1, n_pop=20, n_gen=4)
    r2 = H.run(inst, c, 1, n_pop=20, n_gen=4)
    assert r1.perms == r2.perms and np.array_equal(r1.F, r2.F) and r1.rng_state_end == r2.rng_state_end
    assert len(r1.perms) == 20 and all(is_perm(p, n) for p in r1.perms)
    # mục tiêu NSGA-II dùng == chấm lại độc lập bằng decoder (kể cả con đi qua LS)
    for p, row in zip(r1.perms, r1.F):
        assert np.array_equal(row, to_min_vector(evaluate_detail(p, inst)))
    if "init_smart" in CONFIGS[label]:
        assert r1.init_sources[:4] == ["nn"] * 4 and r1.init_sources[4:8] == ["tw"] * 4
    else:
        assert set(r1.init_sources) == {"random"}
    if "local_search" in CONFIGS[label]:
        lc = r1.ls_counters
        assert lc["n_ls_calls"] == 20 * 4 and lc["n_ls_triggered"] > 0
        # kế toán đánh giá chính xác: mỗi lần LS chạy, lần chấm nghiệm ban đầu thay cho lần chấm
        # chính thức của con, nên tổng = n_pop*(gen+1) + real_evals_LS - triggered
        assert r1.n_evals == 20 * 5 + lc["n_real_model_evals"] - lc["n_ls_triggered"]
        assert lc["n_evals_total"] == r1.n_evals
    else:
        assert r1.ls_counters == {} and r1.n_evals == 20 * 5


def test_init_only_changes_only_initial_population_source():
    inst = load_instance("R201", 50)
    a = H.run(inst, cfg_with(init_smart=True), 0, n_pop=20, n_gen=0)
    b = H.run(inst, all_off_cfg(), 0, n_pop=20, n_gen=0)
    assert a.init_sources != b.init_sources
    assert a.n_evals == b.n_evals == 20


def test_ls_child_detail_matches_official_evaluation():
    """Detail mà hook trả về và NSGA-II dùng lại phải bằng đúng lần chấm chính thức."""
    from src.improvements.tv2_hooks import LocalSearchHook
    inst = load_instance("RC201", 100)
    imp = copy.deepcopy(cfg_with(local_search=True)["improvements"])
    imp["local_search_params"]["p_ls"] = 1.0
    hook = LocalSearchHook.from_config(imp, inst, lambda p, m: evaluate_detail(p, inst))
    rng = np.random.default_rng(0)
    parent = rng.permutation(np.arange(1, 101)).tolist()
    snap = list(parent)
    for _ in range(5):
        child, d = hook(parent, rng)
        assert parent == snap                                  # không sửa cha mẹ / đầu vào
        fresh = evaluate_detail(child, inst)
        assert d.keys() == fresh.keys()
        for k, v in fresh.items():
            if isinstance(v, np.ndarray):
                assert np.array_equal(d[k], v, equal_nan=True), k
            else:
                assert d[k] == v, k


# ------------------------------------------------------------------ chỉ số harness
def test_metrics_sanity():
    F = np.array([[0, 1, 0.5], [1, 0, 0.5], [0.5, 0.5, 0.5], [1, 1, 1]], float)
    nd = H.nondominated(F)
    assert len(nd) == 3
    norm = H.Normalizer(nd)
    Fn = norm(nd)
    assert Fn.min() == 0 and Fn.max() == 1
    assert H.hypervolume(Fn) > 0
    assert H.igd(Fn, Fn) == pytest.approx(0.0)
    assert H.hypervolume(np.array([[2.0, 2.0, 2.0]])) == 0.0
    assert H.spacing(np.array([[0, 0, 0]])) == 0.0
    # HV đơn điệu theo tập: thêm điểm không làm giảm
    assert H.hypervolume(Fn[:2]) <= H.hypervolume(Fn) + 1e-12


def test_nondominated_sort_matches_bruteforce():
    rng = np.random.default_rng(0)
    F = rng.random((40, 3))
    fronts = H.fast_non_dominated_sort(F)
    rank = np.empty(40, int)
    for r, idx in enumerate(fronts):
        rank[idx] = r
    for i in range(40):
        for j in range(40):
            if np.all(F[i] <= F[j]) and np.any(F[i] < F[j]):
                assert rank[i] < rank[j]
    assert sorted(np.concatenate(fronts).tolist()) == list(range(40))


def test_ox_and_inversion_keep_permutation():
    rng = np.random.default_rng(0)
    for n in (1, 2, 3, 10, 50):
        for _ in range(50):
            a, b = rng.permutation(np.arange(1, n + 1)).tolist(), rng.permutation(np.arange(1, n + 1)).tolist()
            c1, c2 = H.ox_crossover(a, b, rng)
            assert is_perm(c1, n) and is_perm(c2, n)
            assert is_perm(H.inversion_mutation(a, rng), n)
