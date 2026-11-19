# Phase 2A — Điều hướng toàn cục, trang chủ và bố cục toàn website

## 1. Kết quả

Đã thay sidebar bằng header dùng chung với logo độc lập và thanh điều hướng pill. Trang chủ mới là điểm vào mặc định, gồm Hero, một CTA và ba thẻ khám phá. Bốn trang phân tích/thông tin tiếp tục hoạt động trong khung nội dung rộng và cân đối hơn.

Không thêm KPI vào Home, CTA trong header, form đăng ký, tài khoản hay nội dung tiếp thị ngoài phạm vi. Không thêm dependency.

## 2. Các file thay đổi trong riêng Phase 2A

| Thao tác | File | Nội dung |
|---|---|---|
| Thêm | `web/src/components/GlobalHeader.jsx` | Logo, năm liên kết chính, menu thu gọn và hỗ trợ bàn phím |
| Thêm | `web/src/pages/Home.jsx` | Hero, CTA và ba thẻ khám phá |
| Thêm | `web/src/navigation.js` | Đọc và tạo URL điều hướng |
| Thêm | `web/src/navigation.css` | Header, Home và điều chỉnh khung bố cục |
| Sửa | `web/src/App.jsx` | Shell chung, Home mặc định, lịch sử URL và liên kết hồ sơ đô thị |
| Sửa | `web/src/main.jsx` | Nạp CSS điều hướng sau hệ màu Phase 1 |
| Sửa | `web/src/components/WorldMap.jsx` | Xử lý an toàn khi đóng trang giữa lúc Leaflet đang zoom/vẽ canvas |
| Thêm | `tests/ui_navigation.py` | Chín kiểm thử mới cho Home, URL, lịch sử, mobile và vòng đời bản đồ |
| Sửa | `tests/ui_overview.py` | Mở trực tiếp Overview; kiểm tra liên kết mới và thêm mốc 1024px |
| Sửa | `tests/ui_market_search.py` | Mở trực tiếp Market; thêm mốc 1024px |
| Sửa | `tests/ui_video_background.py` | Liên kết header mới, thêm Home vào chuỗi chuyển trang và kiểm tra video |
| Sửa | `tests/ui_living_earth.py` | Cập nhật kiểm thử điểm vào mặc định sang Home và màu nền Phase 1 |
| Xóa | `web/src/components/Sidebar.jsx` | Thành phần điều hướng cũ không còn được render |
| Thêm | `docs/phase-2a-navigation-home.md` | Báo cáo này |

Script, ảnh và số đo QA hỗ trợ được lưu trong `.local/`, không được Git theo dõi. Những thay đổi có sẵn trước Phase 2A trong working tree được giữ lại.

## 3. Header toàn cục

Logo giữ nguyên biểu tượng Leaf, hộp mint và chữ GreenSegment AI; nằm ngoài `nav` và liên kết về Home. Desktop dùng lưới ba cột để đặt pill gần giữa màn hình, độc lập với chiều rộng nội dung từng trang. Header sticky nằm trong luồng bố cục; main có khoảng cách riêng phía dưới.

Năm liên kết chính, đúng thứ tự:

1. Trang chủ.
2. Tổng quan.
3. Tra cứu đô thị.
4. Market Explorer.
5. Giới thiệu.

Trang hiện tại có chữ mint, nền nhấn, gạch chỉ báo và `aria-current="page"`. Liên kết có vùng tương tác ít nhất 44px, focus rõ và hover nhẹ. Header không chứa CTA “Khám phá dữ liệu”. Có liên kết bỏ qua header để đến nội dung chính và cập nhật tiêu đề tab theo trang.

## 4. URL, lịch sử và trạng thái

Giữ cách render trang bằng state React, bổ sung hash URL để hoạt động trên host tĩnh mà không cần router mới hoặc cấu hình rewrite phía server:

| Đích | URL |
|---|---|
| Home | `/` hoặc `/#/` |
| Overview | `/#/overview` |
| City Explorer | `/#/city` |
| Hồ sơ đô thị | `/#/city?city=<mã-đô-thị>` |
| Market Explorer | `/#/market` |
| About | `/#/about` |

Liên kết native cập nhật lịch sử trình duyệt; `hashchange` đồng bộ state. Đã kiểm tra Back, Forward, mở trực tiếp và refresh. Click marker và chọn kết quả đô thị ghi mã hồ sơ vào URL, nên có thể refresh hoặc chia sẻ đúng hồ sơ đó. Đường dẫn Advisor cũ vẫn được hỗ trợ dưới dạng `/#/advisor?city=...`, không thêm thành mục điều hướng thứ sáu.

