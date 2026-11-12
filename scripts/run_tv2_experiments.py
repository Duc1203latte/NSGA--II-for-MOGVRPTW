"""Thí nghiệm TV2: baseline / init_only / ls_only / both (mọi cải tiến khác TẮT).

CHẠY TRÊN HARNESS TẠM scripts/tv2_harness.py (src/nsga2.py của TV1 chưa có) -> kết quả SƠ BỘ.

    python -m scripts.run_tv2_experiments --preset main --tag main_gen200
    python -m scripts.run_tv2_experiments --preset main --tag main_budget --max-evals 16080 --n-gen 100000
    python -m scripts.run_tv2_experiments --preset tune --seeds 100-104 --tag tune
    python -m scripts.run_tv2_experiments --analyze-only --tag main_gen200

Đầu ra (results/tv2/<tag>/, không đưa lên git):
    runs/<instance>__<variant>__s<seed>.npz   front cuối, quần thể đầu, lịch sử front 1
    runs.csv        một dòng mỗi run: HV, IGD, SP, #Pareto, #eval, thời gian, bộ đếm LS, vi phạm đội xe
    summary.csv     mean ± std theo (instance, variant), delta HV so với 'off'
    hv_history.csv  HV front 1 theo generation (cùng chuẩn hoá) cho biểu đồ hội tụ
    metadata.json   config, commit, python, seed, thời điểm, tham số dòng lệnh

Chuẩn hoá: mỗi instance một reference set = tập không bị trội của MỌI front cuối (mọi variant, mọi
seed trong cùng tag); min-max theo reference set đó; HV với ref point trong config (1.1, 1.1, 1.1).
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from src.instance import ROOT, load_config, load_instance

FLAGS = ("init_smart", "local_search", "diversity", "dp_split", "adaptive_rates")

MAIN = {
    "off": {},
    "init_only": {"flags": {"init_smart": True}},
    "ls_only": {"flags": {"local_search": True}},
    "both": {"flags": {"init_smart": True, "local_search": True}},
}

# Tuning một-tham-số-một-lần quanh giá trị mặc định, CHỈ trên seed tuning (100..104)
TUNE = {
    "off": {},
    "init_default": {"flags": {"init_smart": True}},
    "init_r10_10_80": {"flags": {"init_smart": True},
                       "init": {"ratios": {"nn": 0.1, "tw": 0.1, "random": 0.8}}},
    "init_r30_30_40": {"flags": {"init_smart": True},
                       "init": {"ratios": {"nn": 0.3, "tw": 0.3, "random": 0.4}}},
    "ls_default": {"flags": {"local_search": True}},
    "ls_p01": {"flags": {"local_search": True}, "ls": {"p_ls": 0.1}},
    "ls_pareto": {"flags": {"local_search": True}, "ls": {"acceptance": "pareto"}},
    "ls_drift_eval": {"flags": {"local_search": True}, "ls": {"split_drift_policy": "evaluate_actual"}},
    "ls_evals20": {"flags": {"local_search": True}, "ls": {"max_candidate_evals": 20}},
}
PRESETS = {"main": MAIN, "tune": TUNE}


def parse_seeds(s: str) -> list[int]:
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def build_cfg(base: dict, spec: dict, ls_override: dict, init_override: dict) -> dict:
    cfg = copy.deepcopy(base)
    imp = cfg["improvements"]
    for f in FLAGS:
        if f in imp:
            imp[f] = False
    imp.update(spec.get("flags", {}))
    imp["init_smart_params"] = {**imp["init_smart_params"], **init_override, **spec.get("init", {})}
    imp["local_search_params"] = {**imp["local_search_params"], **ls_override, **spec.get("ls", {})}
    return cfg


def _one(job: dict) -> dict:
    from scripts.tv2_harness import run
    inst = load_instance(job["name"], job["n"])
    r = run(inst, job["cfg"], job["seed"], n_pop=job["n_pop"], n_gen=job["n_gen"],
            max_evals=job["max_evals"])
    mask = r.front_mask()
    hist_F = np.concatenate(r.history_front) if r.history_front else np.zeros((0, 3))
    hist_g = np.concatenate([np.full(len(h), g) for g, h in enumerate(r.history_front)])
    np.savez_compressed(job["path"], F=r.F, front_mask=mask, fleet_ok=r.fleet_ok, init_F=r.init_F,
                        hist_F=hist_F, hist_gen=hist_g, hist_evals=np.array(r.history_evals))
    lc = r.ls_counters
    return {
        "instance": inst.name, "variant": job["variant"], "seed": job["seed"],
        "n_gen_done": r.n_gen_done, "n_evals": r.n_evals, "elapsed_s": round(r.elapsed_s, 3),
        "n_front": int(mask.sum()), "n_pareto_unique": int(len(np.unique(r.F[mask], axis=0))),
        "fleet_viol_pop": int((~r.fleet_ok).sum()), "fleet_viol_front": int((~r.fleet_ok[mask]).sum()),
        "init_sources": json.dumps({s: r.init_sources.count(s) for s in sorted(set(r.init_sources))}),
        **{k: lc.get(k, 0) for k in ("n_ls_calls", "n_ls_triggered", "n_ls_candidate_evals",
                                     "n_ls_accepted", "n_ls_rejected_split",
                                     "n_ls_rejected_feasibility", "n_ls_rejected_no_improve",
                                     "n_ls_split_drift", "n_real_model_evals")},
        "ls_elapsed_s": round(lc.get("elapsed_s", 0.0), 3),
        "npz": str(Path(job["path"]).relative_to(ROOT)),
    }


# --------------------------------------------------------------------------- phân tích
def analyze(out: Path, ref_point) -> None:
    from scripts.tv2_harness import Normalizer, hypervolume, igd, nondominated, spacing
    rows = list(csv.DictReader(open(out / "runs_raw.csv", encoding="utf-8")))
    by_inst: dict[str, list[dict]] = {}
    for r in rows:
        by_inst.setdefault(r["instance"], []).append(r)
    hist_rows, final_rows = [], []
    for inst_name, rs in by_inst.items():
        data = {id(r): np.load(ROOT / r["npz"]) for r in rs}
        fronts = {id(r): data[id(r)]["F"][data[id(r)]["front_mask"]] for r in rs}
        ref = nondominated(np.vstack(list(fronts.values())))
        norm = Normalizer(ref)
        ref_n = norm(ref)
        np.savetxt(out / f"refset_{inst_name}.csv", ref, delimiter=",", header="g1_f1,g2_f2,g3_1mf3")
        for r in rs:
            d = data[id(r)]
            Fn = norm(nondominated(fronts[id(r)]))
            init_front = nondominated(d["init_F"])
            r2 = dict(r)
            r2.update(hv=hypervolume(Fn, ref_point), igd=igd(Fn, ref_n), sp=spacing(Fn),
                      init_hv=hypervolume(norm(init_front), ref_point),
                      ref_lo=json.dumps(norm.lo.tolist()), ref_hi=json.dumps(norm.hi.tolist()))
            final_rows.append(r2)
            hg, hF, he = d["hist_gen"], d["hist_F"], d["hist_evals"]
            for g in range(int(hg.max()) + 1 if len(hg) else 0):
                hist_rows.append({"instance": inst_name, "variant": r["variant"], "seed": r["seed"],
                                  "gen": g, "evals": int(he[g]),
                                  "hv": hypervolume(norm(hF[hg == g]), ref_point)})
    keys = list(final_rows[0].keys())
    with open(out / "runs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(final_rows)
    with open(out / "hv_history.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["instance", "variant", "seed", "gen", "evals", "hv"])
        w.writeheader()
        w.writerows(hist_rows)
    summarize(out, final_rows)


def summarize(out: Path, rows: list[dict]) -> None:
    from scipy.stats import wilcoxon
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        groups.setdefault((r["instance"], r["variant"]), []).append(r)
    metrics = ["hv", "igd", "sp", "init_hv", "n_pareto_unique", "n_evals", "elapsed_s",
               "n_ls_accepted", "n_ls_candidate_evals", "n_ls_rejected_split", "fleet_viol_front",
               "n_gen_done"]
    summ = []
    for (inst, var), rs in sorted(groups.items()):
        rs = sorted(rs, key=lambda r: int(r["seed"]))
        row = {"instance": inst, "variant": var, "n_seeds": len(rs)}
        for m in metrics:
            v = np.array([float(r[m]) for r in rs])
            row[f"{m}_mean"] = v.mean()
            row[f"{m}_std"] = v.std(ddof=1) if len(v) > 1 else 0.0
        base = sorted(groups.get((inst, "off"), []), key=lambda r: int(r["seed"]))
        if base and var != "off" and [r["seed"] for r in base] == [r["seed"] for r in rs]:
            a = np.array([float(r["hv"]) for r in rs])
            b = np.array([float(r["hv"]) for r in base])
            row["delta_hv"] = a.mean() - b.mean()
            row["wins_vs_off"] = int((a > b).sum())
            diff = a - b
            # chỉ để tham khảo; kiểm định chính thức của nhóm do TV3 thực hiện
            row["p_signed_rank_indicative"] = (wilcoxon(a, b).pvalue
                                               if len(a) >= 5 and np.any(diff != 0) else np.nan)
        summ.append(row)
    keys = sorted({k for r in summ for k in r}, key=lambda k: (k not in ("instance", "variant", "n_seeds"), k))
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(summ)
    print(f"{'instance':12s} {'variant':16s} {'HV mean±std':>18s} {'dHV':>8s} {'win':>4s} "
          f"{'IGD':>8s} {'#eval':>8s} {'time s':>7s} {'LSacc':>7s}")
    for r in summ:
        print(f"{r['instance']:12s} {r['variant']:16s} {r['hv_mean']:9.4f}±{r['hv_std']:.4f} "
              f"{r.get('delta_hv', 0):+8.4f} {r.get('wins_vs_off', ''):>4} {r['igd_mean']:8.4f} "
              f"{r['n_evals_mean']:8.0f} {r['elapsed_s_mean']:7.1f} {r['n_ls_accepted_mean']:7.0f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=list(PRESETS), default="main")
    ap.add_argument("--variants", default="", help="lọc variant, phân cách dấu phẩy")
    ap.add_argument("--instances", default="C102:25,R201:50,RC201:100")
    ap.add_argument("--seeds", default="0-9")
    ap.add_argument("--n-pop", type=int, default=None)
    ap.add_argument("--n-gen", type=int, default=None)
    ap.add_argument("--max-evals", type=int, default=None)
    ap.add_argument("--ls-param", action="append", default=[], help="key=json_value (ghi đè)")
    ap.add_argument("--init-param", action="append", default=[], help="key=json_value (ghi đè)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--tag", required=True)
    ap.add_argument("--analyze-only", action="store_true")
    args = ap.parse_args()

    base = load_config()
    out = ROOT / base["experiment"]["results_dir"] / "tv2" / args.tag
    ref_point = base["metrics"]["hv_ref_point"]
    if args.analyze_only:
        analyze(out, ref_point)
        return 0

    ls_o = {k: json.loads(v) for k, v in (s.split("=", 1) for s in args.ls_param)}
    init_o = {k: json.loads(v) for k, v in (s.split("=", 1) for s in args.init_param)}
    variants = PRESETS[args.preset]
    if args.variants:
        variants = {k: v for k, v in variants.items() if k in args.variants.split(",")}
    insts = [(s.split(":")[0], int(s.split(":")[1])) for s in args.instances.split(",")]
    seeds = parse_seeds(args.seeds)
    n_pop = args.n_pop or base["nsga2"]["n_pop"]
    n_gen = base["nsga2"]["n_gen"] if args.n_gen is None else args.n_gen
    (out / "runs").mkdir(parents=True, exist_ok=True)

    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                                capture_output=True, text=True, cwd=ROOT).stdout.strip())
    cfgs = {v: build_cfg(base, spec, ls_o, init_o) for v, spec in variants.items()}
    meta = {"note": "HARNESS TV2 tạm (scripts/tv2_harness.py), KHÔNG phải nsga2.py của TV1 - sơ bộ",
            "commit": sha, "dirty_tracked_files": dirty, "python": sys.version,
            "platform": platform.platform(), "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "args": vars(args), "n_pop": n_pop, "n_gen": n_gen, "seeds": seeds,
            "instances": insts, "variants": {v: cfgs[v]["improvements"] for v in cfgs},
            "split_rule": base["split_rule"], "satisfaction_time": base["satisfaction_time"]}
    jobs = [{"name": nm, "n": n, "seed": s, "variant": v, "cfg": cfgs[v], "n_pop": n_pop,
             "n_gen": n_gen, "max_evals": args.max_evals,
             "path": str(out / "runs" / f"{nm}-{n}__{v}__s{s}.npz")}
            for nm, n in insts for v in variants for s in seeds]
    print(f"{len(jobs)} runs, {args.workers} workers -> {out}", flush=True)
    rows, t0 = [], time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_one, j): j for j in jobs}
        for k, fu in enumerate(as_completed(futs), 1):
            rows.append(fu.result())                 # lỗi ở run nào thì dừng hẳn, không bỏ qua
            if k % 10 == 0 or k == len(jobs):
                print(f"  {k}/{len(jobs)} xong, {time.perf_counter() - t0:.0f}s", flush=True)
    rows.sort(key=lambda r: (r["instance"], r["variant"], r["seed"]))
    with open(out / "runs_raw.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    meta["wall_s"] = time.perf_counter() - t0
    (out / "metadata.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    analyze(out, ref_point)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
