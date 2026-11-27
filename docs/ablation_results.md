# Kết quả ablation giai đoạn 3

Tài liệu tổng hợp mọi thí nghiệm ablation của giai đoạn 3 (27/11/2026): tuning tham số đa dạng, ablation
3 nhóm (D, P, A), ablation 5 nhóm (thêm I, L của TV2), so sánh cùng chi phí, và `every_eval` trên
RC201-100. Số liệu thô nằm trong `results/` (không đưa lên git), đường dẫn ghi ở cuối mỗi mục.

## Tóm tắt

1. **`init_smart` (I) là cải tiến mạnh nhất** và không tốn thêm lần đánh giá nào. Đứng riêng nó hơn
   baseline có ý nghĩa trên cả 4 instance ở 200 thế hệ và trên 3 instance Solomon ở 1000 thế hệ. Bỏ I
   khỏi tổ hợp là thay đổi làm kết quả tụt nhiều nhất.
2. **Pc/Pm thích nghi (A) không giúp, có chỗ còn hại.** Đứng riêng ở 1000 thế hệ làm C102-25 kém đi rõ
   (ΔHV −0.151, p = 0.023). Tổ hợp tắt A tốt nhất hoặc ngang tốt nhất ở mọi bảng. Khớp với khuyến nghị
   tắt A của TV4.
3. **Polish (P) luôn tăng HV một chút** (kiểm định cặp: mọi seed đều tăng trên 3 instance Solomon, +0.02
   đến +0.14), tốn khoảng 5% số lần đánh giá. Trên case29 gần như không thêm gì.
4. **Đa dạng (D, SDE k = 1) đứng riêng chỉ có ý nghĩa trên RC201-100 ở 1000 thế hệ** (+0.055, p = 0.049).
   Trong tổ hợp, bỏ D gần như không đổi kết quả.
5. **Local search (L) chỉ có lợi khi tính theo số thế hệ.** Tính theo cùng số lần đánh giá, L thua việc
   dùng số lần đánh giá đó để chạy thêm thế hệ ở 3/4 instance (mục 6).
6. **Cấu hình đề xuất cho giai đoạn 4: I + D + P, tắt A và L** (khoảng 1.05 lần số lần đánh giá của
   baseline). Nếu so theo số thế hệ cố định thì I + L + D + P tốt nhất, nhưng tốn 3.4–7.7 lần đánh giá.

## 1. Thiết lập chung

| Mục | Giá trị |
|---|---|
| Mô hình | `satisfaction_time: arrival`, `split_rule: capacity_time`, tham số `config.yaml` |
| NSGA-II | n_pop 80, pc 0.7, pm 0.1 (Solomon) / 0.2 (case29), OX, đột biến `standard`, loại trùng |
| Instance | C102-25, R201-50, RC201-100, case29 (mỗi kích thước một instance, cộng case thực tế) |
| Ngân sách | 200 thế hệ với seed 0–19; 1000 thế hệ với seed 0–9 |
| Chỉ số | HV (điểm tham chiếu 1.1), IGD; reference set và cận chuẩn hoá gộp mọi front của mọi cấu hình trong **cùng một thí nghiệm** |
| Kiểm định | Wilcoxon rank-sum hai phía so với baseline; riêng P dùng thêm signed-rank theo cặp seed (mục 5) |
| Tuning | seed 100–104, tách khỏi seed báo cáo |

Năm nhóm cải tiến, mỗi nhóm là một bộ ghi đè config (định nghĩa trong `scripts/ablation.py`):

| Nhóm | Người làm | Bật gì | Tham số và nguồn |
|---|---|---|---|
| I | TV2 | `init_smart` | tỉ lệ nn/tw/random 20/20/60 (TV2 tuning, không tỉ lệ nào thắng đều nên giữ mặc định) |
| L | TV2 | `local_search` | `split_drift_policy: evaluate_actual` (TV2 tuning: tốt nhất 2/3 instance; bản `reject` bị loại 71–88% bước đi) |
| D | TV3 | `diversity` | `sde`, k = 1, tắt archive (mục 2) |
| P | TV4 | `dp_split`, `mode: polish` | K = 10 vector trọng số (TV4 tuning; K = 30 không đáng) |
| A | TV4 | `adaptive_rates` | khoảng `adapt_v1`: pc 0.7–0.9, pm 0.1–0.3 (TV4 tuning; bản mặc định làm R201-50 kém đi) |

Cấu hình ablation với G nhóm: `baseline`, `only_X` (chỉ bật X), `all` (bật hết), `all_minus_X` (tắt
đúng X). "Chỉ bật X" cho biết X đứng riêng tốt đến đâu; "tắt đúng X" cho biết X còn đóng góp gì khi các
nhóm khác đã bật.

**Cách đọc bảng.** Mỗi ô: HV trung bình ± độ lệch chuẩn, dòng dưới là chênh lệch với baseline và p-value.
Ô **đậm** là p < 0.05. HV càng lớn càng tốt, IGD càng nhỏ càng tốt. **Số HV/IGD chỉ so được trong cùng một
bảng**: mỗi thí nghiệm có reference set và cận chuẩn hoá riêng, thêm hay bớt một cấu hình là mọi số đổi
theo. Các p-value chưa hiệu chỉnh đa so sánh (mỗi bảng 5 nhóm có khoảng 44 phép so HV), nên p trong khoảng
0.01–0.05 chỉ nên đọc là gợi ý.

**Khả thi.** Mọi lời giải trên front của mọi run trong mọi thí nghiệm ở tài liệu này đều không vượt đội
xe (CV = 0), nên chênh lệch HV không đến từ lời giải bất khả thi.

## 2. Tuning cơ chế đa dạng (seed 100–104, 200 thế hệ)

Thí nghiệm `tune_div`, archive tắt ở mọi cấu hình. HV:

