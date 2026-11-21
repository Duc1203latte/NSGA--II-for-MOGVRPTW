# Chú thích hình cho slide (phần TV4)

Dựng bằng `python -m scripts.tv4_figures` từ kết quả có sẵn trong `results/tv4_main/` (không chạy tiến hoá). Màu cố định theo cấu hình ở mọi hình: xanh dương = baseline, cam = dp (chấm mọi cá thể), xanh ngọc = polish, tím = baseline chạy dài hoặc thế hệ thêm. Hình thứ năm là `docs/tv4_adaptive_rates.png` (giữ nguyên).

**1. `hv_vs_cpu.png`.** Tính theo chi phí CPU, baseline chạy thêm thế hệ vượt `dp` chấm mọi cá thể ở cả hai instance (đường xanh dương so với chấm cam tại 1.0); polish (hình thoi) là bước hoàn thiện rẻ, cộng thêm HV ở cả ngân sách ngắn lẫn dài. HV tính trên reference set 7 cấu hình, trung bình ± độ lệch chuẩn qua seed 0–9; vùng mờ là ± độ lệch chuẩn của baseline cắt ở n_gen khác nhau.

**2. `polish_vs_extra_gens.png`.** So polish với việc dùng đúng lượng CPU đó cho thêm thế hệ baseline: ở 200 thế hệ chạy thêm thế hệ ngang (C102-25) hoặc tốt hơn rõ (R201-50), chỉ ở ngân sách đã hội tụ polish mới hơn. Chấm là từng seed (10 seed), vạch là trung bình; ở ngân sách hội tụ giá trị "thêm thế hệ" là ước lượng ngoại suy, và p = 0.049 ở R201-50 là sát ngưỡng.

**3. `front_f1_f2.png`.** Front cuối của một seed đại diện, chọn seed có HV baseline ở hạng 5/10 (trung vị dưới): seed 7 cho C102-25 và seed 9 cho R201-50. `dp` mở front sang vùng f2 thấp (f1 cao hơn), polish làm dày front, baseline chạy dài hội tụ gần nhất; trục f1 dùng thang log vì `dp` và polish có vài điểm f1 rất lớn.

**4. `split_rules.png`.** Quy tắc `capacity_time` đã loại gần hết trễ so với `capacity` (số phút trễ, thang log; f1 cũng ở thang log), nên khoảng cải thiện còn lại cho DP ở quần thể cuối là nhỏ; ở C102-100 `capacity_time` vượt đội xe (26.8 so với 25, thanh vạch chéo, 0% khả thi) và rất trễ, còn DP luôn khả thi và trễ ít hơn khoảng 8.5 lần. Giá trị là trung bình: 800 hoán vị quần thể cuối (seed 0–9) ở C102-25 và R201-50, 200 hoán vị ngẫu nhiên ở C102-100.
