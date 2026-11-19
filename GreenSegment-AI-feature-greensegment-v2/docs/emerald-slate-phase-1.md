# Emerald Slate — báo cáo Phase 1

## Phạm vi

Áp dụng màu, bề mặt kính và bản đồ tối theo ảnh tham chiếu. Giữ nguyên cấu trúc, kích thước, vị trí, font, nội dung và dữ liệu hiện có. Không chép số liệu hoặc tọa độ trong mockup.

Các file chỉnh sửa trong đợt này:

- `web/src/styles.css`: token màu, bề mặt, trạng thái tương tác, Leaflet và Recharts.
- `web/src/constants.js`: ba màu cụm dùng chung; giữ nguyên bảy màu lĩnh vực.
- `web/src/components/WorldMap.jsx`: Stadia, dự phòng OpenStreetMap, màu marker dùng chung và viền mảnh hơn.
- `web/src/components/SectorCharts.jsx`: màu chữ, lưới, viền chọn và màu hai chuỗi so sánh đô thị/tâm cụm.
- `web/src/pages/Overview.jsx`, `ClusterExplorer.jsx`: lấy màu hiển thị từ bộ màu frontend thay cho màu cũ trong phản hồi API.
- `web/src/pages/MarketExplorer.jsx`: màu cột xếp hạng dùng token accent.
- `tests/ui_overview.py`, `tests/ui_market_search.py`: cập nhật màu/viền được duyệt; chặn dịch vụ tile bên ngoài trong kiểm thử chức năng.

File tạo mới: `web/.env.example` và báo cáo này. Script, ảnh và kết quả đo hỗ trợ nằm trong `.local/emerald-review/` và không được Git theo dõi. Không thêm dependency.

`App.jsx` và `VideoBackground.jsx` giống hệt bản trước khi bắt đầu Phase 1. Video, poster, tốc độ, vị trí và cơ chế phát không đổi. Không sửa backend, API Gemini, EDGAR, K-Means, tính toán hay bộ lọc.

## Hệ màu và bề mặt thực tế

| Token / bề mặt | Giá trị |
|---|---|
| Nền dự phòng | `#0A1B20` |
| Chữ chính / phụ / muted | `#F2FAF7` / `#B5D5CC` / `#A3C5BC` |
| Accent / hover / chữ trên nút mint | `#83DBB9` / `#A1E9CE` / `#0A1B20` |
| Sidebar | `rgb(16 43 44 / 86%)` |
| Panel bộ lọc | `rgb(25 55 53 / 82%)` |
| KPI | `rgb(25 55 53 / 84%)` |
| Panel bản đồ, biểu đồ và nội dung | `rgb(25 55 53 / 87%)` |
| Bề mặt con | `rgb(10 27 32 / 68%)` |
| Input | `rgb(10 27 32 / 82%)` |
| Tooltip / nút chọn cụm trên bản đồ | `rgb(16 43 44 / 97%)` |
| Chọn / vô hiệu hóa | `#235248` / `#253A3B` |
| Viền panel / viền control | `rgb(92 151 136 / 60%)` / `#658F83` |
| Focus / lưới biểu đồ | `#83DBB9` / `#39605C` |
| Nền biển khi tile đang tải | `#071925` |

Bề mặt chính dùng `backdrop-filter: blur(10px)`, kèm tiền tố WebKit. Không blur thêm ở các thành phần con hoặc từng marker. Trình duyệt không hỗ trợ blur dùng nền tối 94% để giữ khả năng đọc. Bóng panel nhẹ; không thêm glow quanh cả thẻ hoặc số KPI. Giữ luồng in hồ sơ đô thị với chữ tối và nền sáng.

Các label cụm nhỏ và nhãn trục đang chọn dùng sắc sáng hơn: 65% màu cụm + 35% trắng. Cách này giữ quan hệ màu và cải thiện tương phản. Nút chọn vẫn có check, viền và trạng thái `aria-pressed`; không chỉ dựa vào màu. Focus bàn phím được giữ rõ. Dropdown native dùng `color-scheme: dark`, option nền đặc tối; màu popup cuối cùng còn phụ thuộc trình duyệt/hệ điều hành.

## Bản đồ và dữ liệu trực quan

Dùng **Stadia Maps — Alidade Smooth Dark** trên localhost. Attribution hiển thị Stadia Maps, OpenMapTiles và OpenStreetMap bằng liên kết nguồn. Leaflet, canvas renderer, tọa độ, giới hạn 5.000 điểm, zoom/pan, auto-fit, tooltip và click mở hồ sơ được giữ nguyên.

