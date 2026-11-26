# Phần của TV4: tách tuyến tối ưu (DP split), polish và tỉ lệ lai/đột biến thích nghi

> Bản nháp cho báo cáo nhóm. Mọi con số lấy từ `docs/tv4_results.md`; những chỗ là suy luận chưa được kiểm bằng thực nghiệm (cơ chế khiến polish hiệu quả) đều ghi rõ.

## 1. Phương pháp

### 1.1. Tách tuyến Prins bằng quy hoạch động

Cho một hoán vị khách hàng, bước giải mã cần cắt hoán vị thành các tuyến liên tiếp. Bộ giải mã gốc (`split_greedy`, `split_capacity_time`) cắt theo quy tắc tham lam. Chúng tôi thay bằng cách tách tối ưu của Prins: dựng đồ thị có hướng trên các vị trí cắt 0, 1, ..., n; cung (i, j) với i < j biểu diễn một tuyến phục vụ các khách ở vị trí i+1 đến j, và chỉ tồn tại nếu tuyến đó thoả ràng buộc tải trọng (và ràng buộc thời gian khi `split_rule = capacity_time`). Một cách tách tương ứng một đường đi từ đỉnh 0 đến đỉnh n, nên cách tách tối ưu là đường đi ngắn nhất, tính bằng quy hoạch động trên đồ thị không chu trình theo thứ tự vị trí. Chi phí của mọi cung được tính tăng dần theo từng khách thêm vào tuyến (O(1) mỗi lần thêm) và tuân theo `satisfaction_time` (`arrival` hoặc `service_start`) của bộ giải mã gốc.

### 1.2. Vì sao tổng có trọng số vẫn chính xác

Bài toán có ba mục tiêu (f1, f2 và hài lòng f3). Chúng tôi dùng tổng có trọng số của (f1, f2, 1 − f3) làm chi phí vô hướng cho DP. Điều này chính xác vì hai tính chất: (i) mỗi mục tiêu viết được dưới dạng tổng các số hạng theo tuyến (f1_r, f2_r, g3_r, với g3 = 1 − f3), và (ii) các tuyến độc lập với nhau (chi phí của một tuyến chỉ phụ thuộc các khách trong tuyến đó). Do đó chi phí vô hướng `w · (số hạng / thang đo)` cộng được theo cung, và đường đi ngắn nhất cho đúng nghiệm tối ưu của tổng có trọng số trên mọi cách tách của hoán vị đó. Thang đo của f1, f2 là trung bình qua ba hoán vị tất định (thứ tự ID, láng giềng gần nhất, thứ tự theo thời điểm sớm nhất) được giải bằng `decoder.split()`, còn g3 dùng hệ số cố định `g3_scale = 1.0`. Cần lưu ý giới hạn: tổng có trọng số chỉ tìm được các nghiệm tối ưu theo một vector trọng số, nên không bảo đảm phủ các điểm Pareto nằm trong phần lõm của front.

### 1.3. Giới hạn đội xe: DP nhiều lớp

Khi `fleet_size` cố định, đồ thị được nhân thành các lớp theo số tuyến đã dùng (trạng thái là cặp: vị trí cắt, số tuyến), và chỉ cho phép đường đi dùng không quá `fleet_size` tuyến. Nếu không có cách tách khả thi trong giới hạn đó, hàm quay về `split_greedy` và phát cảnh báo một lần.

### 1.4. Trọng số riêng cho từng cá thể

Mỗi cá thể mang một vector trọng số (lưu trong mảng song song W, kích thước N × 3), bốc từ phân phối Dirichlet (hoặc one-hot). Con được sinh ra nhận trọng số mới (`weight_inherit: fresh`) hoặc thừa hưởng từ cha mẹ (`parent`). Nhờ đó quần thể được chấm theo nhiều hướng khác nhau trên mặt Pareto thay vì một hướng. Khi cờ tắt, mã của chúng tôi không gọi RNG nào và kết quả giống từng bit với nhánh `main` (có test so với fixture sinh từ merge-base).

### 1.5. Chế độ polish

