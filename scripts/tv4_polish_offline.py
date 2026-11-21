"""Polish ngoại tuyến: áp dụng đúng thủ tục của mode=polish lên kết quả ĐÃ LƯU, không chạy lại tiến hoá.

Thủ tục là `src.nsga2.polish_front` (cùng hàm mà `nsga2.run` gọi khi mode=polish): K vector trọng số từ
lưới simplex tất định, scales = objective_scales(inst, g3_scale), gộp với quần thể cuối, bỏ trùng, lấy tập
không trội. Quần thể cuối của baseline (đã lưu trong .pkl) chính là quần thể trước polish, vì polish
không bốc số ngẫu nhiên nên run mode=polish và run baseline cùng seed có cùng quần thể cuối.

Trước khi xử lý, script CHỨNG MINH đường ngoại tuyến khớp đường trực tuyến: polish lại các run baseline của
`tv4_tune` (seed 100-104) rồi so từng bit với các run `dp_polish_k10` / `dp_polish_k30` đã lưu (do code
chạy trực tuyến sinh ra). Lệch một chút là dừng.

    python -m scripts.tv4_polish_offline --exp tv4_main --instances C102-25 R201-50
Ghi: results/<exp>/<instance>/{baseline_polish,baseline_eqtime_polish}/seed_XX.pkl (+ config_used.yaml).
"""
from __future__ import annotations
import argparse
import copy
import pickle
import time
from pathlib import Path

import numpy as np
import yaml

from src import nsga2
from src.instance import load_config, load_instance
from src.runner import results_root

PAIRS = [("baseline", "baseline_polish"), ("baseline_eqtime", "baseline_eqtime_polish")]


def load_pkl(path: Path) -> dict:
    with open(path, "rb") as f:
        return pickle.load(f)


def polish_result(res: dict, inst, dp_params: dict) -> dict:
    """Polish một kết quả đã lưu; trả về dict kết quả mới cùng khuôn với run mode=polish."""
    pop = [np.array(x) for x in res["pop"]]
    t = time.process_time()
    pol = nsga2.polish_front(pop, res["F"], res["CV"], inst, dp_params)
    cpu = time.process_time() - t
    new = dict(res)
    new.update(
        pop=[x.tolist() for x in pol["pop"]], F=pol["F"], CV=pol["CV"], W=pol["W"], front=pol["front"],
        n_evals=res["n_evals"] + pol["n_calls"], n_dp_calls=pol["n_calls"], dp_mode="polish",
        pre_polish={"pop": res["pop"], "F": res["F"].copy(), "CV": res["CV"].copy(), "front": res["front"].copy()},
        feasible_frac_pop=float(np.mean(pol["CV"] == 0)),
        feasible_frac_front=float(np.mean(pol["CV"][pol["front"]] == 0)),
        polish_cpu_s=cpu,
    )
    return new


def same_result(a: dict, b: dict) -> list[str]:
    """Các khoá khác nhau giữa hai kết quả polish (so từng bit)."""
    bad = []
    if a["pop"] != b["pop"]:
        bad.append("pop")
    for k in ("F", "CV", "front"):
        if not np.array_equal(a[k], b[k]):
            bad.append(k)
    if not np.array_equal(a["W"], b["W"], equal_nan=True):
        bad.append("W")
    for k in ("n_evals", "n_dp_calls"):
        if a[k] != b[k]:
            bad.append(k)
    return bad


def inst_of(res: dict, cfg: dict):
    name, n = res["instance"].rsplit("-", 1)
    return load_instance(name, int(n), cfg)


def verify_against_online(root: Path, instances: list[str], seeds=range(100, 105), tune_exp="tv4_tune") -> int:
    """Polish ngoại tuyến run baseline của tv4_tune == run dp_polish đã lưu. Trả về số run đã so."""
    n_checked = 0
    for inst_name in instances:
        for k in (10, 30):
            cfg_name = f"dp_polish_k{k}"
            with open(root / tune_exp / inst_name / cfg_name / "config_used.yaml", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            dp_params = cfg["improvements"]["dp_split_params"]
            assert dp_params["mode"] == "polish" and dp_params["polish_k"] == k
            for seed in seeds:
                base = load_pkl(root / tune_exp / inst_name / "baseline" / f"seed_{seed:02d}.pkl")
                online = load_pkl(root / tune_exp / inst_name / cfg_name / f"seed_{seed:02d}.pkl")
                if base["pop"] != online["pre_polish"]["pop"]:
                    raise AssertionError(f"{inst_name} {cfg_name} seed {seed}: quần thể cuối baseline != trước polish")
                offline = polish_result(base, inst_of(base, cfg), dp_params)
                bad = same_result(offline, online)
                if bad:
                    raise AssertionError(f"{inst_name} {cfg_name} seed {seed}: ngoại tuyến khác trực tuyến ở {bad}")
                n_checked += 1
    return n_checked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", default="tv4_main")
    ap.add_argument("--instances", nargs="+", default=["C102-25", "R201-50"])
    ap.add_argument("--k", type=int, default=None, help="polish_k; mặc định lấy từ config.yaml")
    ap.add_argument("--skip-verify", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    base_cfg = load_config()
    root = results_root(base_cfg)
    k = args.k or base_cfg["improvements"]["dp_split_params"]["polish_k"]

    if not args.skip_verify:
        n = verify_against_online(root, args.instances)
        print(f"kiểm chứng: polish ngoại tuyến khớp từng bit {n} run dp_polish trực tuyến của tv4_tune")

    for inst_name in args.instances:
        for src_cfg, out_cfg in PAIRS:
            src_dir, out_dir = root / args.exp / inst_name / src_cfg, root / args.exp / inst_name / out_cfg
            with open(src_dir / "config_used.yaml", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            cfg_pol = copy.deepcopy(cfg)
            cfg_pol["improvements"]["dp_split"] = True
            cfg_pol["improvements"]["dp_split_params"].update(mode="polish", polish_k=k)
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(out_dir / "config_used.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg_pol, f, allow_unicode=True, sort_keys=False)
            cpus = []
            for path in sorted(src_dir.glob("seed_*.pkl")):
                target = out_dir / path.name
                if target.exists() and not args.overwrite:
                    continue
                res = load_pkl(path)
                new = polish_result(res, inst_of(res, cfg_pol), cfg_pol["improvements"]["dp_split_params"])
                new["config_name"] = out_cfg
                with open(target, "wb") as f:
                    pickle.dump(new, f)
                cpus.append(new["polish_cpu_s"])
            if cpus:
                print(f"{inst_name} {out_cfg}: {len(cpus)} run, polish CPU {np.mean(cpus):.1f} s/run (K={k})")


if __name__ == "__main__":
    main()
