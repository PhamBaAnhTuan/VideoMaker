# VieNeu Video Studio

Tạo video tiếng Việt theo quy trình **nội dung → AI viết kịch bản → VieNeu-TTS → motion graphics → MP4**.

Dự án độc lập, không cần clone hai repo gốc. Giữ sáu kiểu cảnh và tư duy căn hình theo audio của `auto-video-gen`, chuyển phần dựng hình sang **Pillow + FFmpeg** để dùng chung Python với VieNeu. Hiệu ứng được lập trình sẵn; AI chọn nội dung/bố cục, không sinh footage bằng mô hình text-to-video.

## Những gì đã có

- Nhập chủ đề, nội dung văn bản, file UTF-8 `.txt/.md` hoặc URL bài viết.
- AI viết JSON bằng server tương thích `chat/completions`: Ollama chạy local hoặc API do bạn cấu hình.
- Giao diện tiếng Việt: xem/sửa JSON trước khi render; có tùy chọn chạy tự động cả quy trình.
- SDK **VieNeu 3.8.3**, v3 Turbo (mặc định), v3 Nano tùy chọn; preset hoặc file giọng mẫu.
- Tám bố cục: `hook`, `comparison`, `stat-hero`, `feature-list`, `workflow`, `quote`, `callout`, `outro`.
- Bốn phong cách hình ảnh, chữ nảy/trượt/hiện dần, số đếm, chuyển cảnh và nền chuyển động; ảnh riêng từng cảnh nếu cần.
- Khung dọc 9:16, ngang 16:9, vuông 1:1, 4:5 hoặc kích thước tự nhập.
- Phụ đề ghi vào hình và file SRT, căn theo audio từng đoạn; không tô sáng từng từ.
- Audio cache theo nội dung, giọng, model, phiên bản SDK và nội dung giọng mẫu.
- Nhạc nền tùy chọn, âm chuyển cảnh nhẹ được tổng hợp bằng code.
- Kết quả: MP4 H.264/AAC, WAV giọng sạch, WAV có SFX, SRT, JSON và poster.

Ảnh xem trước các bố cục: [dọc](docs/preview-portrait.jpg) · [ngang](docs/preview-wide.jpg).

## 1. Cài đặt trên Windows

### Yêu cầu

- Python **3.12 64-bit** (project hỗ trợ 3.10–3.13; 3.12 là cấu hình hướng dẫn).
- FFmpeg và FFprobe có trong PATH.
- Internet để cài thư viện và tải model ở lần đầu. Sau khi model đã lưu, TTS local có thể dùng lại cache của SDK; LLM local cũng cần tải model trước.
- Để viết kịch bản tự động: một model trên Ollama hoặc API tương thích. VieNeu chỉ tạo giọng, không viết kịch bản.

Cài FFmpeg trong PowerShell, rồi mở lại terminal:

```powershell
winget install Gyan.FFmpeg
ffmpeg -version
ffprobe -version
```

Giải nén dự án vào một thư mục. Chạy `setup-windows.bat`, sau đó chạy `start-windows.bat`. Giao diện mở ở `http://127.0.0.1:8501`. Nếu muốn cài thủ công:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[tts,ui]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m studio.cli doctor
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Không cần lệnh `uv`, không cần kích hoạt môi trường bằng `Activate.ps1`.

### macOS/Linux

Cài FFmpeg bằng trình quản lý gói của hệ điều hành, sau đó:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e ".[tts,ui]"
cp .env.example .env
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

Lệnh `python` trong các ví dụ bên dưới nghĩa là Python trong `.venv`; trên Windows có thể dùng đầy đủ `.\.venv\Scripts\python.exe`.

## 2. Cấu hình AI viết kịch bản

### A. Google Gemini (mặc định)

