# Kết quả cuối giai đoạn 4

Tài liệu chốt kết quả của nhóm (27/11/2026): NSGA-II gốc (baseline) và cấu hình cuối I+D+P trên đủ 9
instance Solomon mà bài báo dùng và case thực tế 29 điểm, kèm bảng đặt cạnh số của bài báo. Cách chọn cấu
hình cuối xem `docs/ablation_results.md` và README mục "Kết quả giai đoạn 3". Số liệu tổng hợp nằm ở
`results/final_summary.csv` (không đưa lên git), lệnh tái hiện ở mục 7.

## Tóm tắt

1. **I+D+P tốt hơn NSGA-II gốc có ý nghĩa thống kê trên 10/10 instance ở 200 thế hệ** (p < 0.001 cả HV lẫn
   IGD) **và trên 7/10 ở 1000 thế hệ**. Ba instance còn lại (R201-25, RC202-25, case29) là nơi baseline chạy
   lâu cũng gần hội tụ; I+D+P vẫn có HV cao hơn ở cả ba, và IGD tốt hơn có ý nghĩa trên R201-25 và case29.
2. **Cải tiến càng rõ khi bài toán càng lớn.** Ở 200 thế hệ HV tăng 8–37% với 25 khách, 42–100% với 50
   khách, 115–300% với 100 khách.
3. **Chi phí thêm nhỏ:** 5% số lần đánh giá; thời gian chạy khoảng 1.1–2.3 lần baseline (phần polish).
4. **So với bài báo:** mức cải thiện của nhóm cùng chiều với mức INSGA-III cải thiện so với NSGA-II trong bài
   báo, và lớn hơn ở instance 50 và 100 khách. f1 của nhóm thấp hơn bài báo nhiều lần, nhưng **không so trực
   tiếp được** vì hai mô hình khác nhau (mục 5). Instance so sát nhất là case29: f1 nhỏ nhất của nhóm (2224)
   ngang INSGA-III (2262).
5. Mọi lời giải trên front của mọi run đều không vượt đội xe.

## 1. Thiết lập

| Mục | Giá trị |
|---|---|
| Instance | C102, R201, RC202 ở 25 và 50 khách; C102, R201, RC201 ở 100 khách (đúng danh sách bài báo); case29 |
| Mô hình | mô hình đã sửa của nhóm (README mục "Chỉnh sửa bài báo và giả định"); `satisfaction_time: arrival`, `split_rule: capacity_time` |
| NSGA-II | n_pop 80, pc 0.7, pm 0.1 (Solomon) / 0.2 (case29), lai ghép OX, đột biến `standard`, loại cá thể trùng |
| baseline | NSGA-II gốc, mọi cờ cải tiến tắt |
| **I+D+P** (cấu hình cuối) | `init_smart` (20/20/60) + `diversity` (SDE, k = 1, tắt archive) + `dp_split` chế độ polish (K = 10) |
| I+L+D+P (tham khảo) | I+D+P cộng `local_search` (`split_drift_policy: evaluate_actual`); chỉ chạy 200 thế hệ vì tốn 3–7 lần số lần đánh giá |
| Ngân sách | `final_g200`: 200 thế hệ (bằng bài báo), seed 0–19; `final_g1000`: 1000 thế hệ, seed 0–9 |
| Chỉ số | HV (điểm tham chiếu 1.1), IGD, SP, DM; chuẩn hoá và reference set gộp mọi front của mọi cấu hình trong cùng thí nghiệm |
| Kiểm định | Wilcoxon rank-sum hai phía so với baseline cùng thí nghiệm |

**Cách đọc bảng.** Mỗi ô: trung bình ± độ lệch chuẩn qua các seed; dòng dưới là chênh lệch với baseline cùng
ngân sách và p-value; ô **đậm** là p < 0.05. HV lớn là tốt, IGD nhỏ là tốt. Số HV/IGD của cột 200 thế hệ và
cột 1000 thế hệ thuộc hai thí nghiệm khác nhau, chuẩn hoá riêng, **không so ngang giữa hai nhóm cột**.

## 2. HV