Chế độ `mode: polish` giữ nguyên toàn bộ tiến hoá với split baseline (nên quần thể cuối giống hệt baseline cùng seed, có test). Sau thế hệ cuối, mỗi hoán vị trong quần thể được chấm lại bằng DP với K vector trọng số cố định, lấy từ lưới simplex tất định (chọn điểm xa nhất bắt đầu từ các đỉnh, không dùng RNG); mặc định K = 10. Các điểm mới được gộp với quần thể cuối, bỏ điểm trùng vector mục tiêu, và lấy tập không trội làm front. Chi phí thêm là n_pop × K lời gọi DP, được tính vào `n_evals`.

### 1.6. Tỉ lệ lai/đột biến thích nghi

Với mỗi cặp cha mẹ, pc và pm là hàm tuyến tính của r/R, trong đó r là hạng không trội nhỏ nhất của hai cha mẹ và R là hạng lớn nhất (mặc định pc ∈ [0.6, 0.9], pm ∈ [0.05, 0.3]). Hai cơ chế bổ sung: (a) nhánh dự phòng, nếu tỉ lệ cá thể ở front 1 (`front1_fraction`) đạt ngưỡng 0.9 thì dùng lại pc/pm của baseline, để tránh thoái hoá về cận dưới khi cả quần thể là một front; (b) tăng pm khi trì trệ: nếu tập vector mục tiêu của front 1 không đổi trong k thế hệ liên tiếp thì nhân pm với hệ số `boost`, bị chặn bởi `boost_pm_cap`. Cơ chế này tắt theo mặc định (`stagnation_gens = 0`).

## 2. Thiết lập thí nghiệm

- **Instance:** C102-25 và R201-50. RC201-100 chưa chạy (xem mục 5).
- **Cấu hình chung:** n_pop = 80, pc = 0.7, pm = 0.1, `satisfaction_time: arrival`, `split_rule: capacity_time`, tham số cải tiến mặc định chưa tuning.
- **Kết quả báo cáo:** seed 0–9, n_gen = 200 (riêng `baseline_eqtime` là 1400 cho C102-25 và 3500 cho R201-50). **Tuning:** chỉ seed 100–104, n_gen = 200, không dùng lại seed 0–9.
- **Quy ước reference set:** HV và IGD tính trên front gộp của mọi cấu hình trong cùng bảng và cùng instance, cùng một cận chuẩn hoá. Thêm hoặc bớt cấu hình thì reference set đổi và mọi giá trị HV/IGD đổi theo, nên **chỉ so HV/IGD trong cùng một bảng**. Các bảng ở mục 3 dùng ba reference set khác nhau (3a và 3b: 5 cấu hình; 3c: 7 cấu hình; tuning: 12 cấu hình), vì vậy không so được giữa các bảng.
- **Kiểm định:** Wilcoxon rank-sum hai phía khi so các cấu hình độc lập (so với baseline, hoặc với baseline_eqtime); Wilcoxon signed-rank hai phía khi so cặp theo seed (bản đã polish với bản chưa polish; polish với thế hệ thêm). Không hiệu chỉnh đa so sánh. Với 10 seed, p nhỏ nhất của phép so cặp là khoảng 0.002; với 5 seed mỗi bên (rank-sum) là khoảng 0.008.
- **Đo chi phí:** dùng thời gian CPU (`time.process_time`) chạy tuần tự, không dùng thời gian tường, vì máy có tải nền khi chạy `baseline_eqtime` (khoảng 45% CPU từ ứng dụng khác), làm một thế hệ baseline tốn khoảng 40 ms thay vì khoảng 19 ms ở lượt `tv4_main`; vì vậy không so được thời gian tường giữa hai lượt chạy. Hệ số chi phí dp/baseline đo trên seed 0, nên sai số cỡ ±20–30%.

## 3. Kết quả

### 3a. Theo số thế hệ (200 thế hệ, seed 0–9, so với baseline)

