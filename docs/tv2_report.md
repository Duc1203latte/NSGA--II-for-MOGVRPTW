# Báo cáo TV2: khởi tạo thông minh và local search

Branch `feat/tv2-init-local-search`, tách từ `origin/main` `5197d65`. Chưa merge vào `main`.

> **Phạm vi của các số liệu dưới đây.** `src/nsga2.py`, `src/metrics.py`, `src/runner.py` của TV1
> còn rỗng nên mọi thí nghiệm chạy trên **harness NSGA-II tạm của TV2** (`scripts/tv2_harness.py`,
> NSGA-II chuẩn: OX, đột biến đảo đoạn, giải đấu nhị phân, (μ+λ)). Đây là kết quả **sơ bộ**: đúng
> phương pháp, đúng decoder của nhóm, nhưng chưa phải baseline của TV1. Khi TV1 bàn giao phải chạy
> lại bằng cùng các lệnh trong mục 8.

## 1. Vấn đề

- Khởi tạo ngẫu nhiên đặt quần thể đầu rất xa vùng tốt: với `split_rule: capacity_time`, hoán vị
  ngẫu nhiên tạo nhiều tuyến ngắn, đi vòng, đến muộn.
- NSGA-II hoán vị không có bước tinh chỉnh thứ tự trong từng tuyến.

## 2. Thiết kế

### 2.1 `init_smart` (`src/improvements/init_smart.py`)

| Nguồn | Cách sinh | Phá hoà |
|---|---|---|
| `nn` | từ kho, mỗi bước chọn khách chưa ghé gần nhất (`inst.dist`), không xét khung giờ | ID nhỏ hơn |
| `tw` | chọn tuần tự khách có **ETa** (`tw_expected[:,0]`) nhỏ nhất | gần điểm trước đó (kho với khách đầu) hơn, rồi ID nhỏ hơn |
| `random` | đúng `baseline_factory(rng)` của baseline | — |

- Quota bằng largest remainder (n_pop = 80, tỉ lệ 0.2/0.2/0.6 → 16/16/48), hoà phần dư theo thứ tự nn, tw, random.
- Slot đầu của nn/tw là bản thuần; các slot khác là bản gốc sau 1..3 lần hoán đổi hai vị trí (vẫn là hoán vị).
- Khử trùng toàn quần thể; hết `dedup_max_attempts` thì sinh random dự phòng, nhãn `random_fallback`,
  thống kê trong `effective_counts`. Khi n! < n_pop thì chấp nhận trùng và ghi chú.
- RNG: chỉ `rng` truyền vào, thứ tự sinh nn → tw → random, không xáo quần thể. Số lần gọi RNG cố định theo đặc tả trong docstring.

### 2.2 `local_search` (`src/improvements/local_search.py`)

- Toán tử: `two_opt(route, i, j)` đảo `route[i..j]`; `or_opt(route, start, L, insert_at)` với L ∈ {1,2,3},
  `insert_at` tính trên mảng đã bỏ khối (ví dụ `(1,2,3,4,5,6)`, khối `(2,3)` → `[1,4,5,2,3,6]`).
- Mỗi lượt: xáo thứ tự các tuyến dài ≥ 2 của **nghiệm hiện tại** (lấy từ decoder), mỗi tuyến bốc một bước
  2-opt và một bước Or-opt ngẫu nhiên không no-op, first-improvement (tuỳ chọn `best`).
- Mọi ứng viên được ghép lại thành hoán vị và **chấm bằng đúng evaluator mà NSGA-II dùng**.
- Mục tiêu tối thiểu hoá `g = (f1, f2, 1 − f3)`.
  - `pareto`: nhận khi g mới trội nghiêm ngặt g cũ (có ε).
  - `weighted` (mặc định): trọng số Dirichlet bốc **một lần mỗi lần gọi**, scale cố định
    `(mean f1, mean f2, 1)` trên 3 hoán vị tất định (ID, NN, ETa), tính một lần mỗi run. Nhận khi
    `Σ w·g/s` giảm hơn ε. **Đây không phải cải thiện Pareto**: từng mục tiêu có thể xấu đi.
  - Ghi lịch sử before/after và `accepted_by` của từng bước để kiểm tra lại.