| Instance | baseline (200) | I+D+P (200) | I+L+D+P (200) | baseline (1000) | I+D+P (1000) |
|---|---|---|---|---|---|
| C102-25 | 0.865 ± 0.164 | **1.183 ± 0.039<br>Δ +0.318, p < 0.001** | **1.227 ± 0.012<br>Δ +0.362, p < 0.001** | 0.995 ± 0.125 | **1.111 ± 0.041<br>Δ +0.116, p 0.002** |
| R201-25 | 0.880 ± 0.080 | **0.980 ± 0.062<br>Δ +0.100, p < 0.001** | **1.010 ± 0.051<br>Δ +0.131, p < 0.001** | 0.914 ± 0.034 | 0.945 ± 0.058<br>Δ +0.032, p 0.174 |
| RC202-25 | 0.911 ± 0.051 | **0.983 ± 0.034<br>Δ +0.072, p < 0.001** | **1.039 ± 0.049<br>Δ +0.128, p < 0.001** | 0.966 ± 0.049 | 0.988 ± 0.036<br>Δ +0.022, p 0.257 |
| C102-50 | 0.552 ± 0.079 | **1.108 ± 0.065<br>Δ +0.555, p < 0.001** | **1.085 ± 0.072<br>Δ +0.533, p < 0.001** | 0.782 ± 0.112 | **1.164 ± 0.069<br>Δ +0.382, p < 0.001** |
| R201-50 | 0.653 ± 0.078 | **0.929 ± 0.060<br>Δ +0.276, p < 0.001** | **1.060 ± 0.050<br>Δ +0.407, p < 0.001** | 0.972 ± 0.084 | **1.086 ± 0.057<br>Δ +0.114, p 0.002** |
| RC202-50 | 0.699 ± 0.061 | **1.013 ± 0.049<br>Δ +0.313, p < 0.001** | **1.071 ± 0.052<br>Δ +0.372, p < 0.001** | 0.767 ± 0.070 | **0.991 ± 0.092<br>Δ +0.224, p < 0.001** |
| C102-100 | 0.282 ± 0.050 | **1.129 ± 0.042<br>Δ +0.846, p < 0.001** | **1.145 ± 0.041<br>Δ +0.863, p < 0.001** | 0.514 ± 0.080 | **1.172 ± 0.061<br>Δ +0.657, p < 0.001** |
| R201-100 | 0.377 ± 0.041 | **0.809 ± 0.065<br>Δ +0.432, p < 0.001** | **0.934 ± 0.059<br>Δ +0.557, p < 0.001** | 0.666 ± 0.072 | **0.899 ± 0.072<br>Δ +0.233, p < 0.001** |
| RC201-100 | 0.389 ± 0.042 | **0.858 ± 0.047<br>Δ +0.469, p < 0.001** | **0.968 ± 0.035<br>Δ +0.578, p < 0.001** | 0.797 ± 0.079 | **1.112 ± 0.061<br>Δ +0.315, p < 0.001** |
| case29 | 0.725 ± 0.108 | **0.910 ± 0.071<br>Δ +0.185, p < 0.001** | **0.991 ± 0.076<br>Δ +0.266, p < 0.001** | 0.771 ± 0.134 | 0.817 ± 0.091<br>Δ +0.046, p 0.326 |

## 3. IGD

