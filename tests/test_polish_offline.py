"""Polish ngoại tuyến (scripts/tv4_polish_offline.py) phải khớp từng bit với polish trực tuyến của nsga2.run."""
import copy

import numpy as np
import pytest

from scripts.tv4_polish_offline import polish_result, same_result
from src import nsga2
from src.instance import load_config, load_instance


def cfg_for(k, polish):
    cfg = copy.deepcopy(load_config())
    cfg["nsga2"].update(n_gen=6, n_pop=20)
    if polish:
        cfg["improvements"]["dp_split"] = True
        cfg["improvements"]["dp_split_params"].update(mode="polish", polish_k=k)
    return cfg


@pytest.mark.parametrize("name,n,k", [("C102", 25, 10), ("R201", 50, 30)])
def test_offline_polish_matches_online(name, n, k):
    base_cfg, pol_cfg = cfg_for(k, False), cfg_for(k, True)
    inst = load_instance(name, n, base_cfg)
    base = nsga2.run(inst, base_cfg, 3)          # run baseline, quần thể cuối đã lưu
    online = nsga2.run(inst, pol_cfg, 3)         # run mode=polish cùng seed
    assert base["pop"] == online["pre_polish"]["pop"]
    offline = polish_result(base, inst, pol_cfg["improvements"]["dp_split_params"])
    assert same_result(offline, online) == []
    assert offline["n_evals"] == base["n_evals"] + 20 * k and offline["n_dp_calls"] == 20 * k
    assert offline["dp_mode"] == "polish" and offline["polish_cpu_s"] >= 0
    assert np.array_equal(offline["pre_polish"]["F"], base["F"])
    assert base["pop"] == [x for x in base["pop"]]                      # polish không sửa kết quả gốc


def test_same_result_detects_differences():
    cfg = cfg_for(10, True)
    inst = load_instance("C102", 25, cfg)
    a = nsga2.run(inst, cfg, 1)
    b = dict(a, F=a["F"] + 1e-12)
    assert same_result(a, a) == [] and "F" in same_result(a, b)
