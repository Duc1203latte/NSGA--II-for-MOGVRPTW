# TV4: kết quả giai đoạn 2 (n = 25, 50) trên baseline thật

Thí nghiệm `tv4_main`; bảng dựng bởi `python -m scripts.tv4_report --exp tv4_main --instances C102-25 R201-50`,
phần chẩn đoán bởi `python -m scripts.tv4_diagnose --exp tv4_main --instances C102-25 R201-50`.

- **Instance:** C102-25 và R201-50. RC201-100 chưa chạy, chờ TV1 quyết định về việc `split_capacity_time` vượt đội xe ở n = 100.
- **Cấu hình:** `baseline` (mọi cờ tắt), `dp` (`improvements.dp_split=true`), `adapt` (`improvements.adaptive_rates=true`), `both` (cả hai), và `baseline_eqtime` (baseline với nhiều thế hệ hơn, xem mục "Equal-time comparison").
- **Thiết lập:** `config.yaml` mặc định (n_pop 80, n_gen 200 trừ `baseline_eqtime`, pc 0.7, pm 0.1, `satisfaction_time: arrival`, `split_rule: capacity_time`, tham số cải tiến mặc định chưa tuning), seed 0–9 cho mọi cấu hình.

## Bảng kết quả

| Instance | Cấu hình | n_gen | HV | ΔHV vs baseline | p (HV) | p (HV) vs eqtime | IGD | p (IGD) | p (IGD) vs eqtime | SP | n_evals | Thời gian/run (s) | Khả thi (front) | Khả thi (quần thể) | Số xe TB (front) | Số điểm front |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C102-25 | baseline | 200 | 0.9034 ± 0.1763 | — | — | — | 0.2455 ± 0.1070 | — | — | 0.0447 ± 0.0429 | 16080 | 3.8 | 1.00 | 1.00 | 3.0 | 9.7 |
| C102-25 | baseline_eqtime | 1400 | 1.1609 ± 0.0781 | +0.2575 | 0.002 | — | 0.1114 ± 0.0333 | 0.002 | — | 0.0135 ± 0.0093 | 112080 | 56.4 | 1.00 | 1.00 | 3.0 | 34.4 |
| C102-25 | dp | 200 | 0.9998 ± 0.1528 | +0.0963 | 0.174 | 0.016 | 0.1980 ± 0.1001 | 0.364 | 0.082 | 0.0897 ± 0.0732 | 16080 | 25.1 | 1.00 | 1.00 | 3.2 | 19.0 |
| C102-25 | adapt | 200 | 0.8641 ± 0.2028 | -0.0393 | 0.496 | 0.002 | 0.2651 ± 0.1331 | 0.545 | 0.010 | 0.0422 ± 0.0284 | 16080 | 3.9 | 1.00 | 1.00 | 3.1 | 7.9 |
| C102-25 | both | 200 | 1.0505 ± 0.1784 | +0.1471 | 0.059 | 0.112 | 0.1692 ± 0.1179 | 0.082 | 0.450 | 0.0657 ± 0.0544 | 16080 | 25.4 | 1.00 | 1.00 | 3.1 | 18.0 |
| R201-50 | baseline | 200 | 0.6769 ± 0.0573 | — | — | — | 0.2898 ± 0.0395 | — | — | 0.0166 ± 0.0095 | 16080 | 5.8 | 1.00 | 1.00 | 6.9 | 19.7 |
| R201-50 | baseline_eqtime | 3500 | 1.1490 ± 0.0575 | +0.4721 | <0.001 | — | 0.0387 ± 0.0218 | <0.001 | — | 0.0056 ± 0.0040 | 280080 | 201.7 | 1.00 | 1.00 | 4.5 | 80.0 |
| R201-50 | dp | 200 | 0.6825 ± 0.0689 | +0.0056 | 0.406 | <0.001 | 0.3118 ± 0.0573 | 0.450 | <0.001 | 0.0254 ± 0.0106 | 16080 | 91.2 | 1.00 | 1.00 | 6.6 | 34.0 |
| R201-50 | adapt | 200 | 0.5856 ± 0.0394 | -0.0914 | 0.001 | <0.001 | 0.3612 ± 0.0411 | 0.002 | <0.001 | 0.0185 ± 0.0127 | 16080 | 6.0 | 1.00 | 1.00 | 7.7 | 21.6 |
| R201-50 | both | 200 | 0.6656 ± 0.0954 | -0.0113 | 0.705 | <0.001 | 0.3286 ± 0.0785 | 0.226 | <0.001 | 0.0365 ± 0.0219 | 16080 | 92.4 | 1.00 | 1.00 | 6.5 | 32.4 |

