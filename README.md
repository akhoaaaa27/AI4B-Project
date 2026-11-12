# GreenSegment AI — workspace local

Mở **GreenSegment.code-workspace** trong VS Code để chọn đúng thư mục dự án, Python `.venv` và cấu hình UTF-8.

Môi trường đã cấu hình: **Python 3.14**, **Node.js 24**, **npm 11**. Dự án nằm trong thư mục con `GreenSegment-AI-feature-greensegment-v2`; lệnh dưới đây chạy được từ cả thư mục ngoài và thư mục dự án.

## Chạy dự án

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\project.ps1 dev
```

Mở **http://127.0.0.1:5173**. Swagger API ở **http://127.0.0.1:8000/docs**. Giữ terminal mở; nhấn **Ctrl+C** để dừng cả hai dịch vụ. Chế độ dev tự nạp lại khi sửa mã nguồn. Log nằm trong `.local/` của thư mục dự án.

Máy hiện đặt PowerShell ExecutionPolicy là `Restricted`. Tùy chọn `-ExecutionPolicy Bypass` chỉ áp dụng cho tiến trình này, không đổi chính sách hệ thống. Bạn cũng có thể dùng **Terminal → Run Task → GreenSegment: dev** trong workspace đã mở.

## Các lệnh khác

Thay `dev` trong lệnh trên bằng:

| Lệnh | Chức năng |
| --- | --- |
| `setup` | Tạo `.venv` nếu thiếu, cài Python theo lockfile, cài Node bằng `npm ci`, tạo `.env` nếu chưa có |
| `check` | Kiểm tra dependency, chạy tests backend, kiểm tra import ML và build frontend |
| `smoke` | Khởi động hai dịch vụ, thử HTTP qua proxy và tự dừng |
| `ui` | Build rồi kiểm thử Overview và Market Explorer trên preview riêng ở cổng 5175, không gọi Gemini thật và tự dừng |
| `backend` | Chỉ chạy backend với reload và `.env` |
| `frontend` | Chỉ chạy Vite dev server |

`setup` cần Internet để tải dependency. Không cần chạy lại setup mỗi lần mở dự án. Kiểm thử `ui` dùng Chrome tại `C:\Program Files\Google\Chrome\Application\chrome.exe`; đặt `MARKET_CHROME` nếu Chrome nằm nơi khác.

## Gemini

Mở `.env` trong **thư mục dự án** và điền `GEMINI_API_KEY`, sau đó khởi động lại backend. File này đã được bỏ qua trong `.gitignore`. Các chức năng dữ liệu chạy được khi chưa có key; các tests dùng mock, không gọi Gemini thật.

## Làm việc với dữ liệu và model

`requirements-web.txt` dành cho backend; `requirements-dev.txt` thêm tests và Playwright; `requirements-ml.txt` dành cho scripts trong `src/`. `requirements-lock.txt` khóa toàn bộ môi trường Python đã kiểm tra; frontend dùng `web/package-lock.json`.

Chạy pipeline bằng Python trong `.venv`, ví dụ từ thư mục dự án:

```powershell
.\.venv\Scripts\python.exe src\prepare_data.py
```

Các lệnh pipeline có thể ghi lại dữ liệu/báo cáo/model; `setup`, `check`, `smoke` và `ui` chỉ chuẩn bị môi trường hoặc kiểm tra, không huấn luyện lại model. Hướng dẫn tính năng/API chi tiết nằm trong `GreenSegment-AI-feature-greensegment-v2/RUN_LOCAL.md`.
