# MOGVRPTW giải bằng NSGA-II

Bài tập lớn môn Tính toán tiến hóa, nhóm 4 người, hạn 30/11/2026.

Bài báo gốc: Li, X.; Gao, C.; Wang, J.; Tang, H.; Ma, T.; Yuan, F. *Research on Multi-Objective
Green Vehicle Routing Problem with Time Windows Based on the Improved Non-Dominated Sorting
Genetic Algorithm III*. Symmetry 2025, 17, 734. Họ dùng NSGA-III, **nhóm này dùng NSGA-II**
cộng bốn cải tiến, rồi so kết quả với cả cột NSGA-II lẫn cột INSGA-III của họ.

---

## 0. Đọc trước khi viết dòng code đầu tiên

Ba điều quan trọng nhất trong file này:

1. **Mục 3** liệt kê bốn chỗ sai trong bài báo. Code theo đúng công thức in trong bài báo sẽ
   cho `f2` âm. Phải áp các chỉnh sửa ở mục 3.
2. **Mục 6** là cổng kiểm tra. Decoder phải tái tạo được số mà bài báo công bố trước khi viết
   NSGA-II. Dữ liệu kiểm tra đã verify sẵn, nằm trong phụ lục B.
3. **Mục 4** là những chỗ bài báo nói không rõ và nhóm phải tự chốt. Nếu số không khớp ở mục 6,
   đây là chỗ đầu tiên cần thử cách hiểu khác.

---

## 1. Bài toán

Một kho, đội xe tải đồng nhất, `n` khách trong thành phố. Mỗi khách biết trước toạ độ, nhu cầu,
thời gian dỡ hàng, và khung giờ muốn nhận. Mỗi xe đi một vòng từ kho, ghé một số khách, về kho.
Cần chia khách cho xe và sắp thứ tự ghé.

Tối ưu đồng thời ba mục tiêu đối nhau, nên đầu ra là **tập Pareto** chứ không phải một lời giải.

| Mục tiêu | Nội dung | Chiều |
|---|---|---|
| `f1` | Chi phí giao hàng | min |
| `f2` | Khí thải carbon | min |
| `f3` | Hài lòng khách hàng trung bình | max |

Trong code, đổi `f3` thành `1 - f3` để cả ba cùng chiều min. Chỉ đổi lại khi xuất báo cáo.

---

## 2. Mô hình toán học

### Ký hiệu

| Ký hiệu | Nghĩa |
|---|---|
| `c[i][j]` | khoảng cách Euclid giữa i và j |
| `v` | vận tốc, hằng số 40 km/h |
| `d[i]` | nhu cầu của khách i |
| `d[i][j][k]` | lượng hàng còn trên xe k khi đi chặng (i, j) |
| `R` | tải trọng xe |
| `s[i]` | thời gian dỡ hàng tại i |
| `t[i][k]` | giờ xe k đến khách i |
| `[ET, LT]` | khung giờ quy định (giới hạn chấp nhận được) |
| `[ETa, LTb]` | khung giờ kỳ vọng, nằm trong khung quy định |
| `x[i][j][k]` | 1 nếu xe k đi thẳng i sang j |
| `y[i][k]` | 1 nếu khách i do xe k phục vụ |

### f1, chi phí giao hàng

```
f1 = F1 + F2 + F3 + F4

F1 = s1 * SUM_ijk  c[i][j] * x[i][j][k] * ( rho0 + (rho_star - rho0) / R * d[i][j][k] )
F2 = s2 * SUM_jk   x[0][j][k]
F3 = s3 * SUM_ijk  c[i][j] * x[i][j][k]
F4 = alpha * SUM_i max(ETa[i] - t[i][k], 0) + beta * SUM_i max(t[i][k] - LTb[i], 0)
```

`F1` là chỗ duy nhất mà **thứ tự ghé ảnh hưởng chi phí** ngoài quãng đường: xe chở nặng tốn xăng
hơn, nên giao khách lấy nhiều hàng trước thì rẻ hơn. Đừng rút gọn `F1` thành hằng số nhân quãng
đường.

### f2, khí thải carbon (mô hình MEET)