| Instance | baseline (200) | I+D+P (200) | I+L+D+P (200) | baseline (1000) | I+D+P (1000) |
|---|---|---|---|---|---|
| C102-25 | 0.482 ± 0.065 | **0.088 ± 0.043<br>Δ -0.394, p < 0.001** | **0.052 ± 0.015<br>Δ -0.430, p < 0.001** | 0.521 ± 0.021 | **0.120 ± 0.032<br>Δ -0.401, p < 0.001** |
| R201-25 | 0.170 ± 0.045 | **0.087 ± 0.027<br>Δ -0.083, p < 0.001** | **0.074 ± 0.022<br>Δ -0.096, p < 0.001** | 0.084 ± 0.019 | **0.056 ± 0.023<br>Δ -0.028, p 0.019** |
| RC202-25 | 0.098 ± 0.020 | **0.077 ± 0.010<br>Δ -0.022, p < 0.001** | **0.061 ± 0.015<br>Δ -0.037, p < 0.001** | 0.064 ± 0.016 | 0.062 ± 0.016<br>Δ -0.001, p 0.650 |
| C102-50 | 0.528 ± 0.054 | **0.100 ± 0.033<br>Δ -0.428, p < 0.001** | **0.121 ± 0.046<br>Δ -0.407, p < 0.001** | 0.391 ± 0.068 | **0.082 ± 0.050<br>Δ -0.310, p < 0.001** |
| R201-50 | 0.301 ± 0.056 | **0.130 ± 0.039<br>Δ -0.171, p < 0.001** | **0.068 ± 0.025<br>Δ -0.233, p < 0.001** | 0.106 ± 0.036 | **0.049 ± 0.030<br>Δ -0.057, p 0.002** |
| RC202-50 | 0.266 ± 0.040 | **0.089 ± 0.025<br>Δ -0.177, p < 0.001** | **0.058 ± 0.021<br>Δ -0.208, p < 0.001** | 0.220 ± 0.035 | **0.090 ± 0.040<br>Δ -0.130, p < 0.001** |
| C102-100 | 0.725 ± 0.055 | **0.074 ± 0.024<br>Δ -0.651, p < 0.001** | **0.069 ± 0.019<br>Δ -0.656, p < 0.001** | 0.606 ± 0.048 | **0.097 ± 0.054<br>Δ -0.509, p < 0.001** |
| R201-100 | 0.514 ± 0.041 | **0.218 ± 0.053<br>Δ -0.296, p < 0.001** | **0.159 ± 0.051<br>Δ -0.355, p < 0.001** | 0.369 ± 0.043 | **0.200 ± 0.068<br>Δ -0.170, p < 0.001** |
| RC201-100 | 0.467 ± 0.046 | **0.152 ± 0.027<br>Δ -0.316, p < 0.001** | **0.094 ± 0.022<br>Δ -0.374, p < 0.001** | 0.265 ± 0.055 | **0.076 ± 0.027<br>Δ -0.189, p < 0.001** |
| case29 | 0.274 ± 0.067 | **0.134 ± 0.035<br>Δ -0.140, p < 0.001** | **0.109 ± 0.044<br>Δ -0.165, p < 0.001** | 0.186 ± 0.045 | **0.141 ± 0.050<br>Δ -0.045, p 0.023** |

## 4. Độ đều và độ trải của front (1000 thế hệ)

SP: độ đều khoảng cách giữa các điểm, nhỏ là đều. DM: độ trải trên ba mục tiêu (đã chuẩn hoá), lớn là trải
rộng. Trung bình qua 10 seed.

| Instance | SP baseline | SP I+D+P | DM baseline | DM I+D+P | Số điểm front baseline | Số điểm front I+D+P |
|---|---|---|---|---|---|---|
| C102-25 | 0.022 | 0.030 | 0.424 | 1.272 | 27.6 | 48.2 |
| R201-25 | 0.014 | 0.034 | 0.850 | 1.339 | 58.4 | 72.3 |
| RC202-25 | 0.010 | 0.009 | 0.724 | 0.898 | 75.1 | 77.6 |
| C102-50 | 0.013 | 0.024 | 0.320 | 0.957 | 22.0 | 28.2 |
| R201-50 | 0.010 | 0.026 | 0.578 | 1.077 | 47.8 | 71.4 |
| RC202-50 | 0.006 | 0.016 | 0.609 | 1.021 | 71.4 | 92.2 |
| C102-100 | 0.009 | 0.021 | 0.294 | 1.119 | 29.1 | 52.2 |
| R201-100 | 0.008 | 0.023 | 0.383 | 1.049 | 39.2 | 94.5 |
| RC201-100 | 0.005 | 0.028 | 0.360 | 1.009 | 45.8 | 91.7 |
| case29 | 0.068 | 0.068 | 0.739 | 0.884 | 15.8 | 23.8 |