- Ngân sách cứng: `max_candidate_evals` (tính cả bước bị loại và bước trúng cache), `max_accepted_moves`,
  `max_passes`. Không dùng giới hạn thời gian, nên kết quả tất định theo seed.
- Bộ đếm: `n_ls_calls, n_ls_triggered, n_ls_candidate_evals, n_ls_accepted, n_ls_rejected_split,
  n_ls_rejected_feasibility, n_ls_rejected_no_improve, n_ls_split_drift, n_eval_requests,
  n_real_model_evals, n_evals_total, elapsed_s`.

### 2.3 Lệch biên tuyến (boundary drift)

Đề xuất trên tuyến B có thể làm decoder cắt lại khác: phản ví dụ trong test
(`test_boundary_drift_counterexample_rejected`): tải 10, demand 6/5/3, `[1,2,3]` → `[1] | [2,3]`; đảo B
→ `[1,3,2]` → decoder cắt `[1,3] | [2]`. Có hai chính sách:

- `reject` (mặc định trong config): bộ tuyến decoder trả về khác bộ tuyến đề xuất thì loại bước đi.
- `evaluate_actual`: vẫn dùng kết quả **thật** của decoder cho hoán vị ứng viên (không có fitness giả),
  nhưng bước đi lúc đó không còn thuần nội tuyến.

Với DP split (TV4), không ép bộ tuyến; mọi lần chấm dùng cùng `metadata["dp_weights"]` của con.

**Phát hiện đo được:** với `split_rule: capacity_time` (mặc định của nhóm), **71–89% ứng viên bị loại vì
lệch biên** (seed 0..9, 200 thế hệ: C102 87–88%, R201 74–75%, RC201 71–74%; tuning: 75–89%). Cắt theo thời gian làm hầu hết
mọi thay đổi thứ tự trong tuyến dịch chuyển chỗ cắt.

### 2.4 Đội xe

Nghiệm hiện tại feasible (`fleet_ok`) → ứng viên infeasible bị loại; đã infeasible → chỉ nhận ứng viên
không dùng nhiều xe hơn. LS **không** sửa evaluator hay chọn lọc toàn cục. Lưu ý: chính baseline cũng
giữ nghiệm vượt 25 xe trên RC201-100 (trung bình 6 nghiệm/front cuối) vì decoder chưa cưỡng chế
`fleet_size` (README: chưa xử lý). Cấu hình có `init_smart` có nhiều nghiệm vượt đội xe hơn trong front
cuối (8.9–17.4). Đây là việc cần cả nhóm quyết định chính sách.

### 2.5 Điểm gắn và RNG

```
khởi tạo:  init_smart bật ? smart_initial_population(...) : [baseline_factory(rng) ...]
mỗi con:   lai (OX) -> đột biến -> [dp weights, TV4] -> [LS hook: 1×rng.random() < p_ls ?] -> chấm
```

Cờ tắt → không import, không tạo hook, không gọi RNG. Hook trả `detail` chính xác để NSGA-II dùng lại
(không chấm hai lần). Chi tiết hợp đồng: `docs/tv2_integration.md`.

### 2.6 Độ phức tạp

- init: NN và TW O(n²) mỗi lần (một lần mỗi run); xáo O(k).
- LS: mỗi lần gọi ≤ `max_candidate_evals + 1` lần chấm, mỗi lần O(n) (greedy/capacity_time) hoặc O(n·L·K)
  với DP. Với p_ls = 0.2, ngân sách 40: ~3.2k lần gọi LS mỗi run 200 thế hệ, **gấp 3.3–7.8 lần số lần
  đánh giá** so với baseline (16 080) và tốn thời gian tương ứng.

