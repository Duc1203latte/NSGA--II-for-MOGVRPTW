"""Chẩn đoán cho TV4 (chỉ đọc kết quả thô, không đổi thuật toán).

  1. adaptive_rates: front1_fraction, pc, pm trung bình theo thế hệ; số thế hệ rơi vào nhánh
     "một front" (front1_fraction >= single_front_threshold); pc/pm hiệu dụng so với pc/pm cố định
     của baseline. Vẽ hình docs/tv4_adaptive_rates.png.
  2. Cực trị theo mục tiêu trên front cuối (f1 nhỏ nhất, f2 nhỏ nhất, f3 lớn nhất) và trung bình
     f1/f2/f3 của front, kiểu Bảng 6-7 của bài báo; set coverage SC giữa các cấu hình cùng seed.

Chạy:  python -m scripts.tv4_diagnose --exp tv4_main --instances C102-25 R201-50
Ghi:   results/<exp>/diagnose_adaptive.md, results/<exp>/diagnose_extremes.md, docs/tv4_adaptive_rates.png
"""
from __future__ import annotations
import argparse
import pickle
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml

from src.instance import ROOT, load_config
from src.metrics import sc
from src.runner import results_root

ORDER = ["baseline", "baseline_eqtime", "dp", "adapt", "both"]


def load(exp_dir: Path, config: str) -> list[dict]:
    out = []
    for p in sorted((exp_dir / config).glob("seed_*.pkl")):
        with open(p, "rb") as f:
            out.append(pickle.load(f))
    return out


def configs_present(exp_dir: Path) -> list[str]:
    have = {p.name for p in exp_dir.iterdir() if p.is_dir()}
    return [c for c in ORDER if c in have]


def front(res: dict) -> np.ndarray:
    return res["F"][res["front"]]


def ms(x, nd=3) -> str:
    x = np.asarray(x, float)
    return f"{x.mean():.{nd}f} ± {x.std(ddof=1):.{nd}f}"


# ---------------------------------------------------------------- 1. adaptive rates
def front1_fraction_curve(res: dict, n_pop: int) -> np.ndarray:
    """|front 1| / n_pop ở từng thế hệ, lấy từ history (history[g] = front 1 của thế hệ g)."""
    return np.array([len(h) for h in res["history"][:-1]]) / n_pop


def adaptive_section(exp: str, instances: list[str], threshold: float, base_pc: float, base_pm: dict,
                     fig_path: Path) -> str:
    cfg = load_config()
    n_pop = cfg["nsga2"]["n_pop"]
    fig, axes = plt.subplots(len(instances), 3, figsize=(13, 3.6 * len(instances)), squeeze=False)
    lines = ["| Instance | Cấu hình | front1_fraction TB | Thế hệ ở nhánh một-front | pc hiệu dụng | "
             "pm hiệu dụng | pc / pm ở thế hệ theo hạng | pc / pm ở thế hệ một-front |",
             "|---|---|---|---|---|---|---|---|"]
    for row, inst in enumerate(instances):
        exp_dir = results_root(cfg) / exp / inst
        pm0 = base_pm["case29" if inst.startswith("case29") else "solomon"]
        for config in [c for c in ("baseline", "dp", "adapt", "both") if (exp_dir / c).is_dir()]:
            runs = load(exp_dir, config)
            curve = np.mean([front1_fraction_curve(r, n_pop) for r in runs], axis=0)
            axes[row, 0].plot(curve, label=config, lw=1.2)
            if config in ("adapt", "both"):
                pcs = np.mean([[np.mean(g["pc"]) for g in r["rate_log"]] for r in runs], axis=0)
                pms = np.mean([[np.mean(g["pm"]) for g in r["rate_log"]] for r in runs], axis=0)
                axes[row, 1].plot(pcs, label=config, lw=1.2)
                axes[row, 2].plot(pms, label=config, lw=1.2)
                fr = np.array([[g["front1_fraction"] for g in r["rate_log"]] for r in runs])
                pc_all = np.array([[np.mean(g["pc"]) for g in r["rate_log"]] for r in runs])
                pm_all = np.array([[np.mean(g["pm"]) for g in r["rate_log"]] for r in runs])
                single = fr >= threshold
                def part(a, m):
                    return f"{a[m].mean():.3f}" if m.any() else "—"
                lines.append(
                    f"| {inst} | {config} | {fr.mean():.3f} | {single.mean() * 100:.1f}% | "
                    f"{pc_all.mean():.3f} | {pm_all.mean():.3f} | "
                    f"{part(pc_all, ~single)} / {part(pm_all, ~single)} | "
                    f"{part(pc_all, single)} / {part(pm_all, single)} |")
            else:
                fr = np.array([front1_fraction_curve(r, n_pop) for r in runs])
                lines.append(f"| {inst} | {config} | {fr.mean():.3f} | "
                             f"{(fr >= threshold).mean() * 100:.1f}% (chỉ để tham khảo, không dùng) | "
                             f"{base_pc:.3f} (cố định) | {pm0:.3f} (cố định) | — | — |")
        axes[row, 0].axhline(threshold, color="gray", ls="--", lw=0.8)
        axes[row, 1].axhline(base_pc, color="k", ls=":", lw=0.9, label="baseline")
        axes[row, 2].axhline(pm0, color="k", ls=":", lw=0.9, label="baseline")
        axes[row, 0].set_title(f"{inst}: front1_fraction (đường đứt = ngưỡng {threshold})")
        axes[row, 1].set_title(f"{inst}: pc trung bình mỗi thế hệ")
        axes[row, 2].set_title(f"{inst}: pm trung bình mỗi thế hệ")
        for ax in axes[row]:
            ax.set_xlabel("thế hệ")
            ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(fig_path, dpi=110)
    plt.close(fig)
    return "\n".join(lines)