| cấu hình | C102-25 | R201-50 | RC201-100 | case29 |
|---|---|---|---|---|
| baseline | 0.651 ± 0.229 | 0.663 ± 0.177 | 0.731 ± 0.109 | 0.771 ± 0.115 |
| sde_k1 | 0.674 ± 0.216<br>Δ +0.023, p 0.917 | 0.704 ± 0.315<br>Δ +0.041, p 0.754 | 0.879 ± 0.183<br>Δ +0.149, p 0.117 | **0.532 ± 0.070<br>Δ -0.240, p 0.009** |
| sde_k3 | 0.654 ± 0.239<br>Δ +0.004, p 0.917 | 0.545 ± 0.067<br>Δ -0.118, p 0.347 | 0.838 ± 0.167<br>Δ +0.108, p 0.175 | 0.820 ± 0.264<br>Δ +0.048, p 0.754 |
| knn_k1 | 0.676 ± 0.137<br>Δ +0.025, p 0.347 | 0.548 ± 0.258<br>Δ -0.116, p 0.465 | 0.804 ± 0.214<br>Δ +0.074, p 0.602 | 0.802 ± 0.076<br>Δ +0.031, p 0.754 |
| knn_k3 | 0.616 ± 0.322<br>Δ -0.035, p 0.602 | 0.485 ± 0.130<br>Δ -0.178, p 0.076 | 0.847 ± 0.148<br>Δ +0.116, p 0.076 | 0.727 ± 0.094<br>Δ -0.044, p 0.465 |
| knn_k5 | 0.810 ± 0.220<br>Δ +0.159, p 0.347 | 0.651 ± 0.102<br>Δ -0.012, p 0.917 | 0.685 ± 0.055<br>Δ -0.046, p 0.465 | 0.758 ± 0.072<br>Δ -0.013, p 0.917 |

Hạng trung bình của 5 biến thể qua 4 instance (1 là tốt nhất): `sde_k1` 2.50, `knn_k1` 2.75, `knn_k5` 2.75,
`sde_k3` 3.00, `knn_k3` 4.00.

**Chốt: `sde`, k = 1** (giữ mặc định của TV3). Không cấu hình nào thắng trên cả 4 instance, chênh lệch nằm
trong độ lệch chuẩn của 5 seed; `sde_k1` có hạng trung bình tốt nhất và mạnh nhất ở instance lớn nhất.
Lượt tuning độc lập của TV4 (nhánh `feat/tv4-phase4`, C102-25 và R201-50) ra cùng kết luận và khuyên
không dùng k ≥ 3. Điểm yếu đã biết: SDE kém baseline trên case29 (−0.240, p = 0.009). Đoán nguyên nhân:
trên case29 f1 và f2 tương quan khoảng 0.93, front gần như một chiều, mà SDE phạt cá thể chỉ giỏi một mục
tiêu nên loại mất các điểm đầu mút (f1 nhỏ nhất của `sde_k1` là 2425, của baseline 2361). Lỗi này không
lặp lại ở các lượt ablation với seed 0–19 (only_D trên case29 ở cả bốn bảng ablation: −0.025 đến +0.007, p > 0.3).

**Lỗi phát hiện khi tuning.** `diversity.truncate` báo lỗi `np.lexsort` khi k ≥ 3 và front cuối chỉ cần
giữ rất ít cá thể (không đủ k láng giềng). Với k = 1 lỗi không xảy ra, nên mọi kết quả khác trong tài liệu
này không bị ảnh hưởng. Hai cấu hình k = 3, k = 5 trong bảng trên chạy với một bản sửa tạm (dùng láng giềng
xa nhất còn có) đã gỡ ra sau đó; `main` hiện vẫn là bản chưa sửa, bản sửa chính thức nằm ở nhánh
`feat/tv4-phase4` của TV4 (khi thiếu láng giềng thì cho mọi cá thể hoà). Hai cách sửa chỉ khác nhau ở
bước cắt cuối cùng khi còn ít hơn k cá thể.

Kết quả thô: `results/tune_div/`.

## 3. Ablation 5 nhóm (kết quả chính)

### 3.1. 200 thế hệ, seed 0–19

Thí nghiệm `abl5_g200`, 12 cấu hình × 4 instance × 20 seed = 960 run, 36 phút trên 16 tiến trình. HV:

| cấu hình | C102-25 | R201-50 | RC201-100 | case29 |
|---|---|---|---|---|
| baseline | 0.954 ± 0.130 | 0.715 ± 0.066 | 0.448 ± 0.044 | 0.668 ± 0.080 |
| only_D | 1.009 ± 0.128<br>Δ +0.055, p 0.194 | 0.734 ± 0.069<br>Δ +0.019, p 0.344 | 0.465 ± 0.048<br>Δ +0.017, p 0.245 | 0.653 ± 0.072<br>Δ -0.015, p 0.417 |
| only_P | 1.020 ± 0.116<br>Δ +0.065, p 0.137 | **0.763 ± 0.058<br>Δ +0.048, p 0.035** | **0.524 ± 0.044<br>Δ +0.076, p < 0.001** | 0.672 ± 0.079<br>Δ +0.004, p 0.695 |
| only_A | 0.976 ± 0.118<br>Δ +0.022, p 0.646 | 0.709 ± 0.079<br>Δ -0.006, p 0.417 | 0.456 ± 0.054<br>Δ +0.008, p 0.745 | 0.676 ± 0.052<br>Δ +0.008, p 1.000 |
| only_I | **1.191 ± 0.027<br>Δ +0.236, p < 0.001** | **0.932 ± 0.045<br>Δ +0.217, p < 0.001** | **0.851 ± 0.053<br>Δ +0.403, p < 0.001** | **0.832 ± 0.060<br>Δ +0.164, p < 0.001** |
| only_L | 0.976 ± 0.112<br>Δ +0.022, p 0.607 | **0.787 ± 0.075<br>Δ +0.072, p 0.007** | **0.590 ± 0.053<br>Δ +0.141, p < 0.001** | **0.805 ± 0.097<br>Δ +0.137, p < 0.001** |
| all | **1.245 ± 0.026<br>Δ +0.290, p < 0.001** | **1.053 ± 0.048<br>Δ +0.338, p < 0.001** | **1.029 ± 0.049<br>Δ +0.581, p < 0.001** | **0.858 ± 0.053<br>Δ +0.190, p < 0.001** |
| all_minus_D | **1.242 ± 0.020<br>Δ +0.288, p < 0.001** | **1.042 ± 0.062<br>Δ +0.327, p < 0.001** | **1.044 ± 0.043<br>Δ +0.596, p < 0.001** | **0.850 ± 0.045<br>Δ +0.182, p < 0.001** |
| all_minus_P | **1.210 ± 0.032<br>Δ +0.255, p < 0.001** | **1.023 ± 0.048<br>Δ +0.309, p < 0.001** | **0.972 ± 0.057<br>Δ +0.524, p < 0.001** | **0.857 ± 0.053<br>Δ +0.189, p < 0.001** |
| all_minus_A | **1.248 ± 0.011<br>Δ +0.294, p < 0.001** | **1.061 ± 0.042<br>Δ +0.346, p < 0.001** | **1.048 ± 0.034<br>Δ +0.600, p < 0.001** | **0.865 ± 0.055<br>Δ +0.197, p < 0.001** |
| all_minus_I | **1.047 ± 0.087<br>Δ +0.092, p 0.013** | **0.875 ± 0.052<br>Δ +0.161, p < 0.001** | **0.654 ± 0.038<br>Δ +0.205, p < 0.001** | **0.752 ± 0.096<br>Δ +0.084, p 0.007** |
| all_minus_L | **1.221 ± 0.038<br>Δ +0.267, p < 0.001** | **0.957 ± 0.048<br>Δ +0.242, p < 0.001** | **0.949 ± 0.044<br>Δ +0.501, p < 0.001** | **0.811 ± 0.059<br>Δ +0.143, p < 0.001** |

