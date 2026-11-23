# TV3: Cơ chế giữ đa dạng (`diversity`)

## 1. Mục tiêu

NSGA-II gốc dùng crowding distance để chọn cá thể trong front cuối cùng khi quần thể bị tràn. Với ba
mục tiêu, crowding distance có hai điểm yếu đã biết. Thứ nhất, nó cộng khoảng cách theo từng trục
riêng lẻ nên ước lượng mật độ kém khi số mục tiêu tăng. Thứ hai, nó tính mật độ một lần rồi cắt
cả loạt, nên hai cá thể gần nhau có thể bị loại cùng lúc, để lại một khoảng trống trên front.

Cải tiến `diversity` thay crowding distance bằng một độ đo mật độ khác và thêm một external archive.
Cải tiến được bật bằng cờ `improvements.diversity` và tắt theo mặc định.

## 2. Thiết kế

### 2.1 Chuẩn hoá

f1 (chi phí) cỡ vài nghìn CNY, f2 (CO2) cỡ vài trăm kg, còn 1 − f3 nhỏ hơn 1. Mọi khoảng cách vì vậy
được đo trên mục tiêu đã chuẩn hoá min-max về [0, 1]. Cận chuẩn hoá lấy theo chính tập đang xét, tức
front cần cắt hoặc archive.

### 2.2 Hai độ đo mật độ (`diversity_params.density`)

- **kNN:** điểm thưa của cá thể p là khoảng cách Euclid từ p tới láng giềng gần thứ k.
- **SDE (shift-based density estimation, Li, Yang & Liu 2014):** khi đo khoảng cách từ p tới q, trước
  hết dịch q về phía p ở những mục tiêu mà q tốt hơn p: q'ᵢ = max(qᵢ, pᵢ). Sau đó lấy khoảng cách từ p
  tới q' như kNN. Một cá thể chỉ giỏi một mục tiêu nhưng kém các mục tiêu còn lại sẽ có nhiều láng
  giềng "được kéo lại gần", nên bị coi là đông đúc. Như vậy SDE ưu tiên các lời giải cân bằng, đồng
  thời vẫn giữ được độ phủ.

Điểm thưa càng lớn thì cá thể càng tốt. Điểm này được dùng ở cả hai nơi mà baseline dùng crowding
distance: chọn lọc giải đấu và chọn cá thể sống sót.

### 2.3 Cắt front cuối từng bước

Baseline sắp front cuối theo crowding distance một lần rồi lấy phần đầu. Bản cải tiến thì bỏ dần
từng cá thể đông nhất, và mỗi lần bỏ thì tính lại mật độ của các cá thể còn lại. Cách này giống
truncation của SPEA2. Khi hai cá thể hoà ở láng giềng thứ k, ta so tiếp láng giềng thứ k+1, k+2...
Nếu vẫn hoà thì bỏ cá thể có chỉ số nhỏ hơn, nên kết quả luôn tất định.

### 2.4 External archive (`diversity_params.archive`)

Archive lưu mọi lời giải không bị trội tìm được qua các thế hệ, có loại vector mục tiêu trùng. Phép
so trội dùng constrained domination giống NSGA-II, tức xét số xe vượt giới hạn trước. Khi archive
vượt `archive_size` thì cắt bằng cùng thủ tục ở mục 2.3. Nếu bật archive, kết quả cuối là archive chứ
không phải front của quần thể cuối. `history` cũng ghi archive của từng thế hệ.

### 2.5 Tham số (`config.yaml`)

| Tham số | Giá trị | Lý do |
|---|---|---|
| `density` | `sde` | thắng kNN trên 3/4 instance (mục 4) |
| `k` | 1 | đã có tie-break theo láng giềng k+1, k+2... nên k = 1 là đủ |
| `archive` | `true` | theo yêu cầu đề, nhưng xem nhận xét ở mục 5 |
| `archive_size` | 80 (= `n_pop`) | để số điểm trả về ngang baseline và phép so HV công bằng |

Các giá trị này chưa được tuning. Việc tuning do TV4 làm ở giai đoạn 3, trên seed 100–104.