# ---------------------------------------------------------------- 2. cực trị và coverage
def extremes_section(exp: str, instances: list[str]) -> str:
    cfg = load_config()
    head = ("| Instance | Cấu hình | f1 tốt nhất | f2 tốt nhất | f3 tốt nhất | f1 TB front | f2 TB front | "
            "f3 TB front |\n|---|---|---|---|---|---|---|---|")
    lines, cov = [head], []
    for inst in instances:
        exp_dir = results_root(cfg) / exp / inst
        runs = {c: load(exp_dir, c) for c in configs_present(exp_dir)}
        for c, rs in runs.items():
            fs = [front(r) * np.array([1, 1, -1]) + np.array([0, 0, 1]) for r in rs]   # cột 3 -> f3 thật
            best = lambda j, f: f(x[:, j].min() if f is min else x[:, j].max())  # noqa: E731
            f1b = [x[:, 0].min() for x in fs]
            f2b = [x[:, 1].min() for x in fs]
            f3b = [x[:, 2].max() for x in fs]
            lines.append(f"| {inst} | {c} | {ms(f1b, 1)} | {ms(f2b, 1)} | {ms(f3b, 4)} | "
                         f"{ms([x[:, 0].mean() for x in fs], 1)} | {ms([x[:, 1].mean() for x in fs], 1)} | "
                         f"{ms([x[:, 2].mean() for x in fs], 4)} |")
        # set coverage cùng seed: SC(A, B) = tỉ lệ điểm của B bị A trội
        pairs = [(c, "baseline") for c in ("dp", "adapt", "both", "baseline_eqtime") if c in runs]
        if "baseline_eqtime" in runs and "dp" in runs:
            pairs.append(("dp", "baseline_eqtime"))
        for a, b in pairs:
            fa = {r["seed"]: front(r) for r in runs[a]}
            fb = {r["seed"]: front(r) for r in runs[b]}
            seeds = sorted(fa.keys() & fb.keys())
            ab = [sc(fa[s], fb[s]) for s in seeds]
            ba = [sc(fb[s], fa[s]) for s in seeds]
            cov.append(f"| {inst} | {a} vs {b} | {ms(ab, 3)} | {ms(ba, 3)} | "
                       f"{sum(x > y for x, y in zip(ab, ba))} / {sum(x < y for x, y in zip(ab, ba))} / "
                       f"{sum(x == y for x, y in zip(ab, ba))} |")
    cov_head = ("| Instance | Cặp (A vs B) | SC(A, B): phần B bị A trội | SC(B, A): phần A bị B trội | "
                "Số seed A phủ nhiều hơn / ít hơn / bằng |\n|---|---|---|---|---|")
    return "\n".join(lines) + "\n\n" + cov_head + "\n" + "\n".join(cov)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--instances", nargs="+", required=True)
    args = ap.parse_args()
    cfg = load_config()
    ad = cfg["improvements"]["adaptive_params"]
    root = results_root(cfg) / args.exp
    fig = ROOT / "docs" / "tv4_adaptive_rates.png"
    a = adaptive_section(args.exp, args.instances, ad["single_front_threshold"], cfg["nsga2"]["pc"],
                         cfg["nsga2"]["pm"], fig)
    e = extremes_section(args.exp, args.instances)
    (root / "diagnose_adaptive.md").write_text(a + "\n", encoding="utf-8")
    (root / "diagnose_extremes.md").write_text(e + "\n", encoding="utf-8")
    print(a, "\n")
    print(e)
    print(f"\nHình: {fig.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
