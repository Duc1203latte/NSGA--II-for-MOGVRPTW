"""Hình cho báo cáo và slide giai đoạn 4.

Hai nhóm hình, lưu ở docs/figures/final/:
  Trực quan bài toán (không cần kết quả thí nghiệm, trừ hình tuyến và lịch giao):
    f01_case29_map         kho và 29 khách của case thực tế, kích thước điểm theo nhu cầu
    f02_satisfaction       hàm hài lòng W(t) và tiền phạt F4 theo giờ đến, một khách Solomon
    f03_algorithm          sơ đồ vòng lặp NSGA-II và chỗ gắn ba cải tiến I, D, P
    f04_routes_case29      bộ tuyến của ba lời giải đầu mút (f1 nhỏ nhất, f2 nhỏ nhất, f3 lớn nhất)
    f05_timeline_case29    giờ đến từng khách so với khung giờ, lời giải f3 lớn nhất
  Kết quả:
    f06_pareto_2d          front baseline và I+D+P (chiếu f1-f3 và f1-f2), seed có HV trung vị
    f07_pareto_3d          như trên, không gian ba mục tiêu
    f08_convergence        HV trung bình theo thế hệ, 1000 thế hệ
    f09_hv_box             phân bố HV qua 20 seed, 200 thế hệ
    f10_ablation_heatmap   ΔHV của 11 cấu hình ablation so với baseline
    f11_paper_vs_ours      mức tăng HV so với NSGA-II của chính mình: bài báo và nhóm

    python -m scripts.plot_final              # vẽ tất cả
    python -m scripts.plot_final f04 f08      # chỉ vẽ vài hình

Cần có kết quả của scripts.final_runs (final_g200, final_g1000) và scripts.ablation (abl5_g200,
abl5_g1000), cùng results/final_summary.csv.
"""
from __future__ import annotations
import pickle
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch
from src.decoder import evaluate_detail, satisfaction
from src.instance import ROOT, load_config, load_instance

OUT = ROOT / "docs" / "figures" / "final"
RES = ROOT / "results"

# Bảng màu phân loại (đã kiểm CVD cho 3 màu đầu, mọi cặp): màu đi theo đối tượng, không theo thứ hạng
C_BASE, C_IDP, C_ILDP, C_PAPER = "#257de0", "#f47230", "#00b894", "#6a4ce2"
INK, INK2, GRID, NEUTRAL = "#191919", "#666666", "#e6e6e6", "#b5b5b5"
NAMES = {"baseline": "NSGA-II gốc", "IDP": "I+D+P (cấu hình cuối)", "ILDP": "I+L+D+P (tham khảo)"}
COLORS = {"baseline": C_BASE, "IDP": C_IDP, "ILDP": C_ILDP}
INSTS = ["C102-25", "R201-25", "RC202-25", "C102-50", "R201-50", "RC202-50",
         "C102-100", "R201-100", "RC201-100", "case29-29"]

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9.5, "axes.titlesize": 10.5,
    "axes.edgecolor": NEUTRAL, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.axisbelow": True, "legend.frameon": False, "figure.dpi": 100,
    "savefig.dpi": 170, "savefig.bbox": "tight", "text.color": INK,
})

def label(inst: str) -> str:
    return inst.replace("-29", "")

def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", facecolor="white")
    plt.close(fig)
    print(f"đã lưu {OUT / name}.png")

def load_run(exp: str, inst: str, config: str, seed: int) -> dict:
    with open(RES / exp / inst / config / f"seed_{seed:02d}.pkl", "rb") as f:
        return pickle.load(f)

def median_seed(exp: str, inst: str, config: str) -> int:
    """Seed có HV gần trung vị nhất, để hình front đại diện chứ không chọn run đẹp nhất."""
    r = pd.read_csv(RES / exp / inst / "per_run.csv")
    r = r[r.config == config]
    return int(r.iloc[(r.HV - r.HV.median()).abs().argmin()].seed)

