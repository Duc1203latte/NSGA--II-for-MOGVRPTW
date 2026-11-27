# Giai đoạn 3: quy trình merge và hồi quy (TV2 chuẩn bị)

Chưa merge gì vào `main`. Merge chỉ khi nhóm/owner cho phép. Không force-push.

## 0. Mốc baseline (trước mọi merge)

1. Khi TV1 bàn giao `src/nsga2.py`: sửa `scripts/tv2_regression_snapshot.py` để gọi runner thật thay
   cho `scripts.tv2_harness.run` (giữ nguyên `CASES` = C102-25, R201-50, RC201-100, `SEEDS` = 0, 1).
2. Trên commit baseline của TV1, mọi cờ tắt: `python -m scripts.tv2_regression_snapshot` → ghi
   `tests/fixtures/tv2_alloff_snapshot.json` (hoán vị, mục tiêu float.hex, #eval, trạng thái RNG, SHA).
3. Commit mốc đó riêng, ghi SHA vào PR. Từ đó **không sửa mốc** để khớp code mới.

Hiện tại mốc trong repo là của harness TV2 (ghi rõ trong `_note`), dùng để chứng minh nhánh tắt của
TV2 không đổi kết quả. Nó KHÔNG thay mốc baseline của TV1.

## 1. Thứ tự merge (trên branch `integration/phase3`, mỗi lần một branch)

| Bước | Branch | Sau khi merge chạy |
|---|---|---|
| 1 | baseline TV1 (nếu chưa ở main) | `pytest tests/test_decoder.py`, chụp mốc (mục 0) |
| 2 | `feat/tv2-init-local-search` | `pytest`, `python -m scripts.tv2_regression_snapshot --check` |
| 3 | `feat/dp-split` (TV4) | `pytest`, regression `--check`, `python -m scripts.tv2_dp_compat_check` |
| 4 | branch TV3 (diversity) | `pytest`, regression `--check` |
| 5 | all-on smoke | `run_tv2_experiments` với cờ bật hết (thêm preset), ghi thời gian và #eval |

Fail ở bước nào thì dừng, sửa đúng lỗi của branch vừa merge, chạy lại cả ba loại test rồi mới
merge branch kế tiếp. Không xoá test, không `skip`/`xfail`, không đổi fixture.

## 2. Xung đột đã biết và cách giải

- `config.yaml`, khối `improvements`: TV2 thêm `init_smart_params`, `local_search_params`; TV4 thêm
  `adaptive_rates`, `adaptive_params`, `dp_split_params`. Giải quyết = **giữ cả hai**, chỉ cộng thêm
  khoá, mọi cờ vẫn `false`. Đã thử thật trong worktree tạm: sau khi giải, 246 test pass.
- `src/nsga2.py`: mỗi cải tiến một khối `if imp["<cờ>"]:` gọn, cùng một `rng`; nhánh `else` là
  nguyên văn baseline. Thứ tự trong vòng lặp con: lai → đột biến → gán dp weights (TV4) → LS (TV2)
  → chấm. Chọn lọc môi trường: TV3.

## 3. Quy ước ablation cần nhóm chốt

README nói "bốn cải tiến" nhưng config có 5 cờ (`adaptive_rates` tách khỏi `dp_split`). Cần thống
nhất: ablation 4 nhóm (gộp `dp_split + adaptive_rates` thành nhóm TV4) hay 5 cờ riêng. TV2 không tự
quyết. `init_smart` và `local_search` là hai cờ riêng; nếu nhóm tính "một cải tiến TV2" thì cũng cần ghi rõ.

## 4. Checklist sẵn sàng PR của TV2

- [x] Hai module có code thật, không stub/TODO trên đường chạy
- [x] Test đơn vị + tích hợp (trên harness) pass
- [x] Cờ mặc định tắt; nhánh tắt khớp mốc từng bit (harness), không gọi module TV2
- [x] Thử merge với `feat/dp-split`: test pass, DP+LS compat pass
- [ ] Gắn hook vào `src/nsga2.py` thật — **chờ TV1**
- [ ] Chạy lại thí nghiệm trên baseline thật — **chờ TV1**
- [ ] Nhóm duyệt PR và chốt quy ước ablation
