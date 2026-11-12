# TV2: hợp đồng giao diện `init_smart` và `local_search`

Dành cho TV1 (chủ `src/nsga2.py`), TV3, TV4. Hai cải tiến, hai cờ trong `config.yaml`, mặc định tắt.
Branch: `feat/tv2-init-local-search`, tách từ `origin/main` tại `5197d65` (12/11/2026).

## 1. Hiện trạng repo khi TV2 làm (đã kiểm chứng, không suy đoán)

| File | Trạng thái tại `5197d65` | Ảnh hưởng tới TV2 |
|---|---|---|
| `src/nsga2.py`, `src/runner.py`, `src/metrics.py` | **rỗng (0 dòng)** | Chưa có vòng lặp NSGA-II thật để gắn hook. **Tích hợp vào nsga2.py: BLOCKED, chờ TV1.** |
| `src/decoder.py` | có `split()` chọn theo `split_rule` (`capacity` / `capacity_time`, mặc định `capacity_time`) | Local search phải so với **bộ tuyến mà decoder đang dùng thật** (không chỉ `split_greedy`). Đã làm như vậy. |
| `src/improvements/dp_split.py`, `adaptive.py` | rỗng trên main; có code trên `origin/feat/dp-split` (`af6a2f1`) | Đã thử merge cục bộ trong worktree tạm: 246 test pass, kiểm tra DP+LS pass (mục 6). |
| `docs/tv4_integration.md` | chỉ có trên `feat/dp-split` | Đã đọc, tuân theo quy tắc trọng số/RNG ở đó. |

Vì `nsga2.py` trống, TV2 kiểm thử hook trên một **harness NSGA-II tạm** ở `scripts/tv2_harness.py`
(NSGA-II chuẩn: fast non-dominated sort, crowding, giải đấu nhị phân, OX, đột biến đảo đoạn,
(μ+λ)). Harness **không phải baseline của TV1**, không nằm trong `src/`, chỉ dùng để chứng minh hook
đúng hợp đồng và để chạy thí nghiệm sơ bộ. Khi TV1 bàn giao, phải chạy lại thí nghiệm trên baseline thật.

## 2. Bảng hợp đồng

| Hạng mục | `init_smart` | `local_search` |
|---|---|---|
| Hàm gọi | `smart_initial_population(imp_cfg, inst, n_pop, rng, baseline_factory)` (`tv2_hooks.py`), bên dưới là `make_initial_population(inst, n_pop, rng, params, baseline_factory=None)` | `LocalSearchHook.from_config(imp_cfg, inst, evaluator, baseline_detail_fn=None)` rồi `hook(child_perm, rng, metadata)`; bên dưới là `improve(perm, inst, rng, params, *, decode_and_evaluate, metadata, counters, scales, require_same_routes)` |
| Input | `Instance`, `n_pop > 0`, **RNG của nsga2**, params từ `improvements.init_smart_params`, `baseline_factory(rng) -> list[int]` = đúng dòng sinh cá thể ngẫu nhiên của baseline | hoán vị con sau đột biến, **RNG của nsga2**, `metadata` (vd `{"dp_weights": w}`) |
| Output | `(list[list[int]] n_pop hoán vị 1..n, list[str] nhãn nn/tw/random/random_fallback)` | `(perm, detail)`: `detail is None` khi LS không kích hoạt → caller chấm như cũ; ngược lại `detail` là **kết quả evaluator chính xác** cho `perm` với cùng metadata → caller dùng lại, không chấm lần nữa |
| Kiểu RNG | `np.random.Generator` truyền vào; không tạo RNG, không dùng `random` | như bên trái |
| RNG tiêu thụ | nn/tw: bản thuần 0 lần; mỗi biến thể 1×`integers` + k×`choice`; random: đúng `baseline_factory` | mỗi lần gọi hook: đúng 1×`random()`; khi chạy: 1×`dirichlet` (trọng số), 1×`permutation` mỗi lượt, 2-3×`integers` mỗi bước đi |
| Evaluator | không đánh giá | `evaluator(perm, metadata) -> dict` có `routes, f1, f2, f3, fleet_ok, n_vehicles` — **phải là chính evaluator chấm con** |
| Chấm mục tiêu | — | `g = (f1, f2, 1 - f3)`, tối thiểu hoá |
| Cờ tắt | **không được gọi**, không đọc params | **không tạo hook**, không gọi RNG |
| File chạm | `src/improvements/init_smart.py`, `tv2_hooks.py` (TV2) | `src/improvements/local_search.py`, `tv2_hooks.py` (TV2) |

## 3. Đoạn gắn vào `nsga2.py` (đề xuất cho TV1, chưa áp dụng vì file trống)

```python
imp = cfg["improvements"]
ids = np.arange(1, inst.n + 1)
baseline_factory = lambda r: r.permutation(ids).tolist()   # đúng dòng baseline đang dùng

# --- khởi tạo
if imp["init_smart"]:
    from src.improvements.tv2_hooks import smart_initial_population
    perms, init_sources = smart_initial_population(imp, inst, n_pop, rng, baseline_factory)
else:
    perms = [baseline_factory(rng) for _ in range(n_pop)]      # NGUYÊN đường baseline

# --- trước vòng lặp
ls_hook = None
if imp["local_search"]:
    from src.improvements.tv2_hooks import LocalSearchHook
    ls_hook = LocalSearchHook.from_config(
        imp, inst, evaluator=lambda p, meta: evaluate_child(p, meta),     # cùng evaluator chấm con
        baseline_detail_fn=lambda p: evaluate_detail(p, inst))           # chỉ để tính scales

# --- mỗi con: sau đột biến, SAU khi gán dp weights cho con (nếu dp_split), TRƯỚC khi chấm
detail = None
if ls_hook is not None:
    child.perm, detail = ls_hook(child.perm, rng, {"dp_weights": child.extra.get("weights")})
if detail is None:
    detail = evaluate_child(child.perm, child_meta)
```