## 3. Cài đặt và kiểm tra

- Toàn bộ logic nằm trong `src/improvements/diversity.py`. Trong `src/nsga2.py` chỉ thêm một tham số
  tuỳ chọn `div` vào `rank_and_crowding`, `environmental_selection` và `select_survivors`, cộng phần
  quản lý archive trong `run`. Chữ ký của các hàm đã đóng băng không đổi.
- Cải tiến không dùng bộ sinh ngẫu nhiên, nên dãy số ngẫu nhiên giữ nguyên dù bật hay tắt cờ. Cải tiến
  cũng không gọi thêm decoder: `n_evals` bằng đúng baseline (16 080 ở 200 thế hệ).
- `tests/test_diversity.py` có 16 test:
  - kNN và SDE trên một tập ba điểm tính tay (hai cực biên và một điểm cân bằng). kNN cho ba điểm bằng
    nhau, còn SDE cho điểm cân bằng 0.6 và hai cực biên 0.4;
  - SDE chỉ dịch ở mục tiêu mà q tốt hơn p; chuẩn hoá làm kết quả không phụ thuộc thang đo;
  - truncation bỏ đúng điểm đông nhất, tie-break theo láng giềng thứ hai giữ hai đầu mút;
  - archive chỉ chứa lời giải không bị trội, không có vector trùng, không vượt `archive_size`, và giữ
    các cực biên khi cắt;
  - **tắt cờ cho ra đúng từng số như `main`** (so mã băm của ma trận F của C102-25, seed 0, 200 thế hệ,
    với commit f7e0ed3), và đổi `diversity_params` khi cờ tắt không ảnh hưởng gì;
  - bật cờ thì chạy tất định theo seed, front không bị trội, archive là hoán vị hợp lệ.
- Cả 103 test của repo (87 test cũ và 16 test mới) đều pass.

## 4. Thí nghiệm giai đoạn 2

**Thiết lập:** 4 instance (C102-25, R201-50, RC201-100, case29), 10 seed (0–9), `n_pop` = 80,
200 thế hệ, `satisfaction_time = arrival`. Mọi tham số khác giữ mặc định. Chỉ số được tính bằng
`src.runner analyze`: reference set và cận chuẩn hoá gộp từ mọi cấu hình, p-value tính bằng Wilcoxon
rank-sum trên HV so với baseline.

Bốn cấu hình:

- `baseline`: tắt hết cải tiến.
- `sde_archive`: SDE kèm archive (cấu hình mặc định khi bật cờ).
- `knn_archive`: kNN kèm archive.
- `sde_only`: SDE, không archive.

Thư mục kết quả: `results/tv3_div/<instance>/`.

### HV (trung bình ± độ lệch chuẩn, 10 seed)

| Instance | baseline | sde_archive | ΔHV | p | knn_archive | ΔHV | p |
|---|---|---|---|---|---|---|---|
| C102-25 | 0.753 ± 0.260 | 0.809 ± 0.316 | +0.057 | 0.60 | 0.698 ± 0.289 | −0.055 | 0.88 |
| R201-50 | 0.635 ± 0.158 | 0.660 ± 0.181 | +0.026 | 0.82 | 0.612 ± 0.271 | −0.022 | 0.94 |
| RC201-100 | 0.739 ± 0.126 | 0.838 ± 0.189 | **+0.099** | 0.20 | 0.788 ± 0.159 | +0.049 | 0.60 |
| case29 | 0.912 ± 0.138 | 0.861 ± 0.081 | −0.051 | 0.23 | 0.939 ± 0.109 | +0.028 | 0.94 |

`sde_only` cho kết quả **giống hệt** `sde_archive` trên cả 40 run (mục 5).

### IGD (nhỏ hơn là tốt hơn)

| Instance | baseline | sde_archive | knn_archive |
|---|---|---|---|
| C102-25 | 0.314 | 0.299 | 0.361 |
| R201-50 | 0.253 | 0.252 | 0.313 |
| RC201-100 | 0.270 | **0.212** | 0.220 |
| case29 | 0.182 | 0.206 | **0.152** |