Mỗi ô: trung bình ± độ lệch chuẩn qua [10] run (cùng bộ seed cho mọi cấu hình). p-value: Wilcoxon rank-sum hai phía so với baseline cùng instance; chưa hiệu chỉnh đa so sánh.

Lưu ý khi so với bản trước của tài liệu này: bảng nay có thêm `baseline_eqtime` trong reference set, nên **mọi con số HV và IGD đã đổi** (ví dụ HV baseline R201-50 từ 0.884 xuống 0.677) dù các lượt chạy 200 thế hệ không đổi; p-value của HV không đổi vì chỉ phụ thuộc thứ hạng. Chỉ so HV/IGD trong cùng bảng.

## Nhận xét

Ở ngân sách 200 thế hệ, chỉ `adapt` trên R201-50 đạt p < 0.05 trong 12 phép so với baseline (6 HV, 6 IGD) và là theo hướng kém hơn (HV 0.586 so với 0.677, p = 0.001; IGD p = 0.002); các phép so còn lại không phân biệt được với baseline, trong đó `both` trên C102-25 là gần nhất (ΔHV +0.147, p = 0.059), và chưa hiệu chỉnh đa so sánh. `dp` và `both` cho front nhiều điểm hơn (19.0 và 18.0 so với 9.7 điểm trên C102-25; 34.0 và 32.4 so với 19.7 trên R201-50) nhưng SP cao hơn, tức phân bố điểm kém đều hơn. Số xe trung bình trên front gần như không đổi, và mọi cấu hình đều có 100% nghiệm khả thi ở hai kích thước này. Khi cho baseline thêm thế hệ (mục "Equal-time comparison") nó vượt `dp` rõ rệt với chi phí CPU tương đương hoặc thấp hơn, nên ở hai instance này và tham số mặc định chưa có bằng chứng `dp_split` đáng giá hơn việc chạy baseline lâu hơn. Đây là một lượt chạy với tham số chưa tuning trên hai instance, chưa đủ để kết luận cho kích thước lớn hơn hay cho tham số đã tuning.

## Diagnosis: adaptive rates

Dữ liệu: `rate_log` của `adapt` và `both`, hình `docs/tv4_adaptive_rates.png` (front1_fraction, pc, pm trung bình theo thế hệ, trung bình 10 seed; đường chấm là pc/pm cố định của baseline, đường đứt là ngưỡng một-front 0.9).

![adaptive rates](tv4_adaptive_rates.png)

| Instance | Cấu hình | front1_fraction TB | Thế hệ ở nhánh một-front | pc hiệu dụng | pm hiệu dụng | pc / pm ở thế hệ theo hạng | pc / pm ở thế hệ một-front |
|---|---|---|---|---|---|---|---|
| C102-25 | baseline | 0.094 | 0.0% (chỉ để tham khảo, không dùng) | 0.700 (cố định) | 0.100 (cố định) | — | — |
| C102-25 | dp | 0.194 | 0.0% (chỉ để tham khảo, không dùng) | 0.700 (cố định) | 0.100 (cố định) | — | — |
| C102-25 | adapt | 0.089 | 0.0% | 0.672 | 0.110 | 0.672 / 0.110 | — / — |
| C102-25 | both | 0.178 | 0.0% | 0.656 | 0.097 | 0.656 / 0.097 | — / — |
| R201-50 | baseline | 0.211 | 0.0% (chỉ để tham khảo, không dùng) | 0.700 (cố định) | 0.100 (cố định) | — | — |
| R201-50 | dp | 0.378 | 0.0% (chỉ để tham khảo, không dùng) | 0.700 (cố định) | 0.100 (cố định) | — | — |
| R201-50 | adapt | 0.207 | 0.0% | 0.655 | 0.096 | 0.655 / 0.096 | — / — |
| R201-50 | both | 0.367 | 0.0% | 0.632 | 0.077 | 0.632 / 0.077 | — / — |