| Instance | Cấu hình | HV | ΔHV | p (HV) | IGD | p (IGD) | Số điểm front |
|---|---|---|---|---|---|---|---|
| C102-25 | baseline | 0.9034 ± 0.1763 | — | — | 0.2455 ± 0.1070 | — | 9.7 |
| C102-25 | dp | 0.9998 ± 0.1528 | +0.096 | 0.174 | 0.1980 ± 0.1001 | 0.364 | 19.0 |
| C102-25 | adapt | 0.8641 ± 0.2028 | −0.039 | 0.496 | 0.2651 ± 0.1331 | 0.545 | 7.9 |
| C102-25 | both | 1.0505 ± 0.1784 | +0.147 | 0.059 | 0.1692 ± 0.1179 | 0.082 | 18.0 |
| R201-50 | baseline | 0.6769 ± 0.0573 | — | — | 0.2898 ± 0.0395 | — | 19.7 |
| R201-50 | dp | 0.6825 ± 0.0689 | +0.006 | 0.406 | 0.3118 ± 0.0573 | 0.450 | 34.0 |
| R201-50 | adapt | 0.5856 ± 0.0394 | −0.091 | 0.001 | 0.3612 ± 0.0411 | 0.002 | 21.6 |
| R201-50 | both | 0.6656 ± 0.0954 | −0.011 | 0.705 | 0.3286 ± 0.0785 | 0.226 | 32.4 |

Trong 12 phép so với baseline (6 HV, 6 IGD) chỉ `adapt` trên R201-50 đạt p < 0.05 và theo hướng kém hơn. `dp` và `both` cho front nhiều điểm hơn gần gấp đôi nhưng SP cao hơn (C102-25: 0.090 và 0.066 so với 0.045; R201-50: 0.025 và 0.037 so với 0.017), tức điểm phân bố kém đều. Về cực trị trên front, lợi thế của `dp` chỉ nằm ở một đầu: f2 tốt nhất thấp hơn khoảng 16% (C102-25: 139.7 so với 167.3) và 12% (R201-50: 695.6 so với 786.6), trong khi f1 tốt nhất không tốt hơn và f3 tốt nhất thấp hơn (C102-25: 0.947 so với 0.958; R201-50: 0.737 so với 0.793). Mọi cấu hình đều có 100% nghiệm khả thi ở hai kích thước này.

### 3b. Theo chi phí CPU (baseline cắt ở n_gen khác nhau so với `dp` 200 thế hệ)

Một thế hệ `dp` tốn gấp 8.7 lần (C102-25) và 18 lần (R201-50) một thế hệ baseline. `history[g]` của một run chính là run n_gen = g cùng seed, nên baseline được cắt ở nhiều ngân sách từ cùng các lượt chạy.

| Instance | Baseline n_gen | Chi phí CPU so với dp | HV | p (HV) so với dp |
|---|---|---|---|---|
| C102-25 | 200 | 0.11 | 0.9034 ± 0.1763 | 0.174 |
| C102-25 | 700 | 0.40 | 1.0825 ± 0.1362 | 0.257 |
| C102-25 | 1400 | 0.80 | 1.1609 ± 0.0781 | 0.016 |
| C102-25 | dp (200) | 1.00 | 0.9998 ± 0.1528 | — |
| R201-50 | 200 | 0.06 | 0.6769 ± 0.0573 | 0.406 |
| R201-50 | 875 | 0.24 | 0.9973 ± 0.0645 | < 0.001 |
| R201-50 | 3500 | 0.97 | 1.1490 ± 0.0575 | < 0.001 |
| R201-50 | dp (200) | 1.00 | 0.6825 ± 0.0689 | — |

Ở R201-50, baseline chỉ cần khoảng 0.24 chi phí của `dp` để vượt `dp` rõ rệt (p < 0.001), và ở 0.97 chi phí `baseline_eqtime` phủ 99.7% điểm front của `dp` trong khi `dp` không phủ điểm nào. Ở C102-25, baseline ngang `dp` ở 0.40 chi phí (p = 0.257) và cao hơn ở 0.80 (p = 0.016).

### 3c. Polish ở ngân sách ngắn và ngân sách đã hội tụ