## 3. Kiểm thử

| Lệnh | Kết quả |
|---|---|
| `python --version` | 3.11.18 (conda env riêng, các gói đúng bản ghim trong `requirements.txt`) |
| `python -m pip check` | No broken requirements found |
| `pytest -q tests/test_init_smart.py` | 91 passed |
| `pytest -q tests/test_local_search.py` | 79 passed |
| `pytest -q tests/test_tv2_integration.py` | 21 passed (trên harness, không phải nsga2.py thật) |
| `pytest -q tests/test_plot_tv2.py` | 2 passed (dữ liệu đồ chơi trong thư mục tạm) |
| `pytest -q` (toàn bộ) | 193 passed |
| `python -m scripts.smoke_phase0` | chạy, exit 0 |
| `python -m scripts.tv2_regression_snapshot --check` | REGRESSION PASS |
| `python -m scripts.tv2_dp_compat_check` trên branch | BLOCKED (exit 2), đúng như mong đợi: chưa có dp_split |
| Merge thử `origin/feat/dp-split` (worktree tạm, đã xoá) | 246 passed; DP+LS compat PASS |

Các bất biến được test: mọi hoán vị là 1..n đúng một lần; không sửa input/inst/config/cha mẹ; quota 16/16/48
và n_pop lẻ; phá hoà NN/TW trên instance tự dựng; ETa chứ không phải ET; perturb giữ multiset và số lần
gọi RNG; n = 1..5 không treo; random dự phòng có nhãn; cùng seed ra cùng chuỗi; nhóm random 100% trùng
từng phần tử với dãy baseline và trạng thái RNG; 2-opt/Or-opt theo ví dụ và biên; ứng viên chỉ đổi đúng
một tuyến và giữ tập khách; phản ví dụ lệch biên bị loại; bước được nhận luôn giảm score / trội Pareto;
f3 đúng chiều MAX; trọng số bốc đúng một lần, metadata chuyển nguyên; trần ngân sách; cache trùng; chính
sách đội xe; evaluator kiểu DP; **all-off khớp mốc đã lưu từng bit (float.hex) và trạng thái RNG cuối**;
chặn import module TV2 thì đường all-off vẫn ra đúng kết quả; kế toán #eval chính xác khi bật LS.

## 4. Thiết lập thí nghiệm

- Instance: C102-25, R201-50, RC201-100. n_pop 80, 200 thế hệ, pc 0.7, pm 0.1, `split_rule:
  capacity_time`, `satisfaction_time: arrival`. Các cờ khác (diversity, dp_split, adaptive) TẮT.
- Tuning: seed **100..104**, một tham số một lần. Báo cáo: seed **0..9**, không tuning trên bộ này.
- Chỉ số: HV theo quy ước nhóm (min-max theo reference set = tập không bị trội của mọi front cuối cùng
  tag/instance, ref point 1.1); IGD tới reference set đó; SP (Schott); `hv_wide` (**chỉ số phụ** của TV2:
  cùng ideal nhưng nadir = max mọi front cuối, để front nằm ngoài hộp reference vẫn so được);
  `init_hv_own` (HV quần thể ban đầu, chuẩn hoá theo hợp các front ban đầu).
- Hai góc nhìn: **cùng 200 thế hệ** và **cùng ngân sách ≈16 080 lần đánh giá** (dừng ở thế hệ đầu tiên
  vượt ngân sách; vượt tối đa ~2%).
- p-value: Wilcoxon signed-rank ghép cặp theo seed, **chỉ để tham khảo**; kiểm định chính thức do TV3.
  Với 10 cặp, p nhỏ nhất có thể là 0.002 (thắng cả 10).