```
phi(v) = 110 + 0.000375 * v**3 + 8702 / v
psi(v) = 1.27 + 0.0614 * v - 0.0011 * v**2 - 1.33235 / v     # v**2, KHÔNG phải v**3, xem mục 3.1

f2 = SUM_ijk  phi(v) * psi(v) * (c[i][j] / 1000) * x[i][j][k]
```

Thành phần hiệu chỉnh độ dốc `r(v)` bỏ qua, coi đường đô thị bằng phẳng.

### f3, hài lòng trung bình

```
W(t) = 100 * (t - ET) / (ETa - ET)      neu ET  <= t <  ETa
       100                              neu ETa <= t <= LTb
       100 * (LT - t) / (LT - LTb)      neu LTb <  t <= LT
       0                                neu t < ET hoac t > LT

f3 = (1/n) * SUM_i  W(t[i][k]) / 100      # thang 0-1, mot dau SUM, xem muc 3.3
```

### Ràng buộc

| Mã | Nội dung | Cách xử lý trong code |
|---|---|---|
| C1, C2 | mỗi khách ghé đúng một lần, bởi đúng một xe | tự động thoả nhờ mã hoá permutation |
| C3 | tổng hàng một tuyến không vượt R | tự động thoả nhờ split |
| C4 | bảo toàn hàng hoá, giao đủ | tự động thoả |
| C5 | số xe rời kho = số xe về kho, không vượt đội xe m | kiểm tra sau split |
| C6 | `t[j] = t[i] + s[i] + c[i][j] / v` | decoder tính tuần tự dọc tuyến |
| C7 | x, y nhị phân | tự nhiên từ biểu diễn |

**Khung thời gian là ràng buộc mềm.** Giao ngoài giờ không làm lời giải bất khả thi, chỉ bị phạt
qua `F4` và trừ điểm qua `f3`. Không cần cơ chế sửa chữa lời giải.

### Tham số (Table 2 của bài báo)

```yaml
sigma1: 10        # CNY/L, gia nhien lieu
sigma2: 100       # CNY/xe, chi phi co dinh moi xe
sigma3: 2         # CNY/km, chi phi theo quang duong
rho0: 0.122       # L/km, suat tieu thu khi xe rong
rho_star: 0.388   # L/km, suat tieu thu khi xe day
alpha: 20         # CNY/h, phat den som
beta: 60          # CNY/h, phat den muon
v: 40             # km/h
R: 400            # kg cho benchmark Solomon, 4000 kg cho case thuc te
```

Tham số thuật toán: `nPop = 80`, `Pc = 0.7`, `Pm = 0.1`, 200 generation, 10 run độc lập mỗi cấu hình.

Để hết trong `config.yaml`. Không hardcode số nào trong code.

---

## 3. Bốn lỗi trong bài báo

Phải áp các chỉnh sửa này. Mỗi cái cũng là một mục trong báo cáo.

### 3.1. Công thức (12) sai bậc, làm f2 âm

Bài báo in `psi(v) = 1.27 + 0.0614*v - 0.0011*v**3 - 1.33235/v`.

Thay `v = 40`: `0.0011 * 64000 = 70.4`, nên `psi(40) = 1.27 + 2.456 - 70.4 - 0.033 = -66.7`. Âm,
tức là xe chạy càng nhiều thì hút CO2 về.

**Sửa: đổi `v**3` thành `v**2`.** Khi đó `psi(40) = 1.933` và `phi(40) * psi(40) = 680 g/km`.
Kiểm chứng ngược: bài báo báo `f2 = 257 kg` trên C102 25 khách, ứng với khoảng 380 km tổng quãng
đường, hợp lý với 25 khách. Vậy `v**2` đúng.

### 3.2. psi(v) không chứa biến tải trọng, nên f2 trùng với F3

Đây là lỗi nặng nhất về mặt mô hình. `psi(v)` được bài báo gọi là "load correction function"
nhưng công thức chỉ phụ thuộc `v`, không có biến tải trọng nào. Cộng với giả định vận tốc hằng số:

```
f2 = hang_so * tong_quang_duong
F3 = sigma3 * tong_quang_duong
```