Tuning (seed 100–104, 200 thế hệ, 5 seed, chi phí CPU tuần tự so với baseline): `every_eval` tốn 8.9 lần (C102-25) và 19.7 lần (R201-50), `polish` K = 10 tốn 1.3 lần và 1.8 lần, và giữ 50–63% mức tăng HV của `every_eval` (+0.065 so với +0.127 ở C102-25; +0.079 so với +0.127 ở R201-50). K = 30 chỉ hơn K = 10 khoảng 0.001–0.005 HV nhưng tốn gấp 1.6–2.2 lần so với K = 10. Không cấu hình nào trong ba đạt p < 0.05 về HV với 5 seed.

Sau đó polish được áp dụng ngoại tuyến lên các quần thể cuối đã lưu của seed 0–9 (kết quả ngoại tuyến đã được kiểm khớp từng bit với polish chạy trực tiếp trên 20 lượt chạy tuning). Bảng dưới: ΔHV, ΔIGD là hiệu cặp theo seed so với bản chưa polish, tất cả p (signed-rank) = 0.002.

| Instance | Ngân sách (thế hệ) | HV chưa polish → polish | ΔHV | IGD chưa polish → polish | ΔIGD | Số điểm front | CPU polish (s/run) |
|---|---|---|---|---|---|---|---|
| C102-25 | 200 | 0.8469 → 0.9207 | +0.0738 ± 0.0463 | 0.3140 → 0.2272 | −0.0868 ± 0.0225 | 9.7 → 18.9 | 2.2 |
| C102-25 | 1400 | 1.0863 → 1.1379 | +0.0516 ± 0.0328 | 0.2058 → 0.1092 | −0.0966 ± 0.0281 | 34.4 → 38.3 | 2.4 |
| R201-50 | 200 | 0.7028 → 0.7476 | +0.0448 ± 0.0213 | 0.2739 → 0.2598 | −0.0141 ± 0.0043 | 19.7 → 38.4 | 8.4 |
| R201-50 | 3500 | 1.1268 → 1.1451 | +0.0183 ± 0.0099 | 0.0545 → 0.0408 | −0.0137 ± 0.0046 | 80.0 → 87.4 | 8.7 |

Khi ngân sách dài ra, ΔHV co lại (khoảng −30% ở C102-25, −59% ở R201-50) còn ΔIGD tuyệt đối giữ hoặc tăng nhẹ; tính theo tỉ lệ IGD, mức cải thiện tăng (C102-25: 28% lên 47%; R201-50: 5% lên 25%). Chi phí polish gần như không đổi theo ngân sách (khoảng 6% CPU của run dài).

So với việc dùng đúng lượng CPU đó cho thêm thế hệ baseline (so cặp theo seed, signed-rank):

| Instance | Ngân sách | ΔHV của polish | ΔHV nếu dùng cùng CPU cho thế hệ | p |
|---|---|---|---|---|
| C102-25 | 200 | +0.0738 | +0.0528 (thêm 82 thế hệ) | 0.432 |
| C102-25 | 1400 | +0.0516 | +0.0007 (ước lượng) | 0.002 |
| R201-50 | 200 | +0.0448 | +0.1490 (thêm 205 thế hệ) | 0.002 |
| R201-50 | 3500 | +0.0183 | +0.0073 (ước lượng) | 0.049 |

### 3d. Tỉ lệ thích nghi

Mặc định (pc ∈ [0.6, 0.9], pm ∈ [0.05, 0.3]) gây suy giảm trên R201-50 (bảng 3a). Chẩn đoán trên `rate_log` cho thấy nhánh dự phòng một-front không bao giờ chạy (front1_fraction chỉ tới khoảng 0.28 khi không có `dp` và 0.5 khi có `dp`, xa ngưỡng 0.9), và vì chọn lọc ưu tiên cha mẹ hạng thấp nên r/R trung bình chỉ khoảng 0.18, nghĩa là pc và pm hiệu dụng nằm sát cận dưới (R201-50, `adapt`: pc 0.655, pm 0.096 so với 0.7 và 0.1 của baseline; `both`: pm 0.077). Mức chênh nhỏ này không tự giải thích được mức giảm HV; nguyên nhân chưa được xác lập.

Tuning (5 seed, 200 thế hệ):