Bằng chứng: `docs/tv2_results/*_summary.csv`, `*_runs.csv`, `*_metadata.json` (commit, Python, seed,
thời điểm, tham số). Dữ liệu thô `.npz` và hình: `results/tv2/<tag>/`, `results/figures/tv2/<tag>/`
(không đưa lên git). Lượt cố định ngân sách ghi `dirty_tracked_files: true` vì lúc đó phần phân tích
(chỉ số phụ) chưa commit; code thuật toán giống hệt lượt 200 thế hệ.

## 5. Kết quả tuning (seed 100..104)

| Instance | off IGD | init 20/20/60 | init 10/10/80 | init 30/30/40 | LS mặc định | LS p=0.1 | LS pareto | LS drift=eval | LS evals=20 |
|---|---|---|---|---|---|---|---|---|---|
| C102-25 | 8.70 | 0.80 | **0.74** | 1.50 | 6.60 | 9.09 | 6.42 | **5.21** | 6.23 |
| R201-50 | 0.70 | 0.27 | **0.21** | **0.21** | 0.62 | 0.59 | **0.53** | 0.62 | 0.87 |
| RC201-100 | 0.55 | 0.27 | 0.33 | **0.27** | 0.53 | 0.54 | 0.51 | **0.40** | 0.54 |

(IGD trung bình, thấp hơn là tốt.) Không có tỉ lệ khởi tạo nào thắng đều trên cả 3 instance → giữ
20/20/60. Với LS, `split_drift_policy: evaluate_actual` tốt nhất trên 2/3 instance và tốn ít lần đánh giá
hơn (không phí ngân sách vào bước bị loại) → thêm làm biến thể `*_drift_eval` trong thí nghiệm chính.
**Config mặc định vẫn là `reject`**; đổi mặc định là việc tuning của TV4/nhóm.

## 6. Kết quả chính (seed 0..9, 10 run mỗi ô)

### 6.1 Cùng 200 thế hệ

| Instance | Cấu hình | HV (nhóm) | HV_wide | IGD | SP | #Pareto | #eval | Thời gian (s) | thắng off (IGD) | p (tham khảo) |
|---|---|---|---|---|---|---|---|---|---|---|
| C102-25 | off | 0.009±0.020 | 0.438±0.196 | 1.607±0.570 | 0.116 | 12.9 | 16 080 | 13.9 | – | – |
| | init_only | 0.661±0.244 | 1.150±0.113 | 0.398±0.136 | 0.118 | 10.7 | 16 080 | 14.6 | 10/10 | 0.002 |
| | ls_only | 0.000±0.000 | 0.309±0.054 | 1.839±0.210 | 0.134 | 13.0 | 64 363 | 47.7 | 4/10 | 0.25 |
| | both | 0.787±0.279 | 1.170±0.133 | 0.364±0.133 | 0.253 | 13.4 | 56 183 | 45.2 | 10/10 | 0.002 |
| | ls_drift_eval | 0.124±0.220 | 0.670±0.236 | 1.058±0.426 | 0.177 | 10.6 | 56 542 | 48.9 | 8/10 | 0.078 |
| | both_drift_eval | **0.937±0.246** | **1.216±0.101** | **0.295±0.130** | 0.177 | 11.8 | 52 828 | 55.7 | 10/10 | 0.002 |
| R201-50 | off | 0.000±0.000 | 0.321±0.075 | 3.007±0.464 | 0.183 | 21.7 | 16 080 | 31.0 | – | – |
| | init_only | 0.028±0.075 | 0.782±0.150 | 1.096±0.511 | 0.136 | 24.2 | 16 080 | 22.4 | 10/10 | 0.25* |
| | ls_only | 0.000±0.000 | 0.408±0.126 | 2.530±0.707 | 0.118 | 30.9 | 112 835 | 148.5 | 7/10 | – |
| | both | 0.036±0.060 | 0.842±0.104 | 0.903±0.336 | 0.149 | 48.0 | 99 244 | 143.4 | 10/10 | 0.125* |
| | ls_drift_eval | 0.000±0.000 | 0.512±0.130 | 2.024±0.648 | 0.113 | 42.9 | 84 514 | 119.4 | 9/10 | – |
| | both_drift_eval | **0.087±0.228** | **0.876±0.147** | **0.867±0.407** | 0.087 | 52.5 | 82 736 | 93.6 | 10/10 | 0.125* |
| RC201-100 | off | 0.004±0.007 | 0.348±0.056 | 1.152±0.141 | 0.076 | 18.9 | 16 080 | 41.5 | – | – |
| | init_only | 0.651±0.122 | 0.906±0.075 | 0.324±0.094 | 0.052 | 36.2 | 16 080 | 44.9 | 10/10 | 0.002 |
| | ls_only | 0.022±0.036 | 0.395±0.077 | 1.090±0.161 | 0.058 | 34.2 | 125 082 | 387.6 | 7/10 | 0.125 |
| | both | 0.682±0.115 | 0.929±0.072 | 0.297±0.089 | 0.021 | 58.5 | 125 417 | 380.0 | 10/10 | 0.002 |
| | ls_drift_eval | 0.112±0.089 | 0.546±0.105 | 0.868±0.183 | 0.018 | 46.2 | 98 022 | 273.1 | 10/10 | 0.008 |
| | both_drift_eval | **1.018±0.147** | **1.157±0.080** | **0.118±0.060** | 0.019 | 54.9 | 94 964 | 181.1 | 10/10 | 0.002 |

