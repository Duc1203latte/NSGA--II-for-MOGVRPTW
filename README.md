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

## Bài toán

Một kho, một đội xe tải giống nhau, n khách. Mỗi khách có toạ độ, lượng hàng cần giao, thời gian dỡ
hàng và khung giờ muốn nhận. Cần quyết định xe nào phục vụ khách nào và ghé theo thứ tự nào, sao
cho đồng thời:

- **chi phí giao hàng** thấp nhất (nhiên liệu, chi phí cố định mỗi xe, chi phí theo km, phạt sai giờ),
- **khí thải CO₂** thấp nhất,
- **mức hài lòng trung bình** của khách cao nhất.

Ba mục tiêu này xung đột nhau nên đầu ra không phải một lời giải mà là một tập Pareto.

Công thức chi tiết, các lỗi trong bài báo mà nhóm đã sửa và các giả định nhóm tự chốt nằm trong
[CLAUDE.md](CLAUDE.md). Đọc file đó trước khi sửa decoder.

## Tiến độ

| Giai đoạn | Thời gian | Nội dung | Trạng thái |
|---|---|---|---|
| 0 | 3/11 – 4/11 | Cấu trúc repo, môi trường, dữ liệu, data loader, decoder | đang làm |
| 1 | 5/11 – 11/11 | Validate decoder với số liệu bài báo, NSGA-II baseline, bộ đo | |
| 2 | 12/11 – 18/11 | Bốn nhánh cải tiến | |
| 3 | 19/11 – 25/11 | Merge, ablation, tuning | |
| 4 | 26/11 – 2/12 | Chạy đầy đủ, báo cáo, slide | |

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

**Case thực tế.** 29 điểm giao hàng của một công ty logistics, lấy từ Table 8 của bài báo.

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