def front_points(res: dict) -> np.ndarray:
    """Front cuối, cột 3 đổi về f3 thật (trong code lưu 1 - f3)."""
    F = res["F"][res["front"]].copy()
    F[:, 2] = 1 - F[:, 2]
    return F

def solution_detail(res: dict, i: int, inst, cfg: dict) -> dict:
    """Bộ tuyến của cá thể i. Cá thể do polish sinh ra (W không NaN) cắt tuyến bằng DP."""
    perm = [int(x) for x in res["pop"][i]]
    W = res.get("W")
    if W is None or np.isnan(W[i]).all():
        return evaluate_detail(perm, inst)
    from src.improvements.dp_split import evaluate_dp, objective_scales
    scales = objective_scales(inst, cfg["improvements"]["dp_split_params"]["g3_scale"])
    return evaluate_dp(perm, inst, W[i], scales)

# --------------------------------------------------------------------- trực quan bài toán

def f01_case29_map() -> None:
    inst = load_instance("case29", 29)
    xy, dem = inst.coords, inst.demand / 1000          # tấn
    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    ax.scatter(xy[1:, 0], xy[1:, 1], s=40 + 90 * dem[1:], color=C_BASE, alpha=0.85,
               edgecolor="white", linewidth=1.2, zorder=3)
    ax.scatter(*xy[0], s=190, marker="s", color=INK, zorder=4)
    ax.annotate("Kho (0)", xy[0], xytext=(8, -4), textcoords="offset points", fontsize=9.5, weight="bold")
    for i in range(1, inst.n + 1):
        ax.annotate(str(i), xy[i], xytext=(6, 4), textcoords="offset points", fontsize=8, color=INK2)
    for t in (0.5, 1.5, 2.5):                           # chú giải kích thước
        ax.scatter([], [], s=40 + 90 * t, color=C_BASE, alpha=0.85, label=f"{t:g} tấn")
    ax.legend(title="Nhu cầu", loc="upper right", labelspacing=1.2, borderpad=0.8)
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.set_aspect("equal")
    ax.set_title("Case thực tế: 1 kho, 29 khách, tổng nhu cầu 31.3 tấn, xe chở 4 tấn", loc="left")
    save(fig, "f01_case29_map")

def f02_satisfaction() -> None:
    et, eta, ltb, lt = 882, 912, 967, 997               # khách Solomon, phút
    p = load_config()["cost"]
    t = np.linspace(850, 1030, 721)
    W = np.array([satisfaction(x, et, eta, ltb, lt) for x in t])
    F4 = p["alpha"] * np.maximum(eta - t, 0) / 60 + p["beta"] * np.maximum(t - ltb, 0) / 60
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.4, 5.6), sharex=True, gridspec_kw={"hspace": 0.25})
    for ax in (a1, a2):
        ax.axvspan(eta, ltb, color=C_BASE, alpha=0.08, lw=0)
        for x in (et, eta, ltb, lt):
            ax.axvline(x, color=NEUTRAL, lw=0.8, ls="--", zorder=1)
    a1.plot(t, W, color=C_BASE, lw=2)
    a1.set_ylabel("Hài lòng W(t)")
    a1.set_ylim(-5, 122)
    for x, s in ((et, "ET"), (eta, "ETa"), (ltb, "LTb"), (lt, "LT")):
        a1.text(x, 110, s, ha="center", fontsize=8.5, color=INK2)
    a1.text((eta + ltb) / 2, 50, "khung kỳ vọng\nW = 100", ha="center", fontsize=8.5, color=INK2)
    a1.set_title("Một khách Solomon: khung quy định [ET, LT] nới 30 phút mỗi đầu so với khung kỳ vọng [ETa, LTb]",
                 loc="left")
    a2.plot(t, F4, color=C_IDP, lw=2)
    a2.set_ylabel("Tiền phạt F4 (CNY)")
    a2.set_xlabel("Giờ xe đến (phút tính từ lúc kho mở cửa)")
    a2.text(852, 38, f"đến sớm: chờ tới ETa,\nphạt α = {p['alpha']} CNY/giờ chờ", fontsize=8.5, color=INK2)
    a2.text(1003, 6, f"đến muộn:\nphạt β = {p['beta']}\nCNY/giờ muộn", fontsize=8.5, color=INK2)
    save(fig, "f02_satisfaction")

