"""Kiểm tra local search TV2 + dp_split TV4 (chạy SAU khi merge feat/dp-split).

    python -m scripts.tv2_dp_compat_check

Kiểm tra: evaluator DP nhận đúng metadata (cùng object, cùng trọng số) ở mọi lần chấm; detail LS trả
về == evaluate_dp chấm lại; hoán vị hợp lệ; không làm nghiệm feasible (fleet_ok) thành infeasible;
in thời gian mỗi lần gọi LS. Chưa có dp_split -> in BLOCKED và trả mã 2.
"""

from __future__ import annotations

import copy
import time

import numpy as np

from src.decoder import evaluate_detail
from src.improvements.tv2_hooks import LocalSearchHook
from src.instance import load_config, load_instance


def main() -> int:
    try:
        from src.improvements.dp_split import evaluate_dp, objective_scales, sample_weights
    except ImportError:
        print("BLOCKED: src/improvements/dp_split.py chưa có evaluate_dp (chưa merge feat/dp-split)")
        return 2
    cfg = load_config()
    imp = copy.deepcopy(cfg["improvements"])
    if "dp_split_params" not in imp:
        print("BLOCKED: config chưa có improvements.dp_split_params")
        return 2
    imp["local_search"] = True
    imp["dp_split"] = True
    imp["local_search_params"]["p_ls"] = 1.0
    for name, n in [("C102", 25), ("R201", 50), ("RC201", 100)]:
        inst = load_instance(name, n)
        sc = objective_scales(inst)
        calls = []

        def ev(p, m):
            calls.append(m)
            return evaluate_dp(p, inst, m["dp_weights"], sc)

        hook = LocalSearchHook.from_config(imp, inst, ev,
                                           baseline_detail_fn=lambda p: evaluate_detail(p, inst))
        assert hook.require_same_routes is False
        rng = np.random.default_rng(0)
        t = time.perf_counter()
        worsened = 0
        for _ in range(20):
            perm = rng.permutation(np.arange(1, n + 1)).tolist()
            meta = {"dp_weights": sample_weights(rng, imp["dp_split_params"])}
            w0 = meta["dp_weights"].copy()
            calls.clear()
            out, d = hook(perm, rng, meta)
            fresh = evaluate_dp(out, inst, w0, sc)
            assert all(m is meta for m in calls) and np.array_equal(meta["dp_weights"], w0)
            assert d["routes"] == fresh["routes"] and d["f1"] == fresh["f1"]
            assert np.array_equal(d["weights"], w0) and sorted(out) == list(range(1, n + 1))
            if evaluate_dp(perm, inst, w0, sc)["fleet_ok"] and not d["fleet_ok"]:
                worsened += 1
        dt = (time.perf_counter() - t) / 20
        c = hook.counters
        print(f"{inst.name}: 20 LS OK, accepted={c.n_ls_accepted}, candidates={c.n_ls_candidate_evals}, "
              f"real_evals={c.n_real_model_evals}, fleet_worsened={worsened}, {dt * 1000:.0f} ms/LS")
        assert worsened == 0
    print("DP+LS compatibility: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