I+D+P cho front **trải rộng hơn hẳn** (DM gấp 1.2–3.8 lần) và **nhiều điểm hơn**, đổi lại SP thường cao hơn
(khoảng cách giữa các điểm kém đều hơn). Đây là tác dụng của polish: chấm lại mỗi hoán vị với 10 vector trọng
số khác nhau nên thêm điểm ở nhiều vùng của front, kể cả vùng xa.

## 5. Đặt cạnh bài báo

### 5.1. Mức cải thiện HV so với NSGA-II của chính mình

Bài báo và nhóm chuẩn hoá HV khác nhau (bài báo không ghi cách chuẩn hoá và điểm tham chiếu), nên **không so
số HV giữa hai bên**. Chỉ so mức tăng tương đối mỗi bên đạt được so với NSGA-II của chính mình.

| Instance | Bài báo: HV NSGA-II → INSGA-III | Tăng | Nhóm 200 thế hệ: baseline → I+D+P | Tăng | Nhóm 1000 thế hệ: baseline → I+D+P | Tăng |
|---|---|---|---|---|---|---|
| C102-25 | 0.845 → 0.861 | +1.9% | 0.865 → 1.183 | +36.7% | 0.995 → 1.111 | +11.7% |
| R201-25 | 0.720 → 0.849 | +17.9% | 0.880 → 0.980 | +11.4% | 0.914 → 0.945 | +3.5% |
| RC202-25 | 0.731 → 0.818 | +11.9% | 0.911 → 0.983 | +7.9% | 0.966 → 0.988 | +2.2% |
| C102-50 | 0.737 → 0.858 | +16.4% | 0.552 → 1.108 | +100.5% | 0.782 → 1.164 | +48.8% |
| R201-50 | 0.760 → 0.830 | +9.3% | 0.653 → 0.929 | +42.3% | 0.972 → 1.086 | +11.8% |
| RC202-50 | 0.755 → 0.811 | +7.4% | 0.699 → 1.013 | +44.8% | 0.767 → 0.991 | +29.2% |
| C102-100 | 0.779 → 0.829 | +6.4% | 0.282 → 1.129 | +299.7% | 0.514 → 1.172 | +127.8% |
| R201-100 | 0.530 → 0.753 | +41.9% | 0.377 → 0.809 | +114.6% | 0.666 → 0.899 | +35.0% |
| RC201-100 | 0.692 → 0.803 | +16.1% | 0.389 → 0.858 | +120.5% | 0.797 → 1.112 | +39.5% |
| case29 | 0.604 → 0.805 | +33.3% | 0.725 → 0.910 | +25.5% | 0.771 → 0.817 | +6.0% |

Ở 200 thế hệ (cùng ngân sách với bài báo), mức tăng của nhóm lớn hơn của bài báo trên 7/10 instance; nhỏ hơn
ở R201-25, RC202-25 và case29, ba instance nhỏ mà baseline của nhóm vốn đã tốt. Mức tăng ở 1000 thế hệ nhỏ
hơn vì baseline có thêm thời gian để bắt kịp. Phần trăm tăng phụ thuộc cách chuẩn hoá, nên chỉ dùng để nói
"cùng chiều, cùng độ lớn hay lớn hơn", không dùng để xếp hạng chính xác.

### 5.2. Giá trị mục tiêu

Mỗi ô: **tốt nhất qua các run / trung bình qua các run**. Với nhóm, "tốt nhất" là giá trị nhỏ nhất (f1, f2)
hoặc lớn nhất (f3) trên front của run tốt nhất, "trung bình" là trung bình qua các run của giá trị đó. Bài báo
không nói rõ cột min/avg của họ tính thế nào; đây là cách hiểu của nhóm.

**f1, chi phí (CNY), nhỏ là tốt:**