| Cấu hình | ΔHV C102-25 (p) | ΔHV R201-50 (p) |
|---|---|---|
| `adapt_v1` (pc 0.7–0.9, pm 0.1–0.3) | +0.012 (0.754) | −0.005 (0.602) |
| `adapt_v2_*` (pc/pm cố định + tăng pm khi trì trệ) | −0.002 đến +0.006 (trong 4 cấu hình có 2 cấu hình trùng hệt baseline) | 0.000 (4/4 trùng hệt baseline) |
| `adapt_v3_g10_b2.0` (v1 + v2 tốt nhất) | +0.013 (0.754) | −0.005 (0.602) |

Cơ chế tăng pm khi trì trệ gần như không kích hoạt: ở `stagnation_gens = 10` chỉ 0–15 trên 200 thế hệ mỗi run ở C102-25 và 0 ở R201-50; ở 20 là 0 ở cả hai. Lý do là front 1 gần như đổi sau mỗi thế hệ nên điều kiện "không đổi k thế hệ" hầu như không xảy ra. Do đó v2 gần như trùng baseline và v3 trùng v1.

## 4. Thảo luận

**Vì sao `dp` ở chế độ chấm mọi cá thể không đáng chi phí.** Hai quan sát từ dữ liệu. Thứ nhất, tính theo số thế hệ, `dp` không cải thiện HV có ý nghĩa thống kê (p = 0.174 ở C102-25, p = 0.406 ở R201-50); điều nó thay đổi rõ là hình dạng front (nhiều điểm hơn, f2 tốt nhất thấp hơn 12–16%) với cái giá là SP cao hơn, f1 và f3 trung bình xấu hơn. Thứ hai, tính theo chi phí CPU, mỗi thế hệ `dp` tốn 8.7–18 lần một thế hệ baseline và baseline đạt HV cao hơn sau khoảng 0.24–0.8 chi phí đó. Quan sát đầu được giải thích một phần bằng số đo trực tiếp (không chạy tiến hoá, tách lại cùng các hoán vị bằng ba quy tắc, `scripts/tv4_split_lateness.py`): quy tắc `capacity_time` của baseline đã loại gần hết trễ, nên tách tối ưu còn rất ít để cải thiện ở quần thể đã tiến hoá.

| Quần thể cuối baseline (800 hoán vị, seed 0–9) | Quy tắc | late_min | F4 | f1 | f3 | Số xe |
|---|---|---|---|---|---|---|
| C102-25 | `capacity` | 12900 | 13080 | 14430 | 0.429 | 2.0 |
| | `capacity_time` | 8.5 | 128 | 1493 | 0.898 | 3.15 |
| | `dp` | 12.9 | 111 | 1469 | 0.906 | 3.12 |
| R201-50 | `capacity` | 27090 | 27380 | 33100 | 0.164 | 2.0 |
| | `capacity_time` | 32.4 | 850 | 6291 | 0.691 | 7.27 |
| | `dp` | 84.0 | 857 | 6263 | 0.692 | 6.97 |

So với `capacity`, `capacity_time` giảm số phút trễ từ hàng chục nghìn xuống còn 8–32 phút; `dp` chỉ hơn `capacity_time` khoảng 1.6% (C102-25) và 0.4% (R201-50) về f1, f3 gần như không đổi, F4 ngang nhau, và còn trễ nhiều hơn (12.9 so với 8.5 phút; 84 so với 32). Điều này khớp với việc `dp` không cải thiện HV có ý nghĩa. Hai giới hạn: trên hoán vị ngẫu nhiên (chưa tiến hoá) `dp` hơn rõ về f1 (C102-25: 4332 so với 4809, khoảng 10%; R201-50: 11660 so với 12460, khoảng 6%), tức khoảng trống chỉ hẹp khi hoán vị đã được tiến hoá theo `capacity_time` (quần thể cuối thiên về quy tắc này, và các hoán vị của 10 seed không độc lập nên đây là số liệu mô tả). Lợi ích f2 của `dp` được giải thích bằng cơ chế sau: f2 bằng hằng số nhân với `total_km`, và `dp` với trọng số nghiêng về f2 tạo ít tuyến hơn và dài hơn (trên 50 hoán vị ngẫu nhiên, trọng số [0, 1, 0]: 2.0 xe so với 10.4 xe và `total_km` 495 so với 750 ở C102-25, giảm 33.9%; 2.7 xe so với 21.2 xe và 1800 so với 2137 ở R201-50, giảm 15.7%; `dp` thấp hơn ở 50/50 hoán vị), nên f2 tốt nhất thấp hơn. Con số R201-50 khớp mức −12% đo ở `tv4_main`; con số C102-25 lớn hơn mức −16% vì phép đo dùng hoán vị ngẫu nhiên và bỏ qua trễ. Đánh đổi là tuyến dài thì trễ nhiều hơn, khớp với việc f1 và f3 tốt nhất của `dp` không tốt hơn.

