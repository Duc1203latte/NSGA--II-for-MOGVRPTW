# TV4: kết quả giai đoạn 2 (n = 25, 50) trên baseline thật

Thí nghiệm `tv4_main`, chạy bằng `python -m src.runner run` / `analyze`, bảng dựng bởi
`python -m scripts.tv4_report --exp tv4_main --instances C102-25 R201-50`.

- **Instance:** C102-25 và R201-50. RC201-100 chưa chạy, chờ TV1 quyết định về việc `split_capacity_time` vượt đội xe ở n = 100.
- **Cấu hình:** `baseline` (mọi cờ tắt), `dp` (`improvements.dp_split=true`), `adapt` (`improvements.adaptive_rates=true`), `both` (cả hai).
- **Thiết lập:** `config.yaml` mặc định (n_pop 80, n_gen 200, pc 0.7, pm 0.1, `satisfaction_time: arrival`, `split_rule: capacity_time`, tham số cải tiến mặc định chưa tuning), seed 0–9 cho mọi cấu hình, 8 tiến trình song song.

## Bảng kết quả

| Instance | Cấu hình | HV | ΔHV vs baseline | p (HV) | IGD | p (IGD) | SP | n_evals | Thời gian/run (s) | Khả thi (front) | Khả thi (quần thể) | Số xe TB (front) | Số điểm front |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C102-25 | baseline | 0.9034 ± 0.1763 | — | — | 0.2413 ± 0.1031 | — | 0.0447 ± 0.0429 | 16080 | 3.8 | 1.00 | 1.00 | 3.0 | 9.7 |
| C102-25 | dp | 0.9998 ± 0.1528 | +0.0963 | 0.174 | 0.1941 ± 0.0969 | 0.364 | 0.0897 ± 0.0732 | 16080 | 25.1 | 1.00 | 1.00 | 3.2 | 19.0 |
| C102-25 | adapt | 0.8641 ± 0.2028 | -0.0393 | 0.496 | 0.2604 ± 0.1285 | 0.597 | 0.0422 ± 0.0284 | 16080 | 3.9 | 1.00 | 1.00 | 3.1 | 7.9 |
| C102-25 | both | 1.0505 ± 0.1784 | +0.1471 | 0.059 | 0.1678 ± 0.1137 | 0.082 | 0.0657 ± 0.0544 | 16080 | 25.4 | 1.00 | 1.00 | 3.1 | 18.0 |
| R201-50 | baseline | 0.8844 ± 0.0758 | — | — | 0.1177 ± 0.0338 | — | 0.0185 ± 0.0098 | 16080 | 5.8 | 1.00 | 1.00 | 6.9 | 19.7 |
| R201-50 | dp | 0.8900 ± 0.0912 | +0.0056 | 0.406 | 0.1227 ± 0.0583 | 0.940 | 0.0284 ± 0.0117 | 16080 | 91.2 | 1.00 | 1.00 | 6.6 | 34.0 |
| R201-50 | adapt | 0.7638 ± 0.0523 | -0.1206 | 0.001 | 0.1879 ± 0.0371 | 0.001 | 0.0201 ± 0.0132 | 16080 | 6.0 | 1.00 | 1.00 | 7.7 | 21.6 |
| R201-50 | both | 0.8675 ± 0.1258 | -0.0169 | 0.705 | 0.1437 ± 0.0788 | 0.545 | 0.0405 ± 0.0237 | 16080 | 92.4 | 1.00 | 1.00 | 6.5 | 32.4 |

Mỗi ô: trung bình ± độ lệch chuẩn qua 10 run (cùng bộ seed cho mọi cấu hình). p-value: Wilcoxon rank-sum hai phía so với baseline cùng instance; chưa hiệu chỉnh đa so sánh.

## Nhận xét

Với 10 seed, chỉ `adapt` trên R201-50 đạt p < 0.05 trong 12 phép so với baseline (6 HV, 6 IGD) và là theo hướng kém hơn (HV 0.764 so với 0.884, p = 0.001; IGD p = 0.001); các phép so còn lại không phân biệt được với baseline, trong đó `both` trên C102-25 là gần nhất (ΔHV +0.147, p = 0.059; IGD p = 0.082), và chưa hiệu chỉnh đa so sánh. `dp` và `both` cho front nhiều điểm hơn rõ rệt (19.0 và 18.0 so với 9.7 điểm trên C102-25; 34.0 và 32.4 so với 19.7 trên R201-50) nhưng SP cao hơn, tức phân bố điểm kém đều hơn, nên HV khó đọc riêng lẻ, không tách được hội tụ khỏi độ phủ. Số xe trung bình trên front gần như không đổi (3.2 so với 3.0 ở n = 25; 6.6 so với 6.9 ở n = 50), và mọi cấu hình, kể cả baseline, đều có 100% nghiệm khả thi ở hai kích thước này, nên ràng buộc đội xe của DP chưa tạo ra khác biệt nào ở đây (nó chỉ bắt đầu chạm ở n = 100). Tất cả cấu hình dùng cùng 16080 lần đánh giá nhưng `dp`/`both` tốn thời gian gấp khoảng 6.6 lần (n = 25) và 15.7 lần (n = 50) trong lượt chạy song song này, nên so cùng số thế hệ có lợi cho DP và chưa có phép so cùng thời gian chạy. Kết quả chỉ là một lượt chạy với tham số chưa tuning trên hai instance, chưa đủ để kết luận về hướng của hiệu ứng, và nguyên nhân `adapt` kém ở R201-50 chưa được điều tra.

## Ghi chú

- Thời gian chạy đo khi 8 tiến trình chạy song song, chỉ so được với nhau trong bảng này; một số run `dp`/`both` ở seed cuối chậm gấp đôi trung vị (xem `results/tv4_main/<instance>/per_run.csv`), nên trung bình bị kéo lên. Chi phí tham chiếu của `dp_split` khi chạy tuần tự (lượt chạy thử, 20 thế hệ): ~9x ở n = 25, ~24x ở n = 50, ~28x ở n = 100 so với baseline.
- HV và IGD chỉ so được giữa các cấu hình trong **cùng** bảng này: `analyze` gộp front của cả bốn cấu hình trên mỗi instance thành một reference set và một cận chuẩn hoá, nên thêm hoặc bớt cấu hình thì mọi HV/IGD đổi theo, và không được so số HV giữa hai instance hay với bảng khác.
- "Khả thi" là tỉ lệ nghiệm không vượt đội xe (CV = 0); "Số xe TB" chấm lại từng cá thể trên front cuối bằng đúng evaluator của cấu hình đó (script kiểm F chấm lại trùng F đã lưu).
- Dữ liệu thô nằm ở `results/tv4_main/` (không đưa lên git).
