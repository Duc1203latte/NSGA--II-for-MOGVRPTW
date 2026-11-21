"""Hinh cho slide phan TV4, chi dung ket qua da co (khong chay tien hoa).
  1 hv_vs_cpu.png            HV theo chi phi CPU tuong doi so voi dp
  2 polish_vs_extra_gens.png polish so voi thoi gian CPU tuong duong dung cho them the he
  3 front_f1_f2.png          front cuoi (f1, f2) cua mot seed dai dien
  4 split_rules.png          late_min / f1 / so xe duoi ba quy tac tach tuyen
Chay: python -m scripts.tv4_figures [--exp tv4_main] [--out docs/figures/tv4]
Mau co dinh theo cau hinh (xem COLOR) o moi hinh."""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scripts.tv4_report import DP_COST_RATIO, analyze_all, load_seed_files
from scripts.tv4_split_lateness import RULES, measure
from src.improvements.dp_split import objective_scales
from src.instance import load_config, load_instance
from src.metrics import evaluate_front
from src.runner import front_of, results_root

INSTANCES = ["C102-25", "R201-50"]
# mau co dinh theo cau hinh (lay tu bang mau tham chieu 8 slot: blue, orange, aqua, violet; da chay validate_palette.js)
COLOR = {"baseline": "#2a78d6", "dp": "#eb6834", "baseline_polish": "#1baf7a", "baseline_eqtime": "#6250d6"}
RULE_COLOR = {"capacity": "#8a8a85", "capacity_time": "#2a78d6", "dp": "#eb6834"}
RULE_LABEL = {"capacity": "capacity", "capacity_time": "capacity_time", "dp": "DP"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
DPI = 200


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 17, "axes.titlesize": 20, "axes.labelsize": 18,
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 16, "figure.facecolor": "white",
        "axes.facecolor": "white", "axes.edgecolor": INK2, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 1.0, "axes.axisbelow": True,
        "savefig.dpi": DPI, "savefig.bbox": "tight", "savefig.facecolor": "white"})


def load_inst(cfg, name):
    n_name, n = name.split("-")
    return load_instance(n_name, int(n), cfg)


class Data:
    """Doc mot lan: per_run, reference set, cac run da lap theo seed, chi phi mot the he baseline."""

    def __init__(self, exp, inst_name):
        cfg = load_config()
        self.cfg = cfg
        root = results_root(cfg)
        self.dir = root / exp / inst_name
        self.ref_point = cfg["metrics"]["hv_ref_point"]
        self.per_run, self.ref, self.bounds = analyze_all(self.dir, self.ref_point, with_ref=True)
        self.runs = {c: sorted(load_seed_files(self.dir, c), key=lambda r: r["seed"])
                     for c in ("baseline", "dp", "baseline_polish", "baseline_eqtime", "baseline_eqtime_polish")}
        cpu = pd.read_csv(root / "tv4_tune" / "cpu_cost.csv")
        row = cpu[(cpu.instance == inst_name) & (cpu.config == "baseline")]
        self.per_gen = float(row.cpu_s.iloc[0]) / cfg["nsga2"]["n_gen"]
        self.base_gen = cfg["nsga2"]["n_gen"]
        self.n_eq = len(self.runs["baseline_eqtime"][0]["history"]) - 1
        self.ratio = DP_COST_RATIO[inst_name]

    def hv(self, name):
        return self.per_run[self.per_run.config == name].sort_values("seed").HV.to_numpy()

    def hv_at(self, g):
        return np.array([evaluate_front(r["history"][g], self.ref, self.bounds, self.ref_point)["HV"]
                         for r in self.runs["baseline_eqtime"]])

    def polish_gens(self, name):
        return int(round(np.mean([r["polish_cpu_s"] for r in self.runs[name]]) / self.per_gen))

    def cpu(self, gens):
        """Chi phi CPU tuong doi so voi dp 200 the he (1 the he dp = ratio the he baseline)."""
        return gens / (self.base_gen * self.ratio)


