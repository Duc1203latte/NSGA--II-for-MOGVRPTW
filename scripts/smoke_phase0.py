"""Chạy thử decoder: tiêu chí xong giai đoạn 0 (chạy được, chưa yêu cầu khớp số bài báo)."""
import random

import pandas as pd

from src.instance import ROOT, load_instance
from src.decoder import evaluate_detail, evaluate_routes_detail

# 1. Nạp đủ 9 cấu hình Solomon + case29, in số khách và tổng demand
for name, n in [("C102", 25), ("R201", 25), ("RC202", 25), ("C102", 50), ("R201", 50),
                ("RC202", 50), ("C102", 100), ("R201", 100), ("RC201", 100), ("case29", 29)]:
    inst = load_instance(name, n)
    print(f"{inst.name:12s} n={inst.n:3d}  tổng demand={inst.demand.sum():8.1f} kg  "
          f"R={inst.capacity:.0f}  xuất phát={inst.depart_time:.0f} phút")

'''# 2. Một hoán vị ngẫu nhiên trên C102-25 (seed 0 để lần nào chạy cũng ra cùng số)
inst = load_instance("C102", 25)
perm = list(range(1, inst.n + 1))
random.Random(0).shuffle(perm)
print("\nC102-25, hoán vị ngẫu nhiên:", evaluate(perm, inst))'''

# 3. Ba bộ tuyến của bài báo trên case29
'''inst = load_instance("case29", 29)
fx = pd.read_csv(ROOT / "data/paper/fixture_routes.csv")
for table, g in fx.groupby("table"):
    routes = [[int(c) for c in str(s).split("-")] for s in g["sequence"]]  # "16-15" -> [16, 15]
    d = evaluate_routes_detail(routes, inst)
    print(f"\nTable {table} ({g['scenario'].iloc[0]}): {d['n_vehicles']} xe, {d['total_km']:.2f} km")
    print(f"  F1={d['F1']:.2f}  F2={d['F2']:.2f}  F3={d['F3']:.2f}  F4={d['F4']:.2f}")
    print(f"  f1={d['f1']:.2f}  f2={d['f2']:.2f}  f3={d['f3']:.4f}  "
          f"(sớm {d['early_min']:.1f} phút, muộn {d['late_min']:.1f} phút)")'''

# 2. Một hoán vị ngẫu nhiên trên C102-25 (seed 0 để lần nào chạy cũng ra cùng số),
#    cắt tuyến theo cả hai cách
inst = load_instance("C102", 25)
perm = list(range(1, inst.n + 1))
random.Random(0).shuffle(perm)
print("\nC102-25, hoán vị ngẫu nhiên:")
for rule in ("capacity", "capacity_time"):
    inst.params["split_rule"] = rule          # chỉ đổi tạm trong script này, không sửa config
    d = evaluate_detail(perm, inst)
    print(f"  {rule:14s} {d['n_vehicles']:2d} xe  f1={d['f1']:.2f}  f2={d['f2']:.2f}  "
          f"f3={d['f3']:.4f}  muộn {d['late_min']:.0f} phút")

# 3. Ba bộ tuyến của bài báo trên case29, tính theo cả hai cách tính hài lòng
fx = pd.read_csv(ROOT / "data/paper/fixture_routes.csv")
for mode in ("arrival", "service_start"):
    inst = load_instance("case29", 29)
    inst.params["satisfaction_time"] = mode   # chỉ đổi tạm trong script này, không sửa config
    print(f"\n===== satisfaction_time = {mode} =====")
    for table, g in fx.groupby("table"):
        routes = [[int(c) for c in str(s).split("-")] for s in g["sequence"]]  # "16-15" -> [16, 15]
        d = evaluate_routes_detail(routes, inst)
        print(f"\nTable {table} ({g['scenario'].iloc[0]}): {d['n_vehicles']} xe, {d['total_km']:.2f} km")
        print(f"  F1={d['F1']:.2f}  F2={d['F2']:.2f}  F3={d['F3']:.2f}  F4={d['F4']:.2f}")
        print(f"  f1={d['f1']:.2f}  f2={d['f2']:.2f}  f3={d['f3']:.4f}  "
              f"(sớm {d['early_min']:.1f} phút, muộn {d['late_min']:.1f} phút)")