IGD:

| cấu hình | C102-25 | R201-50 | RC201-100 | case29 |
|---|---|---|---|---|
| baseline | 0.408 ± 0.045 | 0.272 ± 0.046 | 0.468 ± 0.050 | 0.322 ± 0.049 |
| only_D | 0.385 ± 0.030<br>Δ -0.023, p 0.088 | 0.250 ± 0.052<br>Δ -0.022, p 0.256 | 0.446 ± 0.051<br>Δ -0.022, p 0.152 | 0.334 ± 0.057<br>Δ +0.012, p 0.482 |
| only_P | **0.180 ± 0.062<br>Δ -0.228, p < 0.001** | 0.247 ± 0.043<br>Δ -0.024, p 0.099 | **0.421 ± 0.045<br>Δ -0.047, p 0.002** | 0.319 ± 0.048<br>Δ -0.003, p 0.766 |
| only_A | 0.395 ± 0.035<br>Δ -0.013, p 0.372 | 0.278 ± 0.057<br>Δ +0.007, p 0.372 | 0.461 ± 0.054<br>Δ -0.007, p 0.935 | 0.310 ± 0.038<br>Δ -0.012, p 0.449 |
| only_I | **0.368 ± 0.009<br>Δ -0.040, p < 0.001** | **0.143 ± 0.025<br>Δ -0.129, p < 0.001** | **0.171 ± 0.032<br>Δ -0.297, p < 0.001** | **0.229 ± 0.035<br>Δ -0.093, p < 0.001** |
| only_L | 0.384 ± 0.035<br>Δ -0.024, p 0.117 | **0.234 ± 0.051<br>Δ -0.038, p 0.045** | **0.360 ± 0.039<br>Δ -0.108, p < 0.001** | **0.247 ± 0.046<br>Δ -0.075, p < 0.001** |
| all | **0.068 ± 0.026<br>Δ -0.340, p < 0.001** | **0.075 ± 0.023<br>Δ -0.197, p < 0.001** | **0.079 ± 0.025<br>Δ -0.388, p < 0.001** | **0.227 ± 0.026<br>Δ -0.095, p < 0.001** |
| all_minus_D | **0.073 ± 0.033<br>Δ -0.335, p < 0.001** | **0.089 ± 0.038<br>Δ -0.183, p < 0.001** | **0.078 ± 0.025<br>Δ -0.389, p < 0.001** | **0.231 ± 0.020<br>Δ -0.091, p < 0.001** |
| all_minus_P | **0.363 ± 0.013<br>Δ -0.045, p < 0.001** | **0.095 ± 0.020<br>Δ -0.177, p < 0.001** | **0.108 ± 0.027<br>Δ -0.360, p < 0.001** | **0.227 ± 0.026<br>Δ -0.095, p < 0.001** |
| all_minus_A | **0.060 ± 0.013<br>Δ -0.348, p < 0.001** | **0.064 ± 0.023<br>Δ -0.208, p < 0.001** | **0.073 ± 0.024<br>Δ -0.395, p < 0.001** | **0.227 ± 0.027<br>Δ -0.095, p < 0.001** |
| all_minus_I | **0.170 ± 0.039<br>Δ -0.238, p < 0.001** | **0.164 ± 0.033<br>Δ -0.108, p < 0.001** | **0.321 ± 0.035<br>Δ -0.147, p < 0.001** | **0.273 ± 0.053<br>Δ -0.049, p 0.005** |
| all_minus_L | **0.085 ± 0.045<br>Δ -0.323, p < 0.001** | **0.117 ± 0.034<br>Δ -0.155, p < 0.001** | **0.126 ± 0.038<br>Δ -0.341, p < 0.001** | **0.245 ± 0.026<br>Δ -0.077, p < 0.001** |

Số lần gọi evaluate trung bình mỗi run:

| cấu hình | C102-25 | R201-50 | RC201-100 | case29-29 |
|---|---|---|---|---|
| baseline | 16,080 | 16,080 | 16,080 | 16,080 |
| only_D | 16,080 | 16,080 | 16,080 | 16,080 |
| only_P | 16,880 | 16,880 | 16,880 | 16,880 |
| only_A | 16,080 | 16,080 | 16,080 | 16,080 |
| only_I | 16,080 | 16,080 | 16,080 | 16,080 |
| only_L | 56,727 | 85,547 | 94,716 | 81,644 |
| all | 54,324 | 82,215 | 111,377 | 83,731 |
| all_minus_D | 54,011 | 83,040 | 110,371 | 83,761 |
| all_minus_P | 53,524 | 81,415 | 110,577 | 82,931 |
| all_minus_A | 54,074 | 81,234 | 111,531 | 84,279 |
| all_minus_I | 56,060 | 83,379 | 98,055 | 83,049 |
| all_minus_L | 16,880 | 16,880 | 16,880 | 16,880 |

### 3.2. 1000 thế hệ, seed 0–9

Thí nghiệm `abl5_g1000`, 12 cấu hình × 4 instance × 10 seed = 480 run, 85 phút trên 16 tiến trình. HV:

