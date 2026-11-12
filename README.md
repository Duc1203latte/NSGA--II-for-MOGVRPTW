# NSGA-II cho bài toán định tuyến xe xanh đa mục tiêu có khung thời gian

Bài tập lớn môn **Tính toán tiến hóa**, nhóm 4 người.

Repo cài đặt thuật toán NSGA-II để giải bài toán MOGVRPTW (Multi-Objective Green Vehicle Routing
Problem with Time Windows), thêm bốn cải tiến và đo xem mỗi cải tiến đóng góp bao nhiêu. Kết quả
được so với bài báo:

> Li, X.; Gao, C.; Wang, J.; Tang, H.; Ma, T.; Yuan, F. *Research on Multi-Objective Green Vehicle
> Routing Problem with Time Windows Based on the Improved Non-Dominated Sorting Genetic Algorithm
> III*. Symmetry 2025, 17, 734.

Bài báo dùng NSGA-III. Nhóm dùng NSGA-II và so với cả hai cột NSGA-II và INSGA-III trong các bảng
kết quả của họ.

Bài báo là nguồn mô hình, tham số, dữ liệu và là mốc để so sánh, không phải đáp án. Bài báo có công
thức sai và nhiều chỗ không nói rõ, nên nhóm không cố tái tạo đúng số của họ. Code được kiểm bằng test
tính tay theo mô hình của nhóm. Chỗ nào số lệch bài báo thì ghi vào báo cáo kèm nguyên nhân.

Nhóm cũng không bắt buộc dùng đúng phương pháp của bài báo (cách mã hoá, toán tử lai ghép, đột biến,
chọn lọc...). Mỗi lựa chọn được quyết định bằng lý do hợp lý hoặc bằng thực nghiệm, cách nào cho kết
quả tốt hơn thì dùng. Chỗ nào khác bài báo thì ghi rõ khác ở đâu và vì sao.

## Bài toán

Một kho, một đội xe tải giống nhau, n khách. Mỗi khách có toạ độ, lượng hàng cần giao, thời gian dỡ
hàng và khung giờ muốn nhận. Cần quyết định xe nào phục vụ khách nào và ghé theo thứ tự nào, sao
cho đồng thời:

- **chi phí giao hàng** thấp nhất (nhiên liệu, chi phí cố định mỗi xe, chi phí theo km, phạt sai giờ),
- **khí thải CO₂** thấp nhất,
- **mức hài lòng trung bình** của khách cao nhất.

Ba mục tiêu này xung đột nhau nên đầu ra không phải một lời giải mà là một tập Pareto.

## Tiến độ

| Giai đoạn | Thời gian | Nội dung | Số người | Trạng thái |
|---|---|---|---|---|
| 0 | 3/11 – 4/11 | Cấu trúc repo, môi trường, dữ liệu, data loader, decoder | 1 | xong |
| 1 | 5/11 – 11/11 | Test decoder, NSGA-II baseline, bộ đo | 1 | |
| 2 | 12/11 – 18/11 | Bốn nhánh cải tiến | 3 | |
| 3 | 19/11 – 25/11 | Merge, ablation, tuning | 3 | |
| 4 | 26/11 – 2/12 | Chạy đầy đủ, báo cáo, slide | 4 | |

## Phân công

| Mã | Thành viên |
|---|---|
| TV1 | *(điền tên)* |
| TV2 | *(điền tên)* |
| TV3 | *(điền tên)* |
| TV4 | *(điền tên)* |

### Giai đoạn 0 (3/11 – 4/11): TV1

- [x] Cấu trúc thư mục, môi trường Python 3.11, `requirements.txt`, `config.yaml`
- [x] Dữ liệu Solomon, `data/paper/case29.csv`, `data/paper/fixture_routes.csv`
- [x] `src/instance.py`: đọc instance, đổi đơn vị, sinh hai khung giờ
- [x] `src/decoder.py`: split, tính giờ đến, tính f1, f2, f3
- [x] `scripts/smoke_phase0.py`: chạy thử decoder trên cả 10 instance

### Giai đoạn 1 (5/11 – 11/11): TV1

Mục tiêu: có một NSGA-II gốc chạy đúng và bộ đo đầy đủ, làm nền cho ba người làm cải tiến ở giai đoạn 2.

- [x] `tests/test_decoder.py`: test tính tay từng thành phần (hàm hài lòng, split, F1–F4, f2, f3) và
      test bất biến (mỗi khách đúng một lần, không vượt tải)
- [ ] Đối chiếu ba bộ tuyến mẫu với số bài báo, ghi lại chỗ lệch
- [x] Chốt tải trọng Solomon 400 kg và cách cắt tuyến `capacity_time` (12/11)
- [ ] `src/nsga2.py`: sắp xếp không trội, crowding distance, chọn lọc giải đấu, lai ghép, đột biến,
      vòng lặp chính. Chỉ dùng một bộ sinh ngẫu nhiên có seed
