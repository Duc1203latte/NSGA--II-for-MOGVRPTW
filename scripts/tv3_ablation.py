"""TV3, giai đoạn 3: ablation, đo đóng góp của từng cải tiến.

Cấu hình (với G nhóm cải tiến): baseline, chỉ bật từng nhóm (G), bật tất cả (1), bật tất cả trừ
một (G). Với 4 nhóm là 10 cấu hình. Mọi cấu hình dùng cùng bộ seed.

Chỉ số tính bằng src.runner.analyze, nên reference set của IGD và cận chuẩn hoá gộp front của MỌI
cấu hình trong thí nghiệm. Delta HV = HV trung bình của cấu hình - HV trung bình của baseline,
p-value là Wilcoxon rank-sum trên HV so với baseline. Bảng ghi cả số lần gọi evaluate (n_evals),
vì local_search và dp_split tốn thêm đánh giá.

Ví dụ:
  python -m scripts.tv3_ablation --exp tv3_ablation
  python -m scripts.tv3_ablation --exp tv3_ablation --set improvements.dp_split_params.mode=polish
  python -m scripts.tv3_ablation --exp thu --groups diversity --instances C102:25 --seeds 0,1
  python -m scripts.tv3_ablation --exp tv3_ablation --analyze-only

Kết quả: results/<exp>/<instance>/<cấu hình>/seed_XX.pkl (chạy lại thì bỏ qua seed đã có),
results/<exp>/ablation_table.csv và ablation_table.md.

Lưu ý: chỉ dùng trên code đã merge đủ các cải tiến được chọn. Cờ của một cải tiến chưa merge vẫn có
trong config.yaml nhưng nsga2 bỏ qua, nên cấu hình "bật" nó sẽ trùng baseline.
"""
from __future__ import annotations
import argparse
import copy
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import ranksums
from src.instance import load_config
from src.runner import analyze, apply_overrides, results_root, run_config

# Một nhóm = một cải tiến trong README. dp_split và Pc/Pm thích nghi là một nhóm (TV4), dù config
# tách thành hai cờ.
GROUPS = {
    "init_smart": ["init_smart"],
    "local_search": ["local_search"],
    "diversity": ["diversity"],
    "dp_split": ["dp_split", "adaptive_rates"],
}
DEFAULT_INSTANCES = "C102:25,R201:50,RC201:100,case29:29"

def ablation_configs(groups: list[str]) -> dict[str, set[str]]:
    """Tên cấu hình -> tập nhóm được bật, theo đúng thứ tự trình bày trong báo cáo."""
    out = {"baseline": set()}
    out.update({f"only_{g}": {g} for g in groups})
    out["all"] = set(groups)
    if len(groups) > 1:
        out.update({f"all_minus_{g}": set(groups) - {g} for g in groups})
    return out

def config_for(base_cfg: dict, on: set[str]) -> dict:
    cfg = copy.deepcopy(base_cfg)
    imp = cfg["improvements"]
    for g, flags in GROUPS.items():
        for flag in flags:
            if flag in imp:                 # adaptive_rates chỉ có sau khi merge nhánh TV4
                imp[flag] = g in on
    return cfg

def _job(args):
    exp, name, n, config_name, cfg, seeds = args
    run_config(exp, config_name, name, n, cfg, seeds)
    return f"{name}-{n} / {config_name}"

def build_table(exp: str, inst_names: list[str], configs: list[str], cfg: dict) -> pd.DataFrame:
    rows = []
    for inst in inst_names:
        per_run = analyze(exp, inst, cfg)["per_run"]
        hv_base = per_run.loc[per_run.config == "baseline", "HV"].to_numpy()
        for c in configs:
            r = per_run[per_run.config == c]
            if r.empty:
                continue
            hv = r["HV"].to_numpy()
            rows.append({
                "instance": inst, "config": c, "n_seeds": len(r),
                "HV_mean": hv.mean(), "HV_std": hv.std(ddof=1) if len(hv) > 1 else np.nan,
                "dHV": hv.mean() - hv_base.mean(),
                "p_HV": np.nan if c == "baseline" else ranksums(hv, hv_base).pvalue,
                "IGD_mean": r["IGD"].mean(), "SP_mean": r["SP"].mean(),
                "n_evals_mean": r["n_evals"].mean(), "runtime_s_mean": r["runtime_s"].mean(),
            })
    return pd.DataFrame(rows)

