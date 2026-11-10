# TV4: ghi chú tích hợp `dp_split` và `adaptive_rates`

Dành cho TV1/TV2. Hai cải tiến độc lập, mỗi cái một cờ trong `config.yaml`, mặc định tắt.

## Những gì được cung cấp

| File | Hàm / lớp | Việc |
|---|---|---|
| `src/improvements/dp_split.py` | `evaluate_dp(perm, inst, weights, scales=None) -> dict` | split tối ưu (Prins) rồi chấm bằng `evaluate_routes_detail`; thêm khoá `weights`, `split="dp"` |
| | `sample_weights(rng, params) -> ndarray(3)` | trọng số cho cá thể mới; `params` = `cfg["improvements"]["dp_split_params"]` |
| | `child_weights(rng, wa, wb, params) -> ndarray(3)` | trọng số cho con theo `weight_inherit` |
| | `split_dp`, `objective_scales(inst)` | `scales` tất định, cache theo instance, không RNG |
| `src/improvements/adaptive.py` | `resolve_params(adaptive_params, nsga2_cfg, case29)` | gộp khoảng pc/pm + pc/pm gốc thành dict phẳng |
| | `adaptive_rates(rank_a, rank_b, max_rank, params, front1_fraction, pm_boost=1.0) -> (pc, pm)` | pc/pm theo hạng cha mẹ tốt hơn |
| | `StagnationTracker(stagnation_gens, boost)` | `update(front1_objs)` trả hệ số nhân pm |
| | `rate_history(logs)` | `(front1_fraction, pc_tb, pm_tb)` để vẽ |

## Chỗ gắn vào vòng lặp `nsga2.py`

1. **Tạo cá thể** (chỉ khi `dp_split` bật): `ind.extra["weights"] = sample_weights(rng, params)`, `rng` là bộ sinh nsga2 truyền vào.
   `weight_dist: dirichlet` → đúng 1 lần `rng.dirichlet`; `onehot` → đúng 1 lần `rng.integers(3)`.
   Trọng số gắn với cá thể, **không chọn lại khi đánh giá** (cùng hoán vị + cùng trọng số luôn ra cùng kết quả).
2. **Đánh giá:** `dp_split` bật → `evaluate_dp(perm, inst, ind.extra["weights"])`, ngược lại → `evaluate` như cũ. Lấy `f1, f2, f3` từ dict trả về.
3. **Sinh con:** `child.extra["weights"] = child_weights(rng, wa, wb, params)`. `fresh` → bốc mới, cùng số lần rng như bước 1; `parent` → chép trọng số của một cha mẹ, đúng 1 lần `rng.integers(2)`. Cả hai hàm chỉ dùng `rng` được truyền vào.
4. **Mỗi cặp ghép:** `adaptive_rates(rank_a, rank_b, max_rank, params, front1_fraction, pm_boost=tracker.multiplier)`. `rank` tính từ 0 (front 1), `max_rank` là hạng lớn nhất hiện có, `front1_fraction = |front 1| / n_pop`. Dùng `resolve_params(cfg["improvements"]["adaptive_params"], cfg["nsga2"], case29=...)` một lần trước vòng lặp.
5. **Mỗi generation:** `tracker.update(objectives_của_front_1)` (mảng m×3). Tracker chỉ đếm khi `stagnation_gens > 0`.

`front1_fraction >= single_front_threshold` (0.9) thì trả về pc/pm gốc của `nsga2`, vì khi gần cả quần thể ở front 1 thì mọi cặp có `r = 0` và thích nghi thoái hoá thành pc_min/pm_min cố định. Lúc đó chỉ còn tracker điều chỉnh pm.

## Khoá config

`improvements.dp_split` (cờ), `improvements.dp_split_params`: `weight_dist`, `weight_inherit`, `g3_scale` (1.0).
`improvements.adaptive_rates` (cờ), `improvements.adaptive_params`: `pc_min/pc_max`, `pm_min/pm_max`, `pm_case29: {min, max}`, `single_front_threshold`, `stagnation_gens` (0 = tắt), `boost`.

## Quy tắc RNG: cờ tắt thì không gọi RNG lần nào

Hai module này **không tự tạo RNG**, chỉ dùng `rng` được truyền vào, và chỉ trong `sample_weights`/`child_weights`. `nsga2.py` chỉ được gọi hai hàm này khi `cfg["improvements"]["dp_split"]` là true. Cờ tắt mà vẫn gọi thì dãy số ngẫu nhiên bị lệch và không còn khớp baseline. Hai cờ `dp_split` và `adaptive_rates` bật tắt riêng, để ablation đo riêng được.

## Chi phí đo được

- `split_dp` ở n = 100: khoảng **10 ms/lần gọi** (C102 9.8 ms, RC201 10.5 ms); `split_greedy` rẻ hơn nhiều.
- Giới hạn 25 xe **chạm trên hầu hết các lần gọi** ở n = 100 (C102 49/50, RC201 40/50 hoán vị ngẫu nhiên với trọng số nghiêng về f3), nên DP phân tầng chạy gần như mọi lần.
- Một lần `evaluate_dp` tính là một lần đánh giá, nhưng đắt hơn `evaluate` nhiều. Khi so ngân sách (TV3) nên ghi cả thời gian chạy.
- Nếu không có cách cắt nào trong giới hạn xe, `split_dp` rơi về `split_greedy` và cảnh báo một lần.

Test: `tests/test_dp_split.py`, `tests/test_adaptive.py`.