`evaluate_child` = `evaluate_detail(p, inst)` khi `dp_split` tắt, `evaluate_dp(p, inst, meta["dp_weights"], scales)` khi bật.
Với DP, `from_config` tự đặt `require_same_routes=False` (DP được phép cắt lại).

Bộ đếm: `ls_hook.counters` (`n_ls_calls, n_ls_triggered, n_ls_candidate_evals, n_ls_accepted,
n_ls_rejected_split, n_ls_rejected_feasibility, n_ls_rejected_no_improve, n_ls_split_drift,
n_eval_requests, n_real_model_evals, n_evals_total, elapsed_s`). `n_evals_total` do nsga2 điền.
Mọi lần LS gọi evaluator đều phải được tính vào tổng số lần đánh giá của run (harness làm vậy).

## 4. Chính sách quan trọng

- **Lệch biên tuyến (boundary drift).** Bước đi đề xuất trên một tuyến của nghiệm hiện tại, ghép lại
  thành hoán vị rồi chấm bằng evaluator thật. Nếu evaluator cắt ra bộ tuyến khác bộ đề xuất
  (`split_rule` capacity hoặc capacity_time), mặc định **loại** (`split_drift_policy: reject`).
  Tuỳ chọn `evaluate_actual` vẫn so sánh trên kết quả thật của decoder (không có fitness giả,
  nhưng bước đi không còn thuần nội tuyến). Với `capacity_time`, drift rất phổ biến (xem báo cáo).
- **DP split.** Không ép bộ tuyến; mọi lần chấm dùng **cùng `metadata` của con** (cùng trọng số),
  không gọi `sample_weights`/`child_weights` lần nữa. Bộ tuyến trả về là bộ tuyến DP thật.
- **Đội xe (`fleet_ok`).** Nghiệm hiện tại feasible → ứng viên infeasible bị loại. Nghiệm hiện tại đã
  vượt đội xe → chỉ nhận ứng viên không dùng nhiều xe hơn. LS không sửa evaluator toàn cục.
  *Câu hỏi cho nhóm/TV1:* có cưỡng chế `fleet_size` trong selection không? (README: chưa xử lý.)
- **Weighted acceptance.** Trọng số bốc 1 lần mỗi lần gọi; `scales = (mean f1, mean f2, 1.0)` trên
  3 hoán vị tất định (ID, NN, ETa), tính 1 lần mỗi run, không cache toàn cục, không RNG. Nhận khi
  `Σ w·g/s` giảm hơn ε. Đây không phải cải thiện Pareto.

## 5. Câu hỏi kỹ thuật cho TV1 (cần trả lời trước khi gắn)

1. Cá thể là object gì (`Individual` có `perm`, `F`, `extra`?) và quần thể lưu ở đâu?
2. Dòng sinh cá thể ngẫu nhiên baseline có đúng là `rng.permutation(np.arange(1, n+1))` không?
   (`init_smart` cần chính hàm đó làm `baseline_factory`.)
3. Thứ tự gọi RNG trong một generation: lai → đột biến → (dp weights) → LS → chấm? LS phải nằm sau
   đột biến và sau khi gán weights.
4. Có tái dùng `detail` LS trả về được không, hay bắt buộc chấm lại? (Cả hai đều đúng; tái dùng đỡ 1 lần chấm.)
5. Cách đếm số lần đánh giá và ghi log generation (để so sánh cùng ngân sách).
6. Chính sách `fleet_ok=false` trong chọn lọc.

## 6. Kiểm tra tương thích với TV4 (đã chạy, cục bộ, không push)

Worktree tạm, merge `origin/feat/dp-split` vào branch TV2: xung đột duy nhất ở `config.yaml`
(khối `improvements`), giải quyết bằng cách giữ cả hai (cờ `adaptive_rates`, `adaptive_params`,
`dp_split_params` của TV4 + `init_smart_params`, `local_search_params` của TV2). Sau merge:
`pytest` **246 passed**; `python -m scripts.tv2_dp_compat_check` **PASS** trên C102-25, R201-50,
RC201-100 (metadata giữ nguyên, detail == `evaluate_dp` chấm lại, không làm xấu `fleet_ok`).
Thời gian mỗi lần LS với DP: ~30 ms (n=25), ~87 ms (n=50), ~230 ms (n=100), p_ls=1, ngân sách 40.
Trên branch TV2 (chưa merge), script đó in `BLOCKED` và trả mã 2.

Lưu ý cho TV4: `dp_split.py` dùng `split_greedy` làm fallback và `objective_scales` chấm bằng
`split_greedy`, trong khi main đã chuyển sang `split()`/`capacity_time`. Không thuộc phạm vi TV2, chỉ báo lại.