| cấu hình | C102-25 | R201-50 | RC201-100 | case29 |
|---|---|---|---|---|
| baseline | 1.024 ± 0.111 | 0.925 ± 0.077 | 0.746 ± 0.069 | 0.762 ± 0.101 |
| only_D | 1.044 ± 0.076<br>Δ +0.020, p 0.762 | 0.912 ± 0.075<br>Δ -0.013, p 0.545 | **0.801 ± 0.045<br>Δ +0.055, p 0.049** | 0.769 ± 0.141<br>Δ +0.007, p 0.940 |
| only_P | 1.097 ± 0.071<br>Δ +0.073, p 0.096 | 0.957 ± 0.079<br>Δ +0.032, p 0.226 | 0.770 ± 0.075<br>Δ +0.024, p 0.326 | 0.762 ± 0.100<br>Δ +0.000, p 0.940 |
| only_A | **0.873 ± 0.128<br>Δ -0.151, p 0.023** | 0.910 ± 0.072<br>Δ -0.015, p 0.597 | 0.797 ± 0.037<br>Δ +0.051, p 0.070 | 0.769 ± 0.108<br>Δ +0.007, p 0.880 |
| only_I | **1.113 ± 0.037<br>Δ +0.089, p 0.016** | **1.029 ± 0.046<br>Δ +0.104, p 0.001** | **1.036 ± 0.068<br>Δ +0.290, p < 0.001** | 0.794 ± 0.033<br>Δ +0.033, p 0.450 |
| only_L | 1.056 ± 0.097<br>Δ +0.032, p 0.406 | 0.932 ± 0.073<br>Δ +0.007, p 0.940 | 0.791 ± 0.051<br>Δ +0.045, p 0.131 | 0.824 ± 0.065<br>Δ +0.062, p 0.131 |
| all | **1.186 ± 0.002<br>Δ +0.162, p < 0.001** | **1.070 ± 0.062<br>Δ +0.145, p 0.001** | **1.076 ± 0.049<br>Δ +0.331, p < 0.001** | 0.861 ± 0.103<br>Δ +0.099, p 0.059 |
| all_minus_D | **1.181 ± 0.014<br>Δ +0.157, p < 0.001** | **1.079 ± 0.086<br>Δ +0.154, p 0.001** | **1.078 ± 0.057<br>Δ +0.332, p < 0.001** | 0.817 ± 0.038<br>Δ +0.055, p 0.199 |
| all_minus_P | **1.140 ± 0.002<br>Δ +0.116, p < 0.001** | **1.045 ± 0.063<br>Δ +0.120, p 0.002** | **1.056 ± 0.051<br>Δ +0.310, p < 0.001** | 0.861 ± 0.103<br>Δ +0.099, p 0.059 |
| all_minus_A | **1.183 ± 0.008<br>Δ +0.159, p < 0.001** | **1.093 ± 0.067<br>Δ +0.168, p < 0.001** | **1.087 ± 0.054<br>Δ +0.341, p < 0.001** | **0.874 ± 0.106<br>Δ +0.112, p 0.034** |
| all_minus_I | 1.085 ± 0.133<br>Δ +0.061, p 0.174 | **0.998 ± 0.062<br>Δ +0.073, p 0.023** | **0.844 ± 0.057<br>Δ +0.098, p 0.007** | 0.799 ± 0.134<br>Δ +0.037, p 0.496 |
| all_minus_L | **1.170 ± 0.013<br>Δ +0.146, p < 0.001** | **1.029 ± 0.074<br>Δ +0.104, p 0.005** | **1.064 ± 0.074<br>Δ +0.318, p < 0.001** | 0.770 ± 0.140<br>Δ +0.008, p 0.880 |

IGD:

| cấu hình | C102-25 | R201-50 | RC201-100 | case29 |
|---|---|---|---|---|
| baseline | 0.322 ± 0.028 | 0.170 ± 0.034 | 0.281 ± 0.050 | 0.237 ± 0.067 |
| only_D | 0.321 ± 0.016<br>Δ -0.001, p 0.290 | 0.166 ± 0.041<br>Δ -0.004, p 0.821 | 0.238 ± 0.034<br>Δ -0.042, p 0.070 | 0.234 ± 0.110<br>Δ -0.003, p 0.821 |
| only_P | **0.138 ± 0.048<br>Δ -0.184, p < 0.001** | 0.146 ± 0.035<br>Δ -0.025, p 0.082 | 0.261 ± 0.054<br>Δ -0.020, p 0.174 | 0.237 ± 0.067<br>Δ +0.000, p 1.000 |
| only_A | 0.355 ± 0.049<br>Δ +0.033, p 0.070 | 0.177 ± 0.041<br>Δ +0.007, p 0.450 | 0.249 ± 0.030<br>Δ -0.032, p 0.096 | 0.227 ± 0.066<br>Δ -0.010, p 0.821 |
| only_I | 0.307 ± 0.008<br>Δ -0.015, p 0.821 | **0.120 ± 0.027<br>Δ -0.051, p 0.002** | **0.109 ± 0.030<br>Δ -0.172, p < 0.001** | 0.200 ± 0.019<br>Δ -0.038, p 0.082 |
| only_L | 0.314 ± 0.024<br>Δ -0.007, p 0.226 | 0.171 ± 0.040<br>Δ +0.001, p 0.762 | 0.260 ± 0.038<br>Δ -0.021, p 0.199 | 0.206 ± 0.033<br>Δ -0.031, p 0.199 |
| all | **0.113 ± 0.008<br>Δ -0.209, p < 0.001** | **0.087 ± 0.030<br>Δ -0.084, p < 0.001** | **0.082 ± 0.021<br>Δ -0.199, p < 0.001** | **0.171 ± 0.056<br>Δ -0.067, p 0.023** |
| all_minus_D | **0.123 ± 0.019<br>Δ -0.199, p < 0.001** | **0.089 ± 0.046<br>Δ -0.081, p 0.001** | **0.088 ± 0.028<br>Δ -0.193, p < 0.001** | 0.197 ± 0.025<br>Δ -0.040, p 0.070 |
| all_minus_P | **0.299 ± 0.004<br>Δ -0.023, p 0.010** | **0.110 ± 0.026<br>Δ -0.061, p < 0.001** | **0.103 ± 0.020<br>Δ -0.178, p < 0.001** | **0.171 ± 0.056<br>Δ -0.067, p 0.023** |
| all_minus_A | **0.114 ± 0.007<br>Δ -0.208, p < 0.001** | **0.074 ± 0.030<br>Δ -0.097, p < 0.001** | **0.072 ± 0.021<br>Δ -0.209, p < 0.001** | **0.167 ± 0.050<br>Δ -0.070, p 0.019** |
| all_minus_I | **0.138 ± 0.069<br>Δ -0.184, p < 0.001** | **0.106 ± 0.033<br>Δ -0.064, p 0.001** | **0.208 ± 0.035<br>Δ -0.073, p 0.004** | 0.230 ± 0.097<br>Δ -0.007, p 0.880 |
| all_minus_L | **0.126 ± 0.011<br>Δ -0.196, p < 0.001** | **0.101 ± 0.035<br>Δ -0.069, p 0.001** | **0.086 ± 0.028<br>Δ -0.195, p < 0.001** | 0.227 ± 0.080<br>Δ -0.011, p 0.705 |

Số lần gọi evaluate trung bình mỗi run:

| cấu hình | C102-25 | R201-50 | RC201-100 | case29-29 |
|---|---|---|---|---|
| baseline | 80,080 | 80,080 | 80,080 | 80,080 |
| only_D | 80,080 | 80,080 | 80,080 | 80,080 |
| only_P | 80,880 | 80,880 | 80,880 | 80,880 |
| only_A | 80,080 | 80,080 | 80,080 | 80,080 |
| only_I | 80,080 | 80,080 | 80,080 | 80,080 |
| only_L | 272,128 | 415,531 | 599,517 | 416,884 |
| all | 269,298 | 393,072 | 623,431 | 417,269 |
| all_minus_D | 268,425 | 397,609 | 611,330 | 416,663 |
| all_minus_P | 268,498 | 392,272 | 622,631 | 416,469 |
| all_minus_A | 268,964 | 382,640 | 618,803 | 415,901 |
| all_minus_I | 272,244 | 392,873 | 613,236 | 422,076 |
| all_minus_L | 80,880 | 80,880 | 80,880 | 80,880 |

### 3.3. Đọc kết quả

- **I.** Đóng góp lớn nhất ở cả hai ngân sách, không tốn thêm đánh giá. Ở 1000 thế hệ khoảng cách thu hẹp
  (RC201-100: +0.403 xuống +0.290) vì baseline có thời gian bắt kịp, và trên case29 không còn ý nghĩa
  (+0.033, p = 0.45). Bỏ I khỏi tổ hợp làm HV tụt mạnh nhất (200 thế hệ, RC201-100: `all` +0.581,
  `all_minus_I` +0.205).
- **L.** Ở 200 thế hệ có ý nghĩa trên R201-50, RC201-100, case29; ở 1000 thế hệ mất ý nghĩa ở cả 4 instance.
  Tức L chủ yếu giúp hội tụ sớm hơn, đổi lại tốn 3.5–7.8 lần số lần đánh giá. Trên case29 L đóng góp rõ khi
  ghép (1000 thế hệ: `all` +0.099, `all_minus_L` +0.008). Mục 6 so L theo cùng chi phí.
- **D.** Đứng riêng chỉ có ý nghĩa trên RC201-100 ở 1000 thế hệ. Trong tổ hợp, bỏ D chênh trong khoảng
  ±0.015 trên Solomon. Trên case29 ở 1000 thế hệ bỏ D làm HV giảm (+0.099 xuống +0.055) nhưng không có ý nghĩa.
- **P.** Đứng riêng có ý nghĩa theo rank-sum ở 200 thế hệ trên R201-50, RC201-100. Kiểm định cặp (mục 5)
  cho thấy P tăng HV ở mọi seed trên Solomon. Về IGD, P cải thiện rõ nhất trên C102-25 (200 thế hệ
  −0.228, 1000 thế hệ −0.184): polish lấp các khoảng trống trên front.
- **A.** Đứng riêng không giúp ở 200 thế hệ, hại ở 1000 thế hệ trên C102-25 (−0.151, p = 0.023). Tổ hợp
  tắt A (`all_minus_A` = I+L+D+P) có HV cao nhất trên 4/4 instance ở 200 thế hệ và 3/4 ở 1000 thế hệ.
  So `all` với `all_minus_A`: tắt A chưa bao giờ làm HV giảm quá 0.003, và thường tăng.

## 4. Ablation 3 nhóm D, P, A (trước khi merge TV2)

Chạy trước khi có code của TV2, giữ lại vì dùng cùng seed và cho cùng kết luận về D, P, A. Cấu hình
`all` ở đây là D+P+A, khác `all` ở mục 3. Lượt 200 thế hệ chạy trên hai phiên bản `main` (trước và sau khi
kéo code TV2 về giữa chừng); đã kiểm tra lại một run bằng code mới, kết quả giống hệt từng chữ số, vì khi
cờ TV2 tắt code đi đúng đường cũ.

### 4.1. 200 thế hệ, seed 0–19 (`abl_g200`)

| cấu hình | C102-25 | R201-50 | RC201-100 | case29 |
|---|---|---|---|---|
| baseline | 0.955 ± 0.128 | 0.867 ± 0.084 | 0.772 ± 0.080 | 0.906 ± 0.116 |
| only_D | 1.009 ± 0.126<br>Δ +0.054, p 0.204 | 0.891 ± 0.086<br>Δ +0.024, p 0.372 | 0.803 ± 0.087<br>Δ +0.030, p 0.245 | 0.881 ± 0.100<br>Δ -0.025, p 0.358 |
| only_P | 1.024 ± 0.114<br>Δ +0.069, p 0.110 | **0.935 ± 0.075<br>Δ +0.069, p 0.014** | **0.911 ± 0.081<br>Δ +0.139, p < 0.001** | 0.912 ± 0.114<br>Δ +0.006, p 0.655 |
| only_A | 0.977 ± 0.116<br>Δ +0.022, p 0.665 | 0.860 ± 0.099<br>Δ -0.007, p 0.433 | 0.786 ± 0.096<br>Δ +0.014, p 0.725 | 0.915 ± 0.073<br>Δ +0.008, p 0.978 |
| all | 1.024 ± 0.114<br>Δ +0.069, p 0.088 | **0.938 ± 0.081<br>Δ +0.071, p 0.017** | **0.960 ± 0.086<br>Δ +0.188, p < 0.001** | 0.892 ± 0.117<br>Δ -0.015, p 0.808 |
| all_minus_D | **1.055 ± 0.112<br>Δ +0.100, p 0.017** | **0.936 ± 0.091<br>Δ +0.069, p 0.042** | **0.915 ± 0.090<br>Δ +0.143, p < 0.001** | 0.920 ± 0.072<br>Δ +0.014, p 0.871 |
| all_minus_P | 0.929 ± 0.122<br>Δ -0.026, p 0.372 | 0.866 ± 0.087<br>Δ -0.001, p 0.871 | **0.836 ± 0.089<br>Δ +0.064, p 0.033** | 0.880 ± 0.119<br>Δ -0.026, p 0.534 |
| all_minus_A | **1.087 ± 0.119<br>Δ +0.133, p 0.003** | **0.967 ± 0.091<br>Δ +0.100, p 0.002** | **0.927 ± 0.086<br>Δ +0.155, p < 0.001** | 0.885 ± 0.098<br>Δ -0.021, p 0.449 |

### 4.2. 1000 thế hệ, seed 0–9 (`abl_g1000`)