"pc / pm hiệu dụng" là trung bình trên mọi cặp ghép và mọi thế hệ của 10 seed. Baseline cố định pc 0.7, pm 0.1.

**Chẩn đoán.** (1) Nhánh dự phòng "một front" không bao giờ chạy: front1_fraction chỉ lên tới khoảng 0.28 (cấu hình không có `dp`) và 0.5 (có `dp`) sau 200 thế hệ, xa ngưỡng 0.9, nên 0% thế hệ rơi vào nhánh đó và vấn đề "thoái hoá về pc_min/pm_min" mà nhánh đó phòng ngừa không phải là thứ đang xảy ra ở đây. (2) Vì chọn lọc giải đấu ưu tiên cha mẹ hạng thấp, r/R trung bình chỉ khoảng 0.18, nên pc và pm nằm sát cận dưới: `adapt` trên R201-50 có pc hiệu dụng 0.655 (so với 0.7) và pm 0.096 (so với 0.1); `both` còn thấp hơn (pc 0.632, pm 0.077, tức pm giảm khoảng 23% so với baseline). Khoảng giá trị không đặt tâm ở baseline: pc 0.7 nằm ở một phần ba khoảng từ cận dưới, pm 0.1 ở một phần năm. (3) Về mặt trung bình, mức chênh so với baseline là nhỏ (pc −6%, pm −4% với `adapt` ở R201-50), và tỉ lệ con trùng hoàn vị đã có trong quần thể chỉ tăng từ 31% lên 35% (đo ngoài bằng bọc `make_offspring`, 5 seed, không sửa code thuật toán). **Những thay đổi nhỏ đó không tự giải thích rõ ràng mức giảm HV trên R201-50 (ΔHV −0.09, p = 0.001); nguyên nhân chưa được xác lập.** Giả thuyết còn mở: R201-50 nhạy với việc bớt thăm dò, hoặc chính sự khác biệt giữa các cặp ghép gây hại. Chưa kiểm cái nào.

**Ba thay đổi tham số nên thử khi tuning (chưa áp dụng; dùng seed tuning 100–104, không dùng seed 0–9):**
1. **Đặt tâm khoảng vào baseline và chỉ mở rộng lên trên:** `pc_min = 0.7`, `pc_max = 0.9`; `pm_min = 0.1`, `pm_max = 0.3` (case29: `pm_min = 0.2`), để cha mẹ hạng tốt nhận đúng tỉ lệ baseline còn cha mẹ hạng kém được thăm dò nhiều hơn; pc/pm hiệu dụng khi đó không thể thấp hơn baseline.
2. **Bật riêng cơ chế tăng pm khi tri trệ:** `stagnation_gens` khoảng 10–20, `boost` 1.5–2.0, giữ pc/pm ở mức baseline (`pc_min = pc_max = 0.7`, `pm_min = pm_max = 0.1`) để tách tác dụng của nó khỏi phần theo hạng.
3. **Ngưỡng một-front:** giữ 0.9 cho cấu hình không `dp`, vì không bao giờ chạm tới; chỉ hạ xuống (ví dụ 0.5) nếu muốn nhánh đó có tác dụng cùng `dp`, nơi front1_fraction lên tới 0.45–0.5. Ngoài ra có thể xét đổi cách chuẩn hoá hạng (dùng phần trăm quần thể ở các front tốt hơn thay cho r/R) để tỉ lệ trải đều trên cả khoảng; việc đó cần sửa code `adaptive_rates`, không chỉ tham số.

## Per-objective extremes and coverage