def to_markdown(t: pd.DataFrame) -> str:
    """Bảng cấu hình × instance, mỗi ô: HV ± std, ΔHV, p."""
    def cell(r):
        s = f"{r.HV_mean:.3f} ± {r.HV_std:.3f}"
        return s if r.config == "baseline" else f"{s}<br>Δ {r.dHV:+.3f}, p = {r.p_HV:.3f}"
    hv = t.assign(cell=t.apply(cell, axis=1)).pivot(index="config", columns="instance", values="cell")
    ev = t.pivot(index="config", columns="instance", values="n_evals_mean").round(0).astype(int)
    order = list(dict.fromkeys(t.config))
    hv, ev = hv.loc[order], ev.loc[order]

    def md(df):
        lines = ["| cấu hình | " + " | ".join(df.columns) + " |", "|---" * (len(df.columns) + 1) + "|"]
        lines += [f"| {i} | " + " | ".join(str(v) for v in row) + " |" for i, row in df.iterrows()]
        return "\n".join(lines)
    return ("## HV (trung bình ± độ lệch chuẩn), ΔHV so với baseline, p (Wilcoxon rank-sum)\n\n" + md(hv)
            + "\n\n## Số lần gọi evaluate trung bình mỗi run\n\n" + md(ev) + "\n")

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Ablation các cải tiến (TV3, giai đoạn 3)")
    ap.add_argument("--exp", default="tv3_ablation")
    ap.add_argument("--instances", default=DEFAULT_INSTANCES, help="dạng TÊN:n, cách nhau bởi dấu phẩy")
    ap.add_argument("--groups", default=",".join(GROUPS), help=f"chọn trong {list(GROUPS)}")
    ap.add_argument("--seeds", help="ví dụ 0,1,2; mặc định lấy experiment.seeds trong config")
    ap.add_argument("--set", action="append", default=[], metavar="KHOÁ=GIÁ_TRỊ",
                    help="ghi đè config cho mọi cấu hình, ví dụ improvements.dp_split_params.mode=polish")
    ap.add_argument("--workers", type=int, default=4, help="số tiến trình chạy song song")
    ap.add_argument("--analyze-only", action="store_true", help="chỉ tính bảng từ kết quả đã có")
    args = ap.parse_args(argv)

    groups = [g.strip() for g in args.groups.split(",")]
    unknown = set(groups) - set(GROUPS)
    if unknown:
        raise ValueError(f"nhóm không có: {sorted(unknown)}; chỉ nhận {list(GROUPS)}")
    base_cfg = apply_overrides(load_config(), args.set)
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else base_cfg["experiment"]["seeds"]
    instances = [(s.split(":")[0], int(s.split(":")[1])) for s in args.instances.split(",")]
    configs = ablation_configs(groups)

    if not args.analyze_only:
        jobs = [(args.exp, name, n, c, config_for(base_cfg, on), seeds)
                for name, n in instances for c, on in configs.items()]
        # việc nặng (nhiều nhóm bật, n lớn) chạy trước để các tiến trình kết thúc gần nhau
        jobs.sort(key=lambda j: (-j[2], -len(configs[j[3]])))
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for i, done in enumerate(pool.map(_job, jobs), 1):
                print(f"[{i}/{len(jobs)}] xong {done}", flush=True)

    root = results_root(base_cfg) / args.exp
    inst_names = sorted(p.name for p in root.iterdir() if p.is_dir())
    table = build_table(args.exp, inst_names, list(configs), base_cfg)
    table.to_csv(root / "ablation_table.csv", index=False, encoding="utf-8")
    (root / "ablation_table.md").write_text(to_markdown(table), encoding="utf-8")
    print(to_markdown(table))
    print(f"Đã lưu {root / 'ablation_table.csv'} và ablation_table.md")

if __name__ == "__main__":
    main()
