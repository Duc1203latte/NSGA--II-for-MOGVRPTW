"""Giai đoạn 3: ablation các cải tiến đã merge (I, L của TV2; D của TV3; P, A của TV4).

    I: init_smart, tỉ lệ nn/tw/random = 20/20/60 (TV2 tuning trên seed 100-104, giữ mặc định)
    L: local_search, split_drift_policy = evaluate_actual (TV2 tuning: tốt nhất trên 2/3 instance)
    D: diversity, SDE k = 1, tắt archive (archive_size = n_pop không giúp gì, xem README)
    P: dp_split chế độ polish, K = 10 vector trọng số (TV4 đã tuning trên seed 100-104)
    A: Pc/Pm thích nghi với khoảng adapt_v1 (TV4 đã tuning; bản mặc định làm R201-50 kém đi)

Cấu hình (G nhóm): baseline, chỉ bật từng nhóm, bật tất cả, tắt đúng một nhóm (2G + 2 cấu hình).
Mọi cấu hình cùng bộ seed. Dùng lại hàm chạy và lập bảng của scripts/tv3_ablation.py, chỉ thay cách
bật nhóm: mỗi nhóm là một danh sách ghi đè --set thay vì một cờ.

    python -m scripts.ablation --exp abl_g200 --seeds 0-19
    python -m scripts.ablation --exp abl5_g200 --groups D,P,A,I,L --seeds 0-19
    python -m scripts.ablation --exp abl5_g1000 --groups D,P,A,I,L --seeds 0-9 --set nsga2.n_gen=1000
    python -m scripts.ablation --exp abl5_g200 --groups D,P,A,I,L --analyze-only
"""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
from scripts.tv3_ablation import DEFAULT_INSTANCES, _job, ablation_configs, build_table, to_markdown
from scripts.tv4_tune_configs import V1_RANGES
from src.instance import load_config
from src.runner import apply_overrides, results_root

IMP = "improvements."
GROUPS = {
    "D": [IMP + "diversity=true", IMP + "diversity_params.density=sde",
          IMP + "diversity_params.k=1", IMP + "diversity_params.archive=false"],
    "P": [IMP + "dp_split=true", IMP + "dp_split_params.mode=polish",
          IMP + "dp_split_params.polish_k=10"],
    "A": [IMP + "adaptive_rates=true", *V1_RANGES],
    "I": [IMP + "init_smart=true"],
    "L": [IMP + "local_search=true", IMP + "local_search_params.split_drift_policy=evaluate_actual"],
}

def parse_seeds(text: str) -> list[int]:
    """'0-19' hoặc '0,1,2'."""
    if "-" in text:
        lo, hi = text.split("-")
        return list(range(int(lo), int(hi) + 1))
    return [int(s) for s in text.split(",")]

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Ablation các cải tiến (giai đoạn 3)")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--instances", default=DEFAULT_INSTANCES, help="dạng TÊN:n, cách nhau bởi dấu phẩy")
    ap.add_argument("--seeds", help="ví dụ 0-19 hoặc 0,1,2; mặc định lấy experiment.seeds trong config")
    ap.add_argument("--set", action="append", default=[], metavar="KHOÁ=GIÁ_TRỊ",
                    help="ghi đè cho mọi cấu hình, ví dụ nsga2.n_gen=1000")
    ap.add_argument("--groups", default="D,P,A", help=f"chọn trong {list(GROUPS)}, ví dụ D,P,A,I,L")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--analyze-only", action="store_true")
    args = ap.parse_args(argv)

    base_cfg = apply_overrides(load_config(), args.set)
    seeds = parse_seeds(args.seeds) if args.seeds else base_cfg["experiment"]["seeds"]
    instances = [(s.split(":")[0], int(s.split(":")[1])) for s in args.instances.split(",")]
    groups = [g.strip() for g in args.groups.split(",")]
    unknown = set(groups) - set(GROUPS)
    if unknown:
        raise ValueError(f"nhóm không có: {sorted(unknown)}; chỉ nhận {list(GROUPS)}")
    configs = ablation_configs(groups)

    if not args.analyze_only:
        # mỗi việc là một (instance, cấu hình, seed) để chia đều cho các tiến trình
        jobs = [(args.exp, name, n, c, apply_overrides(base_cfg, [o for g in on for o in GROUPS[g]]), [s])
                for name, n in instances for c, on in configs.items() for s in seeds]
        # việc nặng chạy trước (có local search, rồi instance lớn) để các tiến trình kết thúc gần nhau
        jobs.sort(key=lambda j: ("L" not in configs[j[3]], -j[2]))
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for i, done in enumerate(pool.map(_job, jobs), 1):
                if i % 50 == 0 or i == len(jobs):
                    print(f"[{i}/{len(jobs)}] xong {done}", flush=True)

    root = results_root(base_cfg) / args.exp
    inst_names = sorted(p.name for p in root.iterdir() if p.is_dir())
    table = build_table(args.exp, inst_names, list(configs), base_cfg)
    table.to_csv(root / "ablation_table.csv", index=False, encoding="utf-8")
    (root / "ablation_table.md").write_text(to_markdown(table), encoding="utf-8")
    print(to_markdown(table))

if __name__ == "__main__":
    main()