Hai thứ tỉ lệ tuyệt đối. Bài toán mang tiếng ba mục tiêu nhưng chỉ có **hai chiều độc lập**, và
Pareto front 3D sẽ bị dẹt.

**Xử lý, hai phương án:**

- **A, bắt buộc.** Giữ nguyên mô hình để còn so số với bài báo, nhưng đo hệ số tương quan Pearson
  giữa `f1`, `f2`, `f3` trên toàn bộ front và báo cáo con số đó. Làm ở giai đoạn 1.
- **B, làm thêm nếu kịp.** Cho `v[i][j]` khác nhau theo cung (sinh theo loại đường hoặc khung giờ
  cao điểm), khi đó `phi(v)*psi(v)` phi tuyến thật và `f2` tách khỏi quãng đường. Chạy như một thí
  nghiệm riêng, không thay thế A. Làm ở giai đoạn 4.

### 3.3. Công thức (15) thừa một dấu tổng

Bài báo viết `f3 = (1/n) * SUM_i SUM_k W(t[i][k])`. Tổng theo cả i và k, nhưng mỗi khách chỉ được
một xe phục vụ (C2) nên tổng theo k là thừa. Thêm nữa (14) trả giá trị thang 0–100 nhưng bảng kết
quả report `f3 = 0.9152`, tức thang 0–1.

**Sửa: bỏ tổng theo k, chia 100 để về thang 0–1.**

### 3.4. R không nhất quán

Bài báo ghi `R = 400 kg` ở phần benchmark, `R = 4000 kg` ở case thực tế, mô tả xe là "tải trọng
3.5 tấn", còn capacity gốc của Solomon C1 là 200.

**Dùng đúng 400 kg cho benchmark như bài báo ghi, nhưng kiểm tra ngay ở giai đoạn 1**: tính tổng
demand chia cho 400 ra số xe tối thiểu, so với số xe bài báo dùng. Lệch quá lớn thì chuyển sang
capacity gốc Solomon và ghi rõ lý do trong báo cáo.

Với case thực tế 29 điểm thì `R = 4000 kg` đã kiểm tra là hợp lý: tổng demand 31.32 tấn, cần tối
thiểu 8 xe, bài báo dùng 9 đến 10 xe. Khớp.

---

## 4. Những chỗ bài báo không nói rõ, nhóm tự chốt

Ghi hết vào báo cáo như giả định của nhóm.

### 4.1. Xe đến sớm thì chờ hay giao luôn?

Bài báo gọi phạt đến sớm là "waiting cost", nên hiểu là xe chờ.

**Chốt: xe chờ đến `ETa[i]` rồi mới phục vụ.** Phí chờ `alpha * thoi_gian_cho`. Thời điểm dùng để
tính hài lòng `W` là **giờ đến**, không phải giờ bắt đầu phục vụ.

Nếu validate ở mục 6 không khớp, đây là chỗ đầu tiên thử cách hiểu ngược lại.

### 4.2. Đơn vị

Toạ độ Solomon không có đơn vị, quy ước coi là km. Thời gian Solomon coi là phút, nhưng `alpha` và
`beta` tính theo giờ nên **nhớ đổi đơn vị khi tính F4**. Đây là chỗ rất dễ sai và sai thì `F4` lệch
60 lần.

Trong `f2`, công thức chia `c[i][j]` cho 1000, hàm ý khoảng cách tính bằng mét. Nhưng ở case thực
tế toạ độ rõ ràng là km (route dài 11 đến 75 km). Giữ nguyên hệ số `/1000` như bài báo để khớp số
của họ, và ghi chú lại chỗ bất nhất này.

### 4.3. Xe xuất phát lúc mấy giờ?

Chốt: xe rời kho tại thời điểm mở cửa kho (`ET[0]`, với case thực tế là 6:00). Không tối ưu giờ
xuất phát.

---

## 5. Dữ liệu

### Solomon benchmark

Đọc bằng `vrplib`, không tự viết parser:

```bash
pip install vrplib
```

```python
import vrplib
inst = vrplib.read_instance("C102.txt", instance_format="solomon")
# tra ve dict: node_coord, demand, time_window, service_time, edge_weight
```

