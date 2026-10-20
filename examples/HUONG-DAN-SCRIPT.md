# Cách dùng script mẫu

Mở `script-mau.json` hoặc bấm **Bắt đầu từ kịch bản mẫu → Mở script mẫu** trong ứng dụng. Mẫu có đủ tám bố cục để bạn sửa và render mà không gọi LLM. Không cần điền API key nếu dùng mẫu; tạo giọng lần đầu vẫn có thể cần tải model VieNeu.

- `title`, `subtitle`, `bullets`: chữ ngắn hiển thị trên video.
- `narration[].text`: câu đọc đầy đủ; nên viết số và tên khó đọc thành cách phát âm tiếng Việt.
- `narration[].caption`: phụ đề hiển thị, giữ cách viết chuẩn.
- `layout`: `hook`, `comparison`, `stat-hero`, `feature-list`, `workflow`, `quote`, `callout`, `outro`.
- `animation`: `auto`, `fade`, `slide`, `spring`, `wipe`, `typewriter`.
- `transition`: `auto`, `cut`, `fade`, `slide`, `wipe`.

`workflow` và `feature-list` cần 1–4 mục trong `bullets`. `comparison` cần `left` và `right`, mỗi bên có `label` và `value`. `stat-hero` cần `value`. Chỉ dùng số liệu có cơ sở; số 4 trong mẫu chỉ số phong cách có sẵn của ứng dụng. Với `quote`, đặt ý chính trong `title`, ngữ cảnh hoặc nguồn trong `subtitle`.

Chọn phong cách hình ảnh trong giao diện. Khi `animation` hoặc `transition` là `auto` (hoặc không ghi), ứng dụng chọn hiệu ứng theo phong cách đó. Mẫu đặt một số hiệu ứng cụ thể để bạn so sánh; đổi thành `auto` nếu muốn toàn bộ video theo preset.

Script cũ như `excel.json` vẫn chạy được vì các trường hiệu ứng đều có mặc định. Đặt `image` là đường dẫn ảnh nếu cần; khi upload JSON, đường dẫn tương đối được tính từ thư mục dự án.
