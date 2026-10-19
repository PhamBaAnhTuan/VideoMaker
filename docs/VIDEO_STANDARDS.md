# Quy Chuẩn Sản Xuất Video — VieNeu Video Studio

Tài liệu này chuẩn hóa quy trình biên tập kịch bản và phát âm VieNeu-TTS dựa trên quy chuẩn kỹ thuật [skill/SKILL.md](../skill/SKILL.md).

---

## 1. Cấu trúc kịch bản video ngắn (TikTok / Shorts / Reels)

| Vị trí | Layout | Mục đích & Yêu cầu |
|---|---|---|
| **Cảnh 1** | `hook` | **Bắt buộc**: Giữ chân 3 giây đầu bằng tuyên bố giật mình, con số ấn tượng hoặc câu hỏi tò mò. Tuyệt đối không mở bài chung chung ("Chào các bạn...", "Hôm nay chúng ta sẽ..."). |
| **Thân bài** | `feature-list` | 1–4 gạch đầu dòng ngắn gọn. |
| | `comparison` | So sánh 2 vế rõ ràng (`left` và `right`). |
| | `stat-hero` | Làm nổi bật một con số ấn tượng (`value`). |
| | `callout` | Nhấn mạnh một thông điệp hoặc lời khuyên đắt giá. |
| **Cảnh cuối** | `outro` | **Bắt buộc**: Kêu gọi hành động ngắn gọn (Follow / Đăng ký kênh) và nêu nguồn bài viết. |

---

## 2. Quy chuẩn phát âm Tiếng Việt cho VieNeu-TTS (Phonetic Rules)

VieNeu-TTS đọc từng ký tự theo nghĩa đen. Do đó, trường kịch bản tách biệt thành hai phần:
* **`caption` (Hiển thị màn hình)**: Giữ cách viết chuẩn, đẹp mắt để người xem dễ đọc lướt (`GPT 5.5`, `82.7%`, `$5`, `VLOOKUP`).
* **`text` (Lời đọc âm thanh)**: Phải được phiên âm hoàn toàn bằng chữ tiếng Việt để tránh đọc sai ngữ nghĩa.

### Bảng tra cứu phiên âm bắt buộc:

| Loại dữ liệu | Viết trên màn hình (`caption`) | Phiên âm lời đọc TTS (`text`) | Ghi chú |
|---|---|---|---|
| **Phiên bản thập phân** | `GPT 5.5` | `GPT năm chấm năm` | Tránh TTS đọc thành "năm rưỡi" |
| **Hệ điều hành / App** | `iOS 18.2` | `ai ô ét mười tám chấm hai` | Phiên âm cả chữ viết tắt tiếng Anh |
| **Tỷ lệ phần trăm** | `82.7%` | `tám mươi hai phẩy bảy phần trăm` | Không để ký hiệu `%` |
| **Phần trăm chẵn** | `30%` | `ba mươi phần trăm` | |
| **Tiền tệ (USD)** | `$5` | `năm đô la` (hoặc `năm đô`) | Không để ký hiệu `$` |
| **Tiền tệ (VND)** | `21 triệu đồng` | `hai mươi mốt triệu đồng` | |
| **Camera / Thông số** | `200MP` | `hai trăm megapixel` | |
| **Dung lượng pin** | `5000mAh` | `năm nghìn miliampe giờ` | |
| **Ngữ cảnh LLM** | `1M tokens` | `một triệu token` | |
| **Hệ số tăng trưởng** | `2x` | `gấp đôi` | Tự nhiên hơn "hai lần" |
| **Năm** | `2026` | `hai nghìn không trăm hai mươi sáu` | |
| **Viết tắt: AI** | `AI` | `ây ai` | |
| **Viết tắt: API** | `API` | `ây pi ai` | |

---

## 3. Quy chuẩn dấu câu và ngữ điệu

* **Dấu kết thúc câu**: Mỗi câu trong `text` cần kết thúc bằng dấu chấm `.` hoặc hỏi chấm `?` để TTS ngắt nhịp và tạo ngữ điệu tự nhiên.
* **Ký hiệu cấm trong `text`**: Tuyệt đối không dùng `→`, `&`, `%`, `$`, `#`, `+`, `=`. Phải chuyển thành từ: "sang", "và", "phần trăm", "đô la", "cộng", "bằng".
* **Độ dài câu chữ trên màn hình**: Mỗi dòng chữ hiển thị tối đa 25–30 ký tự, súc tích, tránh đưa nguyên cả đoạn thuyết minh lên màn hình.