Tải bộ instance, có sẵn ba bản theo quy mô:

```
https://neo.lcc.uma.es/vrp/wp-content/data/instances/solomon/solomon_25.zip
https://neo.lcc.uma.es/vrp/wp-content/data/instances/solomon/solomon_50.zip
https://neo.lcc.uma.es/vrp/wp-content/data/instances/solomon/solomon_100.zip
```

Bản 25 và 50 khách chính là 25 hoặc 50 khách đầu của bản 100.

**Chín instance phải dùng, lấy theo bài báo, không tự chọn:**

| Quy mô | Instance |
|---|---|
| 25 khách | C102, R201, RC202 |
| 50 khách | C102, R201, RC202 |
| 100 khách | C102, R201, **RC201** |

Ở mức 100 khách bài báo đổi sang RC201. Đó không phải lỗi gõ của mình, giữ nguyên.

### Sinh hai khung giờ

Solomon chỉ có một khung giờ mỗi khách, bài toán cần hai khung lồng nhau:

```
[ETa, LTb] = khung goc trong file                    # khung ky vong
[ET,  LT ] = [max(0, ETa - 30), LTb + 30]            # khung quy dinh, noi 30 phut moi dau
```

Nhớ clamp cận dưới về 0.

### Case thực tế

29 điểm, dữ liệu đầy đủ trong phụ lục A. Khoảng cách là Euclid trên toạ độ thô, đã verify.

---

## 6. Cổng kiểm tra: validate decoder

**Chưa qua cổng này thì không được viết NSGA-II.** Mọi thứ xây trên decoder sai đều vô nghĩa, và
sai kiểu này không tự lộ ra, thuật toán vẫn chạy và vẫn in ra số đẹp.

### Quy ước khoảng cách, đã xác nhận

Euclid thường trên toạ độ thô, không scale, không làm tròn:

```python
dist = math.hypot(x[i] - x[j], y[i] - y[j])
```

Đã kiểm chứng trên 28 tuyến của bài báo, khớp tới 4 chữ số thập phân.

### Bước 1, kiểm tra độ dài tuyến

Nạp case 29 điểm (phụ lục A), nạp ba bộ tuyến (phụ lục B), tính độ dài từng tuyến, so với cột
"Route Length (km)".

Bước này chỉ đụng đến toạ độ và thứ tự, chưa đụng thời gian hay chi phí, nên nếu sai thì khoanh
vùng được ngay.

Mức đạt: sai số dưới 0.1%. Dữ liệu trong phụ lục B đã verify sẵn, đạt mức này.

### Bước 2, kiểm tra ba hàm mục tiêu

Tính `f1`, `f2`, `f3` của ba bộ tuyến đó, so với Table 10 của bài báo:

| Chỉ tiêu | Giá trị bài báo |
|---|---|
| `min f1` | 2262 |
| `min f2` | 140.65 |
| `max f3` | 1.0000 |

Dùng `R = 4000 kg` cho case này.

### Đọc kết quả lệch thế nào

| Triệu chứng | Nguyên nhân khả dĩ |
|---|---|
| mọi tuyến lệch cùng một hệ số | sai đơn vị hoặc sai scale toạ độ |
| lệch ngẫu nhiên từng tuyến | gõ sai toạ độ hoặc sai thứ tự khách |
| độ dài khớp nhưng `f1` lệch | sai công thức chi phí, hoặc sai mô hình tải trọng trong F1 |
| `f1` lệch đúng 60 lần ở phần phạt | quên đổi phút sang giờ trong F4 (mục 4.2) |
| độ dài khớp nhưng `f3` lệch | sai chỗ xe chờ hay không chờ (mục 4.1), hoặc sai cách sinh hai khung giờ |
| `f2` âm | chưa áp chỉnh sửa mục 3.1 |

### Lỗi gõ trong Table 11 của bài báo, đã sửa sẵn

Table 11 in tuyến 7 là `0-13-9-27-0` với độ dài 50.8931. Tính ra chỉ 46.0878, lệch 9.4%. Ngoài ra
khách 27 xuất hiện hai lần trong bảng còn khách 29 không xuất hiện lần nào.

