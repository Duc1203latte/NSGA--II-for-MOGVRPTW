"""Bảng kết quả giai đoạn 2 của TV4: cấu hình x instance.

Đọc các file seed_XX.pkl thô và tính HV, IGD, SP, n_evals, runtime theo seed bằng đúng các hàm của
runner (load_runs, reference_set, normalization_bounds, evaluate_front), cùng feasible_frac_front và
số xe trên front cuối (chấm lại để kiểm). Không gọi runner.analyze vì nó dựng bảng hội tụ và lỗi khi
các cấu hình có n_gen khác nhau (như baseline_eqtime); hàm ở đây giống analyze trừ bước hội tụ, và
ghi đè per_run.csv, pairwise.csv của instance để không để lại file cũ.
p-value: Wilcoxon rank-sum (scipy.stats.ranksums, hai phía) của từng cấu hình so với baseline.

Chạy:  python -m scripts.tv4_report --exp tv4_main --instances C102-25 R201-50 [--out results/tv4_main/table.md]
Không cần chạy `runner analyze` trước.
"""
from __future__ import annotations
import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.stats import ranksums, wilcoxon

from src.decoder import evaluate_detail
from src.improvements.dp_split import evaluate_dp, objective_scales
from src.instance import ROOT, load_config, load_instance
from src.metrics import evaluate_front, normalization_bounds, reference_set
from src.runner import check_same_problem, front_of, load_runs, results_root

DP_COST_RATIO = {"C102-25": 8.7, "R201-50": 18.0}   # đo bằng CPU time, cùng phiên, 60/300 thế hệ
CONFIG_ORDER = ["baseline", "baseline_eqtime", "dp", "adapt", "both"]
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
    if use_dp and cfg["improvements"]["dp_split_params"].get("mode", "every_eval") == "every_eval" and res.get("W") is None:
        return float("nan")   # every_eval + archive (TV3) không giữ trọng số của cá thể, nên không chấm lại được
    counts = []
    for i in res["front"]:
        perm = res["pop"][i]
        w = None if res.get("W") is None else res["W"][i]
        # polish: hàng NaN được chấm bằng split baseline, hàng có trọng số được chấm bằng DP
        dp_row = use_dp and w is not None and not np.isnan(w).any()
        d = evaluate_dp(perm, inst, w, scales) if dp_row else evaluate_detail(perm, inst)
        if not np.array_equal(res["F"][i], [d["f1"], d["f2"], 1 - d["f3"]]):
            raise AssertionError(f"seed {res['seed']}: F chấm lại khác F đã lưu")
        counts.append(d["n_vehicles"])
    return float(np.mean(counts))


def analyze_all(exp_dir: Path, ref_point, exclude: tuple[str, ...] = (), with_ref: bool = False):
    """Giống runner.analyze (per_run + pairwise HV) nhưng không dựng bảng hội tụ. Reference set và cận
    chuẩn hoá gộp front của mọi cấu hình có mặt (trừ `exclude`, chỉ dùng để kiểm lại bảng cũ)."""
    runs = {c: rs for c, rs in load_runs(exp_dir).items() if c not in exclude}
    check_same_problem(exp_dir, list(runs))
    all_fronts = [front_of(r) for rs in runs.values() for r in rs]
    ref, bounds = reference_set(all_fronts), normalization_bounds(all_fronts)
    rows = []
    for config, rs in runs.items():
        for r in rs:
            F = front_of(r)
            rows.append({"config": config, "seed": r["seed"], **evaluate_front(F, ref, bounds, ref_point),
                         "n_evals": r["n_evals"], "runtime_s": r["runtime_s"]})
    df = pd.DataFrame(rows)
    return (df, ref, bounds) if with_ref else df