| cấu hình | C102-25 | R201-50 | RC201-100 | case29 |
|---|---|---|---|---|
| baseline | 1.027 ± 0.111 | 0.975 ± 0.079 | 0.959 ± 0.090 | 0.834 ± 0.116 |
| only_D | 1.047 ± 0.076<br>Δ +0.020, p 0.762 | 0.961 ± 0.077<br>Δ -0.014, p 0.597 | **1.031 ± 0.058<br>Δ +0.072, p 0.049** | 0.839 ± 0.154<br>Δ +0.006, p 0.940 |
| only_P | 1.104 ± 0.071<br>Δ +0.077, p 0.096 | 1.010 ± 0.081<br>Δ +0.035, p 0.226 | 0.990 ± 0.098<br>Δ +0.031, p 0.364 | 0.834 ± 0.115<br>Δ +0.000, p 0.880 |
| only_A | **0.876 ± 0.128<br>Δ -0.151, p 0.023** | 0.960 ± 0.074<br>Δ -0.015, p 0.597 | 1.026 ± 0.049<br>Δ +0.067, p 0.070 | 0.839 ± 0.127<br>Δ +0.005, p 0.940 |
| all | **1.099 ± 0.092<br>Δ +0.072, p 0.023** | 0.957 ± 0.067<br>Δ -0.018, p 0.406 | **1.048 ± 0.074<br>Δ +0.089, p 0.023** | 0.757 ± 0.091<br>Δ -0.076, p 0.151 |
| all_minus_D | 0.960 ± 0.132<br>Δ -0.067, p 0.257 | 0.995 ± 0.074<br>Δ +0.020, p 0.762 | **1.054 ± 0.058<br>Δ +0.096, p 0.013** | 0.839 ± 0.126<br>Δ +0.006, p 0.940 |
| all_minus_P | 1.028 ± 0.134<br>Δ +0.001, p 0.545 | 0.921 ± 0.067<br>Δ -0.054, p 0.082 | 1.024 ± 0.076<br>Δ +0.065, p 0.070 | 0.756 ± 0.090<br>Δ -0.077, p 0.151 |
| all_minus_A | **1.125 ± 0.074<br>Δ +0.098, p 0.019** | 0.985 ± 0.077<br>Δ +0.010, p 0.705 | **1.059 ± 0.058<br>Δ +0.100, p 0.008** | 0.839 ± 0.154<br>Δ +0.006, p 0.940 |

Ở cả hai ngân sách, D+P (`all_minus_A`) là tổ hợp tốt nhất trên 3 instance Solomon; A đứng riêng làm
C102-25 kém đi ở 1000 thế hệ; case29 không cấu hình nào khác baseline có ý nghĩa. Trên case29 ở 1000 thế
hệ, các tổ hợp có cả D lẫn A tụt xuống khoảng 0.757 (p = 0.15): có thể là tương tác D–A, chưa đủ bằng chứng.

## 5. Polish: kiểm định theo cặp seed

Với `mode: polish`, quần thể trước bước polish giống hệt bản không polish cùng seed (TV4 có test). Vì vậy
so cặp theo seed bằng Wilcoxon signed-rank mạnh hơn rank-sum. Mỗi ô: ΔHV trung bình (số seed tăng / tổng
số seed, p).

| Thí nghiệm | So sánh | C102-25 | R201-50 | RC201-100 | case29 |
|---|---|---|---|---|---|
| `abl5_g200` | P − baseline | +0.065 (20/20, p < 0.001) | +0.048 (20/20, p < 0.001) | +0.076 (20/20, p < 0.001) | +0.004 (15/20, p 0.001) |
| `abl5_g1000` | P − baseline | +0.073 (10/10, p 0.002) | +0.032 (10/10, p 0.002) | +0.024 (10/10, p 0.002) | +0.000 (2/10, p 0.500) |
| `abl_g200` | P − baseline | +0.069 (20/20, p < 0.001) | +0.069 (20/20, p < 0.001) | +0.139 (20/20, p < 0.001) | +0.006 (15/20, p 0.001) |
| `abl_g200` | D+P − D | +0.079 (20/20, p < 0.001) | +0.076 (20/20, p < 0.001) | +0.125 (20/20, p < 0.001) | +0.004 (15/20, p 0.001) |
| `abl_g1000` | P − baseline | +0.077 (10/10, p 0.002) | +0.035 (10/10, p 0.002) | +0.031 (10/10, p 0.002) | +0.000 (2/10, p 0.500) |
| `abl_g1000` | D+P − D | +0.078 (10/10, p 0.002) | +0.024 (10/10, p 0.002) | +0.028 (10/10, p 0.002) | +0.000 (2/10, p 0.500) |

Với 10 cặp, p nhỏ nhất có thể là 0.002, tức cả 10 seed cùng chiều. Lưu ý: polish chỉ thêm điểm vào front
nên theo cấu tạo HV không thể giảm; kiểm định này chỉ xác nhận mức tăng là thật và có ở mọi seed, không
trả lời "có đáng chi phí không". Câu đó TV4 đã đo trong `docs/tv4_results.md`: ở 200 thế hệ dùng cùng CPU
để chạy thêm thế hệ ngang hoặc tốt hơn polish; ở ngân sách đã hội tụ polish tốt hơn.

## 6. So sánh cùng chi phí

Các bảng ở mục 3 so **cùng số thế hệ**, nên cấu hình có L được dùng gấp 3.4–7.8 lần số lần đánh giá. Ở đây
so các cấu hình có số lần đánh giá gần bằng nhau: cấu hình có L chạy 200 thế hệ (54–111 nghìn lần đánh giá)
với cấu hình không L chạy 1000 thế hệ (80–81 nghìn). Thí nghiệm `eqcost` gộp run seed 0–9 từ `abl5_g200` và
`abl5_g1000` (chép nguyên file, đổi tên theo ngân sách) cộng một cấu hình chạy mới, `IDP_g1000` (I+D+P, tắt
A và L, 1000 thế hệ), rồi chuẩn hoá chung. Baseline so sánh là `baseline_g1000`. Tên cấu hình: chữ cái là
các nhóm được bật, hậu tố là số thế hệ.

HV:

| cấu hình | C102-25 | R201-50 | RC201-100 | case29 |
|---|---|---|---|---|
| baseline_g200 | **0.859 ± 0.160<br>Δ -0.215, p 0.004** | **0.649 ± 0.058<br>Δ -0.340, p < 0.001** | **0.388 ± 0.041<br>Δ -0.412, p < 0.001** | **0.487 ± 0.118<br>Δ -0.313, p < 0.001** |
| baseline_g1000 | 1.075 ± 0.093 | 0.988 ± 0.073 | 0.799 ± 0.070 | 0.800 ± 0.105 |
| I_g1000 | **1.155 ± 0.030<br>Δ +0.080, p 0.016** | **1.088 ± 0.044<br>Δ +0.100, p 0.001** | **1.093 ± 0.070<br>Δ +0.294, p < 0.001** | 0.838 ± 0.035<br>Δ +0.038, p 0.326 |
| IDP_g1000 | **1.166 ± 0.030<br>Δ +0.091, p 0.002** | **1.086 ± 0.050<br>Δ +0.098, p 0.002** | **1.083 ± 0.055<br>Δ +0.283, p < 0.001** | 0.836 ± 0.077<br>Δ +0.035, p 0.450 |
| IDPA_g1000 | **1.182 ± 0.011<br>Δ +0.107, p < 0.001** | **1.089 ± 0.069<br>Δ +0.101, p 0.003** | **1.120 ± 0.075<br>Δ +0.321, p < 0.001** | 0.811 ± 0.148<br>Δ +0.011, p 0.821 |
| L_g200 | **0.911 ± 0.097<br>Δ -0.164, p 0.004** | **0.748 ± 0.076<br>Δ -0.240, p < 0.001** | **0.553 ± 0.059<br>Δ -0.246, p < 0.001** | **0.629 ± 0.091<br>Δ -0.171, p 0.001** |
| ILDP_g200 | **1.193 ± 0.005<br>Δ +0.118, p < 0.001** | 1.019 ± 0.046<br>Δ +0.030, p 0.496 | **1.013 ± 0.045<br>Δ +0.213, p < 0.001** | 0.746 ± 0.082<br>Δ -0.055, p 0.199 |
| ILDPA_g200 | **1.194 ± 0.002<br>Δ +0.120, p < 0.001** | 0.994 ± 0.044<br>Δ +0.006, p 1.000 | **0.987 ± 0.059<br>Δ +0.188, p < 0.001** | 0.750 ± 0.077<br>Δ -0.050, p 0.174 |

IGD:

| cấu hình | C102-25 | R201-50 | RC201-100 | case29 |
|---|---|---|---|---|
| baseline_g200 | **0.550 ± 0.041<br>Δ +0.044, p 0.003** | **0.337 ± 0.039<br>Δ +0.198, p < 0.001** | **0.601 ± 0.056<br>Δ +0.288, p < 0.001** | **0.449 ± 0.100<br>Δ +0.218, p < 0.001** |
| baseline_g1000 | 0.506 ± 0.011 | 0.139 ± 0.035 | 0.313 ± 0.045 | 0.231 ± 0.054 |
| I_g1000 | 0.505 ± 0.005<br>Δ -0.001, p 0.821 | **0.094 ± 0.021<br>Δ -0.045, p 0.002** | **0.154 ± 0.022<br>Δ -0.159, p < 0.001** | 0.200 ± 0.023<br>Δ -0.031, p 0.059 |
| IDP_g1000 | **0.115 ± 0.025<br>Δ -0.392, p < 0.001** | **0.091 ± 0.024<br>Δ -0.047, p 0.002** | **0.107 ± 0.022<br>Δ -0.206, p < 0.001** | 0.209 ± 0.047<br>Δ -0.022, p 0.290 |
| IDPA_g1000 | **0.097 ± 0.023<br>Δ -0.409, p < 0.001** | **0.087 ± 0.033<br>Δ -0.051, p 0.003** | **0.089 ± 0.033<br>Δ -0.224, p < 0.001** | 0.222 ± 0.075<br>Δ -0.009, p 0.821 |
| L_g200 | 0.518 ± 0.031<br>Δ +0.012, p 0.880 | **0.279 ± 0.054<br>Δ +0.141, p < 0.001** | **0.469 ± 0.045<br>Δ +0.156, p < 0.001** | **0.348 ± 0.076<br>Δ +0.117, p < 0.001** |
| ILDP_g200 | **0.085 ± 0.011<br>Δ -0.421, p < 0.001** | 0.122 ± 0.026<br>Δ -0.016, p 0.545 | **0.147 ± 0.029<br>Δ -0.166, p < 0.001** | 0.256 ± 0.054<br>Δ +0.025, p 0.406 |
| ILDPA_g200 | **0.084 ± 0.014<br>Δ -0.422, p < 0.001** | 0.138 ± 0.020<br>Δ -0.001, p 0.705 | **0.158 ± 0.035<br>Δ -0.155, p < 0.001** | 0.261 ± 0.049<br>Δ +0.030, p 0.364 |

Số lần gọi evaluate trung bình mỗi run:

| cấu hình | C102-25 | R201-50 | RC201-100 | case29-29 |
|---|---|---|---|---|
| baseline_g200 | 16,080 | 16,080 | 16,080 | 16,080 |
| baseline_g1000 | 80,080 | 80,080 | 80,080 | 80,080 |
| I_g1000 | 80,080 | 80,080 | 80,080 | 80,080 |
| IDP_g1000 | 80,880 | 80,880 | 80,880 | 80,880 |
| IDPA_g1000 | 80,880 | 80,880 | 80,880 | 80,880 |
| L_g200 | 56,704 | 85,998 | 93,088 | 81,316 |
| ILDP_g200 | 53,944 | 80,639 | 110,936 | 84,506 |
| ILDPA_g200 | 54,296 | 81,986 | 111,062 | 84,002 |

So từng cặp có chi phí gần nhau (ΔHV, p rank-sum):

| Cặp | C102-25 | R201-50 | RC201-100 | case29 |
|---|---|---|---|---|
| L_g200 − baseline_g1000 | −0.164 (p 0.004) | −0.240 (p < 0.001) | −0.246 (p < 0.001) | −0.171 (p 0.001) |
| ILDP_g200 − IDP_g1000 | **+0.027 (p 0.002)** | −0.067 (p 0.010) | −0.070 (p 0.008) | −0.090 (p 0.019) |
| ILDPA_g200 − IDPA_g1000 | **+0.013 (p 0.003)** | −0.095 (p 0.007) | −0.133 (p 0.004) | −0.061 (p 0.364) |
| ILDP_g200 − I_g1000 | **+0.038 (p < 0.001)** | −0.069 (p 0.007) | −0.081 (p 0.010) | −0.092 (p 0.008) |

**Đọc kết quả.**

- L đứng riêng thua hẳn việc dùng cùng số lần đánh giá để chạy baseline thêm thế hệ, trên cả 4 instance.
- Trong tổ hợp, thêm L (rồi chạy ít thế hệ hơn) chỉ thắng trên C102-25, instance nhỏ nhất, và thua có ý
  nghĩa trên R201-50, RC201-100, case29. Ở RC201-100 cấu hình có L còn dùng nhiều đánh giá hơn
  (111 so với 81 nghìn) mà vẫn thua, nên kết luận ở đó chắc chắn.