Cực trị trên front cuối, trung bình ± độ lệch chuẩn qua 10 seed (f1, f2: nhỏ hơn là tốt; f3: lớn hơn là tốt), kiểu Bảng 6–7 của bài báo. `f? TB front` là trung bình của cả front trong từng run.

| Instance | Cấu hình | f1 tốt nhất | f2 tốt nhất | f3 tốt nhất | f1 TB front | f2 TB front | f3 TB front |
|---|---|---|---|---|---|---|---|
| C102-25 | baseline | 1349.1 ± 104.7 | 167.3 ± 21.7 | 0.9584 ± 0.0240 | 1438.9 ± 126.0 | 186.9 ± 23.9 | 0.9137 ± 0.0288 |
| C102-25 | baseline_eqtime | 1226.2 ± 44.0 | 137.6 ± 10.4 | 0.9868 ± 0.0140 | 1312.2 ± 84.1 | 161.7 ± 19.1 | 0.9319 ± 0.0173 |
| C102-25 | dp | 1400.0 ± 195.2 | 139.7 ± 16.5 | 0.9465 ± 0.0283 | 2319.3 ± 530.9 | 174.5 ± 22.6 | 0.8173 ± 0.0427 |
| C102-25 | adapt | 1368.4 ± 106.0 | 170.9 ± 25.6 | 0.9435 ± 0.0209 | 1451.6 ± 124.8 | 188.5 ± 21.8 | 0.9035 ± 0.0362 |
| C102-25 | both | 1336.8 ± 202.8 | 139.7 ± 18.4 | 0.9520 ± 0.0361 | 2064.1 ± 656.0 | 169.6 ± 21.1 | 0.8470 ± 0.0707 |
| R201-50 | baseline | 5767.6 ± 255.9 | 786.6 ± 28.0 | 0.7928 ± 0.0293 | 6179.9 ± 293.6 | 882.9 ± 43.6 | 0.6981 ± 0.0390 |
| R201-50 | baseline_eqtime | 4460.2 ± 179.9 | 615.1 ± 31.5 | 0.9327 ± 0.0169 | 4864.3 ± 174.6 | 722.1 ± 32.8 | 0.8253 ± 0.0268 |
| R201-50 | dp | 6117.0 ± 379.6 | 695.6 ± 35.6 | 0.7372 ± 0.0308 | 7054.7 ± 588.4 | 806.7 ± 34.7 | 0.5903 ± 0.0458 |
| R201-50 | adapt | 6123.6 ± 188.2 | 831.4 ± 19.3 | 0.7699 ± 0.0370 | 6557.0 ± 226.7 | 927.5 ± 34.8 | 0.6808 ± 0.0403 |
| R201-50 | both | 6025.2 ± 513.1 | 696.3 ± 53.6 | 0.7262 ± 0.0301 | 7386.6 ± 657.6 | 820.6 ± 74.2 | 0.5838 ± 0.0377 |

Set coverage cùng seed, `SC(A, B)` là tỉ lệ điểm front của B bị ít nhất một điểm của A trội (hàm `sc` của `metrics.py`); cột cuối đếm số seed (trên 10) mà SC(A, B) lớn hơn / nhỏ hơn / bằng SC(B, A).

| Instance | Cặp (A vs B) | SC(A, B): phần B bị A trội | SC(B, A): phần A bị B trội | Số seed A phủ nhiều hơn / ít hơn / bằng |
|---|---|---|---|---|
| C102-25 | dp vs baseline | 0.281 ± 0.353 | 0.435 ± 0.419 | 4 / 6 / 0 |
| C102-25 | adapt vs baseline | 0.265 ± 0.341 | 0.353 ± 0.291 | 3 / 7 / 0 |
| C102-25 | both vs baseline | 0.519 ± 0.430 | 0.311 ± 0.413 | 7 / 3 / 0 |
| C102-25 | baseline_eqtime vs baseline | 1.000 ± 0.000 | 0.000 ± 0.000 | 10 / 0 / 0 |
| C102-25 | dp vs baseline_eqtime | 0.115 ± 0.272 | 0.726 ± 0.362 | 2 / 8 / 0 |
| R201-50 | dp vs baseline | 0.237 ± 0.309 | 0.358 ± 0.281 | 5 / 5 / 0 |
| R201-50 | adapt vs baseline | 0.109 ± 0.192 | 0.671 ± 0.410 | 2 / 8 / 0 |
| R201-50 | both vs baseline | 0.181 ± 0.293 | 0.434 ± 0.347 | 3 / 7 / 0 |
| R201-50 | baseline_eqtime vs baseline | 1.000 ± 0.000 | 0.000 ± 0.000 | 10 / 0 / 0 |
| R201-50 | dp vs baseline_eqtime | 0.000 ± 0.000 | 0.997 ± 0.011 | 0 / 10 / 0 |

