"""Chụp mốc hồi quy all-off (3 instance x 2 seed) cho harness TV2.

    python -m scripts.tv2_regression_snapshot            # ghi tests/fixtures/tv2_alloff_snapshot.json
    python -m scripts.tv2_regression_snapshot --check    # so với mốc đã lưu, exit 1 nếu lệch

Mốc lưu hoán vị, mục tiêu dạng float.hex (so khớp từng bit) và trạng thái RNG cuối. Khi TV1 bàn giao
src/nsga2.py, chạy lại script này trỏ vào baseline thật (giai đoạn 3, trước khi merge).
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys

from scripts.tv2_harness import run
from src.instance import ROOT, load_config, load_instance

FIXTURE = ROOT / "tests" / "fixtures" / "tv2_alloff_snapshot.json"
CASES = [("C102", 25), ("R201", 50), ("RC201", 100)]
SEEDS = [0, 1]
N_POP, N_GEN = 20, 8
FLAGS = ("init_smart", "local_search", "diversity", "dp_split", "adaptive_rates")


def all_off_cfg() -> dict:
    cfg = copy.deepcopy(load_config())
    for f in FLAGS:
        if f in cfg["improvements"]:
            cfg["improvements"][f] = False
    return cfg


def snapshot() -> dict:
    cfg = all_off_cfg()
    out = {"n_pop": N_POP, "n_gen": N_GEN, "split_rule": cfg["split_rule"],
           "satisfaction_time": cfg["satisfaction_time"], "runs": []}
    for name, n in CASES:
        inst = load_instance(name, n)
        for seed in SEEDS:
            r = run(inst, cfg, seed, n_pop=N_POP, n_gen=N_GEN, record_history=False)
            out["runs"].append({
                "instance": inst.name, "seed": seed, "perms": r.perms,
                "F_hex": [[float(x).hex() for x in row] for row in r.F],
                "n_evals": r.n_evals,
                "rng_state_end": json.loads(json.dumps(r.rng_state_end, default=int)),
            })
    return out


def load_fixture() -> dict:
    ref = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {k: v for k, v in ref.items() if not k.startswith("_")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    snap = snapshot()
    if args.check:
        ref = load_fixture()
        ok = ref == snap
        print("REGRESSION", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                             cwd=ROOT).stdout.strip()
    except OSError:
        sha = "unknown"
    snap_meta = {"_note": "mốc all-off của HARNESS TV2 (không phải nsga2.py của TV1)",
                 "_commit_at_capture": sha, "_python": sys.version.split()[0], **snap}
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(snap_meta, indent=1), encoding="utf-8")
    print("wrote", FIXTURE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