- [ ] `tests/test_nsga2.py`: test sắp xếp không trội, crowding distance, toán tử, cùng seed ra cùng
      kết quả
- [ ] So sánh toán tử (OX/OBX, `standard`/`always`) trên 3 instance × 10 seed, chốt mặc định
- [ ] `src/metrics.py`: HV và IGD qua pymoo, tự viết SP, SC, DM
- [ ] `src/runner.py`: chạy 10 seed trên một cấu hình, lưu kết quả thô vào `results/`
- [ ] Gõ số liệu so sánh của bài báo vào `data/paper/paper_metrics.csv`, `data/paper/paper_objectives.csv`
- [ ] Đo hệ số tương quan giữa f1, f2, f3 trên front của baseline
- [ ] Chạy baseline với cả hai cách tính hài lòng (`satisfaction_time: arrival` và `service_start`),
      lưu kết quả tách thư mục, so front và hệ số tương quan của hai cách
- [ ] Bàn giao: chốt interface, viết hướng dẫn ngắn cách thêm một cải tiến (cờ trong config, chỗ gắn
      vào vòng lặp)

Cổng: test decoder pass; baseline hội tụ, tốt hơn hẳn lời giải ngẫu nhiên, ổn định qua 10 seed.

### Giai đoạn 2 (12/11 – 18/11): TV2, TV3, TV4

Mỗi người một branch, mỗi cải tiến một file trong `src/improvements/`, bật tắt bằng một cờ trong
`config.yaml`, mặc định tắt.

| Người | Cải tiến | Việc cụ thể |
|---|---|---|
| TV2 | `init_smart`, `local_search` | khởi tạo trộn nearest-neighbor, sắp theo khung giờ và ngẫu nhiên; 2-opt và Or-opt trên từng tuyến sau đột biến |
| TV3 | `diversity` | SDE hoặc kNN density thay crowding distance; external archive |
| TV4 | `dp_split` | split tối ưu bằng quy hoạch động (mỗi lần gọi chọn ngẫu nhiên một mục tiêu hoặc trọng số); Pc/Pm thích nghi |

Mỗi người đều phải:

- [ ] Viết test riêng cho cải tiến của mình
- [ ] Chứng minh tắt cờ thì ra đúng kết quả baseline với cùng seed
- [ ] Chạy 10 seed trên ít nhất 3 instance, so HV với baseline

#### Quy tắc chung cho cả ba người

- Branch đặt tên `feat/<tên-cải-tiến>`, ví dụ `feat/init-smart`. Không sửa thẳng `main`.
- Không đổi chữ ký của `load_instance`, `evaluate`, `evaluate_detail`. Cần thêm thông tin thì thêm
  trường vào `Instance` hoặc thêm hàm mới.
- Mọi tham số mới (tỉ lệ, xác suất, kích thước archive...) để trong `config.yaml`, dưới mục
  `improvements`.
- Chỉ dùng bộ sinh ngẫu nhiên mà `nsga2.py` truyền vào, không tự tạo `random` hay
  `np.random` riêng. **Khi cờ tắt, code của cải tiến không được gọi bộ sinh ngẫu nhiên lần nào.** Nếu
  gọi dù chỉ một lần thì dãy số ngẫu nhiên phía sau bị lệch, và kết quả không còn giống baseline.

#### TV2: `init_smart`, khởi tạo quần thể thông minh

- **Gắn vào đâu:** thay bước tạo quần thể ban đầu ngẫu nhiên trong `nsga2.py`.
- **Làm gì:** sinh `nPop` hoán vị bằng ba cách, tỉ lệ đặt trong config (ví dụ 20% / 20% / 60%):
  - *Nearest-neighbor:* bắt đầu từ kho, mỗi bước chọn khách chưa ghé gần nhất.
  - *Theo khung giờ:* sắp khách theo giờ mở khung `ETa`, bằng nhau thì xét khoảng cách.
  - *Ngẫu nhiên:* như baseline.

  Hai cách đầu luôn cho cùng một hoán vị, nên cần xáo nhẹ vài vị trí (hoặc chọn ngẫu nhiên trong vài
  khách gần nhất) để quần thể không có nhiều cá thể trùng nhau.
- **Test:** mọi cá thể là hoán vị hợp lệ của 1..n; tỉ lệ ba nhóm đúng như config; HV của quần thể ban
  đầu cao hơn khởi tạo ngẫu nhiên.

#### TV2: `local_search`, tìm kiếm cục bộ