- Khớp với báo cáo của TV2 (mục 7 của `docs/tv2_report.md`): cùng ngân sách đánh giá, mọi biến thể LS
  kém hơn.
- Cũng thấy ở bảng này: chạy baseline thêm thế hệ giúp rất nhiều (200 lên 1000 thế hệ: +0.2 đến +0.4 HV),
  tức 200 thế hệ chưa hội tụ, như đã ghi ở giai đoạn 1.
- Hạn chế: "chi phí" ở đây là số lần gọi evaluate. Một lần đánh giá trong LS và một lần đánh giá thường
  tốn gần như nhau (cùng decoder), nhưng LS có thêm chi phí quản lý bước đi; thời gian tường trong các bảng
  không dùng được vì 16 tiến trình chạy song song làm nhiễu.

Kết quả thô: `results/eqcost/`.

## 7. `every_eval` trên RC201-100 (200 thế hệ, seed 0–19)

Thí nghiệm `every_eval_rc201`: baseline, polish (P), và `dp_split` chế độ `every_eval` (mỗi lần chấm đều
chạy DP split với trọng số riêng của cá thể).

| Cấu hình | HV | IGD | Lần đánh giá | Thời gian tường TB (s) | Số điểm front |
|---|---|---|---|---|---|
| baseline | 0.738 ± 0.078 | 0.216 ± 0.028 | 16 080 | 30 | 22.4 |
| polish | **0.873 ± 0.079**<br>Δ +0.135, p < 0.001 | **0.176 ± 0.028**<br>Δ −0.039, p < 0.001 | 16 880 | 62 | 64.9 |
| every_eval | **0.934 ± 0.095**<br>Δ +0.196, p < 0.001 | **0.180 ± 0.029**<br>Δ −0.036, p < 0.001 | 16 080 | 582 | 49.1 |

`every_eval` so với `polish`: HV +0.061 (p = 0.055), IGD +0.004 (p = 0.83), tức không phân biệt được, trong
khi tốn khoảng 9 lần thời gian của polish và 19 lần của baseline. Số lần đánh giá của `every_eval` bằng
baseline nhưng mỗi lần là một lần DP, đắt hơn nhiều. Thời gian tường đo khi 16 tiến trình chạy song song
nên chỉ cho thấy độ lớn. **Kết luận: dùng `polish`, không dùng `every_eval`**, khớp khuyến nghị của TV4.

## 8. Đề xuất cho giai đoạn 4

| Cờ | Đề xuất | Lý do |
|---|---|---|
| `init_smart` (I) | **bật** | đóng góp lớn nhất, không tốn thêm đánh giá |
| `diversity` (D) | **bật**, `sde`, k = 1, archive tắt | có ích ở instance lớn, không tốn thêm; trong tổ hợp gần như trung tính |
| `dp_split` (P) | **bật**, `mode: polish`, K = 10 | luôn tăng HV ở mọi seed trên Solomon, tốn khoảng 5% đánh giá |
| `adaptive_rates` (A) | **tắt** | không giúp, có chỗ hại; ba nguồn độc lập cùng kết luận |
| `local_search` (L) | **tắt** khi so cùng chi phí | thua việc chạy thêm thế hệ ở 3/4 instance; chỉ nên báo như một biến thể "cùng số thế hệ" |

Khi so với bài báo (cùng 200 thế hệ như bài báo dùng), có thể báo thêm I+L+D+P vì đó là cấu hình tốt
nhất theo số thế hệ, nhưng phải ghi rõ nó tốn 3.4–7.7 lần số lần đánh giá.

## 9. Hạn chế

- Bốn instance, mỗi kích thước một instance. Kết luận chưa chắc đúng cho C1/R2/RC2 khác hay các instance
  còn lại trong danh sách chín instance của bài báo.
- Chưa hiệu chỉnh đa so sánh. Các kết luận chính (I, P, A tắt, L theo chi phí) đứng vững vì có p < 0.001
  hoặc lặp lại ở nhiều bảng độc lập; các kết luận về D thì yếu hơn.
- 1000 thế hệ có lẽ vẫn chưa hội tụ hẳn trên RC201-100 (HV vẫn tăng khi thêm thế hệ).
- Tham số của mỗi cải tiến được tuning riêng lẻ, không tuning lại khi ghép.

## 10. Tái hiện

Ablation (script trong repo):

```powershell
python -m scripts.ablation --exp abl5_g200 --groups D,P,A,I,L --seeds 0-19
python -m scripts.ablation --exp abl5_g1000 --groups D,P,A,I,L --seeds 0-9 --set nsga2.n_gen=1000
python -m scripts.ablation --exp abl_g200 --seeds 0-19
python -m scripts.ablation --exp abl_g1000 --seeds 0-9 --set nsga2.n_gen=1000
```

Tuning, `eqcost` và `every_eval_rc201` chạy bằng script tạm, tương đương với các lệnh runner sau (một cấu
hình mỗi lệnh; lặp cho từng instance):

```powershell
# tuning đa dạng, ví dụ sde k = 3 (k >= 3 cần bản sửa truncate)
python -m src.runner run --exp tune_div --config sde_k3 --instance C102 --n 25 --seeds 100,101,102,103,104 `
  --set improvements.diversity=true --set improvements.diversity_params.archive=false `
  --set improvements.diversity_params.density=sde --set improvements.diversity_params.k=3

# I+D+P 1000 thế hệ cho eqcost
python -m src.runner run --exp eqcost --config IDP_g1000 --instance C102 --n 25 --seeds 0,1,2,3,4,5,6,7,8,9 `
  --set nsga2.n_gen=1000 --set improvements.init_smart=true `
  --set improvements.diversity=true --set improvements.diversity_params.archive=false `
  --set improvements.dp_split=true --set improvements.dp_split_params.mode=polish

# every_eval trên RC201-100
python -m src.runner run --exp every_eval_rc201 --config every_eval --instance RC201 --n 100 `
  --seeds 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19 `
  --set improvements.dp_split=true --set improvements.dp_split_params.mode=every_eval
```

Các cấu hình còn lại của `eqcost` là bản chép seed 0–9 từ `abl5_g200` / `abl5_g1000` (baseline, only_I,
only_L, all, all_minus_A, all_minus_L). Phân tích: `python -m src.runner analyze --exp <tên> --instance <C102-25 ...>`.
Mọi tiến trình chạy với `OMP_NUM_THREADS=1`.