def fig_hv_vs_cpu(D, out):
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.6))
    for ax, name in zip(axes, INSTANCES):
        d = D[name]
        gs = np.unique(np.round(np.geomspace(d.base_gen, d.n_eq, 22)).astype(int))
        hv = np.array([d.hv_at(g) for g in gs])
        x = d.cpu(gs)
        m, s = hv.mean(1), hv.std(1, ddof=1)
        ax.fill_between(x, m - s, m + s, color=COLOR["baseline"], alpha=0.15, lw=0)
        ax.plot(x, m, color=COLOR["baseline"], lw=3, label="baseline (cắt ở n_gen khác nhau)")
        ax.plot(x[-1], m[-1], "s", color=COLOR["baseline_eqtime"], ms=11, mec="white", mew=2, zorder=5,
                label="baseline dài (1400 hoặc 3500 thế hệ)")
        dv = d.hv("dp")
        ax.errorbar(1.0, dv.mean(), yerr=dv.std(ddof=1), fmt="o", color=COLOR["dp"], ms=13, mec="white", mew=2,
                    capsize=5, lw=2, zorder=6, label="dp (chấm mọi cá thể, 200 thế hệ)")
        for src, pol, B in (("baseline", "baseline_polish", d.base_gen),
                            ("baseline_eqtime", "baseline_eqtime_polish", d.n_eq)):
            pv = d.hv(pol)
            xp = d.cpu(B + d.polish_gens(pol))
            ax.errorbar(xp, pv.mean(), yerr=pv.std(ddof=1), fmt="D", color=COLOR["baseline_polish"], ms=11,
                        mec="white", mew=2, capsize=5, lw=2, zorder=6,
                        label="baseline + polish" if src == "baseline" else None)
        ax.axvline(1.0, color=INK2, ls=":", lw=1.5)
        ax.set_xscale("log")
        ticks = [t for t in (0.03, 0.06, 0.1, 0.2, 0.5, 1.0) if x[0] * 0.8 <= t <= 1.4]
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{t:g}" for t in ticks])
        ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
        ax.set_title(name, loc="left", fontweight="bold")
        ax.set_xlabel("Chi phí CPU so với dp (1 = chi phí dp)")
        ax.set_ylabel("HV (trung bình ± độ lệch chuẩn, 10 seed)")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.17))
    fig.tight_layout()
    fig.savefig(out / "hv_vs_cpu.png")
    plt.close(fig)


def gains(d):
    """Cho moi ngan sach (ngan, hoi tu): (gain polish, gain the he them, nhan, la uoc luong) theo seed."""
    res = []
    for src, pol, B in (("baseline", "baseline_polish", d.base_gen), ("baseline_eqtime", "baseline_eqtime_polish", d.n_eq)):
        g_eq = d.polish_gens(pol)
        gp = d.hv(pol) - d.hv(src)
        if B + g_eq <= d.n_eq:
            gg, est = d.hv_at(B + g_eq) - d.hv_at(B), False
        else:
            gg, est = d.hv_at(B) - d.hv_at(B - g_eq), True
        res.append((gp, gg, B, est))
    return res


def fig_polish_vs_gens(D, out):
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.6), sharey=False)
    rng = np.random.default_rng(0)             # chi de rai diem theo chieu ngang
    for ax, name in zip(axes, INSTANCES):
        xt, xl = [], []
        pos = 0.0
        for gp, gg, B, est in gains(D[name]):
            for k, (vals, col, lab) in enumerate(((gp, COLOR["baseline_polish"], "polish"),
                                                  (gg, COLOR["baseline_eqtime"], "thêm thế hệ"))):
                x0 = pos + k * 0.9
                ax.scatter(x0 + rng.uniform(-0.17, 0.17, len(vals)), vals, s=70, color=col, alpha=0.55, lw=0, zorder=3)
                ax.hlines(vals.mean(), x0 - 0.33, x0 + 0.33, color=col, lw=5, zorder=4)
                xt.append(x0)
                xl.append(lab + ("\n(ước lượng)" if (k == 1 and est) else ""))
            ax.text(pos + 0.45, 1.02, f"{B} thế hệ", transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                    fontsize=17, color=INK2)
            pos += 2.5
        ax.axhline(0, color=INK2, lw=1.2)
        ax.set_xticks(xt)
        ax.set_xticklabels(xl)
        ax.set_title(name, loc="left", fontweight="bold", pad=34)
        ax.set_ylabel("ΔHV (chấm: từng seed; vạch: trung bình)")
        ax.set_xlim(-0.7, pos - 0.8)
    fig.tight_layout()
    fig.savefig(out / "polish_vs_extra_gens.png")
    plt.close(fig)


