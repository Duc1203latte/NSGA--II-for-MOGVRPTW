"""Test script vẽ TV2 trên dữ liệu ĐỒ CHƠI tự sinh trong thư mục tạm (không phải kết quả thật)."""
import csv

import numpy as np
import pytest

from scripts.plot_tv2_results import plot_all, read_csv, REQ_RUNS


def make_toy(root):
    run_dir = root / "results" / "tv2" / "toy"
    (run_dir / "runs").mkdir(parents=True)
    rng = np.random.default_rng(0)
    runs, hist = [], []
    for v in ("off", "init_only", "ls_only", "both"):
        for s in range(3):
            F = rng.random((10, 3)) * [1000, 100, 1]
            p = run_dir / "runs" / f"toy__{v}__s{s}.npz"
            np.savez(p, F=F, front_mask=np.ones(10, bool))
            runs.append({"instance": "TOY-5", "variant": v, "seed": s, "hv": rng.random(),
                         "igd": rng.random(), "npz": str(p.relative_to(root))})
            for g in range(5):
                hist.append({"instance": "TOY-5", "variant": v, "seed": s, "gen": g, "hv": g / 5})
    for name, rows in (("runs.csv", runs), ("hv_history.csv", hist)):
        with open(run_dir / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    return run_dir


def test_plot_all_creates_three_figures(tmp_path):
    run_dir = make_toy(tmp_path)
    out = plot_all(tmp_path, run_dir, tmp_path / "fig", 0, ["png"])
    names = sorted(p.name for p in out)
    assert names == ["box_hv_igd_TOY-5.png", "hv_convergence_TOY-5.png", "pareto3d_TOY-5_s0.png"]
    assert all(p.stat().st_size > 1000 for p in out)


def test_missing_columns_rejected(tmp_path):
    p = tmp_path / "runs.csv"
    p.write_text("instance,variant\nA,off\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_csv(p, REQ_RUNS)
    with pytest.raises(FileNotFoundError):
        read_csv(tmp_path / "nope.csv", REQ_RUNS)