Thử thay vào thì `0-13-9-29-0` cho đúng **50.8931**. Vậy "27" là lỗi gõ của "29". Phụ lục B đã ghi
bản đã sửa, và sau khi sửa thì cả ba bảng đều phủ đúng 29 khách mỗi khách một lần.

Table 12 và Table 13 không có lỗi nào, dùng được nguyên văn.

---

## 7. Kiến trúc code

Python + numpy. Bài báo dùng MATLAB, không cần theo.

```
.
├── config.yaml              # moi tham so, khong hardcode
├── data/
│   ├── solomon/             # file instance tai ve
│   └── paper/
│       ├── case29.csv       # phu luc A
│       ├── fixture_routes.csv   # phu luc B
│       ├── paper_metrics.csv    # Table 5
│       └── paper_objectives.csv # Table 6, 7, 10
├── src/
│   ├── instance.py          # load_instance, sinh hai khung gio
│   ├── decoder.py           # split, tinh gio den, tinh f1 f2 f3
│   ├── nsga2.py             # sort, crowding, tournament, crossover, mutate, vong lap
│   ├── improvements/        # bon nhanh cai tien, moi nhanh mot file
│   │   ├── init_smart.py
│   │   ├── local_search.py
│   │   ├── diversity.py
│   │   └── dp_split.py
│   ├── metrics.py           # HV, IGD qua pymoo; SP, SC, DM tu viet
│   └── runner.py            # chay batch 10 run, luu ket qua tho
├── tests/
│   └── test_decoder.py      # cong kiem tra muc 6
└── results/                 # ket qua tho, khong commit
```

### Interface phải chốt sớm rồi đóng băng

Sau khi qua cổng mục 6 thì không ai được đổi chữ ký của hai hàm này, nếu không bốn nhánh cải tiến
sẽ không merge được:

```python
def load_instance(name: str, n: int) -> Instance: ...
    # Instance co: coords, demand, service_time, tw_expected, tw_specified, dist, capacity

def evaluate(perm: list[int], inst: Instance) -> tuple[float, float, float]: ...
    # tra ve (f1, f2, f3)

def evaluate_detail(perm: list[int], inst: Instance) -> dict: ...
    # tra ve routes, route_lengths, arrival_times, F1, F2, F3, F4 tach rieng
    # dung de debug o muc 6, dung bo qua
```

### Chỉ số đánh giá

**HV và IGD dùng pymoo, không tự viết:**

```python
from pymoo.indicators.hv import HV
from pymoo.indicators.igd import IGD
```

Lý do không phải tiết kiệm thời gian. HV trong không gian 3 chiều rất dễ viết sai, và sai thì vẫn
ra một con số trông hợp lý nên không ai phát hiện, trong khi toàn bộ phần so sánh của báo cáo dựa
trên nó. SP, SC, DM công thức đơn giản (29, 31, 32 của bài báo), tự viết.

**NSGA-II thì tự viết**, đó là nội dung môn học.

**Reference set** để tính IGD: gộp front của mọi thuật toán qua mọi run trên cùng instance, lọc lấy
phần non-dominated. Phải gộp cả baseline chứ không chỉ bản tốt nhất, nếu không IGD của bản tốt nhất
sẽ gần bằng 0 và vô nghĩa.

**Chuẩn hoá** ba mục tiêu về [0,1] theo min-max của reference set trước khi tính HV. Điểm tham chiếu
`(1.1, 1.1, 1.1)`.

Lưu ý khi so HV với bài báo: họ không ghi cách chuẩn hoá và điểm tham chiếu của họ, nên **số HV
không so trực tiếp được**. Chỉ so thứ hạng và biên độ cải thiện. `f1`, `f2`, `f3` thì so trực tiếp
được.

---

## 8. Lộ trình