\* p tính trên HV theo quy ước nhóm; trên R201 HV nhóm bằng 0 ở phần lớn run nên test này yếu. Cột
"thắng off" tính trên IGD; HV_wide cho cùng số trận thắng, trừ RC201 `ls_only` (8/10 theo HV_wide).

**HV khởi tạo** (`init_hv_own`, mean 10 seed): random 0.120 / 0.084 / 0.086; init_smart 1.090 / 0.641 /
0.720 (C102 / R201 / RC201). Giả thuyết "quần thể đầu của init_smart có HV cao hơn" đúng trên cả 3 instance
ở 10 seed này, nhưng vẫn là quan sát thực nghiệm, không phải bất biến.

### 6.2 Cùng ngân sách ≈ 16 080 lần đánh giá

| Instance | off IGD | init_only | ls_only | both | ls_drift_eval | both_drift_eval |
|---|---|---|---|---|---|---|
| C102-25 | 7.77±3.34 | **0.87±0.54** | 14.97±2.33 | 1.30±0.82 | 8.56±2.43 | 1.01±0.64 |
| R201-50 | 4.59±0.88 | **1.19±0.86** | 13.32±1.24 | 5.80±1.00 | 8.27±1.27 | 3.82±0.89 |
| RC201-100 | 2.44±0.20 | **0.28±0.10** | 4.08±0.28 | 0.59±0.09 | 3.33±0.35 | 0.35±0.09 |

(IGD theo reference set của lượt ngân sách; LS chỉ chạy được 27–61 thế hệ.) **Cùng ngân sách, LS làm
kết quả tệ hơn** baseline (ls_only thua off ở 10/10 seed trên cả 3 instance), và `both` tệ hơn `init_only`.

### 6.3 Thống kê LS (200 thế hệ, trung bình mỗi run)

| Instance | Cấu hình | LS kích hoạt | ứng viên | nhận | loại lệch biên | loại đội xe | không cải thiện |
|---|---|---|---|---|---|---|---|
| C102-25 | ls_only | 3 187 | 57 317 | 1 216 | 50 014 | 0 | 6 087 |
| | ls_drift_eval | 3 186 | 44 553 | 2 215 | 0 | 0 | 42 338 |
| R201-50 | ls_only | 3 205 | 113 248 | 3 432 | 85 297 | 0 | 24 519 |
| | ls_drift_eval | 3 177 | 74 437 | 5 001 | 0 | 0 | 69 436 |
| RC201-100 | ls_only | 3 210 | 126 719 | 5 619 | 94 012 | 0 | 27 088 |
| | ls_drift_eval | 3 179 | 88 988 | 7 233 | 0 | 617 | 81 137 |