def _box(ax, xy, w, h, text, accent=False):
    ax.add_patch(FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc="#fff3ec" if accent else "#f4f6f9", ec=C_IDP if accent else NEUTRAL,
                                lw=1.6 if accent else 1.0))
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center", fontsize=9)

def _arrow(ax, a, b, text=None, rad=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12, color=INK2, lw=1.2,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.12, text, ha="center", fontsize=8, color=INK2)

def f03_algorithm() -> None:
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.2)
    ax.axis("off")
    _box(ax, (0.2, 3.6), 2.3, 1.0, "Khởi tạo 80 hoán vị\n[I] 20% gần nhất, 20% theo giờ,\n60% ngẫu nhiên", True)
    _box(ax, (3.3, 3.6), 3.0, 1.0, "Decoder: hoán vị → tuyến\ncắt khi quá tải hoặc sẽ đến muộn\n→ (f1 chi phí, f2 CO₂, f3 hài lòng)")
    _box(ax, (7.1, 3.6), 2.7, 1.0, "Chọn lọc môi trường\nsắp không trội +\n[D] mật độ SDE thay crowding", True)
    _box(ax, (7.1, 1.7), 2.7, 1.0, "Giải đấu nhị phân\nchọn cha mẹ")
    _box(ax, (3.3, 1.7), 3.0, 1.0, "Lai ghép OX (pc 0.7)\nĐột biến đảo đoạn / đổi chỗ (pm)\n→ 80 con, chấm bằng decoder")
    _box(ax, (0.2, 1.7), 2.3, 1.0, "Gộp cha mẹ + con\n(160 cá thể), bỏ trùng")
    _box(ax, (3.3, 0.1), 3.0, 1.0, "[P] Polish sau thế hệ cuối:\ncắt tuyến lại bằng quy hoạch động\nvới 10 vector trọng số", True)
    _box(ax, (7.1, 0.1), 2.7, 1.0, "Front Pareto\n(tập lời giải không trội)")
    _arrow(ax, (2.5, 4.1), (3.3, 4.1))
    _arrow(ax, (6.3, 4.1), (7.1, 4.1))
    _arrow(ax, (8.45, 3.6), (8.45, 2.7))
    _arrow(ax, (7.1, 2.2), (6.3, 2.2))
    _arrow(ax, (3.3, 2.2), (2.5, 2.2))
    _arrow(ax, (2.5, 2.5), (7.1, 3.7))
    ax.text(4.6, 2.95, "lặp 200 hoặc 1000 thế hệ", ha="center", fontsize=8, color=INK2, rotation=14)
    _arrow(ax, (1.35, 1.7), (3.3, 0.6), "hết thế hệ", rad=0.15)
    _arrow(ax, (6.3, 0.6), (7.1, 0.6))
    ax.legend(handles=[Patch(fc="#fff3ec", ec=C_IDP, label="cải tiến được giữ: I, D, P"),
                       Patch(fc="#f4f6f9", ec=NEUTRAL, label="NSGA-II gốc")],
              loc="upper left", bbox_to_anchor=(0.0, 1.06), ncol=2)
    save(fig, "f03_algorithm")

def _extremes(exp: str, inst_name: str, config: str):
    """Ba lời giải đầu mút trên front gộp mọi seed: f1 nhỏ nhất, f2 nhỏ nhất, f3 lớn nhất."""
    best = {}
    for path in sorted((RES / exp / inst_name / config).glob("seed_*.pkl")):
        with open(path, "rb") as f:
            res = pickle.load(f)
        for i in res["front"]:
            f1, f2, g3 = res["F"][i]
            for key, val in (("min_f1", (f1, f2)), ("min_f2", (f2, f1)), ("max_f3", (g3, f1))):
                if key not in best or val < best[key][0]:
                    best[key] = (val, res, i)
    return {k: (v[1], v[2]) for k, v in best.items()}

