---
name: product-review
title: Đánh giá & So sánh (Review & Comparison)
description: Video review đồ công nghệ, so sánh điện thoại/laptop/AI model. Trực quan, số liệu đối chiếu rõ ràng giữa 2 phe.
---

# Product Review & Comparison Skill

Biên tập video review, mở hộp, so sánh thông số giữa hai sản phẩm hoặc phiên bản.

## Phong cách biên tập (Tone & Style)
- **Giọng điệu:** Khách quan, dứt khoát, chuyên môn cao nhưng cách nói đời thường.
- **Mục tiêu:** Giúp người xem đưa ra quyết định mua sắm hoặc lựa chọn công cụ phù hợp.

## Cấu trúc kịch bản

### 1. Hook (Mở đầu)
- Đưa ra sự so sánh đối đầu hoặc mức giá gây sốc: "Bỏ thêm 5 triệu để lên bản Pro: Đáng hay phí tiền?", "Liệu chip mới có thực sự mạnh hơn 30%?".
- Bắt buộc layout `hook` kích thích tranh luận.

### 2. Thân bài (Body scenes)
- Bắt buộc có ít nhất 1 cảnh layout `comparison` với cả `left` và `right` để so sánh trực diện (ví dụ: Bản thường vs Bản Pro, iPhone vs Samsung).
- Có cảnh `stat-hero` nêu bật sự khác biệt về thông số (pin, camera, điểm hiệu năng, giá cả).

### 3. Outro (Kết thúc)
- Đặt câu hỏi kích thích bình luận: "Nếu là bạn, bạn sẽ chọn phiên bản nào? Để lại bình luận và đăng ký kênh nhé!".

## ⚠️ Quy chuẩn phát âm tiếng Việt cho VieNeu-TTS
- `caption`: Giữ nguyên thông số (`iPhone 16`, `5000mAh`, `120Hz`, `$999`, `48MP`).
- `text`: Phiên âm toàn bộ sang tiếng Việt:
  * `5000mAh` -> `năm nghìn miliampe giờ`.
  * `120Hz` -> `một trăm hai mươi héc`.
  * `$999` -> `chín trăm chín mươi chín đô la`.
  * `48MP` -> `bốn mươi tám megapixel`.
  * `2x` -> `gấp đôi`.
  * Kết thúc mỗi câu trong `text` bằng dấu `.` hoặc `?`.