| Giai đoạn | Ngày | Nội dung | Cổng |
|---|---|---|---|
| 0 | 31/10 – 1/11 | data loader, decoder, gõ dữ liệu từ bài báo | decoder chạy được |
| 1 | 3/11 – 9/11 | validate decoder, NSGA-II baseline, bộ đo | mục 6 phải PASS; HV baseline trong ±15% cột NSGA-II của bài báo trên ít nhất 6/9 instance |
| 2 | 10/11 – 16/11 | bốn nhánh cải tiến | mỗi nhánh chạy độc lập, có test riêng |
| 3 | 17/11 – 23/11 | merge, ablation, tuning | mỗi cải tiến có một con số delta HV |
| 4 | 24/11 – 30/11 | full experiment, báo cáo, slide | nộp |

### Bốn cải tiến

Ba cái đầu ánh xạ 1-1 với ba cải tiến của INSGA-III trong bài báo, cái thứ tư là của riêng nhóm.
Bốn cái can thiệp vào bốn chỗ khác nhau của vòng lặp nên đo tách được đóng góp từng cái.

| Nhánh | Nội dung | Can thiệp ở đâu |
|---|---|---|
| `init_smart` | greedy nearest-neighbor + TW-aware + random, trộn theo tỉ lệ | khối khởi tạo quần thể |
| `local_search` | 2-opt và Or-opt trên từng tuyến | sau đột biến |
| `diversity` | SDE hoặc kNN density thay crowding distance, cộng external archive | bước chọn lọc |
| `dp_split` | Prins' split bằng quy hoạch động, cộng adaptive Pc/Pm | decoder và toán tử |

**Quy tắc bắt buộc cho cả bốn:** mỗi cải tiến bật tắt được bằng một flag trong config, mặc định
tắt. Tắt hết flag phải ra **đúng** kết quả baseline, kể cả cùng seed. Không có điều kiện này thì
ablation ở giai đoạn 3 không tách được cải tiến khỏi nhiễu ngẫu nhiên.

Hai lưu ý đã biết trước:

- `dp_split` chỉ tối ưu được một mục tiêu mỗi lần gọi. Xử lý bằng cách chọn một mục tiêu ngẫu nhiên
  hoặc tổng có trọng số ngẫu nhiên cho mỗi lần gọi.
- `dp_split` và `local_search` có thể dẫm chân nhau vì cùng tinh chỉnh tuyến. Hai cải tiến tốt riêng
  không đảm bảo tốt khi ghép.

---

## 9. Quy ước làm việc

### Khi sửa code

- Chạy `pytest tests/test_decoder.py` trước khi nói là xong việc gì liên quan đến decoder.
- Không đổi chữ ký của `load_instance`, `evaluate`, `evaluate_detail` sau khi qua cổng mục 6. Nếu
  thấy cần đổi thì hỏi trước.
- Không đổi giá trị nào trong `config.yaml` để làm test pass. Test fail nghĩa là code sai, không
  phải tham số sai.
- Không thêm thư viện ngoài numpy, pandas, pyyaml, pymoo, scipy, matplotlib, vrplib, pytest. Cần
  thêm gì thì hỏi.

### Khi báo cáo kết quả

- Thuật toán tiến hoá có yếu tố ngẫu nhiên. Một lần chạy không nói lên gì. Luôn 10 run và báo trung
  bình kèm độ lệch chuẩn.
- Khi so hai cấu hình, dùng cùng bộ seed.
- Đừng nói "cải tiến X tốt hơn" nếu chưa có p-value. Dùng `scipy.stats.ranksums`.

### Khi bí

- Số không khớp ở mục 6: xem bảng triệu chứng, đừng đoán mò.
- Thấy bài báo mâu thuẫn ở chỗ mới: ghi vào mục 3 của file này, đừng tự chọn cách hiểu rồi quên.
- Thấy một quyết định mô hình không có trong file này: hỏi trước khi chọn, vì nó ảnh hưởng mọi số
  phía sau.

---

## Phụ lục A: case thực tế 29 điểm

Từ Table 8 của bài báo. Điểm 0 là kho. Nhu cầu tính bằng tấn, thời gian phục vụ bằng phút, khung giờ
bằng giờ. `R = 4000 kg`. Tổng nhu cầu 31.32 tấn, tối thiểu 8 xe, bài báo dùng 9 đến 10 xe.