Bộ lọc Overview, cụm phân tích và đô thị vừa chọn tiếp tục được giữ ở cấp App trong cùng phiên. Sau khi đổi trang, focus chuyển đến heading và cuộn về đầu trang. Khi chỉ đổi đô thị trong City Explorer, không cưỡng bức cuộn lại đầu.

Không thêm lưu trữ bền vững: refresh Overview vẫn khởi tạo lại bộ lọc; tìm kiếm cục bộ, bản nháp Market và báo cáo trong các page có thể mất khi page unmount như cơ chế trước đó. Back/Forward khôi phục trang và mã hồ sơ trong URL, không tạo snapshot riêng cho từng thay đổi bộ lọc.

## 5. Home

Hero sử dụng chính video nền toàn màn hình hiện có, với headline **“Hiểu phát thải đô thị toàn cầu”**, mô tả tiếng Việt về phân tích cơ cấu GHG và một CTA **“Khám phá dữ liệu”** dẫn đến Overview.

Ba thẻ là liên kết toàn thẻ, có icon, tiêu đề, mô tả và mũi tên:

- **Tổng quan:** cơ cấu GHG, phân bố địa lý và cụm đô thị.
- **Tra cứu đô thị:** hồ sơ phát thải và so sánh với đặc trưng cụm.
- **Market Explorer:** góc nhìn nghiên cứu thị trường công nghệ xanh từ đặc điểm phát thải.

Các thẻ dùng token kính tối Phase 1 và blur 10px. Hero có lớp che sáng cục bộ, viền chuyển mềm, để chữ vẫn đọc được khi vùng mặt trời của clip đi qua; không đặt overlay mới phủ toàn bộ video. Không sao chép số liệu từ ảnh mockup.

## 6. Thích ứng bố cục và responsive

- Bỏ khoảng chiếm chỗ của sidebar; shell chuyển thành cột với header và main.
- Khung nội dung chính tối đa **1440px**, Home **1320px**, About **1240px**. Các giá trị này bao gồm padding của container.
- Gutter chính lần lượt 40px trên desktop, 28px ở màn hình vừa, 24px trên tablet và 16px ở mobile.
- Header giữ pill ở giữa trên desktop rộng; giảm khoảng cách/font của nav ở 901–1240px để tránh ép nhãn.
- Từ 900px trở xuống dùng nút menu với `aria-expanded` và `aria-controls`. Menu mở trong luồng bố cục, đẩy nội dung xuống thay vì che Hero/bản đồ. Escape đóng và trả focus về nút; click ngoài hoặc chuyển trang cũng đóng menu.
- Ba thẻ Home nằm ngang trên desktop/tablet; từ 630px trở xuống xếp dọc.
- Điều chỉnh vị trí sticky của panel tìm đô thị theo chiều cao header. Biểu đồ so sánh Overview tận dụng chiều rộng mới; vẫn xếp dọc khi màn hình hẹp.
- Giữ thứ tự các section bên trong bốn trang cũ. Header được ẩn khi in; luồng in hồ sơ đô thị được giữ.
- Giảm chuyển động tắt hiệu ứng vào trang và transition mới; cơ chế poster/video theo tùy chọn giảm chuyển động giữ nguyên.

## 7. Chức năng được bảo toàn và sửa lỗi vòng đời bản đồ

Đã đối chiếu snapshot trước Phase 2A: `styles.css`, `constants.js`, `VideoBackground.jsx` và sáu file page hiện có đều không đổi nội dung. Token Emerald Slate, ba màu cụm, bảy màu lĩnh vực, video/poster, playback và nội dung nghiên cứu được giữ nguyên. Không sửa backend, API, CSV, K-Means, tính toán hay nghiệp vụ Gemini.

Provider, URL tile, attribution và cấu hình dự phòng bản đồ **không thay đổi**. `ResizeObserver` hiện có tiếp tục cập nhật kích thước Leaflet khi container đổi chiều rộng.

Kiểm thử chuyển trang nhanh phát hiện callback zoom/canvas của Leaflet có thể chạy sau khi pane/context đã bị hủy. Đã xử lý trong vòng đời từng bản đồ: kết thúc zoom trước teardown, xóa paths khi canvas còn tồn tại và bỏ qua callback redraw khi context đã được hủy. Không đổi dữ liệu, thuật toán vẽ, màu, bán kính, tương tác hay sampling 5.000 điểm. Thêm kiểm thử rời trang trong lúc zoom, lặp ba lần.

Phần bảo vệ này dùng một số API nội bộ của Leaflet 1.9; khi nâng phiên bản Leaflet cần chạy lại kiểm thử điều hướng/zoom/canvas.

## 8. Kết quả kiểm chứng thực tế