Sao chép `.env.example` thành `.env` nếu chưa có. Lấy **Gemini API key** tại [Google AI Studio](https://aistudio.google.com/apikey), rồi điền một giá trị:

```dotenv
GEMINI_API_KEY=your_gemini_api_key
```

Chạy `start-windows.bat`. Giao diện chỉ hiển thị liên kết lấy key; điền key trong `.env` và khởi động lại ứng dụng. URL mặc định là `https://generativelanguage.googleapis.com/v1beta/openai`, model mặc định là `gemini-3.8-flash`; để trống URL/model cũng dùng các giá trị này. Có thể đổi `LLM_MODEL` sang model Gemini mà key được phép dùng.

Tích hợp dùng [endpoint tương thích OpenAI chính thức của Google](https://ai.google.dev/gemini-api/docs/openai), không cần thêm SDK. Với Google, thứ tự ưu tiên key môi trường là `GEMINI_API_KEY`, `GOOGLE_API_KEY`, rồi `LLM_API_KEY`.

Nếu `.env` cũ trỏ tới Cohere hoặc dịch vụ khác, đổi `LLM_BASE_URL` và `LLM_MODEL` theo `.env.example`. API key phải thuộc đúng nhà cung cấp. Không đưa key thật vào Git; `.env` đã được bỏ qua, `.env.example` chỉ chứa mẫu cấu hình.

HTTP 401/403: kiểm tra key và quyền truy cập model. HTTP 429: kiểm tra quota hoặc thử lại sau. Hạn mức và chi phí tùy tài khoản/model.

### B. Ollama local

Cài Ollama từ trang chính thức, chọn model mà máy đủ bộ nhớ. Ví dụ cấu hình đi kèm dùng `qwen3:8b`; có thể thay bằng model khác hỗ trợ tốt tiếng Việt và JSON.

```bash
ollama pull qwen3:8b
```

Đảm bảo Ollama đang chạy. File `.env`:

```dotenv
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen3:8b
LLM_API_KEY=
LLM_TIMEOUT=240
LLM_JSON_MODE=true
```

Tên model phải khớp model thực tế đã cài (`ollama list`). Không xem cấu hình mẫu là bảo đảm tốc độ trên mọi máy. Nếu thiếu RAM hoặc model trả JSON không ổn định, đổi model hoặc dùng API.

### C. API tương thích khác

Điền URL gốc, model và key của nhà cung cấp vào `.env`. Chương trình nối `/chat/completions` vào URL gốc, vì vậy không điền cả đường dẫn endpoint này.

Với nhà cung cấp khác, dùng `LLM_API_KEY`. Gemini API key không tự động được gửi tới endpoint khác.

Nếu server không hỗ trợ `response_format`, đặt `LLM_JSON_MODE=false`. Server phải hỗ trợ messages, temperature, max_tokens và trả `choices[0].message.content`. Đây là adapter giao thức chung; chưa xác nhận mọi nhà cung cấp đều tương thích.

API bên ngoài có thể tính phí. Chế độ nguồn gửi nội dung bạn nhập cho LLM đã cấu hình; chế độ local dùng server trên máy. Chương trình không lưu API key vào thư mục kết quả.

## 3. Cấu hình VieNeu-TTS

CPU, ưu tiên chất lượng:

```dotenv
VIENEU_MODE=v3turbo
VIENEU_BACKEND=onnx
VIENEU_VOICE=Hải Đăng
VIENEU_PRECISION=fp32
```

Máy yếu, chấp nhận chất lượng thấp hơn:

```dotenv
VIENEU_MODE=v3nano
VIENEU_VOICE=Minh Quân
```

Nano và Turbo có danh sách giọng khác nhau. Liệt kê giọng của model đang chọn:

```bash
python -m studio.cli voices
```

Lệnh này nạp model, lần đầu có thể cần tải dữ liệu. SDK 3.8.3 được khóa trong dependency để tránh thay đổi API ngoài ý muốn; model tải riêng, không nằm trong ZIP. Dependency chính thức của VieNeu vẫn bao gồm một số gói của SDK (như Gradio), dù giao diện dự án này dùng Streamlit.

Adapter tắt telemetry tùy chọn của ONNX Runtime qua API chính thức trước khi tạo model, đặt cờ tắt telemetry Hugging Face/Gradio; cấu hình Streamlit cũng tắt thống kê sử dụng. Điều này không chặn kết nối cần thiết để tải model hoặc gọi LLM mà bạn đã cấu hình.

**GPU NVIDIA:** chỉ cài khi máy có NVIDIA/CUDA tương thích. Hướng dẫn upstream hiện dùng:

```bash
python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
python -m pip install transformers==4.57.6
```

Đổi `VIENEU_BACKEND=auto`. Chưa kiểm thử GPU trong môi trường xây dựng gói này. CPU ONNX không cần PyTorch. Giữ `fp32` nếu chưa biết CPU có hỗ trợ INT8 phù hợp hay không.

**Giọng mẫu:** tải WAV/MP3 lên giao diện hoặc đặt `VIENEU_REF_AUDIO` tới clip tham chiếu khoảng 3–8 giây. Khi có giọng mẫu, preset bị thay thế. Dùng giọng của bạn hoặc giọng được chủ sở hữu cho phép. SDK đảm nhiệm chuẩn bị giọng mẫu; dự án không cung cấp công cụ huấn luyện model.

## 4. Dùng giao diện

1. Chọn tỷ lệ, FPS, giao diện tối/sáng và giọng đọc ở thanh bên. Giọng có mô tả và nút **Nghe thử**; danh sách không cần tải model. Giao diện dùng cố định **v3turbo + CPU/ONNX**.
2. Nhập nguồn hoặc chủ đề. Chọn số cảnh, thời lượng mục tiêu và cách trình bày.
3. Bấm **AI viết kịch bản**. Có thể chọn tự tạo video ngay sau đó.
4. Kiểm tra/chỉnh nội dung JSON, đặc biệt số liệu và cách đọc thuật ngữ. Chế độ chủ đề không tự tìm kiếm Internet để kiểm chứng kiến thức.
5. Chọn **Phong cách hình ảnh**: Studio, Neon Tech, Tạp chí hoặc Pop & Bounce. Chọn từng cảnh để xem bố cục và màu sắc. Phụ đề, SFX, nhạc nền và giọng mẫu nằm trong **Âm thanh & tùy chọn bổ sung**.
6. Bấm **Tạo giọng đọc và render video**.
7. Xem và tải MP4, SRT, WAV ngay trong giao diện. Video xem trước cao tối đa 520 px; file tải xuống vẫn giữ nguyên độ phân giải đã chọn.

**Không có LLM vẫn dùng được:** bấm **Mở kịch bản Excel mẫu**, rồi tạo giọng/video. Đường này chỉ bỏ bước viết kịch bản; VieNeu thật vẫn chạy.

**Script tham khảo đầy đủ:** [examples/script-mau.json](examples/script-mau.json), hướng dẫn tại [examples/HUONG-DAN-SCRIPT.md](examples/HUONG-DAN-SCRIPT.md). Có nút mở/tải mẫu ngay trong giao diện. Mẫu gồm tám bố cục, bao gồm `workflow` (quy trình) và `quote` (trích dẫn/ý chính), cùng các trường `animation`, `transition` có thể chỉnh cho từng cảnh. Các trường mới có mặc định nên script cũ vẫn chạy.

Chuyển động bổ sung: spring, hiện chữ theo dòng, mở dần, nền quầng sáng/hạt/hình học, số liệu tăng dần và chuyển cảnh fade/slide/wipe. Thời gian audio và phụ đề được giữ nguyên khi chuyển cảnh. Tham khảo ý tưởng từ [remotion-cuongit-template](https://github.com/Cuongyd196/remotion-cuongit-template), viết lại bằng Pillow.

Xem [bốn phong cách](docs/preview-styles.jpg), [tám bố cục](docs/preview-layouts.jpg) và [chuyển động mẫu](docs/preview-motion.gif).

CLI cũng hỗ trợ `--visual-style studio|neon|editorial|playful`, ví dụ:

```powershell
.\.venv\Scripts\python.exe -m studio.cli demo examples/script-mau.json --visual-style neon --size 320x568 --fps 12 --out output/demo-neon
```

Lệnh `demo` dùng âm thử để kiểm tra hình ảnh, không phải giọng nói. Nút nghe thử giọng dùng VieNeu thật, có thể tải model lần đầu, sau đó lưu WAV trong `output/voice-previews`.

Tên thư mục kết quả giúp quản lý phiên bản. Dùng cùng thư mục để giữ cache. Đổi tỷ lệ hoặc sửa chữ trên hình sẽ dùng lại các đoạn lời đọc không thay đổi. Sửa một đoạn lời đọc hoặc đổi giọng sẽ tạo cache khác. Trong một thư mục, lần build mới thay thế script, timeline và video khi thành công.

## 5. Chạy bằng lệnh

Tự động từ chủ đề tới MP4:

```bash
python -m studio.cli run --topic "Hướng dẫn VLOOKUP cho người mới" --seconds 60 --scenes 5 --size 9:16 --out output/vlookup
```

Từ tài liệu có sẵn, hạn chế AI thêm dữ kiện ngoài nguồn:

```bash
python -m studio.cli run --file examples/source.txt --size 16:9 --out output/bai-hoc
```

Chỉ viết kịch bản để kiểm tra trước:

```bash
python -m studio.cli plan --file examples/source.txt --out output/bai-hoc/script.json
```

Sau khi sửa JSON:

```bash
python -m studio.cli build output/bai-hoc/script.json --size 1920x1080 --fps 30 --out output/bai-hoc
```

Thêm giọng mẫu và nhạc nền:

```bash
python -m studio.cli build examples/excel.json --ref-audio "my-voice.wav" --bgm "music.mp3" --bgm-volume 0.08 --size 1:1 --out output/excel-square
```

Các cờ khác: `--voice`, `--theme light`, `--no-subtitles`, `--no-sfx`, `--font`.

## 6. Khung hình và bố cục

| Giá trị `--size` | Độ phân giải |
|---|---|
| `9:16` | 720 × 1280 |
| `16:9` | 1280 × 720 |
| `1:1` | 1080 × 1080 |
| `4:5` | 1080 × 1350 |
| `1080x1920` | Dọc Full HD |
| `1920x1080` | Ngang Full HD |

Kích thước tùy chỉnh: mỗi chiều 240–3840, số chẵn, tối đa 8.294.400 pixel; tỷ lệ rộng/cao từ 0,4 đến 2,5. Font tự xuống dòng và giảm cỡ trong giới hạn. Hai thẻ so sánh xếp dọc ở khung dọc, xếp ngang khi đủ rộng. Nếu chữ vẫn không vừa, chương trình báo lỗi để rút gọn, không cắt bỏ chữ âm thầm.

Đổi khung hình là dựng lại bố cục theo tỷ lệ, không kéo giãn video đã xuất. Render 4K/60 FPS tốn nhiều CPU và thời gian hơn; nên thử 720p/24 FPS trước.

## 7. Sửa kịch bản và thêm ảnh

Ví dụ một cảnh (xem `examples/excel.json` để có file hoàn chỉnh):

```json
{
  "id": "step-1",
  "layout": "feature-list",
  "title": "Chuẩn bị bảng tra",
  "bullets": ["Mã hàng ở cột đầu", "Xác định cột kết quả"],
  "narration": [
    {
      "text": "Đặt mã hàng ở cột đầu của vùng bảng tra.",
      "caption": "Mã hàng ở cột đầu của vùng bảng tra."
    }
  ],
  "image": "images/bang-hang.png"
}
```

`image` là đường dẫn ảnh trên máy, tương đối với file script khi dùng CLI. Trong giao diện, đường dẫn tương đối của JSON tải lên tính từ thư mục dự án; cũng có thể dùng đường dẫn tuyệt đối. Ảnh được sao chép vào kết quả để dự án render có thể di chuyển. AI mặc định không tự tìm hoặc tạo ảnh; nền đồ họa vẫn hoạt động khi không có ảnh. Các cảnh có thể dùng ảnh khác nhau.

`text` là lời đọc; `caption` là chữ phụ đề. Tách thành các đoạn ngắn giúp phụ đề dễ đọc. Mỗi đoạn được tổng hợp riêng nên có thể nghe rõ chỗ ngắt; hãy gộp thành một câu ngắn tự nhiên thay vì tách từng từ.

## 8. Cách hoạt động và thư mục

| File | Vai trò |
|---|---|
| `app.py` | Giao diện Streamlit |
| `studio/cli.py` | Lệnh plan/run/build/demo/voices/doctor |
| `studio/writer.py` | Đọc nguồn, gọi LLM, sửa JSON lỗi một lần |
| `studio/models.py` | Kiểm tra cấu trúc kịch bản và cấu hình |
| `studio/audio.py` | VieNeu, cache, WAV, timeline và SRT |
| `studio/renderer.py` | Tám bố cục, bốn phong cách, animation, chuyển cảnh, ảnh và FFmpeg |
| `studio/pipeline.py` | Điều phối và bảo vệ thư mục đang render |
| `examples/` | Kịch bản Excel và văn bản thử |
| `tests/` | Kiểm tra cache, adapter, UI và xuất MP4 |
| `licenses/` | Giấy phép phần tham khảo |

Kết quả `output/<tên>/` gồm `video.mp4`, `poster.jpg`, `script.json`, `script.txt`, `narration.wav` (giọng sạch), `voice.wav` (giọng + SFX), `subtitles.srt`, `timeline.json`, `render-options.json`, `status.json`, `render.log`, `cache/` và ảnh nếu có. Nhạc nền được trộn vào MP4, không nằm trong `voice.wav`.

Timeline dùng số mẫu audio 48 kHz; phụ đề bắt đầu/kết thúc cùng đoạn audio tương ứng. Đây là căn theo đoạn tổng hợp, không phải forced alignment theo từng từ; im lặng tự sinh trong đoạn TTS vẫn nằm trong khoảng phụ đề. Giữa đoạn có nghỉ 0,1 giây; giữa cảnh 0,3 giây; cuối video giữ hình thêm 1,5 giây. Cuối audio được đệm đến đúng số frame. Thời lượng mục tiêu LLM không bảo đảm là thời lượng video chính xác.

## 9. Kiểm tra và khắc phục lỗi

```bash
python -m studio.cli doctor
python -m pip install -e ".[dev]"
python -m pytest -q
```

Kiểm tra dựng hình hoàn toàn không gọi AI/VieNeu:

```bash
python -m studio.cli demo examples/excel.json --size 9:16 --out output/demo
```

`demo` dùng âm thử và đóng nhãn rõ trên hình. Không có cơ chế tự chuyển sang âm giả khi VieNeu lỗi.

| Lỗi | Cách xử lý |
|---|---|
| Không kết nối LLM | Kiểm tra Ollama/API, tên model, URL và key |
| HTTP 400 từ LLM | Kiểm tra tham số server; thử `LLM_JSON_MODE=false` |
| JSON không hợp lệ | Thử model khác, giảm số cảnh hoặc sửa JSON trực tiếp |
| Tải model thất bại | Kiểm tra kết nối tới Hugging Face, dung lượng đĩa và thông báo SDK |
| SOCKS proxy thiếu thư viện | Nếu máy dùng SOCKS: `python -m pip install socksio` |
| Không tìm thấy FFmpeg | Cài FFmpeg, mở lại terminal, chạy `doctor` |
| Thiếu/khác tên giọng | Chạy `voices` với đúng model Turbo hoặc Nano |
| TTS đọc sai ký hiệu | Sửa `narration[].text` thành cách đọc bằng chữ; giữ `caption` chuẩn |
| Có `.render.lock` sau khi mất điện | Bảo đảm không có tiến trình chạy rồi xóa file lock |
| Muốn tạo lại audio dù lời không đổi | Xóa các WAV trong `output/<tên>/cache/` |
| Render quá chậm | Dùng 720p, 24 FPS; tránh 4K/60 FPS ở máy yếu |

Giao diện mặc định chỉ mở ở localhost. Video này là motion graphics; chưa có quay thao tác phần mềm, sinh footage AI, karaoke từng từ hay đăng tự động lên mạng xã hội.

## 10. Nguồn và phạm vi kiểm thử

- [auto-video-gen](https://github.com/Cuongyd196/auto-video-gen), tham chiếu commit `86cda98a59b1126bd5e95b6839e87ee67b9fd396`.
- [VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS), SDK PyPI `3.8.3`.
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility).
- Xem `THIRD_PARTY_NOTICES.md` và `docs/TEST_REPORT.md` trước khi đánh giá mức sẵn sàng triển khai.

Không đóng gói model LLM/TTS, môi trường Python, cache tải model hoặc hai repo upstream vào ZIP.