```csv
id,x,y,demand_ton,service_min,tw_start_h,tw_end_h
0,30.956,8.842,0,0,6,12
1,18.692,1.528,1.08,22,7,10
2,22.197,4.345,1.68,25,6,10
3,26.275,5.505,1.5,23,7.5,12
4,12.078,5.638,0.7,14,6,7.5
5,9.72,8.348,0.58,12,7,10
6,8.279,8.691,0.31,6,6,8
7,24.772,8.793,0.8,16,6,9
8,15.096,8.924,0.83,12,6.5,9.5
9,8.991,10.484,0.5,10,8,11
10,18.086,11.073,0.98,20,8,10
11,9.182,14.126,0.5,10,7,11
12,17.378,23.541,0.87,17,7,10
13,20.219,14.498,1.45,22,8,11
14,11.988,12.037,0.65,13,7,11
15,20.771,9.748,1.6,24,6,8.5
16,23.793,8.079,2.21,33,6,9
17,22.388,11.148,1.75,26,8,12
18,24.273,6.217,2.3,35,6,9
19,20.904,6.195,1.63,24,7,11
20,17.467,18.673,0.9,14,7,11
21,8.738,18.799,0.43,9,8,11
22,18.621,8.057,1.05,21,6,9
23,3.311,9.515,1.63,24,7,11
24,7.661,23.979,0.25,5,7.5,11
25,14.63,12.356,0.76,15,7,11
26,15.677,22.054,0.83,12,7,10
27,19.378,9.56,1.1,22,6,9.5
28,19.745,7.877,1.2,24,6.5,9.5
29,20.008,1.984,1.25,19,8,11
```

Khung giờ trong bảng này là khung **quy định**. Khung kỳ vọng sinh thế nào thì bài báo không nói rõ
cho case thực tế (quy tắc nới 30 phút là dành cho Solomon). Đây là một chỗ phải tự chốt, ghi vào
mục 4 khi quyết định.

## Phụ lục B: ba bộ tuyến dùng làm fixture

Từ Tables 11, 12, 13. Tuyến 7 của Table 11 đã sửa lỗi gõ `27` thành `29` (xem mục 6). Cả ba bộ đều
đã verify: phủ đúng 29 khách mỗi khách một lần, không tuyến nào vượt 4000 kg, độ dài khớp số bài báo
với sai số lớn nhất 0.024%.

```csv
table,scenario,route_id,sequence,length_km
11,min_f1,1,16-15,20.8810
11,min_f1,2,7-4-6-28,46.8854
11,min_f1,3,20-26-12-11-24-21,74.8665
11,min_f1,4,25-19-3,36.6570
11,min_f1,5,27-22-8,32.7749
11,min_f1,6,17-10,26.2375
11,min_f1,7,13-9-29,50.8931
11,min_f1,8,18-2,19.8214
11,min_f1,9,1-5-23-14,60.3349
12,min_f2,1,18-2,19.8214
12,min_f2,2,7-1-5-29,51.9434
12,min_f2,3,20-12-26-24-21-9,67.6993
12,min_f2,4,16-19,21.0472
12,min_f2,5,15-17,21.2370
12,min_f2,6,22-4-8-28,39.8151
12,min_f2,7,11-25-10-13,47.9913
12,min_f2,8,3,11.4974
12,min_f2,9,27-6-23-14,56.0404
13,max_f3,1,20-25-23-11,65.1575
13,max_f3,2,3,11.4974
13,max_f3,3,7-27-6-28,45.5127
13,max_f3,4,19-5-14-1,52.8591
13,max_f3,5,17-29,31.2595
13,max_f3,6,13-10-21-9,58.6432
13,max_f3,7,18-2,19.8214
13,max_f3,8,15-4-8,40.1627
13,max_f3,9,16-22,24.7295
13,max_f3,10,26-12-24,59.9664
```

Mỗi `sequence` là danh sách khách giữa kho và kho, tức tuyến đầy đủ là `0 -> sequence -> 0`.

Tổng độ dài: Table 11 là 369.35 km, Table 12 là 337.09 km, Table 13 là 409.61 km. Thứ tự này hợp lý:
bộ tối ưu khí thải đi ít km nhất, bộ tối ưu hài lòng đi nhiều km nhất vì phải dùng thêm một xe để
kịp giờ.
