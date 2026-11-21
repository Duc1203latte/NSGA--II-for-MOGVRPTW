"""Test runner: ghi đè config, chạy rồi phân tích trên một thí nghiệm rất nhỏ.

Chạy: pytest tests/test_runner.py -v
"""
import pytest
import yaml

from src.instance import load_config, load_instance
from src.runner import analyze, apply_overrides, run_config


# =========================================================================== ghi đè config

def test_apply_overrides_types_and_nesting():
    cfg = apply_overrides(load_config(), [
        "nsga2.crossover=obx", "nsga2.pc=0.9", "nsga2.eliminate_duplicates=false",
        "satisfaction_time=service_start",
    ])
    assert cfg["nsga2"]["crossover"] == "obx"
    assert cfg["nsga2"]["pc"] == 0.9                      # đọc ra số, không phải chuỗi "0.9"
    assert cfg["nsga2"]["eliminate_duplicates"] is False  # đọc ra bool
    assert cfg["satisfaction_time"] == "service_start"


def test_apply_overrides_does_not_touch_original():
    base = load_config()
    apply_overrides(base, ["nsga2.crossover=obx"])
    assert base["nsga2"]["crossover"] == load_config()["nsga2"]["crossover"]


@pytest.mark.parametrize("bad", ["nsga2.crosover=obx", "khong_co=1", "nsga2.pm.solomon.x=1", "thieu_dau_bang"])
def test_apply_overrides_rejects_bad_input(bad):
    with pytest.raises((KeyError, ValueError)):
        apply_overrides(load_config(), [bad])


def test_load_instance_uses_given_config():
    cfg = apply_overrides(load_config(), ["satisfaction_time=service_start", "split_rule=capacity"])
    inst = load_instance("C102", 25, cfg)
    assert inst.params["satisfaction_time"] == "service_start"
    assert inst.params["split_rule"] == "capacity"
    assert load_instance("C102", 25).params["satisfaction_time"] == "arrival"   # không truyền cfg thì như cũ


# =========================================================================== chạy và phân tích

def tiny_config(tmp_path, *extra):
    return apply_overrides(load_config(), [
        "nsga2.n_pop=10", "nsga2.n_gen=3", f"experiment.results_dir={tmp_path.as_posix()}", *extra,
    ])


def test_run_then_analyze(tmp_path):
    seeds = [0, 1]
    run_config("thu", "a", "C102", 25, tiny_config(tmp_path), seeds)
    out_dir = run_config("thu", "b", "C102", 25, tiny_config(tmp_path, "nsga2.crossover=obx"), seeds)

    assert sorted(p.name for p in out_dir.glob("seed_*.pkl")) == ["seed_00.pkl", "seed_01.pkl"]
    used = yaml.safe_load((out_dir / "config_used.yaml").read_text(encoding="utf-8"))
    assert used["nsga2"]["crossover"] == "obx"            # lưu lại đúng config đã dùng

    out = analyze("thu", "C102-25", tiny_config(tmp_path))
    assert len(out["per_run"]) == 4                       # 2 cấu hình × 2 seed
    assert set(out["summary"].index) == {"a", "b"}
    assert len(out["pairwise"]) == 1
    assert len(out["convergence"]) == 3 + 1               # n_gen + 1 thế hệ
    for name in ("per_run", "summary", "pairwise", "convergence"):
        assert (tmp_path / "thu" / "C102-25" / f"{name}.csv").exists()


def test_run_skips_existing_seeds(tmp_path, capsys):
    cfg = tiny_config(tmp_path)
    run_config("thu", "a", "C102", 25, cfg, [0])
    run_config("thu", "a", "C102", 25, cfg, [0])
    assert "bỏ qua" in capsys.readouterr().out


def test_analyze_refuses_to_mix_different_problems(tmp_path):
    run_config("tron", "a", "C102", 25, tiny_config(tmp_path), [0])
    run_config("tron", "b", "C102", 25, tiny_config(tmp_path, "satisfaction_time=service_start"), [0])
    with pytest.raises(ValueError, match="hai bài toán khác nhau"):
        analyze("tron", "C102-25", tiny_config(tmp_path))


def test_analyze_allows_different_split_rules(tmp_path):
    # split_rule thuộc thuật toán, không phải bài toán: so sánh được
    run_config("cat", "a", "C102", 25, tiny_config(tmp_path), [0])
    run_config("cat", "b", "C102", 25, tiny_config(tmp_path, "split_rule=capacity"), [0])
    assert len(analyze("cat", "C102-25", tiny_config(tmp_path))["pairwise"]) == 1