- **Gắn vào đâu:** sau đột biến, trước khi đánh giá con.
- **Làm gì:** với xác suất `p_ls`, giải mã con thành các tuyến, rồi cải thiện từng tuyến bằng:
  - *2-opt:* đảo ngược một đoạn trong tuyến.
  - *Or-opt:* chuyển một đoạn 1–3 khách sang vị trí khác trong cùng tuyến.

  Có ba mục tiêu nên phải định nghĩa thế nào là "tốt hơn". Hai cách: nhận bước đi nếu tuyến mới trội
  hơn tuyến cũ, hoặc nhận nếu tổng có trọng số ngẫu nhiên giảm. Giới hạn số vòng lặp để không chạy quá
  lâu.
- **Cẩn thận:** nối các tuyến đã cải thiện lại thành hoán vị, rồi split tham lam lần nữa, có thể ra bộ
  tuyến **khác**. Sau 2-opt, khách đầu tuyến sau có thể vừa chỗ vào tuyến trước. Phải kiểm tra điều này,
  nếu không thì phần cải thiện bị mất khi đánh giá.
- **Test:** mỗi tuyến giữ nguyên tập khách; không có bước nào làm tuyến tệ hơn theo tiêu chí đã chọn;
  hoán vị ghép lại khi split lại ra đúng bộ tuyến đó.

#### TV3: `diversity`, cơ chế giữ đa dạng

- **Gắn vào đâu:** bước chọn lọc môi trường, khi phải chọn bớt cá thể trong front cuối cùng. Thay
  crowding distance bằng một độ đo mật độ khác.
- **Làm gì:**
  - *SDE (shift-based density estimation):* khi đo mật độ quanh cá thể p, dịch các cá thể khác về
    phía p ở những mục tiêu mà chúng tốt hơn p, rồi mới đo khoảng cách. Cách này phạt các cá thể chỉ
    giỏi một mục tiêu.
  - *Hoặc kNN density:* khoảng cách tới láng giềng gần thứ k.

  Chọn một trong hai bằng config. Chuẩn hoá ba mục tiêu về [0, 1] trước khi đo khoảng cách, vì f1 cỡ
  vài nghìn còn f3 nhỏ hơn 1.
- **External archive:** lưu mọi lời giải không bị trội tìm được qua các generation, giới hạn kích
  thước. Khi đầy thì loại cá thể ở vùng đông nhất. Khi bật archive, kết quả cuối là archive chứ không
  phải front của quần thể cuối.
- **Test:** trên một tập điểm nhỏ tự dựng, thứ hạng mật độ đúng như tính tay; archive chỉ chứa lời giải
  không bị trội và không vượt kích thước tối đa.

#### TV4: `dp_split`, split tối ưu bằng quy hoạch động

- **Gắn vào đâu:** thay `split_greedy` trong decoder khi cờ bật.
- **Làm gì (thuật toán split của Prins):** giữ nguyên thứ tự hoán vị, chỉ chọn chỗ cắt tối ưu. Dựng đồ
  thị có các nút 0..n là các vị trí cắt. Cung (i, j) nghĩa là một tuyến phục vụ các khách ở vị trí
  i+1..j, chỉ tồn tại khi không vượt tải. Trọng số của cung là chi phí của tuyến đó. Tìm đường ngắn nhất
  từ 0 đến n bằng quy hoạch động.
- **Chi phí một tuyến:** chỉ tối ưu được một con số. Chọn ngẫu nhiên một mục tiêu hoặc một tổng có
  trọng số ngẫu nhiên, đã chuẩn hoá. **Trọng số phải gắn với từng cá thể và lưu lại**, không được chọn
  lại mỗi lần đánh giá. Nếu chọn lại thì cùng một hoán vị đánh giá hai lần sẽ ra hai kết quả khác nhau.
- **Pc/Pm thích nghi:** Pc và Pm thay đổi trong một khoảng đặt trong config. Ví dụ: cá thể ở front tốt
  thì lai và đột biến ít hơn, hoặc tăng Pm khi HV không cải thiện sau vài generation.
- **Test:** với n ≤ 8, kết quả DP bằng kết quả thử hết mọi cách cắt; DP không bao giờ tệ hơn split tham
  lam trên mục tiêu đã chọn; Pc, Pm luôn nằm trong khoảng cho phép.

### Giai đoạn 3 (19/11 – 25/11): TV2, TV3, TV4

| Người | Việc |
|---|---|
| TV2 | Merge bốn branch vào `main`, giải quyết xung đột; test hồi quy: tắt hết cờ phải ra đúng baseline |
| TV3 | Ablation: từng cải tiến riêng, bật tất cả, bật tất cả trừ một; tính delta HV và p-value (Wilcoxon rank-sum) |
| TV4 | Tuning tham số của các cải tiến; kiểm tra `dp_split` và `local_search` có dẫm chân nhau không |