| Instance | NSGA-II (bài báo) | INSGA-III (bài báo) | baseline nhóm (1000) | I+D+P nhóm (200) | I+D+P nhóm (1000) |
|---|---|---|---|---|---|
| C102-25 | 5042 / 5236 | 2205 / 2456 | 1180 / 1249 | 1168 / 1187 | 1150 / 1168 |
| R201-25 | 14965 / 16143 | 8072 / 8451 | 2355 / 2487 | 2476 / 2594 | 2413 / 2488 |
| RC202-25 | 9422 / 10123 | 6768 / 7265 | 1995 / 2217 | 2170 / 2303 | 2003 / 2235 |
| C102-50 | 35704 / 36874 | 12025 / 13495 | 2572 / 3018 | 2051 / 2594 | 1956 / 2211 |
| R201-50 | 21448 / 22587 | 15491 / 16389 | 4298 / 4741 | 4834 / 5165 | 4276 / 4519 |
| RC202-50 | 27903 / 29006 | 15882 / 16004 | 4391 / 5020 | 4398 / 4879 | 3968 / 4278 |
| C102-100 | 153007 / 158598 | 34458 / 54962 | 9565 / 10396 | 6160 / 6844 | 5038 / 5826 |
| R201-100 | 47380 / 49423 | 33544 / 41019 | 9205 / 9870 | 9808 / 10603 | 8231 / 9099 |
| RC201-100 | 60521 / 61362 | 47715 / 50715 | 10781 / 11983 | 10497 / 11462 | 9157 / 9758 |
| case29 | 4179 / 4342 | 2262 / 2448 | 2200 / 2276 | 2274 / 2310 | 2224 / 2275 |

**f2, khí thải (kg CO₂), nhỏ là tốt:**

| Instance | NSGA-II (bài báo) | INSGA-III (bài báo) | baseline nhóm (1000) | I+D+P nhóm (200) | I+D+P nhóm (1000) |
|---|---|---|---|---|---|
| C102-25 | 280.5 / 315.5 | 257.5 / 306.0 | 129.6 / 140.3 | 112.3 / 116.0 | 112.3 / 114.9 |
| R201-25 | 738.4 / 750.9 | 660.6 / 683.5 | 315.5 / 322.8 | 281.7 / 315.7 | 269.3 / 299.7 |
| RC202-25 | 594.1 / 613.5 | 458.0 / 490.6 | 253.6 / 278.1 | 230.5 / 262.2 | 217.4 / 256.7 |
| C102-50 | 212.8 / 229.8 | 175.8 / 204.1 | 309.2 / 393.2 | 223.3 / 255.6 | 214.8 / 238.2 |
| R201-50 | 532.6 / 559.3 | 486.9 / 512.4 | 606.3 / 659.0 | 597.7 / 667.9 | 575.9 / 615.9 |
| RC202-50 | 544.8 / 583.8 | 503.6 / 529.6 | 564.6 / 693.0 | 429.3 / 554.1 | 404.6 / 516.2 |
| C102-100 | 661.3 / 702.7 | 552.4 / 581.0 | 1319.6 / 1422.2 | 566.4 / 663.3 | 586.5 / 634.9 |
| R201-100 | 1115.9 / 1256.8 | 991.4 / 1084.7 | 1265.9 / 1351.5 | 968.0 / 1224.8 | 895.4 / 1126.6 |
| RC201-100 | 1150.1 / 1365.7 | 1070.1 / 1296.8 | 1573.6 / 1665.6 | 798.5 / 1256.1 | 1105.8 / 1225.8 |
| case29 | 172.0 / 191.4 | 140.7 / 160.4 | 197.3 / 204.4 | 200.3 / 204.2 | 197.3 / 200.9 |

**f3, hài lòng trung bình (0–1), lớn là tốt:**