Hình (đã xem lại bằng mắt): `results/figures/tv2/main_gen200/` và `.../main_budget16080/`, gồm
`pareto3d_<inst>_s0.png`, `hv_convergence_<inst>.png`, `box_hv_igd_<inst>.png`.

## 7. Diễn giải và giới hạn

1. **init_smart là đóng góp rõ nhất**: tốt hơn baseline ở 10/10 seed trên cả 3 instance, ở cả hai góc nhìn
   (cùng thế hệ và cùng ngân sách), không tốn thêm lần đánh giá.
2. **local_search chỉ có lợi khi được thêm ngân sách.** Cùng 200 thế hệ, `ls_only` (reject) gần như không
   hơn baseline vì ~71–88% ứng viên bị loại do lệch biên; `ls_drift_eval` tốt hơn rõ. Cùng ngân sách, mọi
   biến thể LS đều kém hơn. **Không thể kết luận LS là cải tiến tốt trong cấu hình hiện tại.**
3. `both_drift_eval` tốt nhất ở góc nhìn 200 thế hệ trên cả 3 instance nhưng tốn 3.3–5.9 lần số lần đánh giá.
4. HV theo quy ước nhóm bằng 0 ở nhiều run (front nằm ngoài hộp của reference set), nên mất khả năng phân
   biệt; TV2 báo thêm IGD và HV_wide. Đề nghị nhóm (TV1/TV3) xem lại quy ước chuẩn hoá trước giai đoạn 4.
5. Kết quả trên harness tạm, 3 instance, 10 seed; không bảo đảm cho các instance khác hay cho baseline thật.
6. Front cuối của cấu hình có `init_smart` trên RC201-100 chứa nhiều nghiệm vượt 25 xe hơn baseline. Cần
   chính sách chung về `fleet_size` (chặn hay phạt) trước khi so sánh chính thức.

## 8. Tái hiện (PowerShell, Python 3.11)

```powershell
py -3.11 -m venv .venv; .venv\Scripts\activate; pip install -r requirements.txt
python -m pytest -q
python -m scripts.tv2_regression_snapshot --check
python -m scripts.run_tv2_experiments --preset tune --seeds 100-104 --tag tune_s100_104
python -m scripts.run_tv2_experiments --preset main --seeds 0-9 --tag main_gen200
python -m scripts.run_tv2_experiments --preset main --seeds 0-9 --max-evals 16080 --n-gen 100000 --tag main_budget16080
python -m scripts.plot_tv2_results --tag main_gen200
python -m scripts.plot_tv2_results --tag main_budget16080
```

Máy chạy: 18 luồng, 16 worker; lượt tuning ~13 phút, 200 thế hệ ~23 phút, ngân sách ~6 phút.

## 9. Việc cần phối hợp

- **TV1:** bàn giao `src/nsga2.py`/`metrics.py`/`runner.py`; trả lời 6 câu hỏi ở `docs/tv2_integration.md` §5;
  sau đó TV2 gắn hook, chụp lại mốc hồi quy trên baseline thật và chạy lại thí nghiệm.
- **TV4:** `dp_split.py` vẫn dùng `split_greedy` (fallback và `objective_scales`) trong khi main đã chuyển
  sang `split()`/`capacity_time`; quyết định mặc định `split_drift_policy`, `p_ls` khi tuning; LS + DP tốn
  ~230 ms mỗi lần gọi ở n = 100.
- **TV3:** kiểm định chính thức (đề nghị signed-rank vì seed ghép cặp); quy ước chuẩn hoá HV.
- **Cả nhóm:** chính sách `fleet_size`; ablation 4 nhóm hay 5 cờ (`adaptive_rates`).
