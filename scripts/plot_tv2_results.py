"""Biểu đồ TV2 (giai đoạn 4) từ đầu ra của scripts/run_tv2_experiments.py.

    python -m scripts.plot_tv2_results --tag main_gen200 [--seed 0] [--fmt png,pdf]

Đọc results/tv2/<tag>/{runs.csv, hv_history.csv, runs/*.npz}, ghi vào results/figures/tv2/<tag>/:
    pareto3d_<instance>_s<seed>.png   front không bị trội của từng cấu hình, đơn vị gốc (f3 = MAX)
    hv_convergence_<instance>.png     HV front 1 theo generation, mean ± std qua các seed
    box_hv_igd_<instance>.png         boxplot HV và IGD qua các seed
Không tạo số liệu giả: thiếu cột/thiếu file thì báo lỗi rõ ràng.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

# Thứ tự cố định; màu đi theo cấu hình, không theo thứ hạng. Đã kiểm tra bằng validator CVD.
ORDER = ["off", "init_only", "ls_only", "both"]
COLORS = {"off": "#2a78d6", "init_only": "#eb6834", "ls_only": "#1baf7a", "both": "#eda100"}
MARKERS = {"off": "o", "init_only": "s", "ls_only": "^", "both": "D"}   # mã hoá phụ (không chỉ màu)
LABELS = {"off": "baseline", "init_only": "init_smart", "ls_only": "local_search",
          "both": "init_smart + local_search"}
EXTRA = ["#e87ba4", "#008300", "#7a5cd6", "#8a6d3b", "#555555"]

REQ_RUNS = {"instance", "variant", "seed", "hv", "igd", "npz"}
REQ_HIST = {"instance", "variant", "seed", "gen", "hv"}


def read_csv(path: Path, required: set[str]) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"thiếu {path}")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    if not rows:
        raise ValueError(f"{path} rỗng")
    miss = required - set(rows[0])
    if miss:
        raise ValueError(f"{path} thiếu cột {sorted(miss)}")
    return rows


def style(variants: list[str]):
    ordered = [v for v in ORDER if v in variants] + sorted(v for v in variants if v not in ORDER)
    out, k = {}, 0
    for v in ordered:
        if v in COLORS:
            out[v] = (COLORS[v], MARKERS[v], LABELS[v])
        else:
            out[v] = (EXTRA[k % len(EXTRA)], "x", v)
            k += 1
    return ordered, out


def _nondominated(F):
    F = np.unique(F, axis=0)
    keep = [i for i in range(len(F))
            if not np.any(np.all(F <= F[i], axis=1) & np.any(F < F[i], axis=1))]
    return F[keep]


def _setup_ax(ax):
    ax.grid(True, color="#e4e3df", linewidth=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def plot_all(root: Path, run_dir: Path, fig_dir: Path, seed: int, fmts: list[str]) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    runs = read_csv(run_dir / "runs.csv", REQ_RUNS)
    hist = read_csv(run_dir / "hv_history.csv", REQ_HIST)
    fig_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def save(fig, name):
        for f in fmts:
            p = fig_dir / f"{name}.{f}"
            fig.savefig(p, dpi=160, bbox_inches="tight")
            written.append(p)
        plt.close(fig)

    insts = sorted({r["instance"] for r in runs})
    for inst in insts:
        rs = [r for r in runs if r["instance"] == inst]
        order, st = style(sorted({r["variant"] for r in rs}))
        n_seeds = len({r["seed"] for r in rs})

        # ---- Pareto 3D, đơn vị gốc
        fig = plt.figure(figsize=(7.5, 6))
        ax = fig.add_subplot(projection="3d")
        for v in order:
            match = [r for r in rs if r["variant"] == v and int(r["seed"]) == seed]
            if not match:
                continue
            d = np.load(root / match[0]["npz"])
            F = _nondominated(d["F"][d["front_mask"]])
            c, m, lab = st[v]
            ax.scatter(F[:, 0], F[:, 1], 1.0 - F[:, 2], color=c, marker=m, s=28,
                       edgecolors="white", linewidths=0.6, label=f"{lab} ({len(F)})")
        ax.set_xlabel("f1 chi phí (CNY) ↓")
        ax.set_ylabel("f2 CO₂ (kg) ↓")
        ax.set_zlabel("f3 hài lòng ↑")
        ax.set_title(f"{inst}: front không bị trội cuối, seed {seed}", fontsize=11)
        ax.legend(loc="upper left", fontsize=8, frameon=False)
        save(fig, f"pareto3d_{inst}_s{seed}")

        # ---- HV hội tụ
        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        for v in order:
            by_seed = defaultdict(dict)
            for h in hist:
                if h["instance"] == inst and h["variant"] == v:
                    by_seed[h["seed"]][int(h["gen"])] = float(h["hv"])
            if not by_seed:
                continue
            G = min(max(s) for s in by_seed.values()) + 1        # chung độ dài mọi seed
            M = np.array([[s[g] for g in range(G)] for s in by_seed.values()])
            mu, sd = M.mean(axis=0), M.std(axis=0, ddof=1) if len(M) > 1 else np.zeros(G)
            c, m, lab = st[v]
            x = np.arange(G)
            ax.plot(x, mu, color=c, linewidth=2, label=f"{lab}")
            ax.fill_between(x, mu - sd, mu + sd, color=c, alpha=0.15, linewidth=0)
            ax.plot(x[-1], mu[-1], marker=m, color=c, markersize=8, markeredgecolor="white")
        ax.set_xlabel("generation")
        ax.set_ylabel("HV front 1 (chuẩn hoá theo reference set chung)")
        ax.set_title(f"{inst}: HV theo generation, trung bình ± độ lệch chuẩn, {n_seeds} seed",
                     fontsize=11)
        _setup_ax(ax)
        ax.legend(fontsize=8, frameon=False)
        save(fig, f"hv_convergence_{inst}")

        # ---- Boxplot HV / IGD
        fig, axes = plt.subplots(1, 2, figsize=(9, 4))
        for ax, metric, arrow in ((axes[0], "hv", "↑"), (axes[1], "igd", "↓")):
            data = [[float(r[metric]) for r in rs if r["variant"] == v] for v in order]
            bp = ax.boxplot(data, patch_artist=True, widths=0.55,
                            medianprops={"color": "#1a1a19", "linewidth": 1.5})
            for patch, v in zip(bp["boxes"], order):
                patch.set_facecolor(st[v][0])
                patch.set_alpha(0.55)
                patch.set_edgecolor(st[v][0])
            for k, (vals, v) in enumerate(zip(data, order), 1):
                ax.scatter(np.full(len(vals), k), vals, color=st[v][0], marker=st[v][1], s=16,
                           edgecolors="white", linewidths=0.5, zorder=3)
            ax.set_xticks(range(1, len(order) + 1))
            ax.set_xticklabels([st[v][2].replace(" + ", "\n+ ") for v in order], fontsize=8)
            ax.set_title(f"{metric.upper()} {arrow}", fontsize=10)
            _setup_ax(ax)
        fig.suptitle(f"{inst}: {n_seeds} seed mỗi cấu hình", fontsize=11)
        save(fig, f"box_hv_igd_{inst}")
    return written


def main() -> int:
    from src.instance import ROOT, load_config
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--fmt", default="png")
    args = ap.parse_args()
    res = ROOT / load_config()["experiment"]["results_dir"]
    out = plot_all(ROOT, res / "tv2" / args.tag, res / "figures" / "tv2" / args.tag, args.seed,
                   args.fmt.split(","))
    for p in out:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