Cổng: mỗi cải tiến có một con số delta HV kèm p-value.

#### TV2: merge và test hồi quy

- **Trước khi merge:** lưu kết quả baseline làm mốc, gồm front cuối của 3 instance × 2 seed, vào
  `tests/test_regression.py`.
- **Merge từng branch một vào `main`.** Sau mỗi lần merge, chạy đủ ba loại test:
  - test của các branch đã merge,
  - test decoder,
  - test hồi quy: tắt hết cờ phải ra **đúng từng số** như mốc baseline.

  Fail thì sửa ngay trước khi merge branch tiếp theo, để biết lỗi do branch nào gây ra.
- Xung đột hay gặp nhất là ở `nsga2.py` (chỗ gắn các cải tiến) và `config.yaml`.
- Sau khi merge đủ bốn branch, bật tất cả cờ rồi chạy thử: không lỗi, và ghi lại thời gian chạy.

#### TV3: ablation, đo đóng góp của từng cải tiến

- **10 cấu hình:**

  | Nhóm | Cấu hình | Số cấu hình |
  |---|---|---|
  | Mốc | baseline, tắt hết | 1 |
  | Bật từng cái | chỉ bật một cải tiến | 4 |
  | Bật tất cả | | 1 |
  | Bật tất cả trừ một | tắt đúng một cải tiến | 4 |

  "Bật từng cái" cho biết cải tiến đó tốt đến đâu khi đứng riêng. "Bật tất cả trừ một" cho biết nó còn
  đóng góp bao nhiêu khi đã có các cải tiến khác.
- **Instance:** giai đoạn này chạy trên một tập nhỏ đại diện, ví dụ C102-25, R201-50, RC201-100 và case
  thực tế. Bản đầy đủ chạy ở giai đoạn 4.
- **Cách đo:** cùng bộ 10 seed cho mọi cấu hình.
  - Tính HV, IGD, SP.
  - Reference set của IGD gộp front của **cả 10 cấu hình**.
  - Delta HV = HV trung bình của cấu hình trừ HV trung bình của baseline.
  - p-value dùng Wilcoxon rank-sum.
- **Ngân sách tính toán:** `local_search` và `dp_split` tốn thêm phép đánh giá, nên so theo số
  generation là thiên vị cho chúng. Phải ghi lại số lần gọi `evaluate` của mỗi cấu hình và nêu trong báo
  cáo. Nếu kịp thì chạy thêm một lượt so sánh với cùng số lần đánh giá.
- **Đầu ra:** một bảng gồm cấu hình × instance, mỗi ô có HV (trung bình ± độ lệch chuẩn), delta HV và
  p-value. Lưu vào `results/`.

#### TV4: tuning và kiểm tra tương tác

- **Tham số cần chỉnh:**
  - tỉ lệ ba nhóm khởi tạo,
  - `p_ls` và số vòng lặp tối đa của local search,
  - kích thước archive và k,
  - khoảng Pc/Pm thích nghi,
  - cách chọn trọng số trong DP.
- **Cách chỉnh:**
  - Chỉnh từng tham số một (giữ các tham số khác cố định) trên 2–3 instance.
  - Dùng **seed riêng cho tuning** (ví dụ 100–104), khác bộ seed 0–9 dùng để báo kết quả. Nếu dùng chung
    thì tham số bị chỉnh vừa khít với chính các seed đó, và kết quả báo cáo sẽ đẹp hơn thực tế.
- **Kiểm tra `dp_split` × `local_search`:** so ba cấu hình: chỉ `dp_split`, chỉ `local_search`, và bật
  cả hai. Nếu bật cả hai mà tệ hơn bật một cái thì tìm nguyên nhân và đề xuất cách sửa, ví dụ giảm
  `p_ls` khi đã bật DP.
- **Đầu ra:** giá trị đã chọn ghi vào `config.yaml`, kèm comment lý do. Sau giai đoạn 3 thì **khoá
  config**, giai đoạn 4 không chỉnh nữa.

### Giai đoạn 4 (26/11 – 2/12): cả nhóm

| Người | Việc |
|---|---|
| TV1 | Chạy đầy đủ 10 seed trên 9 instance Solomon và case thực tế; bảng so sánh với cột NSGA-II và INSGA-III của bài báo |
| TV2 | Hình vẽ: Pareto front 3D, đường hội tụ HV, boxplot HV/IGD qua 10 seed |
| TV3 | Báo cáo: mô hình, các chỗ sửa bài báo, giả định của nhóm, kết quả và thảo luận |
| TV4 | Slide thuyết trình; nếu kịp, thí nghiệm thêm với vận tốc khác nhau theo cung đường |

Mỗi người viết phần báo cáo về việc mình đã làm ở giai đoạn 2 và 3, TV3 ghép và thống nhất văn phong.