def _draw_routes(ax, inst, routes, title):
    xy = inst.coords
    for k, r in enumerate(routes, 1):
        path = np.array([xy[0]] + [xy[c] for c in r] + [xy[0]])
        ax.plot(path[:2, 0], path[:2, 1], color=NEUTRAL, lw=0.9, ls="--", zorder=1)    # chặng rời kho
        ax.plot(path[-2:, 0], path[-2:, 1], color=NEUTRAL, lw=0.9, ls="--", zorder=1)  # chặng về kho
        ax.plot(path[1:-1, 0], path[1:-1, 1], color=C_BASE, lw=1.6, zorder=2)
        for a, b in zip(path[1:-2], path[2:-1]):        # mũi tên giữa các khách
            m = (a + b) / 2
            ax.annotate("", xy=m + (b - a) * 0.04, xytext=m, zorder=3,
                        arrowprops=dict(arrowstyle="-|>", color=C_BASE, lw=1.0, mutation_scale=8))
        c = path[1]                                     # số xe đặt ở khách đầu tiên của tuyến
        ax.text(c[0] + 0.9, c[1] + 0.9, str(k), fontsize=8, weight="bold", ha="center", va="center", color=INK,
                bbox=dict(boxstyle="circle,pad=0.15", fc="white", ec=NEUTRAL, lw=0.8), zorder=5)
    ax.scatter(xy[1:, 0], xy[1:, 1], s=22, color=C_BASE, edgecolor="white", lw=0.8, zorder=4)
    ax.scatter(*xy[0], s=110, marker="s", color=INK, zorder=6)
    ax.set_aspect("equal")
    ax.set_title(title, loc="left", fontsize=9.5)
    ax.tick_params(labelsize=8)

def f04_routes_case29() -> None:
    cfg = load_config()
    inst = load_instance("case29", 29)
    ext = _extremes("final_g1000", "case29-29", "IDP")
    heads = {"min_f1": "Chi phí nhỏ nhất", "min_f2": "Khí thải nhỏ nhất", "max_f3": "Hài lòng lớn nhất"}
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.6))
    for ax, key in zip(axes, heads):
        res, i = ext[key]
        d = solution_detail(res, i, inst, cfg)
        title = (f"{heads[key]}\nf1 = {d['f1']:.0f} CNY · f2 = {d['f2']:.1f} kg · f3 = {d['f3']:.3f}\n"
                 f"{d['n_vehicles']} xe · {d['total_km']:.1f} km")
        _draw_routes(ax, inst, d["routes"], title)
    fig.suptitle("Ba lời giải đầu mút trên front của I+D+P, case thực tế (gộp 10 seed, 1000 thế hệ)\n"
                 "Số trong vòng tròn là số thứ tự xe (đặt cạnh khách đầu tiên); nét đứt là chặng rời kho và về kho",
                 x=0.01, ha="left", fontsize=10.5)
    save(fig, "f04_routes_case29")

