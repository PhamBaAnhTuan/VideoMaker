# Báo cáo kiểm thử

## Cập nhật giao diện và hiệu ứng — 20/10/2026

Windows, Python 3.12.13, VieNeu 3.8.3, Streamlit 1.66.0, FFmpeg/FFprobe trên máy hiện tại.

`python -X utf8 -m pytest -q -p no:cacheprovider --basetemp=output/test-final-temp`: **63 passed**.

- Tám bố cục mẫu được dựng ở bốn tỷ lệ, hai giao diện và bốn phong cách; kiểm tra cả thời điểm giữa animation.
- AppTest kiểm tra sidebar gọn, không có ô API/model/thiết bị, chọn giọng và nghe thử qua giả lập, nạp script mẫu, đổi phong cách.
- Cache nghe thử phân biệt giọng và tái sử dụng WAV. Đã chạy thêm VieNeu v3turbo/CPU thật với model có sẵn và `HF_HUB_OFFLINE=1`, tạo WAV 453.164 byte. Không dùng âm thử để thay thế lời nói ở nút nghe thử.
- AppTest kiểm tra player với MP4 thật: không exception, không cảnh báo xem trước.
- `output/demo-neon/video.mp4`: script mới đủ tám cảnh, 320×568, 12 FPS, 332 frame, H.264/AAC. FFprobe xác nhận cả audio và video dài 27,666667 giây. Demo này dùng âm thử, có nhãn trên video.
- Đã kiểm tra bằng mắt `docs/preview-styles.jpg`; có thêm `docs/preview-layouts.jpg` và `docs/preview-motion.gif` để đối chiếu.

Chưa gọi LLM thật hoặc thử GPU trong lần cập nhật này. Kết quả dưới đây là lịch sử kiểm thử bản trước.

## Lịch sử — 19/10/2026

## Kết quả đã xác nhận

Môi trường: Linux, Python 3.12.14, FFmpeg/FFprobe, Pillow 12.3.0, Pydantic 2.14.0, HTTPX 0.28.1, Streamlit 1.66.0. Cài đặt thành công SDK VieNeu 3.8.3 từ PyPI; kiểm tra chữ ký constructor của v3 Turbo và Nano trong SDK đã cài.

Lệnh `python -m pytest -q`: **13 passed in 13.88s** ở lần kiểm tra cuối.

| Nhóm | Điều đã kiểm tra |
|---|---|
| Cấu trúc | Bắt ID trùng, comparison thiếu thẻ, khung hình lẻ hoặc tỷ lệ ngoài phạm vi |
| Đọc nguồn | File UTF-8 BOM, nguồn rỗng, giới hạn độ dài, không nhận nhiều nguồn cùng lúc |
| LLM adapter | Giả lập HTTP: phản hồi JSON lỗi, yêu cầu sửa, giữ metadata của người dùng |
| VieNeu adapter | Giả lập SDK: truyền đúng mode/backend/precision/voice, nạp model một lần, gọi tắt telemetry |
| Cache | Nội dung/giọng khác tạo khóa khác; chạy lại không tạo audio; sửa một đoạn chỉ tạo lại một đoạn |
| Timeline | Phụ đề không chồng nhau; WAV khớp duration; đệm đến đúng frame; SRT xử lý đổi phút |
| Video thật | FFmpeg xuất H.264 + AAC ở 320×568, 568×320, 320×320, 320×400; cả sáu template |
| Media | Thêm ảnh nền và BGM, giao diện sáng, đường dẫn có dấu và khoảng trắng |
| An toàn kết quả | Không chạy đồng thời vào cùng thư mục; chữ quá dài báo lỗi |
| Giao diện | Streamlit AppTest mở app và nạp kịch bản mẫu, không có exception |

`compileall` cho app, package và tests hoàn tất không lỗi cú pháp.

Video demo đi kèm `examples/demo-9x16.mp4`:

- 720×1280, 24 FPS, 579 frame.
- Video H.264, audio AAC.
- Cả audio và video dài **24,125 giây** theo FFprobe.
- Dùng **âm thử tổng hợp**, không phải giọng VieNeu; nhãn demo xuất hiện trên hình.
- Kịch bản mẫu được soạn sẵn, không phải kết quả gọi LLM thật.

Đã xem trực tiếp ảnh tổng hợp sáu cảnh ở hai bố cục dọc/ngang (`preview-portrait.jpg`, `preview-wide.jpg`), không thấy chữ chồng/cắt trong mẫu này. Các test khung khác kiểm tra xuất video và tính thời gian, không thay cho kiểm tra bằng mắt mọi nội dung tùy ý.

## Phần chưa xác nhận

1. **Suy luận VieNeu với trọng số thật:** phép thử v3 Nano đã bắt đầu tải model nhưng bị bộ kiểm duyệt tự động chặn do kết nối telemetry tới Microsoft chưa xác định dữ liệu gửi. Không có video nào được tuyên bố là kết quả TTS thật từ phép thử này. Sau đó adapter được sửa để tắt telemetry tùy chọn bằng API chính thức của ONNX Runtime và cờ HF/Gradio; chỉ kiểm tra đường gọi này bằng giả lập, không chạy lại phép thử online bị chặn.
2. **LLM thật:** chưa có server/model hoặc thông tin API của người dùng để kiểm tra sinh kịch bản thực tế. Đã kiểm tra giao thức và xử lý lỗi bằng phản hồi giả lập.
3. **Windows/macOS/GPU/4K/60 FPS:** có cấu hình và hướng dẫn, chưa chạy trên phần cứng tương ứng. Các bài kiểm tra thực tế ở Linux và khung nhỏ; demo ở 720p/24 FPS.
4. Chưa kiểm thử giọng nhân bản, chất lượng phát âm, URL có paywall/JavaScript hoặc mọi API tương thích.

Vì vậy đây là bản triển khai có bộ kiểm thử và demo dựng hình, chưa phải chứng nhận end-to-end với mọi model/API/hệ điều hành.

## Cách xác nhận trên máy dùng thật

1. `python -m studio.cli doctor` để xem FFmpeg và VieNeu.
2. `python -m studio.cli voices` để tải/nạp model và chọn đúng giọng.
3. `python -m studio.cli build examples/excel.json --out output/tts-check` để nghe và xem giọng thật.
4. Cấu hình LLM trong `.env`, chạy `python -m studio.cli plan --file examples/source.txt --out output/ai-check/script.json`.
5. Kiểm tra nội dung, rồi `python -m studio.cli build output/ai-check/script.json --out output/ai-check`.

API tắt telemetry được tham chiếu từ [ONNX Runtime Python API](https://onnxruntime.ai/docs/api/python/api_summary.html#onnxruntime.disable_telemetry_events).