## Cài đặt

Cần Python 3.11 trên Windows. Các bước dưới đây chạy trong PowerShell.

```powershell
git clone https://github.com/Duc1203latte/NSGA--II-for-MOGVRPTW.git
cd NSGA--II-for-MOGVRPTW
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Kiểm tra cài đặt:

```powershell
python -c "import vrplib; print(vrplib.read_instance('data/solomon/C102.txt', instance_format='solomon')['demand'].sum())"
```

Lệnh in ra `1810` là môi trường đã sẵn sàng.

Phiên bản thư viện được ghim cố định trong `requirements.txt` để cả nhóm chạy ra cùng kết quả. Muốn
thêm thư viện mới thì hỏi cả nhóm trước.

## Cấu trúc thư mục

```
data/
  solomon/        56 instance Solomon bản 100 khách
  paper/          số liệu gõ lại từ bài báo (case thực tế, tuyến mẫu, bảng kết quả)
src/
  instance.py     đọc instance, sinh hai khung giờ
  decoder.py      hoán vị -> tuyến -> ba hàm mục tiêu
  nsga2.py        NSGA-II baseline
  metrics.py      HV, IGD, SP, SC, DM
  runner.py       chạy nhiều run, lưu kết quả thô
  improvements/   bốn cải tiến, mỗi cải tiến một file
