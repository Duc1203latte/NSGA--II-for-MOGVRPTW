"""Bảng kết quả giai đoạn 2 của TV4: cấu hình x instance.

Đọc (1) per_run.csv do `python -m src.runner analyze` ghi (HV, IGD, SP, n_evals, runtime theo seed)
và (2) các file seed_XX.pkl thô (feasible_frac_front, số xe trên front cuối, chấm lại để kiểm).
p-value: Wilcoxon rank-sum (scipy.stats.ranksums, hai phía) của từng cấu hình so với baseline.

Chạy:  python -m scripts.tv4_report --exp tv4_main --instances C102-25 R201-50 [--out results/tv4_main/table.md]
Phải chạy `python -m src.runner analyze --exp tv4_main --instance <tên>` trước cho từng instance.
"""
from __future__ import annotations
import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.stats import ranksums

from src.decoder import evaluate_detail
from src.improvements.dp_split import evaluate_dp, objective_scales
from src.instance import ROOT, load_config, load_instance
from src.runner import results_root

CONFIG_ORDER = ["baseline", "dp", "adapt", "both"]
SERIAL_SLOWDOWN = "~9x ở n=25, ~24x ở n=50, ~28x ở n=100"   # đo ở lượt chạy thử, chạy tuần tự

NOTE_RUNTIME = (
    "Thời gian chạy đo khi 8 tiến trình chạy song song, chỉ so được với nhau trong bảng này. "
    "Chi phí tham chiếu của dp_split khi chạy tuần tự (lượt chạy thử, 20 thế hệ): "
    f"{SERIAL_SLOWDOWN} so với baseline."
)
NOTE_REF = (
    "HV và IGD chỉ so được giữa các cấu hình trong CÙNG bảng: `analyze` gộp front của mọi cấu hình "
    "trên một instance thành một reference set và một cận chuẩn hoá. Thêm hoặc bớt một cấu hình "
    "thì reference set đổi, mọi con số HV/IGD đổi theo."
)


def fmt(mean: float, std: float, nd: int = 4) -> str:
    return f"{mean:.{nd}f} ± {std:.{nd}f}"


def pstr(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def load_seed_files(exp_dir: Path, config: str) -> list[dict]:
    out = []
    for path in sorted((exp_dir / config).glob("seed_*.pkl")):
        with open(path, "rb") as f:
            out.append(pickle.load(f))
    return out


def front_vehicles(res: dict, inst, cfg: dict) -> float:
    """Số xe trung bình của các cá thể trên front cuối, chấm lại bằng đúng evaluator đã dùng khi chạy.
    Đồng thời kiểm lại F đã lưu: lệch thì báo lỗi."""
    use_dp = cfg["improvements"]["dp_split"]
    scales = objective_scales(inst, cfg["improvements"]["dp_split_params"]["g3_scale"]) if use_dp else None
    counts = []
    for i in res["front"]:
        perm = res["pop"][i]
        d = evaluate_dp(perm, inst, res["W"][i], scales) if use_dp else evaluate_detail(perm, inst)
        if not np.array_equal(res["F"][i], [d["f1"], d["f2"], 1 - d["f3"]]):
            raise AssertionError(f"seed {res['seed']}: F chấm lại khác F đã lưu")
        counts.append(d["n_vehicles"])
    return float(np.mean(counts))


def instance_rows(exp: str, inst_name: str) -> list[dict]:
    exp_dir = results_root(load_config()) / exp / inst_name
    per_run = pd.read_csv(exp_dir / "per_run.csv")
    name, n = inst_name.rsplit("-", 1)
    base = per_run[per_run.config == "baseline"]
    rows = []
    for config in [c for c in CONFIG_ORDER if c in set(per_run.config)]:
        pr = per_run[per_run.config == config].sort_values("seed")
        with open(exp_dir / config / "config_used.yaml", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        inst = load_instance(name, int(n), cfg)
        runs = load_seed_files(exp_dir, config)
        assert [r["seed"] for r in runs] == pr.seed.tolist()
        row = {
            "instance": inst_name, "config": config, "n_runs": len(pr),
            "HV": fmt(pr.HV.mean(), pr.HV.std()), "IGD": fmt(pr.IGD.mean(), pr.IGD.std()),
            "SP": fmt(pr.SP.mean(), pr.SP.std()),
            "n_evals": f"{pr.n_evals.mean():.0f}", "runtime_s": f"{pr.runtime_s.mean():.1f}",
            "feas_front": f"{np.mean([r['feasible_frac_front'] for r in runs]):.2f}",
            "feas_pop": f"{np.mean([r['feasible_frac_pop'] for r in runs]):.2f}",
            "vehicles": f"{np.mean([front_vehicles(r, inst, cfg) for r in runs]):.1f}",
            "front_size": f"{pr.n_points.mean():.1f}",
            "dHV": "—", "p_HV": "—", "p_IGD": "—",
        }
        if config != "baseline":
            row["dHV"] = f"{pr.HV.mean() - base.HV.mean():+.4f}"
            row["p_HV"] = pstr(ranksums(pr.HV, base.HV).pvalue)
            row["p_IGD"] = pstr(ranksums(pr.IGD, base.IGD).pvalue)
        rows.append(row)
    # đối chiếu p-value HV với bảng so cặp của runner
    pw = pd.read_csv(exp_dir / "pairwise.csv")
    for r in rows[1:]:
        m = pw[(pw.A == "baseline") & (pw.B == r["config"])]
        if len(m):
            assert pstr(float(m.p_HV.iloc[0])) == r["p_HV"], "p_HV khác bảng so cặp của runner"
    return rows


COLS = [("instance", "Instance"), ("config", "Cấu hình"), ("HV", "HV"), ("dHV", "ΔHV vs baseline"),
        ("p_HV", "p (HV)"), ("IGD", "IGD"), ("p_IGD", "p (IGD)"), ("SP", "SP"),
        ("n_evals", "n_evals"), ("runtime_s", "Thời gian/run (s)"),
        ("feas_front", "Khả thi (front)"), ("feas_pop", "Khả thi (quần thể)"),
        ("vehicles", "Số xe TB (front)"), ("front_size", "Số điểm front")]


def to_markdown(rows: list[dict]) -> str:
    head = "| " + " | ".join(h for _, h in COLS) + " |"
    sep = "|" + "|".join("---" for _ in COLS) + "|"
    body = ["| " + " | ".join(str(r[k]) for k, _ in COLS) + " |" for r in rows]
    return "\n".join([head, sep, *body])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--instances", nargs="+", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    rows = [r for inst in args.instances for r in instance_rows(args.exp, inst)]
    n_runs = sorted({r["n_runs"] for r in rows})
    text = (to_markdown(rows) + "\n\n"
            f"Mỗi ô: trung bình ± độ lệch chuẩn qua {n_runs} run (cùng bộ seed cho mọi cấu hình). "
            "p-value: Wilcoxon rank-sum hai phía so với baseline cùng instance; chưa hiệu chỉnh đa so sánh.\n\n"
            f"- {NOTE_RUNTIME}\n- {NOTE_REF}\n")
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
