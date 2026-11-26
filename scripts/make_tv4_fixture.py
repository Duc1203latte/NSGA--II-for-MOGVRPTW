"""Sinh mốc baseline cho tests/test_tv4_integration.py từ nsga2.py CHƯA SỬA của main.

Mốc KHÔNG được sinh từ nsga2.py của branch feat/dp-split. Script lấy nsga2.py đúng như nằm trên
commit merge-base của origin/main (git show <sha>:src/nsga2.py), nạp nó như một module riêng và chạy
với mọi cờ tắt. decoder.py và instance.py của cây làm việc phải trùng với commit đó (script kiểm).

Cách chạy lại (chỉ khi cố ý đổi mốc, và phải ghi lý do vào PR):
    python -m scripts.make_tv4_fixture                # dùng git merge-base HEAD origin/main
    python -m scripts.make_tv4_fixture --sha <commit> # hoặc chỉ định commit

Kết quả: tests/fixtures/tv4_alloff_main.json (hoán vị, F dạng float.hex, n_evals, front).
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

from src.instance import ROOT, load_config, load_instance

CASES = [("C102", 25), ("R201", 50)]
SEEDS = [0, 1]
N_GEN = 10
OUT = ROOT / "tests" / "fixtures" / "tv4_alloff_main.json"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout


def load_main_nsga2(sha: str):
    """Nạp nsga2.py của commit sha thành module tách biệt với src/nsga2.py của cây làm việc."""
    for f in ("src/decoder.py", "src/instance.py"):
        if subprocess.run(["git", "diff", "--quiet", sha, "--", f], cwd=ROOT).returncode != 0:
            raise SystemExit(f"{f} trong cây làm việc khác commit {sha[:7]}: mốc sẽ không sạch")
    src = git("show", f"{sha}:src/nsga2.py")
    tmp = Path(tempfile.mkdtemp()) / "nsga2_main.py"
    tmp.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("nsga2_main", tmp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", default=None)
    sha = ap.parse_args().sha or git("merge-base", "HEAD", "origin/main").strip()
    nsga2_main = load_main_nsga2(sha)

    cfg = copy.deepcopy(load_config())
    cfg["nsga2"]["n_gen"] = N_GEN
    for k in cfg.get("improvements", {}):
        if isinstance(cfg["improvements"][k], bool):
            cfg["improvements"][k] = False      # mọi cờ tắt

    out = {"_note": "Sinh bởi scripts/make_tv4_fixture.py từ src/nsga2.py của commit main (không phải "
                    "của feat/dp-split). Mọi cờ tắt, n_gen=%d, các tham số khác theo config.yaml." % N_GEN,
           "main_sha": sha, "n_gen": N_GEN, "n_pop": cfg["nsga2"]["n_pop"], "cases": {}}
    for name, n in CASES:
        inst = load_instance(name, n, cfg)
        for seed in SEEDS:
            r = nsga2_main.run(inst, cfg, seed)
            out["cases"][f"{inst.name}/seed{seed}"] = {
                "pop": r["pop"],
                "F_hex": [[float(x).hex() for x in row] for row in r["F"]],
                "CV": [float(x) for x in r["CV"]],
                "front": [int(i) for i in r["front"]],
                "n_evals": int(r["n_evals"]),
            }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out), encoding="utf-8")
    print(f"ghi {OUT.relative_to(ROOT)} từ main {sha[:7]}: {len(out['cases'])} run")


if __name__ == "__main__":
    main()