**Vì sao polish hiệu quả.** Polish chỉ tốn một lần chấm lại n_pop × K cá thể ở cuối (vài giây, khoảng 6% CPU của run dài), không can thiệp vào tiến hoá nên không làm đổi quần thể (hoàn toàn trực giao với các cải tiến khác của nhóm), và thêm các điểm mà thứ tự hoán vị đã cho phép nhưng bộ giải mã tham lam không chọn (số điểm front tăng, ví dụ từ 9.7 lên 18.9 ở C102-25 sau 200 thế hệ). Phần giải thích "vì sao" này cũng là suy luận từ cơ chế, chưa kiểm riêng.

**Lưu ý quan trọng về bằng chứng.** So sánh "có polish và không polish" **đơn điệu theo cấu tạo**: front sau polish là tập không trội của (quần thể cuối ∪ điểm mới), nên mọi điểm của front cũ hoặc còn đó hoặc bị điểm mới trội, vì vậy HV không thể giảm (và IGD không thể tăng) trên cùng reference set. Việc 10/10 seed đều tốt lên với p = 0.002 vì thế **không phải bằng chứng** rằng polish hiệu quả; nó chỉ xác nhận mã hoạt động đúng. Câu hỏi có ý nghĩa là polish có đáng so với dùng cùng CPU cho việc khác hay không, tức so với thế hệ thêm ở bảng cuối mục 3c. Kết quả: ở 200 thế hệ polish **không** vượt việc chạy thêm thế hệ (C102-25 ngang nhau, p = 0.432; R201-50 chạy thêm thế hệ tốt hơn rõ, +0.149 so với +0.045, p = 0.002); chỉ ở ngân sách đã hội tụ polish mới hơn (C102-25: +0.052 so với +0.0007, p = 0.002; R201-50: +0.018 so với +0.007, p = 0.049). Hai điểm yếu cần nói rõ: (i) ở ngân sách hội tụ, giá trị "thế hệ thêm" là **ước lượng ngoại suy** HV(B) − HV(B − g) vì không có dữ liệu sau B, nên nghiêng về có lợi cho việc chạy thêm thế hệ (tức bất lợi cho polish), nhưng vẫn là ước lượng; (ii) p = 0.049 ở R201-50 sát ngưỡng 0.05 và chưa hiệu chỉnh đa so sánh, nên không nên coi là kết luận chắc. Kết luận thận trọng chúng tôi rút ra: polish là bước hoàn thiện cuối đáng giá khi ngân sách thế hệ đã bão hoà, chứ không thay cho ngân sách.

**Tỉ lệ thích nghi.** Bằng chứng không ủng hộ bật `adaptive_rates`: bản mặc định kém hơn baseline ở R201-50, `v1` chỉ bỏ được suy giảm đó mà không cải thiện, và cơ chế trì trệ không kích hoạt nên chưa được đánh giá thực sự. Muốn thử lại cần đổi tiêu chí trì trệ (ví dụ ngưỡng cải thiện HV); đó là thay đổi thuật toán, không phải tuning tham số.

## 5. Hạn chế