def f05_timeline_case29() -> None:
    cfg = load_config()
    inst = load_instance("case29", 29)
    res, i = _extremes("final_g1000", "case29-29", "IDP")["max_f3"]
    d = solution_detail(res, i, inst, cfg)
    rows, y = [], 0
    for k, r in enumerate(d["routes"], 1):
        for c in r:
            rows.append((y, k, c))
            y += 1
        y += 0.6                                          # khoảng cách giữa các xe
    fig, ax = plt.subplots(figsize=(8.6, 9))
    status = {"đúng khung": (C_BASE, "o"), "đến sớm (chờ)": (C_IDP, "<"), "đến muộn": (C_ILDP, ">")}
    for yy, k, c in rows:
        et, lt = inst.tw_specified[c] / 60
        arr = d["arrival_times"][c] / 60
        ax.plot([et, lt], [yy, yy], color="#d5dde8", lw=6, solid_capstyle="round", zorder=1)
        s = "đúng khung" if et <= arr <= lt else ("đến sớm (chờ)" if arr < et else "đến muộn")
        col, mk = status[s]
        ax.scatter(arr, yy, color=col, marker=mk, s=46, zorder=3, edgecolor="white", lw=0.6)
    ax.set_yticks([r[0] for r in rows])
    ax.set_yticklabels([f"xe {k} · khách {c}" for _, k, c in rows], fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlabel("Giờ trong ngày")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v)}:{int(round(v % 1 * 60)):02d}"))
    ax.grid(axis="y", visible=False)
    used = set()
    for _, _, c in rows:
        et, lt = inst.tw_specified[c] / 60
        a = d["arrival_times"][c] / 60
        used.add("đúng khung" if et <= a <= lt else ("đến sớm (chờ)" if a < et else "đến muộn"))
    handles = [Line2D([], [], color="#d5dde8", lw=6, label="khung giờ khách [ET, LT]")]
    handles += [Line2D([], [], ls="", marker=mk, color=col, ms=7, label=f"xe đến: {s}")
                for s, (col, mk) in status.items() if s in used]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=len(handles), fontsize=8.5)
    ax.set_title(f"Giờ xe đến so với khung giờ: lời giải hài lòng lớn nhất của case thực tế "
                 f"(f3 = {d['f3']:.3f}, {d['n_vehicles']} xe)", loc="left", pad=28)
    save(fig, "f05_timeline_case29")

# --------------------------------------------------------------------- kết quả

PARETO_INSTS = ["C102-100", "RC201-100", "case29-29"]

def f06_pareto_2d() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 8.4), gridspec_kw={"hspace": 0.32, "wspace": 0.25})
    for j, inst in enumerate(PARETO_INSTS):
        for c in ("baseline", "IDP"):
            s = median_seed("final_g200", inst, c)
            F = front_points(load_run("final_g200", inst, c, s))
            for ax, (a, b) in zip(axes[:, j], ((0, 2), (0, 1))):
                o = np.argsort(F[:, a])
                ax.scatter(F[o, a], F[o, b], s=26, color=COLORS[c], edgecolor="white", lw=0.6,
                           label=f"{NAMES[c]} (seed {s})", zorder=3)
        axes[0, j].set_title(f"{label(inst)}, 200 thế hệ", loc="left")
        axes[0, j].set_ylabel("f3 hài lòng (lớn là tốt)")
        axes[1, j].set_ylabel("f2 khí thải, kg (nhỏ là tốt)")
        axes[1, j].set_xlabel("f1 chi phí, CNY (nhỏ là tốt)")
        axes[0, j].text(0.0, -0.13, "  ·  ".join(f"{NAMES[c].split(' (')[0]}: seed {median_seed('final_g200', inst, c)}"
                                                 for c in ("baseline", "IDP")),
                        transform=axes[0, j].transAxes, fontsize=8, color=INK2)
    fig.legend(handles=[Line2D([], [], ls="", marker="o", color=COLORS[c], ms=7, label=NAMES[c])
                        for c in ("baseline", "IDP")], loc="upper left", bbox_to_anchor=(0.01, 0.955), ncol=2)
    fig.suptitle("Front cuối của run có HV trung vị: hướng tốt là góc trên trái (hàng trên) và góc dưới trái "
                 "(hàng dưới)", x=0.01, ha="left", fontsize=10.5)
    save(fig, "f06_pareto_2d")