### Set coverage và các cực trị trên RC201-100

- SC(sde, baseline) = 0.70: trung bình 70% điểm trên front baseline bị front SDE (cùng seed) trội.
  Chiều ngược lại SC(baseline, sde) chỉ là 0.14.
- f1 nhỏ nhất trung bình: SDE đạt 15 680, baseline đạt 16 338 (giảm 4%). f2 nhỏ nhất: 2 147 so với 2 153.

Thời gian chạy của mọi cấu hình gần bằng nhau, chênh dưới 4%. Truncation từng bước là O(m³) trên
front cuối, nhưng m ≤ 160 nên chi phí này nhỏ so với decoder.

## 5. Thảo luận

1. **SDE tốt hơn baseline trên 3/4 instance, rõ nhất ở instance lớn.** Ở RC201-100, HV tăng 0.099,
   IGD giảm 21% và SC lệch hẳn về phía SDE. Điều này khớp với lý thuyết: với ba mục tiêu và front lớn,
   crowding distance ước lượng mật độ kém nhất. Tuy vậy **không có kết quả nào đạt p < 0.05**. Độ lệch
   chuẩn giữa các seed (±0.1–0.3) lớn hơn chênh lệch trung bình, và điều này cũng xảy ra với baseline,
   vì 200 thế hệ chưa đủ để hội tụ (xem kết quả giai đoạn 1). Muốn khẳng định cần thêm seed hoặc chạy
   lâu hơn.
2. **case29 là ngoại lệ.** Ở đây SDE kém baseline (−0.05) còn kNN tốt hơn. case29 không giới hạn số xe
   và front của nó có ít điểm (khoảng 10). SDE phạt các cá thể cực biên, và trên một front nhỏ như vậy
   các cực biên chiếm phần lớn đóng góp HV. Nhóm giữ SDE làm mặc định vì nó thắng ở 3/4 instance,
   nhưng sẽ báo case29 như một trường hợp SDE không có lợi.
3. **kNN không ổn định:** thua baseline ở hai instance nhỏ và thắng ở hai instance còn lại. Trên
   C102-25 và R201-50, kNN làm f3 lớn nhất giảm rõ (0.941 so với 0.958; 0.768 so với 0.793). Có vẻ kNN
   giữ những vùng thưa nhưng kém chất lượng.
4. **Archive không đóng góp gì khi `archive_size = n_pop`.** NSGA-II là thuật toán tinh hoa (elitist):
   mọi lời giải không bị trội của quần thể gộp (cha mẹ + con) luôn được giữ lại khi front 1 có không quá
   `n_pop` cá thể. Trong thí nghiệm, front chỉ có 9–26 điểm, ít hơn nhiều so với 80, nên archive luôn
   trùng với front của quần thể cuối. Archive chỉ có tác dụng khi front 1 tràn quần thể, hoặc khi
   `archive_size > n_pop`. Trường hợp sau làm front trả về có nhiều điểm hơn baseline, khiến phép so HV
   không còn công bằng. **Vì vậy toàn bộ đóng góp của `diversity` đến từ độ đo SDE.** Trong ablation,
   chỉ cần một cấu hình "diversity" (SDE).
5. Cải tiến không tốn thêm phép đánh giá nào, nên so theo số thế hệ cũng chính là so theo số lần đánh
   giá. Phép so này công bằng, không giống `local_search` và `dp_split`.

## 6. Việc còn lại (giai đoạn 3, TV3)

- Ablation 10 cấu hình (baseline, bật từng cái, bật tất cả, bật tất cả trừ một) trên C102-25, R201-50,
  RC201-100 và case29, 10 seed. Việc này cần TV2 merge xong bốn branch vào `main`.
- Ghi số lần gọi `evaluate` của mỗi cấu hình. Nếu kịp, chạy thêm một lượt so với cùng ngân sách đánh
  giá.
- Bảng cấu hình × instance gồm HV (trung bình ± độ lệch chuẩn), ΔHV và p-value, lưu vào `results/`.