**Nhận xét.** `dp` chỉ có lợi ở một đầu: f2 tốt nhất thấp hơn baseline (139.7 so với 167.3 ở C102-25; 695.6 so với 786.6 ở R201-50, khoảng −16% và −12%), còn f1 tốt nhất không tốt hơn (ngang ở C102-25, kém hơn ở R201-50) và f3 tốt nhất thấp hơn; trung bình f1 và f3 của cả front cũng kém hơn (f1 TB 2319 so với 1439 ở C102-25), nên front rộng hơn nhưng dịch về phía f1 cao và hài lòng thấp. Về coverage, `dp` so với baseline không nghiêng rõ về bên nào (C102-25: dp phủ 28% điểm baseline, baseline phủ 43%, 4 seed dp hơn / 6 kém; R201-50: 24% so với 36%, 5/5); `both` phủ baseline nhiều hơn ở C102-25 (52% so với 31%, 7 seed trên 10) nhưng không lặp lại ở R201-50 (18% so với 43%). Với 10 seed và độ lệch chuẩn lớn (ví dụ SC 0.281 ± 0.353), những khác biệt coverage giữa `dp`/`both` và baseline không đủ để kết luận.

## Equal-time comparison

`baseline_eqtime` là baseline với n_gen = 1400 (C102-25) và 3500 (R201-50), seed 0–9, cùng reference set với các cấu hình khác (n_evals 112080 và 280080 so với 16080).

**Cách chọn n_gen và giới hạn của nó.** Đo CPU time (`process_time`) trên seed 0 trong cùng một phiên, một thế hệ `dp` tốn gấp 8.7 lần (C102-25) và 18 lần (R201-50) một thế hệ baseline, ứng với khoảng 1740 và 3600 thế hệ baseline cho cùng chi phí CPU với 200 thế hệ `dp`; ngoài ra các lượt đo thời gian tường (wall) rải rác hơn: 5.8–9 (C102-25) và 15.7–24 (R201-50), tuỳ lúc đo. Tôi chọn 1400 và 3500 (khoảng 0.80 và 0.97 chi phí CPU của `dp`). **Cột "Thời gian/run" của `baseline_eqtime` (56.4 s và 201.7 s) lớn hơn khoảng 2.2 lần của `dp` (25.1 s và 91.2 s), nhưng hai lượt chạy diễn ra ở hai thời điểm máy tải khác nhau (khi chạy `baseline_eqtime` máy có tải nền từ ứng dụng khác, đo được CPU tổng khoảng 45%, và baseline mất khoảng 40 ms mỗi thế hệ so với khoảng 19 ms ở lượt `tv4_main`), nên không so được thời gian tường giữa chúng.** Vì vậy sự khớp thời gian chỉ là xấp xỉ (sai số cỡ ±20–30% theo phép đo CPU), và để kết quả không phụ thuộc vào xấp xỉ đó, bảng dưới cắt baseline ở các ngân sách nhỏ hơn (`history[g]` của cùng run chính là một run n_gen = g với cùng seed).

