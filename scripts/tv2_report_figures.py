"""Sinh bảng số liệu (LaTeX) và hình cho báo cáo TV2 từ kết quả thật của src.runner.

    python -m scripts.tv2_report_figures

Đọc results/tv2_tune và results/tv2_main (chạy bằng `python -m src.runner run ...`), gọi
src.runner.analyze cho từng instance (cùng quy ước chuẩn hoá của nhóm), rồi ghi:
    docs/bao_cao_tv2/so_lieu/*.tex   các bảng, mọi con số lấy thẳng từ kết quả
    docs/bao_cao_tv2/so_lieu/*.csv   bản CSV tương ứng
    docs/bao_cao_tv2/hinh/*.pdf      các hình
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from src.instance import ROOT, load_config
from src.metrics import hv, hv_history, non_dominated, normalization_bounds
from src.runner import analyze, results_root

OUT = ROOT / "docs" / "bao_cao_tv2"
TAB, FIG = OUT / "so_lieu", OUT / "hinh"
INSTANCES = ["C102-25", "R201-50", "RC201-100", "case29-29"]
MAIN = ["off", "off_long", "init_only", "ls_only", "ls_drift", "both", "both_drift"]
TUNE = ["off", "init_r20", "init_r10", "init_r30", "ls_reject", "ls_drift", "ls_pareto", "ls_p01"]
LABEL = {"off": "Gốc", "off_long": "Gốc, cùng số lần đánh giá", "init_only": "init\\_smart",
         "ls_only": "LS (reject)", "ls_drift": "LS (evaluate\\_actual)",
         "both": "init + LS (reject)", "both_drift": "init + LS (evaluate\\_actual)",
         "init_r20": "init 20/20/60", "init_r10": "init 10/10/80", "init_r30": "init 30/30/40",
         "ls_reject": "LS reject", "ls_pareto": "LS pareto", "ls_p01": "LS $p_{ls}=0{,}1$"}
PLAIN = {k: v.replace("\\_", "_").replace("$p_{ls}=0{,}1$", "LS p=0,1") for k, v in LABEL.items()}
# bảng màu đã kiểm định CVD; off_long cùng màu với off (cùng thuật toán), nét đứt
COLOR = {"off": "#2a78d6", "off_long": "#2a78d6", "init_only": "#eb6834", "ls_only": "#1baf7a",
         "ls_drift": "#e87ba4", "both": "#eda100", "both_drift": "#008300"}
MARK = {"off": "o", "off_long": "o", "init_only": "s", "ls_only": "^", "ls_drift": "v",
        "both": "D", "both_drift": "P"}


def vn(x: float, d: int) -> str:
    """Số kiểu Việt Nam: dấu phẩy thập phân, dấu chấm hàng nghìn."""
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", "{,}").replace("X", ".")


def load(exp: str, inst: str) -> dict[str, list[dict]]:
    root = results_root(load_config()) / exp / inst
    runs = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        runs[d.name] = [pickle.load(open(f, "rb")) for f in sorted(d.glob("seed_*.pkl"))]
    return runs


def write(name: str, tex: str, df: pd.DataFrame | None = None) -> None:
    (TAB / f"{name}.tex").write_text(tex, encoding="utf-8")
    if df is not None:
        df.to_csv(TAB / f"{name}.csv", encoding="utf-8")


# ------------------------------------------------------------------ bảng
def main_table(inst: str, out: dict, runs: dict) -> None:
    s, pw = out["summary"], out["pairwise"]
    rows = []
    for c in [c for c in MAIN if c in s.index]:
        r = s.loc[c]
        p = np.nan
        if c != "off":
            m = pw[((pw.A == c) & (pw.B == "off")) | ((pw.A == "off") & (pw.B == c))]
            p = float(m.p_HV.iloc[0])
        feas = np.mean([x["feasible_frac_front"] for x in runs[c]])
        gens = len(runs[c][0]["history"]) - 1
        rows.append((c, r, p, feas, gens))
    lines = []
    best_hv = max(r["HV_mean"] for _, r, *_ in rows)
    best_igd = min(r["IGD_mean"] for _, r, *_ in rows)
    for c, r, p, feas, gens in rows:
        hvs = f"{vn(r['HV_mean'], 3)} $\\pm$ {vn(r['HV_std'], 3)}"
        igs = f"{vn(r['IGD_mean'], 3)} $\\pm$ {vn(r['IGD_std'], 3)}"
        if r["HV_mean"] == best_hv:
            hvs = f"\\textbf{{{hvs}}}"
        if r["IGD_mean"] == best_igd:
            igs = f"\\textbf{{{igs}}}"
        ps = "--" if np.isnan(p) else ("$<$0{,}001" if p < 0.001 else vn(p, 3))
        lines.append(f"{LABEL[c]} & {gens} & {hvs} & {igs} & {vn(r['SP_mean'], 3)} & "
                     f"{vn(r['n_points_mean'], 1)} & {vn(r['n_evals_mean'], 0)} & "
                     f"{vn(r['runtime_s_mean'], 1)} & {ps} \\\\")
    tex = ("\\begin{tabular}{@{}lrllrrrrr@{}}\n\\toprule\n"
           "Cấu hình & $G$ & HV & IGD & SP & Số điểm & Số lần đánh giá & Thời gian (s) & $p$ \\\\\n"
           "\\midrule\n" + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")
    write(f"main_{inst}", tex, s)


def tune_table(outs: dict) -> None:
    lines = []
    for c in TUNE:
        cells = []
        for inst in INSTANCES:
            s = outs[inst]["summary"]
            col = s.loc[[x for x in TUNE if x in s.index], "HV_mean"]
            v = s.loc[c]
            cell = f"{vn(v['HV_mean'], 3)} $\\pm$ {vn(v['HV_std'], 3)}"
            fam = c.split("_")[0]          # nhóm "init" hoặc "ls"
            grp = [x for x in col.index if x.split("_")[0] == fam] if c != "off" else []
            if grp and v["HV_mean"] == col[grp].max():
                cell = f"\\textbf{{{cell}}}"
            cells.append(cell)
        lines.append(f"{LABEL[c]} & " + " & ".join(cells) + " \\\\")
        if c in ("off", "init_r30"):
            lines.append("\\midrule")
    tex = ("\\begin{tabular}{@{}lllll@{}}\n\\toprule\n"
           "Biến thể & " + " & ".join(INSTANCES) + " \\\\\n\\midrule\n" + "\n".join(lines) +
           "\n\\bottomrule\n\\end{tabular}\n")
    write("tune", tex, pd.concat({i: outs[i]["summary"]["HV_mean"] for i in INSTANCES}, axis=1))


def init_table(all_runs: dict, ref_point) -> pd.DataFrame:
    """HV quần thể đầu: chuẩn hoá theo hợp các front ban đầu của off và init_only (cùng instance)."""
    rows, lines = [], []
    for inst in INSTANCES:
        runs = all_runs[inst]
        firsts = {c: [r["history"][0] for r in runs[c]] for c in ("off", "init_only")}
        bounds = normalization_bounds(firsts["off"] + firsts["init_only"])
        cells = []
        for c in ("off", "init_only"):
            h = np.array([hv(non_dominated(F), bounds, ref_point) for F in firsts[c]])
            f1 = np.array([F[:, 0].min() for F in firsts[c]])
            f3 = np.array([1 - F[:, 2].min() for F in firsts[c]])
            rows.append({"instance": inst, "config": c, "hv0_mean": h.mean(), "hv0_std": h.std(ddof=1),
                         "f1min0": f1.mean(), "f3max0": f3.mean()})
            cells += [f"{vn(h.mean(), 3)} $\\pm$ {vn(h.std(ddof=1), 3)}", vn(f1.mean(), 1), vn(f3.mean(), 3)]
        lines.append(f"{inst} & " + " & ".join(cells) + " \\\\")
    tex = ("\\begin{tabular}{@{}lrrrrrr@{}}\n\\toprule\n"
           " & \\multicolumn{3}{c}{Khởi tạo ngẫu nhiên (gốc)} & \\multicolumn{3}{c}{init\\_smart} \\\\\n"
           "\\cmidrule(lr){2-4}\\cmidrule(l){5-7}\n"
           "Instance & HV & $f_1$ nhỏ nhất & $f_3$ lớn nhất & HV & $f_1$ nhỏ nhất & $f_3$ lớn nhất \\\\\n"
           "\\midrule\n" + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")
    df = pd.DataFrame(rows)
    write("init", tex, df)
    return df


def ls_table(all_runs: dict) -> pd.DataFrame:
    rows, lines = [], []
    for inst in INSTANCES:
        for c in ("ls_only", "ls_drift", "both", "both_drift"):
            lc = pd.DataFrame([r["ls_counters"] for r in all_runs[inst][c]]).mean()
            cand = lc["n_ls_candidate_evals"]
            share = lc["elapsed_s"] / np.mean([r["runtime_s"] for r in all_runs[inst][c]])
            rows.append({"instance": inst, "config": c, **lc.to_dict(), "time_share": share})
            lines.append(
                f"{inst if c == 'ls_only' else ''} & {LABEL[c]} & {vn(lc['n_ls_triggered'], 0)} & "
                f"{vn(cand, 0)} & {vn(100 * lc['n_ls_accepted'] / cand, 1)} & "
                f"{vn(100 * lc['n_ls_split_drift'] / cand, 1)} & "
                f"{vn(100 * lc['n_ls_rejected_split'] / cand, 1)} & "
                f"{vn(100 * lc['n_ls_rejected_feasibility'] / cand, 1)} & "
                f"{vn(100 * share, 0)} \\\\")
        lines.append("\\midrule" if inst != INSTANCES[-1] else "")
    tex = ("\\begin{tabular}{@{}llrrrrrrr@{}}\n\\toprule\n"
           "Instance & Cấu hình & Số lần chạy & Ứng viên & Nhận (\\%) & Lệch biên (\\%) & "
           "Loại do lệch (\\%) & Loại do số xe (\\%) & Thời gian LS (\\%) \\\\\n\\midrule\n" +
           "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")
    df = pd.DataFrame(rows)
    write("ls_stats", tex, df)
    return df


# ------------------------------------------------------------------ hình
def figures(all_runs: dict, bounds_of: dict, ref_point) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.color": "#e4e3df",
                         "grid.linewidth": 0.6, "pdf.fonttype": 42})

    # Hội tụ HV theo thế hệ (các cấu hình 200 thế hệ)
    fig, axes = plt.subplots(2, 2, figsize=(9, 6.6))
    for ax, inst in zip(axes.flat, INSTANCES):
        for c in [c for c in MAIN if c != "off_long"]:
            H = np.array([hv_history(r["history"], bounds_of[inst], ref_point) for r in all_runs[inst][c]])
            mu, sd = H.mean(axis=0), H.std(axis=0, ddof=1)
            x = np.arange(len(mu))
            ax.plot(x, mu, color=COLOR[c], lw=1.8, label=PLAIN[c])
            ax.fill_between(x, mu - sd, mu + sd, color=COLOR[c], alpha=0.12, lw=0)
            ax.plot(x[-1], mu[-1], MARK[c], color=COLOR[c], ms=6, mec="white")
        ax.set_title(inst, fontsize=11)
        ax.set_xlabel("Thế hệ")
        ax.set_ylabel("HV front tốt nhất")
    h, l = axes.flat[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(FIG / "hoi_tu_hv.pdf")
    plt.close(fig)

    # Boxplot HV và IGD
    for inst in INSTANCES:
        per = pd.read_csv(results_root(load_config()) / "tv2_main" / inst / "per_run.csv")
        cfgs = [c for c in MAIN if c in set(per.config)]
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
        for ax, m, t in ((axes[0], "HV", "HV (lớn hơn tốt hơn)"), (axes[1], "IGD", "IGD (nhỏ hơn tốt hơn)")):
            data = [per.loc[per.config == c, m].to_numpy() for c in cfgs]
            bp = ax.boxplot(data, patch_artist=True, widths=0.55, medianprops={"color": "#1a1a19"})
            for k, (patch, c) in enumerate(zip(bp["boxes"], cfgs), 1):
                patch.set_facecolor(COLOR[c])
                patch.set_alpha(0.35 if c == "off_long" else 0.55)
                patch.set_edgecolor(COLOR[c])
                if c == "off_long":
                    patch.set_linestyle("--")
                ax.scatter(np.full(len(data[k - 1]), k), data[k - 1], color=COLOR[c], marker=MARK[c],
                           s=14, edgecolors="white", linewidths=0.4, zorder=3)
            ax.set_xticks(range(1, len(cfgs) + 1))
            ax.set_xticklabels([PLAIN[c] for c in cfgs], rotation=35, ha="right", fontsize=8)
            ax.set_title(t, fontsize=10)
        fig.suptitle(f"{inst}, 10 seed mỗi cấu hình", fontsize=11)
        fig.tight_layout()
        fig.savefig(FIG / f"box_{inst}.pdf")
        plt.close(fig)

    # Pareto 3D, seed 0, đơn vị gốc
    fig = plt.figure(figsize=(10, 8.4))
    for k, inst in enumerate(INSTANCES, 1):
        ax = fig.add_subplot(2, 2, k, projection="3d")
        for c in ("off", "init_only", "ls_drift", "both_drift"):
            r = next(x for x in all_runs[inst][c] if x["seed"] == 0)
            F = non_dominated(r["F"][r["front"]])
            ax.scatter(F[:, 0], F[:, 1], 1 - F[:, 2], color=COLOR[c], marker=MARK[c], s=34,
                       edgecolors="white", linewidths=0.4, label=f"{PLAIN[c]} ({len(F)})")
        ax.set_xlabel("$f_1$ (CNY)", fontsize=8)
        ax.set_ylabel("$f_2$ (kg)", fontsize=8)
        ax.set_zlabel("$f_3$", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.set_title(inst, fontsize=10)
        ax.legend(fontsize=8, loc="upper left", frameon=False, markerscale=1.2)
    fig.tight_layout()
    fig.savefig(FIG / "pareto_3d.pdf")
    plt.close(fig)

    # Quần thể ban đầu: f1 và f3, seed 0
    fig, axes = plt.subplots(2, 2, figsize=(9, 6.6))
    src_col = {"random": "#2a78d6", "nn": "#eb6834", "tw": "#1baf7a", "random_fallback": "#8a8a85"}
    src_mark = {"random": "o", "nn": "s", "tw": "^", "random_fallback": "x"}
    from src.instance import load_instance
    cfg = load_config()
    for ax, inst in zip(axes.flat, INSTANCES):
        name, n = inst.split("-")
        r_off = next(x for x in all_runs[inst]["off"] if x["seed"] == 0)
        r_init = next(x for x in all_runs[inst]["init_only"] if x["seed"] == 0)
        F0 = initial_F(load_instance(name, int(n), cfg), cfg, 0, smart=False)
        F1, srcs = initial_F(load_instance(name, int(n), cfg), cfg, 0, smart=True)
        # quần thể tái tạo phải chứa đúng front ban đầu mà lần chạy đã lưu
        for F, r in ((F0, r_off), (F1, r_init)):
            rows = {tuple(x) for x in F.tolist()}
            assert all(tuple(x) in rows for x in r["history"][0].tolist()), inst
        ax.scatter(F0[:, 0], 1 - F0[:, 2], s=14, facecolors="none", edgecolors="#8a8a85",
                   label="gốc: ngẫu nhiên")
        for sname in ("random", "nn", "tw", "random_fallback"):
            m = np.array([s == sname for s in srcs])
            if m.any():
                ax.scatter(F1[m, 0], 1 - F1[m, 2], s=16, color=src_col[sname], marker=src_mark[sname],
                           edgecolors="white", linewidths=0.4, label=f"init_smart: {sname}")
        ax.set_title(inst, fontsize=11)
        ax.set_xlabel("$f_1$ (CNY)")
        ax.set_ylabel("$f_3$")
    h, l = axes.flat[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(FIG / "quan_the_dau.pdf")
    plt.close(fig)


def initial_F(inst, cfg, seed, smart):
    """Quần thể đầu đúng như nsga2.run tạo (cùng seed, cùng dòng sinh), chấm bằng decoder."""
    from src.decoder import evaluate_detail
    rng = np.random.default_rng(seed)
    if smart:
        from src.improvements.tv2_hooks import smart_initial_population
        imp = {**cfg["improvements"], "init_smart": True}
        ids = np.arange(1, inst.n + 1)
        perms, srcs = smart_initial_population(imp, inst, cfg["nsga2"]["n_pop"], rng,
                                               lambda r: r.permutation(ids).tolist())
    else:
        perms = [rng.permutation(np.arange(1, inst.n + 1)).tolist() for _ in range(cfg["nsga2"]["n_pop"])]
    F = np.array([[d["f1"], d["f2"], 1 - d["f3"]] for d in (evaluate_detail(p, inst) for p in perms)])
    return (F, srcs) if smart else F


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    ref_point = cfg["metrics"]["hv_ref_point"]
    tune_outs = {i: analyze("tv2_tune", i, cfg) for i in INSTANCES}
    tune_table(tune_outs)
    main_outs, all_runs, bounds_of = {}, {}, {}
    for inst in INSTANCES:
        main_outs[inst] = analyze("tv2_main", inst, cfg)
        all_runs[inst] = load("tv2_main", inst)
        fronts = [r["F"][r["front"]] for rs in all_runs[inst].values() for r in rs]
        bounds_of[inst] = normalization_bounds(fronts)
        main_table(inst, main_outs[inst], all_runs[inst])
    init_table(all_runs, ref_point)
    ls_table(all_runs)
    pd.concat({i: main_outs[i]["pairwise"] for i in INSTANCES}).to_csv(TAB / "pairwise.csv", encoding="utf-8")
    figures(all_runs, bounds_of, ref_point)
    print("Đã ghi", TAB, "và", FIG)


if __name__ == "__main__":
    main()