def f07_pareto_3d() -> None:
    fig = plt.figure(figsize=(14, 5.2))
    for j, inst in enumerate(PARETO_INSTS):
        ax = fig.add_subplot(1, 3, j + 1, projection="3d")
        for c in ("baseline", "IDP"):
            s = median_seed("final_g200", inst, c)
            F = front_points(load_run("final_g200", inst, c, s))
            ax.scatter(F[:, 0], F[:, 1], F[:, 2], s=16, color=COLORS[c], depthshade=False, label=NAMES[c])
        ax.set_xlabel("f1 (CNY)", fontsize=8)
        ax.set_ylabel("f2 (kg)", fontsize=8)
        ax.set_zlabel("f3", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.set_title(f"{label(inst)}, 200 thế hệ", fontsize=10)
        ax.view_init(elev=22, azim=-58)
        if j == 0:
            ax.legend(loc="upper left", fontsize=8)
    save(fig, "f07_pareto_3d")

def f08_convergence() -> None:
    fig, axes = plt.subplots(2, 5, figsize=(15, 6.4), sharex=True, gridspec_kw={"hspace": 0.35, "wspace": 0.3})
    for ax, inst in zip(axes.flat, INSTS):
        conv = pd.read_csv(RES / "final_g1000" / inst / "convergence.csv")
        for c in ("baseline", "IDP"):
            ax.plot(conv.generation, conv[c], color=COLORS[c], lw=1.8, label=NAMES[c])
        ax.axvline(200, color=NEUTRAL, lw=0.8, ls="--")
        ax.set_title(label(inst), loc="left")
    for ax in axes[1]:
        ax.set_xlabel("Thế hệ")
    for ax in axes[:, 0]:
        ax.set_ylabel("HV trung bình (10 seed)")
    axes[0, 0].legend(loc="lower right", fontsize=8)
    fig.suptitle("Hội tụ HV qua 1000 thế hệ (trước bước polish; vạch đứt ở thế hệ 200 = ngân sách của bài báo)",
                 x=0.01, ha="left", fontsize=10.5)
    save(fig, "f08_convergence")

def f09_hv_box() -> None:
    configs = ["baseline", "IDP", "ILDP"]
    fig, ax = plt.subplots(figsize=(14, 4.8))
    w = 0.26
    for j, inst in enumerate(INSTS):
        r = pd.read_csv(RES / "final_g200" / inst / "per_run.csv")
        for k, c in enumerate(configs):
            x = j + (k - 1) * w
            v = r.loc[r.config == c, "HV"].to_numpy()
            bp = ax.boxplot(v, positions=[x], widths=w * 0.8, patch_artist=True, showfliers=False,
                            medianprops=dict(color="white", lw=1.6), whiskerprops=dict(color=COLORS[c]),
                            capprops=dict(color=COLORS[c]), boxprops=dict(lw=0))
            bp["boxes"][0].set_facecolor(COLORS[c])
            ax.scatter(np.full(len(v), x) + np.random.default_rng(j * 3 + k).uniform(-w / 4, w / 4, len(v)), v,
                       s=7, color=INK, alpha=0.35, lw=0, zorder=3)
    ax.set_xticks(range(len(INSTS)))
    ax.set_xticklabels([label(i) for i in INSTS])
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("HV (lớn là tốt)")
    ax.legend(handles=[Patch(color=COLORS[c], label=NAMES[c]) for c in configs], loc="upper center",
              bbox_to_anchor=(0.5, -0.07), ncol=3)
    ax.set_title("Phân bố HV qua 20 seed, 200 thế hệ (mỗi chấm là một run; HV chuẩn hoá riêng từng instance)",
                 loc="left")
    save(fig, "f09_hv_box")

def f10_ablation_heatmap() -> None:
    groups = "IPDLA"
    order = [f"only_{g}" for g in groups] + ["all"] + [f"all_minus_{g}" for g in groups]
    names = {"only_I": "chỉ I", "only_P": "chỉ P", "only_D": "chỉ D", "only_L": "chỉ L", "only_A": "chỉ A",
             "all": "cả năm", **{f"all_minus_{g}": f"bỏ {g}" for g in groups}}
    insts = ["C102-25", "R201-50", "RC201-100", "case29-29"]
    cmap = LinearSegmentedColormap.from_list("div", ["#d03b3c", "#ec4647", "#f3b3b3", "#efefef",
                                                     "#9dc8f7", "#338ced", "#1757ac"])
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 6.2), gridspec_kw={"wspace": 0.35})
    for ax, (exp, title) in zip(axes, (("abl5_g200", "200 thế hệ, 20 seed"), ("abl5_g1000", "1000 thế hệ, 10 seed"))):
        t = pd.read_csv(RES / exp / "ablation_table.csv")
        dv = t.pivot(index="config", columns="instance", values="dHV").loc[order, insts]
        pv = t.pivot(index="config", columns="instance", values="p_HV").loc[order, insts]
        im = ax.imshow(dv.to_numpy(), cmap=cmap, norm=TwoSlopeNorm(0, -0.3, 0.6), aspect="auto")
        for a in range(len(order)):
            for b in range(len(insts)):
                v, p = dv.iat[a, b], pv.iat[a, b]
                ax.text(b, a, f"{v:+.2f}{'*' if p < 0.05 else ''}", ha="center", va="center", fontsize=8.5,
                        color="white" if abs(v) > 0.35 else INK, weight="bold" if p < 0.05 else "normal")
        ax.set_xticks(range(len(insts)))
        ax.set_xticklabels([label(i) for i in insts])
        ax.set_yticks(range(len(order)))
        ax.set_yticklabels([names[c] for c in order])
        ax.axhline(4.5, color="white", lw=3)
        ax.axhline(5.5, color="white", lw=3)
        ax.grid(False)
        ax.set_title(title, loc="left")
    cb = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02)
    cb.set_label("ΔHV so với NSGA-II gốc")
    cb.outline.set_visible(False)
    fig.suptitle("Ablation 5 cải tiến (I init_smart, P polish, D đa dạng, L local search, A Pc/Pm thích nghi); "
                 "* = p < 0.05", x=0.01, ha="left", fontsize=10.5)
    save(fig, "f10_ablation_heatmap")

