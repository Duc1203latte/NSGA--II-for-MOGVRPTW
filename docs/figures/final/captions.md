# Chú thích hình giai đoạn 4

Vẽ bằng `python -m scripts.plot_final` (cần kết quả `final_g200`, `final_g1000`, `abl5_g200`, `abl5_g1000`).
Màu đi theo đối tượng ở mọi hình: xanh dương = NSGA-II gốc, cam = I+D+P (cấu hình cuối), xanh lục =
I+L+D+P (tham khảo), tím = số của bài báo.

## Trực quan bài toán

**f01_case29_map.** Case thực tế: kho (ô vuông đen) nằm ở rìa phải, 29 khách rải về phía tây. Kích thước
điểm tỉ lệ với nhu cầu. Tổng nhu cầu 31.3 tấn, xe chở 4 tấn, nên cần ít nhất 8 xe.

**f02_satisfaction.** Hai thành phần phụ thuộc giờ đến của một khách Solomon (khung [882, 912, 967, 997]
phút). Trên: mức hài lòng W(t) hình thang, bằng 100 trong khung kỳ vọng [ETa, LTb], giảm tuyến tính về 0
ở ET và LT. Dưới: tiền phạt F4. Đến sớm thì xe chờ tới ETa, phạt α = 20 CNY mỗi giờ chờ; đến muộn sau
LTb phạt β = 60 CNY mỗi giờ. Hai đường này cho thấy f1 (qua F4) và f3 cùng phạt việc lệch giờ, nhưng theo
hai cách khác nhau (f3 về 0 sau LT, F4 tăng mãi).

**f03_algorithm.** Vòng lặp NSGA-II của nhóm. Ba ô viền cam là ba cải tiến được giữ ở cấu hình cuối:
I (khởi tạo thông minh), D (mật độ SDE trong chọn lọc), P (polish bằng quy hoạch động sau thế hệ cuối).

**f04_routes_case29.** Ba lời giải đầu mút trên front của I+D+P (gộp 10 seed, 1000 thế hệ). Lời giải chi
phí nhỏ nhất dùng đúng 8 xe (số xe tối thiểu theo tải trọng), vì phí cố định 100 CNY mỗi xe. Lời giải khí
thải nhỏ nhất đi ít km nhất (290 km) nhưng phải thêm một xe. Lời giải hài lòng lớn nhất đi nhiều km nhất
(347 km) để giao đúng giờ nhiều khách hơn. Đây là đánh đổi mà front Pareto thể hiện.

**f05_timeline_case29.** Lời giải hài lòng lớn nhất ở f04: thanh xám là khung giờ của từng khách, chấm là
giờ xe đến. 27/29 khách được giao trong khung; khách 17 và khách 3 bị đến sớm trước ET (xe rời kho 6:00,
khung của họ mở lúc 8:00 và 7:30), nên W = 0 với hai khách này và f3 = 27/29 = 0.931. Không xe nào đến muộn.
Hình này giải thích vì sao f3 của nhóm không đạt 1.000 như bài báo: nhóm tính hài lòng tại giờ xe đến
(`arrival`), nên đến sớm cũng bị trừ điểm.

## Kết quả

**f06_pareto_2d, f07_pareto_3d.** Front cuối của run có HV trung vị (không chọn run đẹp nhất), 200 thế hệ,
trên C102-100, RC201-100 và case29. Hàng trên: chi phí so với hài lòng (tốt ở góc trên trái). Hàng dưới: chi
phí so với khí thải (tốt ở góc dưới trái). Ở 100 khách, front của I+D+P nằm hẳn về phía tốt hơn baseline
ở cả hai mặt chiếu và trải rộng hơn nhiều. Trên case29 hai front gần nhau hơn, đúng với bảng HV.

**f08_convergence.** HV trung bình 10 seed theo thế hệ, 1000 thế hệ. Đường cam lên nhanh ngay từ đầu (nhờ
khởi tạo thông minh). Số thế hệ I+D+P cần để bằng HV của baseline chạy đủ 1000 thế hệ: C102-100 15, C102-25
59, C102-50 85, RC201-100 203, RC202-50 214, R201-100 353, R201-50 457, case29 493; tức tiết kiệm 2–67 lần
số thế hệ (tính trên đường cong trước polish). Đường cong
là front **trước** bước polish (polish chỉ chạy sau thế hệ cuối), nên ở R201-25 và RC202-25 đường cam cuối
cùng hơi thấp hơn đường xanh; sau polish thì I+D+P vẫn cao hơn (bảng HV trong `docs/final_results.md`).

**f09_hv_box.** Phân bố HV qua 20 seed, 200 thế hệ. I+D+P không chỉ cao hơn mà còn ổn định hơn baseline
(hộp hẹp hơn), rõ nhất ở C102-25. HV chuẩn hoá riêng từng instance nên không so độ cao giữa các instance.

**f10_ablation_heatmap.** ΔHV so với NSGA-II gốc của 11 cấu hình ablation, dấu * là p < 0.05. Hàng "chỉ I"
và hàng "bỏ I" cho thấy I đóng góp lớn nhất; hàng "chỉ A" ở 1000 thế hệ có ô đỏ (A gây hại trên C102-25);
hàng "bỏ A" luôn ngang hoặc cao hơn hàng "cả năm".

**f11_paper_vs_ours.** Mức tăng HV mỗi bên đạt được so với NSGA-II của chính mình. Hai bên chuẩn hoá HV khác
nhau nên chỉ so chiều và độ lớn: ở 200 thế hệ (cùng ngân sách với bài báo), mức tăng của nhóm lớn hơn bài báo
trên 7/10 instance, rõ nhất ở 50 và 100 khách.