def eq_budget_table(exp: str, inst_name: str, dp_cost_ratio: dict[str, float]) -> str:
    """HV của baseline_eqtime khi cắt ở các số thế hệ nhỏ hơn. history[g] là front sau g thế hệ, nên
    cắt ở g đúng bằng một run n_gen = g cùng seed (cùng dãy ngẫu nhiên). Dùng CHUNG reference set và cận
    chuẩn hoá với bảng chính nên so được với cột dp. Chi phí CPU tính theo hệ số đo cùng lúc
    (dp_cost_ratio: chi phí một thế hệ dp / một thế hệ baseline)."""
    cfg0 = load_config()
    exp_dir = results_root(cfg0) / exp / inst_name
    per_run, ref, bounds = analyze_all(exp_dir, cfg0["metrics"]["hv_ref_point"], with_ref=True)
    runs = load_seed_files(exp_dir, "baseline_eqtime")
    dp_hv = per_run[per_run.config == "dp"].sort_values("seed").HV.to_numpy()
    n_eq = len(runs[0]["history"]) - 1
    ratio = dp_cost_ratio[inst_name]
    gens = [cfg0["nsga2"]["n_gen"], n_eq // 4, n_eq // 2, n_eq]
    lines = ["| Instance | Baseline cắt ở n_gen | Chi phí CPU so với dp | HV | p (HV) so với dp |", "|---|---|---|---|---|"]
    for g in gens:
        hv = np.array([evaluate_front(r["history"][g], ref, bounds, cfg0["metrics"]["hv_ref_point"])["HV"]
                       for r in runs])
        cost = g / (cfg0["nsga2"]["n_gen"] * ratio)
        lines.append(f"| {inst_name} | {g} | {cost:.2f} | {fmt(hv.mean(), hv.std(ddof=1))} | "
                     f"{pstr(ranksums(hv, dp_hv).pvalue)} |")
    lines.append(f"| {inst_name} | dp (200 thế hệ) | 1.00 | {fmt(dp_hv.mean(), dp_hv.std(ddof=1))} | — |")
    return "\n".join(lines)


def polish_vs_generations(exp: str, inst_name: str, tune_exp: str = "tv4_tune") -> str:
    """Bước polish đổi lấy bao nhiêu HV so với việc dùng cùng chi phí CPU cho thêm thế hệ baseline?
    Chi phí một thế hệ baseline = cpu_s(baseline, 200 thế hệ) / 200 từ cpu_cost.csv của tv4_tune (đo tuần
    tự); g_eq = CPU của bước polish / chi phí một thế hệ. Do history[g] của run baseline_eqtime chính là run
    baseline n_gen = g cùng seed, ta tính HV(baseline ở B + g_eq thế hệ). Ở ngân sách dài nhất không có thế hệ
    sau B nên dùng HV(B) - HV(B - g_eq) làm giá trị biên của g_eq thế hệ cuối (ước lượng thiên về có lợi cho
    việc chạy thêm thế hệ, vì lợi ích mỗi thế hệ giảm dần)."""
    cfg0 = load_config()
    root = results_root(cfg0)
    exp_dir = root / exp / inst_name
    ref_point = cfg0["metrics"]["hv_ref_point"]
    per_run, ref, bounds = analyze_all(exp_dir, ref_point, with_ref=True)
    cpu = pd.read_csv(root / tune_exp / "cpu_cost.csv")
    base_cpu = float(cpu[(cpu.instance == inst_name) & (cpu.config == "baseline")].cpu_s.iloc[0])
    per_gen = base_cpu / cfg0["nsga2"]["n_gen"]
    eq = sorted(load_seed_files(exp_dir, "baseline_eqtime"), key=lambda r: r["seed"])
    n_eq = len(eq[0]["history"]) - 1

    def hv_at(g):
        return np.array([evaluate_front(r["history"][g], ref, bounds, ref_point)["HV"] for r in eq])

    def hv_cfg(name):
        return per_run[per_run.config == name].sort_values("seed").HV.to_numpy()

    lines = ["| Instance | Ngân sách B (thế hệ) | CPU polish (s) | = thế hệ baseline | HV polish − HV chưa polish | "
             "HV thêm nếu dùng cùng CPU cho thế hệ | p (HV), signed-rank, polish so với thế hệ thêm |",
             "|---|---|---|---|---|---|---|"]
    for src, out, B in (("baseline", "baseline_polish", cfg0["nsga2"]["n_gen"]),
                        ("baseline_eqtime", "baseline_eqtime_polish", n_eq)):
        runs = load_seed_files(exp_dir, out)
        pol_cpu = float(np.mean([r["polish_cpu_s"] for r in runs]))
        g_eq = int(round(pol_cpu / per_gen))
        gain_pol = hv_cfg(out) - hv_cfg(src)
        if B + g_eq <= n_eq:
            gain_gen, how = hv_at(B + g_eq) - hv_at(B), f"HV({B + g_eq}) − HV({B})"
        else:
            gain_gen, how = hv_at(B) - hv_at(B - g_eq), f"HV({B}) − HV({B - g_eq}) (ước lượng)"
        d = gain_pol - gain_gen
        pv = wilcoxon(gain_pol, gain_gen).pvalue if np.any(d != 0) else 1.0
        lines.append(f"| {inst_name} | {B} | {pol_cpu:.1f} | {g_eq} | {fmt(gain_pol.mean(), gain_pol.std(ddof=1))} | "
                     f"{fmt(gain_gen.mean(), gain_gen.std(ddof=1))} ({how}) | {pstr(pv)} |")
    return "\n".join(lines)


def instance_rows(exp: str, inst_name: str, exclude: tuple[str, ...] = (),
                  order: list[str] | None = None) -> list[dict]:
    base_cfg = load_config()
    exp_dir = results_root(base_cfg) / exp / inst_name
    per_run = analyze_all(exp_dir, base_cfg["metrics"]["hv_ref_point"], exclude)
    if not exclude:
        per_run.to_csv(exp_dir / "per_run.csv", index=False, encoding="utf-8")
    name, n = inst_name.rsplit("-", 1)
    base = per_run[per_run.config == "baseline"]
    eq = per_run[per_run.config == "baseline_eqtime"]
    rows = []
    present = set(per_run.config)
    cpu_csv = exp_dir.parent / "cpu_cost.csv"
    cpu = pd.read_csv(cpu_csv) if cpu_csv.exists() else None
    for config in [c for c in (order or CONFIG_ORDER) if c in present]:
        pr = per_run[per_run.config == config].sort_values("seed")
        with open(exp_dir / config / "config_used.yaml", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        inst = load_instance(name, int(n), cfg)
        runs = load_seed_files(exp_dir, config)
        assert [r["seed"] for r in runs] == pr.seed.tolist()
        row = {
            "instance": inst_name, "config": config, "n_runs": len(pr),
            "n_gen": cfg["nsga2"]["n_gen"],
            "HV": fmt(pr.HV.mean(), pr.HV.std()), "IGD": fmt(pr.IGD.mean(), pr.IGD.std()),
            "SP": fmt(pr.SP.mean(), pr.SP.std()),
            "n_evals": f"{pr.n_evals.mean():.0f}", "runtime_s": f"{pr.runtime_s.mean():.1f}",
            "feas_front": f"{np.mean([r['feasible_frac_front'] for r in runs]):.2f}",
            "feas_pop": f"{np.mean([r['feasible_frac_pop'] for r in runs]):.2f}",
            "vehicles": (lambda v: "—" if np.isnan(v) else f"{v:.1f}")(np.mean([front_vehicles(r, inst, cfg) for r in runs])),
            "front_size": f"{pr.n_points.mean():.1f}",
            "n_dp_calls": f"{np.mean([r.get('n_dp_calls', 0) for r in runs]):.0f}",
            "cpu_rel": "—",
            "polish_cpu": (f"{np.mean([r['polish_cpu_s'] for r in runs]):.1f}"
                           if all(r.get("polish_cpu_s") is not None for r in runs) else "—"),
            "pair_dHV": "—", "pair_p_HV": "—", "pair_dIGD": "—", "pair_p_IGD": "—",
            "dHV": "—", "p_HV": "—", "p_IGD": "—", "p_HV_eq": "—", "p_IGD_eq": "—",
        }
        if cpu is not None:
            m = cpu[(cpu.instance == inst_name) & (cpu.config == config)]
            if len(m):
                row["cpu_rel"] = f"{float(m.relative.iloc[0]):.2f}"
        if config != "baseline":
            row["dHV"] = f"{pr.HV.mean() - base.HV.mean():+.4f}"
            row["p_HV"] = pstr(ranksums(pr.HV, base.HV).pvalue)
            row["p_IGD"] = pstr(ranksums(pr.IGD, base.IGD).pvalue)
        if len(eq) and config not in ("baseline", "baseline_eqtime"):
            row["p_HV_eq"] = pstr(ranksums(pr.HV, eq.HV).pvalue)
            row["p_IGD_eq"] = pstr(ranksums(pr.IGD, eq.IGD).pvalue)
        rows.append(row)
    # kiểm định cặp theo seed (Wilcoxon signed-rank): cấu hình đã polish so với bản chưa polish cùng seed
    partner = {"baseline_polish": "baseline", "baseline_eqtime_polish": "baseline_eqtime"}
    by_cfg = {r["config"]: r for r in rows}
    for r in rows:
        q = partner.get(r["config"])
        if q is None and r["config"].endswith("_polish"):   # polish kiểu tv4_tune_div: <cấu hình>_polish so với <cấu hình>
            q = r["config"][: -len("_polish")]
        if q not in by_cfg:
            continue
        a = per_run[per_run.config == r["config"]].sort_values("seed")
        b = per_run[per_run.config == q].sort_values("seed")
        assert a.seed.tolist() == b.seed.tolist()
        for m in ("HV", "IGD"):
            d = a[m].to_numpy() - b[m].to_numpy()
            pv = wilcoxon(a[m].to_numpy(), b[m].to_numpy()).pvalue if np.any(d != 0) else 1.0
            r[f"pair_d{m}"] = f"{d.mean():+.4f} ± {d.std(ddof=1):.4f}"
            r[f"pair_p_{m}"] = pstr(pv)
    return rows


COLS = [("instance", "Instance"), ("config", "Cấu hình"), ("n_gen", "n_gen"), ("HV", "HV"), ("dHV", "ΔHV vs baseline"),
        ("p_HV", "p (HV)"), ("p_HV_eq", "p (HV) vs eqtime"), ("IGD", "IGD"), ("p_IGD", "p (IGD)"),
        ("p_IGD_eq", "p (IGD) vs eqtime"), ("SP", "SP"),
        ("n_evals", "n_evals"), ("runtime_s", "Thời gian/run (s)"),
        ("feas_front", "Khả thi (front)"), ("feas_pop", "Khả thi (quần thể)"),
        ("vehicles", "Số xe TB (front)"), ("front_size", "Số điểm front")]


TUNE_COLS = [("instance", "Instance"), ("config", "Cấu hình"), ("HV", "HV"), ("dHV", "ΔHV vs baseline"),
             ("p_HV", "p (HV)"), ("IGD", "IGD"), ("p_IGD", "p (IGD)"), ("n_evals", "n_evals"),
             ("n_dp_calls", "n_dp_calls"), ("cpu_rel", "CPU so với baseline"),
             ("feas_front", "Khả thi (front)"), ("front_size", "Số điểm front")]


DIV_COLS = [("instance", "Instance"), ("config", "Cấu hình"), ("HV", "HV"), ("dHV", "ΔHV vs baseline"),
            ("p_HV", "p (HV)"), ("IGD", "IGD"), ("p_IGD", "p (IGD)"), ("SP", "SP"), ("front_size", "Số điểm front"),
            ("cpu_rel", "CPU so với baseline"), ("pair_dHV", "ΔHV so với bản chưa polish (cặp)"),
            ("pair_p_HV", "p (HV), signed-rank")]


POLISH_COLS = [("instance", "Instance"), ("config", "Cấu hình"), ("n_gen", "n_gen"), ("HV", "HV"),
               ("pair_dHV", "ΔHV so với bản chưa polish (cặp)"), ("pair_p_HV", "p (HV), signed-rank"),
               ("IGD", "IGD"), ("pair_dIGD", "ΔIGD so với bản chưa polish (cặp)"),
               ("pair_p_IGD", "p (IGD), signed-rank"), ("front_size", "Số điểm front"),
               ("polish_cpu", "CPU của bước polish (s/run)"), ("feas_front", "Khả thi (front)")]


def to_markdown(rows: list[dict], cols=None) -> str:
    cols = cols or COLS
    head = "| " + " | ".join(h for _, h in cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    body = ["| " + " | ".join(str(r[k]) for k, _ in cols) + " |" for r in rows]
    return "\n".join([head, sep, *body])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--instances", nargs="+", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--exclude", nargs="*", default=[], help="bỏ cấu hình khỏi reference set (kiểm lại bảng cũ)")
    ap.add_argument("--order", nargs="*", default=None, help="thứ tự cấu hình trong bảng")
    ap.add_argument("--cols", choices=["full", "tune", "polish", "div"], default="full")
    args = ap.parse_args()
    rows = [r for inst in args.instances
            for r in instance_rows(args.exp, inst, tuple(args.exclude), args.order)]
    n_runs = sorted({r["n_runs"] for r in rows})
    cols = {"tune": TUNE_COLS, "polish": POLISH_COLS, "div": DIV_COLS}.get(args.cols)
    text = (to_markdown(rows, cols) + "\n\n"
            f"Mỗi ô: trung bình ± độ lệch chuẩn qua {n_runs} run (cùng bộ seed cho mọi cấu hình). "
            "p-value: Wilcoxon rank-sum hai phía so với baseline cùng instance; chưa hiệu chỉnh đa so sánh.\n\n"
            f"- {NOTE_RUNTIME}\n- {NOTE_REF}\n")
    if "baseline_eqtime" in {r["config"] for r in rows}:
        ratios = ", ".join(f"{k}: {v}x" for k, v in DP_COST_RATIO.items())
        text += (
            "\n### Baseline cắt ở các ngân sách nhỏ hơn (cùng reference set)\n\n"
            + "\n\n".join(eq_budget_table(args.exp, i, DP_COST_RATIO) for i in args.instances)
            + "\n\nChi phí CPU: hệ số một thế hệ dp / một thế hệ baseline đo cùng lúc, cùng máy "
            + f"({ratios}); 1.00 = bằng chi phí dp." + "\n")
    if args.cols == "polish":
        text += ("\n### Polish so với dùng cùng chi phí CPU cho thêm thế hệ\n\n"
                 + "\n\n".join(polish_vs_generations(args.exp, i) for i in args.instances)
                 + "\n\nChi phí một thế hệ baseline lấy từ `tv4_tune/cpu_cost.csv` (baseline, 200 thế hệ, CPU tuần tự).\n")
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