| Instance | Baseline cắt ở n_gen | Chi phí CPU so với dp | HV | p (HV) so với dp |
|---|---|---|---|---|
| C102-25 | 200 | 0.11 | 0.9034 ± 0.1763 | 0.174 |
| C102-25 | 350 | 0.20 | 0.9868 ± 0.1591 | 0.880 |
| C102-25 | 700 | 0.40 | 1.0825 ± 0.1362 | 0.257 |
| C102-25 | 1400 | 0.80 | 1.1609 ± 0.0781 | 0.016 |
| C102-25 | dp (200 thế hệ) | 1.00 | 0.9998 ± 0.1528 | — |

| Instance | Baseline cắt ở n_gen | Chi phí CPU so với dp | HV | p (HV) so với dp |
|---|---|---|---|---|
| R201-50 | 200 | 0.06 | 0.6769 ± 0.0573 | 0.406 |
| R201-50 | 875 | 0.24 | 0.9973 ± 0.0645 | <0.001 |
| R201-50 | 1750 | 0.49 | 1.0854 ± 0.0552 | <0.001 |
| R201-50 | 3500 | 0.97 | 1.1490 ± 0.0575 | <0.001 |
| R201-50 | dp (200 thế hệ) | 1.00 | 0.6825 ± 0.0689 | — |

Chi phí CPU: hệ số một thế hệ dp / một thế hệ baseline đo cùng lúc, cùng máy (C102-25: 8.7x, R201-50: 18.0x); 1.00 = bằng chi phí dp.

**Nhận xét.** Trên R201-50, baseline cắt ở 875 thế hệ (khoảng 0.24 chi phí CPU của `dp`) đã có HV 0.997 so với 0.683 của `dp` (p < 0.001), và ở 0.97 chi phí thì `baseline_eqtime` phủ 99.7% điểm front của `dp` trong khi `dp` không phủ điểm nào. Trên C102-25 ở 0.40 chi phí baseline chưa phân biệt được với `dp` (p = 0.257), còn ở 0.80 chi phí baseline cao hơn (HV 1.161 so với 1.000, p = 0.016; baseline phủ 72.6% điểm `dp`, `dp` phủ 11.5%). Nghĩa là, tính theo chi phí CPU, ở hai instance này và tham số mặc định chưa tuning, `dp_split` không cho kết quả tốt hơn việc chạy baseline thêm thế hệ; nó chỉ cho thấy lợi thế khi so theo số thế hệ. Kết luận này chưa áp dụng cho n = 100 (nơi ràng buộc đội xe chạm nhiều và baseline vượt đội xe, chưa chạy) hay cho tham số đã tuning.

**Ghi chú kỹ thuật.** `python -m src.runner analyze` báo lỗi khi các cấu hình trong cùng thí nghiệm có n_gen khác nhau, vì bảng hội tụ dựng từ các mảng độ dài khác nhau (`ValueError: All arrays must be of the same length`). `scripts/tv4_report.py` không gọi `analyze` mà dùng cùng các hàm của runner (`load_runs`, `reference_set`, `normalization_bounds`, `evaluate_front`) trừ bước hội tụ, và ghi đè `per_run.csv` của từng instance; tôi đã kiểm rằng khi bỏ `baseline_eqtime` nó tái tạo đúng từng số của bảng bốn cấu hình trước đó. Nên báo TV1.

## Ghi chú

- Thời gian chạy đo khi 8 tiến trình chạy song song, chỉ so được với nhau trong bảng này. Chi phí tham chiếu của dp_split khi chạy tuần tự (lượt chạy thử, 20 thế hệ): ~9x ở n=25, ~24x ở n=50, ~28x ở n=100 so với baseline.
- HV và IGD chỉ so được giữa các cấu hình trong CÙNG bảng: `analyze` gộp front của mọi cấu hình trên một instance thành một reference set và một cận chuẩn hoá. Thêm hoặc bớt một cấu hình thì reference set đổi, mọi con số HV/IGD đổi theo.
- "Khả thi" là tỉ lệ nghiệm không vượt đội xe (CV = 0); "Số xe TB" chấm lại từng cá thể trên front cuối bằng đúng evaluator của cấu hình đó (script kiểm F chấm lại trùng F đã lưu).
- Dữ liệu thô nằm ở `results/tv4_main/` (không đưa lên git).