scripts/          script chạy thử, chạy bằng python -m scripts.<tên>
tests/            test tự động
results/          kết quả chạy, không đưa lên git
```

## Dữ liệu

**Solomon benchmark.** Bản 25 và 50 khách lấy từ 25 hoặc 50 khách đầu của file 100 khách, nên repo
chỉ lưu bản 100. Nhóm dùng chín cấu hình theo đúng bài báo:

| Số khách | Instance |
|---|---|
| 25 | C102, R201, RC202 |
| 50 | C102, R201, RC202 |
| 100 | C102, R201, RC201 |

**Case thực tế.** 29 điểm giao hàng của một công ty logistics, lấy từ Table 8 của bài báo, lưu ở
`data/paper/case29.csv`. File `data/paper/fixture_routes.csv` chứa ba lời giải mẫu bài báo công bố
(Tables 11, 12, 13), dùng để kiểm tra decoder.

## Chỉnh sửa bài báo và giả định của nhóm

Bài báo có vài công thức sai và nhiều chỗ không nói rõ. Mục này ghi lại cách nhóm xử lý, để cả nhóm
code theo cùng một cách hiểu. Muốn đổi điều nào thì bàn với cả nhóm trước, vì mọi con số phía sau
đều phụ thuộc vào đây.

### Những chỗ bài báo sai, nhóm đã sửa

1. **Hàm hiệu chỉnh khí thải sai bậc.** Bài báo in số hạng `0.0011·v³`. Với v = 40 km/h hàm này ra
   số âm, tức là xe càng chạy thì khí thải càng giảm. Nhóm dùng `0.0011·v²`. Khi đó mỗi km xe
   thải khoảng 679 g CO₂.
2. **Khí thải tỉ lệ thuận với quãng đường.** Vận tốc là hằng số và hàm hiệu chỉnh không phụ thuộc
   tải trọng, nên f2 chỉ là một hằng số nhân tổng km, giống hệt khoản chi phí theo km trong f1.
   Thực chất bài toán chỉ có hai chiều độc lập. Nhóm giữ nguyên mô hình để so được số với bài báo,
   nhưng sẽ đo hệ số tương quan giữa ba mục tiêu và đưa vào báo cáo.
3. **Công thức hài lòng thừa một dấu tổng** theo xe, và cho giá trị thang 0–100 trong khi bảng kết
   quả dùng thang 0–1. Nhóm bỏ tổng theo xe và chia cho 100.
4. **Tải trọng xe không thống nhất.** Bài báo ghi 400 kg cho benchmark và 4000 kg cho case thực
   tế, trong khi capacity gốc của Solomon là 200 hoặc 1000. Nhóm dùng đúng hai số của bài báo.
5. **Lỗi gõ ở Table 11.** Tuyến 7 in là `0-13-9-27-0`, nhưng đúng phải là `0-13-9-29-0`. Với bản
   đã sửa, độ dài tuyến khớp số bài báo và mỗi khách xuất hiện đúng một lần.

### Một chỗ bài báo tự mâu thuẫn

Theo công thức đã sửa, lời giải ở Table 12 (337.09 km) phải thải **229.03 kg** CO₂, và decoder của
nhóm cho đúng số đó. Bài báo lại báo **140.65 kg**, tức chỉ khoảng 417 g/km, trong khi chỗ khác của
bài báo ngầm định khoảng 680 g/km. Nhóm giữ công thức, không chỉnh hệ số cho khớp, và ghi chỗ này
vào báo cáo.

### Giả định nhóm tự chốt

| Vấn đề | Nhóm chọn |
|---|---|
| Đơn vị bên trong code | thời gian tính bằng phút, khối lượng bằng kg, khoảng cách bằng km. Mọi phép đổi đơn vị làm một lần khi đọc dữ liệu |
| Khoảng cách | Euclid trên toạ độ gốc, không làm tròn |
| Thời gian chạy giữa hai điểm | khoảng cách chia vận tốc 40 km/h, đổi ra phút |
| Phạt sớm/muộn | hệ số tính theo CNY/giờ, nên số phút sớm hoặc muộn phải chia 60 |
| Xe đến sớm | xe chờ đến đầu khung kỳ vọng rồi mới phục vụ, thời gian chờ bị phạt ở F4 |
| Cắt hoán vị thành tuyến | khoá `split_rule` trong config. Mặc định `capacity_time`: mở xe mới khi xe đầy hàng, hoặc khi xe sẽ đến khách sau hết khung chấp nhận được mà đội xe còn xe trống. `capacity` (chỉ cắt khi đầy hàng) giữ lại để so sánh: với Solomon nó luôn cho cùng một số xe, nên thuật toán không thể thêm xe để kịp giờ |
| Tải trọng xe Solomon | 400 kg theo bài báo |
| Thời điểm tính mức hài lòng | làm cả hai cách, chọn bằng khoá `satisfaction_time` trong config: `arrival` tính theo giờ đến (mặc định), `service_start` tính theo giờ bắt đầu phục vụ. Hai cách chỉ khác nhau ở f3 |
| Giờ xe rời kho | lúc kho mở cửa: phút 0 với Solomon, 6:00 với case thực tế |
| Hai khung giờ cho Solomon | khung trong file là khung kỳ vọng. Khung chấp nhận được là khung đó nới thêm 30 phút mỗi đầu, không xuống dưới 0 |
| Hai khung giờ cho case thực tế | bài báo chỉ cho một khung, nhóm dùng nó cho cả hai. Giao trong khung thì hài lòng 100%, ngoài khung thì 0% |
| Xác suất đột biến | 0.1 cho benchmark, 0.2 cho case thực tế |

Hai giả định về giờ rời kho và khung giờ của case thực tế dựa trên kết quả bài báo: họ báo mức hài
lòng tối đa 1.0000, chỉ đạt được nếu xe xuất phát lúc 6:00 và mọi khách được giao trong khung.

### Cách cắt hoán vị thành tuyến (`split_rule`), chốt 12/11

**Bối cảnh.** Mỗi lời giải được mã hoá bằng một hoán vị khách, ví dụ `[5, 2, 8, 1, ...]`. Decoder
phải cắt hoán vị đó thành các tuyến, mỗi tuyến là một xe. Bài báo không nói cách cắt.

**Vấn đề của cách cắt đơn giản nhất.** Cách đơn giản nhất là đi dọc hoán vị, cộng dồn hàng, xe đầy
thì mở xe mới (`split_rule: capacity`). Với Solomon, mỗi khách chỉ cần 10–40 kg trong khi xe chở được
400 kg, nên **hoán vị nào cũng ra cùng một số xe**. Thử 200 hoán vị ngẫu nhiên: C102-25 luôn ra 2 xe,
R201-25 luôn ra 1 xe, C102-100 luôn ra 5 xe. Thuật toán chỉ đổi được thứ tự ghé, không bao giờ thử
được phương án "thêm một xe để kịp giờ". Hai xe phục vụ 25 khách C102 (mỗi khách mất 90 phút dỡ
hàng) thì đến muộn hàng nghìn phút là không tránh được.

**Cách nhóm chọn: `split_rule: capacity_time` (mặc định).** Đi dọc hoán vị, mở xe mới khi:

1. thêm khách tiếp theo sẽ làm xe vượt tải. Điều kiện này luôn bắt buộc, vì tải trọng là ràng buộc
   cứng; hoặc
2. xe sẽ đến khách tiếp theo **sau LT** (hết khung chấp nhận được), **và** đội xe vẫn còn xe trống.

Khi cắt, xe mới xuất phát từ kho lúc kho mở cửa.

**Vì sao mốc là LT chứ không phải LTb.** `[ET, LT]` theo định nghĩa là giới hạn chấp nhận được. Nếu
cắt theo LTb thì xe không bao giờ đến muộn, và mất đánh đổi "muộn một chút để đỡ tốn một xe". Thử
nghiệm cho thấy cắt theo LT dùng ít xe hơn, chi phí thấp hơn, mức hài lòng tương đương.

**Hiệu quả.** Cùng một hoán vị ngẫu nhiên trên C102-25 (seed 0):

| | Số xe | f1 (chi phí) | f2 (khí thải) | f3 (hài lòng) | Phút đến muộn |
|---|---|---|---|---|---|
| `capacity` | 2 | 25658 | 355 | 0.12 | 22914 |
| `capacity_time` | 11 | 5022 | 515 | 0.36 | 0 |

Thêm xe làm chi phí giảm 5 lần và hài lòng tăng gấp 3, vì mỗi xe chỉ tốn 100 CNY trong khi phạt
muộn là 60 CNY mỗi giờ. Đổi lại, khí thải tăng vì nhiều xe đi nhiều km hơn. Đây là đánh đổi giữa các
mục tiêu mà cách cắt cũ không bao giờ thấy được.

**Lưu ý khi sửa code.** Hàm `split_capacity_time` tự tính giờ đến để quyết định chỗ cắt. Cách tính
phải **giống hệt** `evaluate_routes_detail` (chờ tới đầu khung kỳ vọng, cộng thời gian dỡ hàng). Sửa
cách tính giờ ở một chỗ thì phải sửa cả chỗ kia.

`capacity` vẫn giữ lại để đưa vào báo cáo như một phép so sánh.

### Thời điểm tính mức hài lòng (`satisfaction_time`), chốt 12/11

**Bối cảnh.** Xe đến sớm thì đứng chờ tới đầu khung kỳ vọng rồi mới dỡ hàng, và thời gian chờ bị phạt
ở F4. Câu hỏi là mức hài lòng W của khách tính tại lúc xe **đến**, hay lúc **bắt đầu dỡ hàng**. Bài
báo không nói rõ.

| | `arrival` (mặc định) | `service_start` |
|---|---|---|
| W tính tại | giờ xe đến | giờ bắt đầu dỡ hàng = max(giờ đến, ETa) |
| Đến sớm bị trừ hài lòng? | có | không |
| Đến sớm bị phạt ở | F4 và f3 | chỉ F4 |
| Cách hiểu | khách khó chịu khi xe tới sớm, đỗ chờ trước cửa | khách chỉ quan tâm lúc nhận hàng |

Hai cách cho cùng tuyến, cùng giờ đến, cùng f1 và f2. **Chỉ f3 khác.** Ví dụ khách 17 trong Table 11:
xe đến lúc 6:13, khung giờ 8:00–12:00, chờ 107 phút. Theo `arrival` thì W = 0; theo `service_start`
thì W = 100. Trên ba lời giải mẫu của bài báo:

| | f3 theo `arrival` | f3 theo `service_start` |
|---|---|---|
| Table 11 | 0.8276 | 1.0000 |
| Table 12 | 0.7586 | 1.0000 |
| Table 13 | 0.7931 | 1.0000 |

**Vì sao làm cả hai.** Mỗi cách có một rủi ro:

- `arrival` tính việc đến sớm hai lần: một lần là chi phí chờ của công ty (F4), một lần là sự không
  hài lòng của khách (f3).
- `service_start` làm f3 chỉ còn đo việc đến muộn. Trên case thực tế, f3 có thể gần như luôn bằng 1.0.
  Cộng với việc f2 tỉ lệ thuận với quãng đường (lỗi số 2 ở trên), bài toán ba mục tiêu gần như chỉ còn
  một chiều.

Giai đoạn 1 chạy NSGA-II baseline với cả hai giá trị, so front Pareto và hệ số tương quan giữa ba mục
tiêu, rồi đưa kết quả vào báo cáo. **Kết quả hai cách phải lưu ở hai thư mục riêng**, không trộn.

### Những điểm mô hình chưa xử lý

- **Số xe tối đa** (`fleet_size`): decoder chỉ báo ra qua `fleet_ok`. NSGA-II xử lý bằng constrained
  domination (xem mục "NSGA-II baseline" bên dưới). Với hoán vị ngẫu nhiên, Solomon 100 khách thường
  cần 26–27 xe, vượt giới hạn 25 xe, vì với v = 40 km/h một đơn vị toạ độ Solomon mất 1.5 phút thay vì
  1 phút như thiết kế gốc, và nhóm C1 có thời gian dỡ hàng 90 phút mỗi khách. Sau 200 thế hệ, NSGA-II
  tìm được lời giải không vượt 25 xe (chạy thử C102-100, seed 0).
- **Giờ đóng cửa kho** chưa được mô hình hoá: xe về kho muộn không bị phạt. Với case thực tế thì chưa
  ảnh hưởng (các lời giải mẫu đều về trước 12:00).
- **Case thực tế** chưa có giới hạn số xe (`case29.fleet_size: null`).

## NSGA-II baseline

Code ở `src/nsga2.py`, test ở `tests/test_nsga2.py`. Các lựa chọn dưới đây chọn theo lý do kỹ thuật,
không theo bài báo. Chỗ nào chưa chắc thì để chọn được trong config và sẽ so bằng thực nghiệm.

| Thành phần | Nhóm dùng | Bài báo | Lý do |
|---|---|---|---|
| Mã hoá | hoán vị khách, decoder cắt tuyến theo `split_rule` | hoán vị có số 0 làm dấu ngăn tuyến | lai ghép và đột biến đơn giản, luôn ra lời giải hợp lệ; số xe do decoder quyết định |
| Mục tiêu bên trong | (f1, f2, 1 - f3), cả ba cực tiểu | | để so trội cùng một chiều |
| Khởi tạo | hoán vị ngẫu nhiên | ngẫu nhiên | khởi tạo thông minh là cải tiến `init_smart` |
| Chọn lọc cha mẹ | giải đấu `tournament_size` = 2: hạng thấp hơn thắng, cùng hạng thì crowding lớn hơn thắng | giống, không ghi kích thước | NSGA-II chuẩn |
| Lai ghép | `crossover: ox` mặc định, `obx` để so | OBX | OX giữ nguyên một đoạn liền của cha 1, tức giữ được các cụm khách đi liền nhau. OBX giữ vị trí tuyệt đối, ít giữ cặp khách liền kề |
| Đột biến | `mutation: standard`: với xác suất pm, inversion hoặc swap 50/50. `always` để so | inversion ba điểm hoặc swap | inversion giống một bước 2-opt, chỉ phá 2 cạnh; swap phá 4 cạnh |
| Số xe tối đa | constrained domination: lời giải vượt ít xe hơn luôn thắng; vượt bằng nhau thì so Pareto | ràng buộc cứng (23) | cách xử lý ràng buộc chuẩn của NSGA-II, không cần chọn hệ số phạt |
| Chọn lọc môi trường | gộp cha mẹ và con, lấy theo front, front cuối lấy theo crowding | | NSGA-II chuẩn |
| Ngẫu nhiên | một bộ sinh `np.random.default_rng(seed)` cho mọi thứ | | cùng seed ra đúng cùng kết quả |

**Về hai chỗ bài báo viết không rõ ở phần đột biến:**

- Bài báo viết: mỗi cá thể bốc số ngẫu nhiên; nhỏ hơn Pm thì inversion, **lớn hơn hoặc bằng Pm thì
  swap**. Đọc đúng chữ thì đứa con nào cũng bị đột biến. Đây là chế độ `mutation: always`.
- "Inversion ba điểm" trong Hình 4a không khớp với phép đảo đoạn thông thường. Nhóm dùng phép đảo đoạn
  thông thường ở cả hai chế độ.

**Chạy thử** (200 thế hệ, 80 cá thể, seed 0, cấu hình mặc định):

| Instance | Thời gian | f1 nhỏ nhất: thế hệ 0 → cuối | f2 nhỏ nhất | f3 lớn nhất |
|---|---|---|---|---|
| C102-25 | 2 giây | 3607 → 1707 | 409.7 → 240.9 | 0.543 → 0.952 |
| case29 | 2 giây | 2834 → 2375 | 288.5 → 219.3 | 0.759 → 0.862 |
| C102-100 | 6 giây | 67073 → 16857 | 2835.7 → 1952.9 | 0.343 → 0.605 |

Đây mới là một seed, chưa phải kết quả để báo cáo.

## Bốn cải tiến

| Cải tiến | Ý tưởng | Tác động vào |
|---|---|---|
| Khởi tạo thông minh | trộn nearest-neighbor, sắp theo khung giờ và ngẫu nhiên | quần thể ban đầu |
| Local search | 2-opt và Or-opt trên từng tuyến | sau đột biến |
| Cơ chế đa dạng | SDE hoặc kNN density thay crowding distance, thêm external archive | bước chọn lọc |
| DP split | cắt tuyến tối ưu bằng quy hoạch động, Pc/Pm thích nghi | decoder và toán tử |

Mỗi cải tiến bật tắt bằng một cờ trong `config.yaml` và mặc định tắt. Tắt hết cờ thì chương trình
phải cho đúng kết quả của NSGA-II gốc với cùng seed, để tách được đóng góp của từng cải tiến.

## Quy ước làm việc

- Mỗi người làm trên một branch riêng, không commit thẳng vào `main`.
- Mọi tham số nằm trong `config.yaml`, không viết cứng số vào code.
- Sửa gì liên quan đến decoder thì chạy `pytest tests/test_decoder.py` trước khi push.
- Báo kết quả luôn dựa trên 10 run, kèm trung bình và độ lệch chuẩn. Khi so hai cấu hình thì dùng
  cùng bộ seed và kiểm định Wilcoxon rank-sum.