- **Cỡ mẫu nhỏ:** 10 seed cho kết quả (5 seed cho tuning), hai instance, p chưa hiệu chỉnh đa so sánh; tuning chọn trong 12 cấu hình trên cùng 5 seed nên có thiên lệch chọn lọc.
- **Chưa chạy n = 100 (RC201-100):** `split_capacity_time` ở n = 100 vượt đội xe và đang chờ TV1 quyết định (đo trên 200 hoán vị ngẫu nhiên ở C102-100: `capacity_time` dùng trung bình 26.8 xe so với `fleet_size` = 25, khả thi 0%, vì quy tắc ngừng cắt theo thời gian khi chỉ còn một xe rồi dồn mọi khách còn lại vào các tuyến cuối, nên trễ rất nhiều; `dp` nhiều lớp luôn khả thi, trễ ít hơn khoảng 8.5 lần (7342 so với 62400 phút) và f1 thấp hơn khoảng 3.2 lần. Vì vậy n = 100 là nơi `dp` chấm mọi cá thể có thể thực sự đáng giá, chưa được kiểm bằng tiến hoá và còn phụ thuộc cách TV1 sửa hoặc quyết định về `split_capacity_time`); mọi kết luận ở trên chưa áp dụng cho kích thước đó, nơi ràng buộc đội xe chạm nhiều hơn. Chi phí `dp` tham chiếu ở n = 100 (đo ở lượt thử 20 thế hệ) là khoảng 28 lần baseline, nên so sánh theo CPU càng bất lợi cho `every_eval`.
- **Ngân sách chưa chốt:** n_gen = 1400 và 3500 của `baseline_eqtime` do chúng tôi chọn để xấp xỉ chi phí `dp` (khoảng 0.80 và 0.97), không phải ngân sách cuối của nhóm; kết luận về polish ở "ngân sách hội tụ" cần xác nhận lại khi nhóm chốt ngân sách, kèm lượt chạy cuối trên seed 0–9.
- **Chưa thử kết hợp** với local search của TV2 và cơ chế đa dạng của TV3; polish lấy quần thể cuối làm đầu vào nên về lý thuyết ghép được, nhưng chưa có số liệu.
- **Đo chi phí:** hệ số CPU dp/baseline đo trên một seed, một phiên, sai số cỡ ±20–30%; thời gian tường không so được giữa các lượt chạy do tải nền.
- **Giới hạn phương pháp:** tổng có trọng số chỉ cho điểm tối ưu theo từng vector trọng số, nên các điểm Pareto ở vùng lõm của front không được bảo đảm.

## Gợi ý hình cho slide

1. **HV theo chi phí CPU (hình quan trọng nhất).** Trục x: chi phí CPU tương đối so với `dp` (0.06–1.0), trục y: HV, mỗi instance một panel. Đường là baseline cắt ở các n_gen, chấm là `dp` 200 thế hệ. Nguồn: bảng "Equal-time comparison" (hàm `eq_budget_table` trong `scripts/tv4_report.py`) và `history` của `baseline_eqtime` trong `results/tv4_main/`; cần dựng hình mới từ dữ liệu có sẵn.
2. **Polish trước và sau theo từng seed.** Biểu đồ cặp (mỗi seed một đoạn nối từ HV chưa polish sang polish) cho 4 ngân sách ở mục 3c; kèm cột "polish so với thế hệ thêm" để thấy điểm đảo chiều giữa ngân sách ngắn và hội tụ. Nguồn: `per_run.csv` của `tv4_main` (cấu hình baseline, baseline_polish, baseline_eqtime, baseline_eqtime_polish) và bảng "Polish so với dùng cùng chi phí CPU"; cần dựng hình mới.
3. **Front (f1, f2) của một seed đại diện:** baseline, `dp`, baseline sau polish, `baseline_eqtime`, để thấy `dp` mở rộng front sang vùng f2 thấp còn polish làm dày front. Nguồn: các F đã lưu trong `results/tv4_main/<instance>/<config>/` (`F` và `front` trong từng file seed) và cực trị ở mục "Per-objective extremes"; cần dựng hình mới.
4. **Tỉ lệ thích nghi theo thế hệ:** front1_fraction, pc, pm trung bình qua 10 seed so với đường baseline cố định, cho thấy pc/pm hiệu dụng nằm sát cận dưới và nhánh một-front không bao giờ chạy. Nguồn: đã có hình `docs/tv4_adaptive_rates.png` (từ `scripts/tv4_diagnose.py`), dùng lại được.