| Instance | NSGA-II (bài báo) | INSGA-III (bài báo) | baseline nhóm (1000) | I+D+P nhóm (200) | I+D+P nhóm (1000) |
|---|---|---|---|---|---|
| C102-25 | 0.902 / 0.863 | 0.997 / 0.915 | 0.999 / 0.985 | 0.992 / 0.990 | 0.992 / 0.992 |
| R201-25 | 0.782 / 0.761 | 0.844 / 0.820 | 0.904 / 0.882 | 0.904 / 0.879 | 0.904 / 0.887 |
| RC202-25 | 0.886 / 0.844 | 0.947 / 0.907 | 0.960 / 0.930 | 0.960 / 0.916 | 0.990 / 0.938 |
| C102-50 | 0.824 / 0.786 | 0.926 / 0.900 | 0.980 / 0.950 | 0.976 / 0.944 | 0.996 / 0.987 |
| R201-50 | 0.803 / 0.785 | 0.865 / 0.839 | 0.932 / 0.894 | 0.915 / 0.869 | 0.954 / 0.922 |
| RC202-50 | 0.835 / 0.816 | 0.909 / 0.885 | 0.970 / 0.948 | 0.938 / 0.909 | 0.960 / 0.939 |
| C102-100 | 0.693 / 0.679 | 0.912 / 0.906 | 0.914 / 0.845 | 0.914 / 0.890 | 0.973 / 0.949 |
| R201-100 | 0.773 / 0.760 | 0.865 / 0.832 | 0.857 / 0.814 | 0.826 / 0.786 | 0.885 / 0.851 |
| RC201-100 | 0.789 / 0.777 | 0.855 / 0.827 | 0.852 / 0.824 | 0.820 / 0.775 | 0.889 / 0.850 |
| case29 | 0.978 / 0.946 | 1.000 / 0.944 | 0.897 / 0.893 | 0.897 / 0.866 | 0.931 / 0.890 |

### 5.3. Vì sao số của nhóm lệch bài báo

Các con số chỉ đặt cạnh nhau, không dùng để kết luận "nhóm tốt hơn bài báo", vì mô hình hai bên khác nhau ở
nhiều chỗ (chi tiết ở README mục "Chỉnh sửa bài báo và giả định của nhóm"):

- **f1 của nhóm thấp hơn bài báo 2–30 lần trên Solomon.** Phần lớn f1 là tiền phạt đến muộn F4. Cách cắt tuyến
  `capacity_time` của nhóm mở thêm xe khi xe sắp đến khách sau giờ muộn nhất, nên lời giải ít bị phạt muộn hơn
  nhiều. Bài báo không nói cách cắt tuyến; nếu họ chỉ cắt khi xe đầy thì tiền phạt sẽ rất lớn (với cách đó,
  C102-25 ngẫu nhiên có f1 khoảng 25 000). Đơn vị phạt (chia 60 để đổi phút sang giờ) cũng có thể khác.
- **f2 là mục tiêu so được sát nhất trên Solomon**, vì f2 chỉ phụ thuộc quãng đường (hệ số 679.44 g/km sau khi
  sửa công thức). Nhóm thấp hơn cả hai cột của bài báo ở 25 khách; ở 50 và 100 khách thấp hơn hoặc ngang, trừ C102-50 và
  R201-50 (cao hơn INSGA-III khoảng 20%).