def fig_front(D, out):
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.8))
    note = []
    for ax, name in zip(axes, INSTANCES):
        d = D[name]
        hv = d.hv("baseline")
        seeds = [r["seed"] for r in d.runs["baseline"]]
        order = np.argsort(hv, kind="stable")
        i = order[len(order) // 2 - 1]            # 10 seed: hang 5 (trung vi duoi)
        seed = seeds[i]
        note.append(f"{name}: seed {seed} (HV baseline {hv[i]:.3f}, hạng 5/10)")
        for cfg_name, label, mk, sz in (("baseline_eqtime", "baseline dài (1400 / 3500 thế hệ)", "s", 90),
                                       ("baseline_polish", "baseline + polish", "D", 90),
                                       ("dp", "dp", "o", 90), ("baseline", "baseline", "o", 90)):
            r = d.runs[cfg_name][i]
            assert r["seed"] == seed
            F = front_of(r)
            c = COLOR["baseline_eqtime" if cfg_name == "baseline_eqtime" else cfg_name]
            ax.scatter(F[:, 0], F[:, 1], s=sz, marker=mk, color=c, alpha=0.85, edgecolor="white", linewidth=1.2,
                       label=label, zorder=3)
        ax.set_title(f"{name} (seed {seed})", loc="left", fontweight="bold")
        ax.set_xscale("log")
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
        ax.set_xticks([1500, 2000, 3000, 5000, 10000] if name == "C102-25" else [5000, 7000, 10000, 20000])
        ax.set_xlabel("f1 (chi phí, nhỏ hơn tốt hơn; thang log)")
        ax.set_ylabel("f2 (khí thải, nhỏ hơn tốt hơn)")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.09), markerscale=1.3)
    fig.tight_layout()
    fig.savefig(out / "front_f1_f2.png")
    plt.close(fig)
    return note


def split_data(cfg, exp):
    import pickle
    sets = []
    warnings.simplefilter("ignore")
    root = results_root(cfg) / exp
    for name, kind in (("C102-25", "final"), ("R201-50", "final"), ("C102-100", "random")):
        n_name, n = name.split("-")
        inst = load_instance(n_name, int(n), cfg)
        scales = objective_scales(inst)
        if kind == "final":
            perms = []
            for f in sorted((root / name / "baseline").glob("seed_*.pkl")):
                perms += [list(map(int, p)) for p in pickle.load(open(f, "rb"))["pop"]]
        else:
            rng = np.random.default_rng(0)
            perms = [list(rng.permutation(np.arange(1, inst.n + 1))) for _ in range(200)]
        sets.append((name, kind, measure(perms, inst, scales), inst.fleet_size))
    return sets


def fig_split_rules(cfg, exp, out):
    sets = split_data(cfg, exp)
    metrics = [("late_min", "Phút trễ (log)", True), ("f1", "f1 (log)", True), ("n_vehicles", "Số xe", False)]
    keys = ("F4", "late_min", "early_min", "n_vehicles", "f1", "f3", "total_km")
    fig, axes = plt.subplots(1, 3, figsize=(18, 6.6))
    w = 0.26
    for ax, (key, title, log) in zip(axes, metrics):
        ki = keys.index(key)
        for si, (name, kind, res, fleet) in enumerate(sets):
            for ri, rule in enumerate(RULES):
                a = res[rule]
                v, feas = a[:, ki].mean(), a[:, -1].mean()
                x = si + (ri - 1) * w
                bad = feas < 1.0
                ax.bar(x, v, w * 0.92, color=RULE_COLOR[rule], hatch="////" if bad else None,
                       edgecolor="white" if not bad else INK, linewidth=1.5 if bad else 0, zorder=3,
                       label=RULE_LABEL[rule] if si == 0 else None)
                if bad and key == "n_vehicles":
                    ax.text(x, v + 0.8, "vượt\nđội xe", ha="center", va="bottom", fontsize=14, color=INK)
        if key == "n_vehicles":
            ax.axhline(25, color=INK2, ls="--", lw=1.5, zorder=2)
            ax.text(-0.45, 25.6, "đội xe = 25", fontsize=14, color=INK2, va="bottom")
            ax.set_ylim(0, 33)
        if log:
            ax.set_yscale("log")
        ax.set_xticks(range(len(sets)))
        ax.set_xticklabels([f"{n}\n{'quần thể' if k == 'final' else 'hoán vị'}\n{'cuối' if k == 'final' else 'ngẫu nhiên'}"
                            for n, k, _, _ in sets],
                           fontsize=14)
        ax.set_title(title, loc="left", fontweight="bold")
    h, l = axes[0].get_legend_handles_labels()
    h.append(matplotlib.patches.Patch(facecolor="white", edgecolor=INK, hatch="////"))
    l.append("vạch chéo: vượt đội xe (0% khả thi)")
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    fig.savefig(out / "split_rules.png")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", default="tv4_main")
    ap.add_argument("--out", default="docs/figures/tv4")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    style()
    cfg = load_config()
    D = {n: Data(args.exp, n) for n in INSTANCES}
    fig_hv_vs_cpu(D, out)
    fig_polish_vs_gens(D, out)
    for line in fig_front(D, out):
        print("front:", line)
    fig_split_rules(cfg, args.exp, out)
    for name in INSTANCES:
        for gp, gg, B, est in gains(D[name]):
            print(f"{name} B={B}: polish {gp.mean():+.4f}, them the he {gg.mean():+.4f}{' (uoc luong)' if est else ''}")


if __name__ == "__main__":
    main()