Theo [tài liệu xác thực Stadia](https://docs.stadiamaps.com/authentication/), localhost/127.0.0.1 không cần khóa; website public cần xác thực tên miền. Sau khi đăng ký đúng domain trong tài khoản và chọn gói phù hợp, đặt `VITE_STADIA_MAPS_ENABLED=true` trong môi trường build rồi build lại. Không đưa API key vào frontend. [Gói miễn phí](https://stadiamaps.com/pricing/) không cho phép sử dụng thương mại; cần kiểm tra hạn mức và gói trước khi triển khai.

Khi domain public chưa bật cấu hình, hoặc tile Stadia gặp lỗi tải, dùng lại OpenStreetMap có attribution. Dự phòng này là bản đồ sáng; không dùng CSS filter để ép màu raster hoặc vượt xác thực dịch vụ. Không tạo tài khoản hay mua gói tự động.

Alidade Smooth Dark giữ địa lý và nhãn rõ nhưng thiên xám than, **không tái tạo chính xác** biển `#071925`, đất `#112B37`, ranh giới `#294957` và nhãn `#8EADB9` trong mockup. Muốn khớp tuyệt đối cần một nguồn/style bản đồ được cấu hình riêng ở giai đoạn sau.

| Cụm | Marker và chú giải |
|---|---|
| 0 — Dân cư · Giao thông | `#50AEFF` |
| 1 — Công nghiệp | `#FFBE61` |
| 2 — Năng lượng | `#39DEAA` |

Overview dùng lõi đặc, viền trắng 0,65px và viền hover 1,3px. Giữ nguyên bán kính và tăng kích thước hover hiện có. Không thêm các lớp halo/blur/shadow riêng cho hàng nghìn điểm; hiệu ứng sáng đến từ màu lõi, viền và tương phản với nền. Market giữ nguyên kích thước, độ đục và tương tác marker, nhận ba màu mới. Chú giải, selector, chip đô thị, biểu đồ phân bố cụm và tiêu đề hồ sơ cùng dùng `CLUSTER_COLORS`. Bảy màu lĩnh vực vẫn dùng `SECTOR_COLORS` riêng.

## Kiểm chứng và giới hạn

- `npm run build` thành công. Còn cảnh báo chunk Three.js khoảng 588 KB từ prototype trước đó.
- 27 kiểm thử Chrome đạt: 7 video, 11 Overview và 9 Market. Bao gồm bộ lọc, chọn cụm, zoom/pan, hover/click/touch, trạng thái rỗng/lỗi, phản hồi cũ, Gemini giả lập, điều hướng, cuộn, fallback và giảm chuyển động. Không gọi Gemini thật.
- So sánh trước/sau tại 1440, 1024, 768, 390 và 320px: không có chênh lệch quá 1px ở các thành phần đo gồm sidebar, vùng nội dung, heading, bộ lọc, input, KPI, map và các panel phân tích. Không tràn ngang.
- Kiểm tra màu chữ trên các bề mặt chính bằng cách tổng hợp alpha qua các lớp, giả định video trắng hoàn toàn phía sau. Các cặp đã đo đạt ít nhất 4,5:1; đây không phải chứng nhận WCAG toàn website. Heading ngoài panel còn được kiểm tra trực quan khi video đang phát.
- Đo zoom canvas với 5.000 marker: khoảng 43–233 ms trong bốn thao tác kiểm thử Chrome headless; các marker được tái sử dụng. Đây không phải benchmark GPU trên điện thoại thật.
- Đã mở và chụp dropdown quốc gia: Chrome hiển thị nền tối và chữ sáng; vùng option đang chọn vẫn dùng highlight xanh của hệ thống. Đã kiểm tra menu mobile mở, tooltip bản đồ, các trạng thái tải/rỗng/lỗi và dự phòng khi Stadia bị chặn. Đã chụp City, Market và About sau khi hiệu ứng biểu đồ/chuyển trang hoàn tất.
- Ảnh chụp và JSON đo nằm tại `.local/emerald-review/`. Kiểm thử với Chrome trên Windows; chưa xác minh popup native của Firefox/Safari hoặc hiệu năng thiết bị yếu.

Số liệu thực, mật độ điểm, bố cục và nội dung được giữ nguyên nên không giống các con số, vị trí điểm, kích thước và cách sắp xếp trong ảnh AI. Nguồn video 736×414 và các giới hạn hòa trộn của clip trước đó vẫn còn; Phase 1 không chỉnh media.