def f11_paper_vs_ours() -> None:
    pm = pd.read_csv(ROOT / "data" / "paper" / "paper_metrics.csv")
    s = pd.read_csv(RES / "final_summary.csv")
    def hv(i, a):
        return pm[(pm.instance == i) & (pm.algorithm == a) & (pm.metric == "HV")].value.iloc[0]
    def ours(exp, i):
        g = s[(s.exp == exp) & (s.instance == i)].set_index("config").HV_mean
        return 100 * (g["IDP"] / g["baseline"] - 1)
    paper = [100 * (hv(i, "INSGA-III") / hv(i, "NSGA-II") - 1) for i in INSTS]
    o200, o1000 = [ours("final_g200", i) for i in INSTS], [ours("final_g1000", i) for i in INSTS]
    x, w = np.arange(len(INSTS)), 0.27
    fig, ax = plt.subplots(figsize=(13, 4.8))
    ax.bar(x - w, paper, w * 0.92, color=C_PAPER, label="Bài báo: INSGA-III so với NSGA-II (200 thế hệ)")
    ax.bar(x, o200, w * 0.92, color=C_IDP, label="Nhóm: I+D+P so với NSGA-II gốc, 200 thế hệ")
    ax.bar(x + w, o1000, w * 0.92, color="white", edgecolor=C_IDP, hatch="////", lw=1.2,
           label="Nhóm: I+D+P so với NSGA-II gốc, 1000 thế hệ")
    ax.set_xticks(x)
    ax.set_xticklabels([label(i) for i in INSTS])
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Mức tăng HV (%)")
    ax.legend(loc="upper left")
    ax.set_title("Mức tăng HV so với NSGA-II của chính mình (hai bên chuẩn hoá HV khác nhau, chỉ so chiều và "
                 "độ lớn)", loc="left")
    save(fig, "f11_paper_vs_ours")

FIGS = [f01_case29_map, f02_satisfaction, f03_algorithm, f04_routes_case29, f05_timeline_case29,
        f06_pareto_2d, f07_pareto_3d, f08_convergence, f09_hv_box, f10_ablation_heatmap, f11_paper_vs_ours]

def main(argv: list[str] | None = None) -> None:
    want = argv if argv is not None else sys.argv[1:]
    for fn in FIGS:
        if not want or fn.__name__.split("_")[0] in want:
            fn()

if __name__ == "__main__":
    main()