- **case29:** f1 nhỏ nhất của nhóm (2224 ở 1000 thế hệ) ngang INSGA-III (2262). f2 nhỏ nhất của nhóm (197) cao
  hơn 140.65 của bài báo; đây là chỗ bài báo tự mâu thuẫn về hệ số phát thải (README, "Một chỗ bài báo tự mâu
  thuẫn": 140.65 kg ứng với 417 g/km, trong khi công thức cho 679 g/km). f3 lớn nhất của nhóm 0.931 so với
  1.000 của bài báo, do nhóm tính hài lòng tại giờ xe đến (`arrival`), nên xe đến sớm cũng bị trừ điểm.
- **f3 trên Solomon** của nhóm (I+D+P, 1000 thế hệ) ngang hoặc cao hơn INSGA-III ở mọi instance; ở 200 thế hệ
  thấp hơn một chút trên R201-100 và RC201-100.

## 6. Chi phí tính toán

| Instance | Lần đánh giá baseline / I+D+P / I+L+D+P (200) | Thời gian TB (s) baseline / I+D+P / I+L+D+P (200) | Thời gian TB (s) baseline / I+D+P (1000) |
|---|---|---|---|
| C102-25 | 16,080 / 16,880 / 54,074 | 6 / 8 / 20 | 27 / 28 |
| R201-25 | 16,080 / 16,880 / 52,846 | 6 / 8 / 20 | 26 / 29 |
| RC202-25 | 16,080 / 16,880 / 49,094 | 5 / 7 / 19 | 25 / 28 |
| C102-50 | 16,080 / 16,880 / 91,259 | 10 / 19 / 58 | 47 / 53 |
| R201-50 | 16,080 / 16,880 / 81,234 | 10 / 20 / 54 | 44 / 52 |
| RC202-50 | 16,080 / 16,880 / 77,600 | 10 / 18 / 50 | 43 / 50 |
| C102-100 | 16,080 / 16,880 / 120,546 | 18 / 38 / 188 | 90 / 105 |
| R201-100 | 16,080 / 16,880 / 105,340 | 18 / 42 / 147 | 85 / 108 |
| RC201-100 | 16,080 / 16,880 / 111,531 | 18 / 39 / 136 | 86 / 104 |
| case29 | 16,080 / 16,880 / 84,279 | 7 / 8 / 34 | 33 / 33 |

Số lần đánh giá là số lần gọi decoder (thước đo chi phí không phụ thuộc máy). Thời gian là thời gian tường
trung bình mỗi run khi 16 tiến trình chạy song song, chỉ dùng để thấy độ lớn. I+D+P tốn thêm 800 lần đánh
giá (polish: 80 hoán vị × 10 trọng số, mỗi lần là một lần DP), tức khoảng 1.1–2.3 lần thời gian baseline ở
200 thế hệ và 1.0–1.3 lần ở 1000 thế hệ. I+L+D+P tốn 3–7.5 lần số lần đánh giá và 3–10 lần thời gian.

## 7. Tái hiện

```powershell
python -m scripts.final_runs run --exp final_g200 --seeds 0-19 --configs baseline,IDP,ILDP
python -m scripts.final_runs run --exp final_g1000 --seeds 0-9 --configs baseline,IDP --set nsga2.n_gen=1000
python -m scripts.final_runs summarize final_g200 final_g1000
```

Lượt chạy gốc: 800 run trên 16 tiến trình, khoảng 1 giờ. Mọi tiến trình đặt `OMP_NUM_THREADS=1`.

## 8. Hạn chế

- Một instance cho mỗi loại và kích thước (đúng như bài báo), nên kết luận chưa chắc đúng cho các instance
  Solomon khác.
- 1000 thế hệ có lẽ vẫn chưa hội tụ hẳn ở 100 khách.
- So với bài báo chỉ ở mức đặt cạnh: khác mô hình, khác cách chuẩn hoá HV, và bài báo không nói rõ cách tính
  cột min/avg.
- Tham số NSGA-II (n_pop, pc, pm) lấy theo bài báo, chưa tuning lại.

## 9. Hình

Ảnh ở `docs/figures/final/`, chú thích và cách đọc từng hình ở `docs/figures/final/captions.md`, vẽ lại bằng
`python -m scripts.plot_final`.

| Hình | Nội dung |
|---|---|
| `f01_case29_map` | kho và 29 khách của case thực tế, kích thước điểm theo nhu cầu |
| `f02_satisfaction` | hàm hài lòng W(t) và tiền phạt F4 theo giờ đến |
| `f03_algorithm` | sơ đồ vòng lặp NSGA-II và chỗ gắn ba cải tiến I, D, P |
| `f04_routes_case29` | bộ tuyến của ba lời giải đầu mút: chi phí nhỏ nhất, khí thải nhỏ nhất, hài lòng lớn nhất |
| `f05_timeline_case29` | giờ xe đến so với khung giờ từng khách, lời giải hài lòng lớn nhất |
| `f06_pareto_2d`, `f07_pareto_3d` | front của baseline và I+D+P, run có HV trung vị |
| `f08_convergence` | HV theo thế hệ, 1000 thế hệ |
| `f09_hv_box` | phân bố HV qua 20 seed, 200 thế hệ |
| `f10_ablation_heatmap` | ΔHV của 11 cấu hình ablation |
| `f11_paper_vs_ours` | mức tăng HV so với NSGA-II của chính mình: bài báo và nhóm |