`npm run build` thành công. Còn cảnh báo chunk Three.js khoảng **588 KB** từ prototype trước đó; không thêm dependency hoặc thay đổi cấu hình bundle trong Phase 2A.

**37 kiểm thử đã chạy đạt:**

| Bộ kiểm thử | Số ca |
|---|---:|
| Home, điều hướng, URL, bàn phím, responsive và vòng đời bản đồ | 9 |
| Video, reduced motion, fallback, cuộn và chuyển trang | 7 |
| Overview: dữ liệu, filter/reset, cụm, bản đồ, hover/click/touch, loading/empty/error | 11 |
| Market: tìm kiếm, bộ lọc, biểu đồ, Gemini giả lập và lỗi | 9 |
| Điểm vào Home độc lập với prototype 3D | 1 |

Không chạy lại toàn bộ bộ thử nghiệm đồ họa 3D độc lập. Dữ liệu API trong UI tests được xử lý bằng FastAPI TestClient với CSV thật; Gemini được giả lập, không gọi dịch vụ Gemini live.

Kiểm tra/chụp thêm **25 tổ hợp**: Home, Overview, City, Market, About tại **1440, 1024, 768, 390 và 320px**. Không có tràn ngang; main không nằm dưới header; các container Recharts có kích thước dương; kích thước Leaflet khớp container sau resize. Đã xem ảnh desktop/mobile và nội dung Hero trên các khung hình video khác nhau.

Tile **Stadia Alidade Smooth Dark** thật tải được trong lần kiểm tra trực quan localhost. Trong chuỗi chụp Home/Overview/City/About, video đi qua **hai vòng lặp tự nhiên**, tốc độ 1×, giữ nguyên phần tử DOM, không phát sinh `loadstart` mới và không có lỗi JavaScript. Market được chụp bằng ngữ cảnh riêng với truy vấn thực trên dữ liệu và Gemini giả lập.

Các ca trước đó đã thất bại trong lúc tìm lỗi Leaflet; kết quả 37/37 ở trên là lượt kiểm thử sau khi sửa. Chỉnh mềm mép lớp che sáng Hero sau đó được build và kiểm tra lại trong đủ 25 tổ hợp trực quan.

## 9. Ảnh giao diện

Ảnh lưu tại `.local/phase-2a/visual/` và `.local/phase-2a/screenshots/`; không được Git theo dõi.

| Trang | Desktop | Mobile |
|---|---|---|
| Home | [1440px](../.local/phase-2a/visual/home-1440-viewport.png) | [390px](../.local/phase-2a/visual/home-390.png) |
| Overview | [1440px](../.local/phase-2a/visual/overview-1440.png) | [390px](../.local/phase-2a/visual/overview-390.png) |
| City Explorer | [1440px](../.local/phase-2a/visual/city-1440.png) | [390px](../.local/phase-2a/visual/city-390.png) |
| Market Explorer | [1440px](../.local/phase-2a/visual/market-1440.png) | [390px](../.local/phase-2a/visual/market-390.png) |
| About | [1440px](../.local/phase-2a/visual/about-1440.png) | [390px](../.local/phase-2a/visual/about-390.png) |

[Menu mobile](../.local/phase-2a/visual/mobile-menu.png) · [Vùng biểu đồ Overview](../.local/phase-2a/visual/overview-analysis.png) · [Hero ở khung hình khác](../.local/phase-2a/visual/home-later-frame.png).

Ảnh full-page có thể chỉ ghi lớp video fixed ở phần viewport đầu của ảnh; kiểm tra khi cuộn xác nhận video vẫn phủ viewport thực tế.

## 10. Giới hạn

- Đã kiểm tra bằng Chrome trên Windows; chưa kiểm tra Safari/Firefox hoặc GPU điện thoại thật. Đây không phải chứng nhận WCAG toàn website.
- Vị trí, độ phân giải 736×414 và chuyển động của video gốc được giữ nguyên; vì vậy bố cục Trái Đất không giống chính xác ảnh tham chiếu có Trái Đất nằm bên phải.
- Routing dùng hash; không thêm URL sạch phía server hoặc lưu bền vững mọi trạng thái page.
- Điều kiện triển khai Stadia/public từ Phase 1 tiếp tục áp dụng; lần kiểm tra này xác minh localhost, không xác minh tài khoản/domain production.

## 11. Công việc để giai đoạn sau

Chưa tái thiết kế luồng filter, di chuyển cluster selector, sắp xếp lại section, thay kiểu biểu đồ hoặc viết lại nội dung của Overview/City/Market/About. Việc tinh chỉnh bản đồ và thiết kế chi tiết từng trang được giữ cho các phase tiếp theo.
