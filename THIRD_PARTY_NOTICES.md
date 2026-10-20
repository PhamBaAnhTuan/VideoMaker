# Nguồn gốc và giấy phép

## auto-video-gen

Nguồn: https://github.com/Cuongyd196/auto-video-gen

Commit tham khảo: `86cda98a59b1126bd5e95b6839e87ee67b9fd396`.

MIT License, Copyright (c) 2026 CuongIT. Bản giấy phép đầy đủ ở `licenses/auto-video-gen-MIT.txt`.

Các phần được chọn để chuyển thể:

- `src/render/script-schema.ts`: sáu loại bố cục và tách lời đọc khỏi chữ trên hình.
- `src/render/html-composer.ts`: phân nhánh bố cục, thẻ so sánh, danh sách, số liệu.
- `src/render/templates/animations.js`: hiệu ứng phóng/trượt/hiện theo thời gian; danh sách vào lần lượt.
- `src/pipeline.ts`: tạo audio trước rồi tính thời gian cảnh, khoảng nghỉ giữa cảnh.

Đây là bản chuyển thể viết lại bằng Python. Không sao chép nguyên cây thư mục, không nhúng Node, HyperFrames, GSAP, quảng bá kênh TikTok, kho SFX hay bộ cấu hình AI Agent của upstream. CSS/HTML upstream không phải dependency runtime. Thiết kế, số đo responsive, chữ, phụ đề, cache theo nội dung, UI và LLM adapter được viết mới cho dự án này. Bộ hiệu ứng không được tuyên bố giống hoàn toàn repo gốc.

## remotion-cuongit-template (tham khảo ý tưởng)

Nguồn: https://github.com/Cuongyd196/remotion-cuongit-template

Tham khảo cách trình bày nội dung ở trung tâm, sơ đồ quy trình từng bước, chuyển động spring theo thứ tự và nền ánh sáng. Bộ bố cục `workflow`/`quote`, hiệu ứng và các preset trong dự án này được viết mới bằng Python/Pillow; không sao chép mã React/Remotion, âm thanh, hình ảnh hay thương hiệu của repo. Không thêm Remotion làm dependency và không tuyên bố tương đương toàn bộ template.

## VieNeu-TTS SDK

Nguồn: https://github.com/pnnbao97/VieNeu-TTS

Tác giả: Phạm Nguyễn Ngọc Bảo. Dùng dependency Python `vieneu==3.8.3` theo API chính thức `Vieneu`, `infer`, `save`, `list_preset_voices`. Không sao chép source hoặc phân phối trọng số trong dự án này. Repo SDK upstream công bố Apache-2.0; giấy phép và điều khoản từng model/dependency vẫn do upstream quy định. Không dùng VieNeu v4 độc quyền.

## Font

DejaVu Sans đi kèm để chữ tiếng Việt hoạt động nhất quán trên các hệ điều hành. Giấy phép font ở `studio/assets/FONT-LICENSE.txt`.

## Thành phần cài riêng

Pillow, NumPy, Pydantic, HTTPX, python-dotenv, trafilatura, Streamlit và VieNeu được cài bằng pip; FFmpeg cài riêng. Mỗi thành phần giữ giấy phép riêng. Bản FFmpeg cụ thể có thể khác về cấu hình/giấy phép codec. Không phân phối binary FFmpeg trong gói này.
