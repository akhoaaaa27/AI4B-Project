# Phase 2B — Bố cục và trải nghiệm Overview

## 1. Kết quả triển khai

Đã bỏ dải nền tối và vùng chặn tương tác của wrapper header; thu gọn bộ lọc; cân bằng bốn KPI; đưa bản đồ lên sớm hơn và tăng chiều cao; thêm selector cụm mở/thu gọn; rút chú thích bản đồ còn hai dòng; làm gọn trạng thái Gemini chưa có báo cáo; trình bày lại nguồn dữ liệu và lưu ý phương pháp.

Giữ nguyên tiêu đề “Bức tranh phát thải đô thị toàn cầu”, mô tả khoa học, hệ màu Emerald Slate, video, điều hướng, basemap, dữ liệu và nghiệp vụ phân tích. Không thêm dependency.

## 2. File thay đổi trong riêng Phase 2B

| Thao tác | File | Mục đích |
|---|---|---|
| Thêm | `web/src/components/MapClusterSelector.jsx` | Trình bày selector và trạng thái mở/thu gọn cục bộ |
| Thêm | `web/src/overview.css` | Bố cục và responsive có phạm vi Overview |
| Sửa | `web/src/pages/Overview.jsx` | Selector mới, chú thích động, KPI số lĩnh vực lấy từ `SECTORS` |
| Sửa | `web/src/components/DataFilters.jsx` | Đưa giải thích và reset vào hàng phụ chung |
| Sửa | `web/src/pages/ClusterExplorer.jsx` | Nhãn giải thích GHG, trạng thái Gemini rỗng và khối phương pháp |
| Sửa | `web/src/navigation.css` | Bỏ nền wrapper header và sửa vùng nhận pointer |
| Sửa | `web/src/main.jsx` | Nạp CSS Overview sau CSS chung |
| Sửa | `tests/ui_overview.py` | Cập nhật kỳ vọng selector mặc định đóng và chú thích mới, giữ các kiểm tra chức năng |
| Thêm | `tests/ui_overview_ux.py` | Tám kiểm thử UI/UX và Gemini giả lập |
| Thêm | `docs/phase-2b-overview.md` | Báo cáo này |

Không xóa file trong Phase 2B. Script QA, ảnh và số đo lưu trong `.local/phase-2b/`, không được Git theo dõi. Các thay đổi có sẵn trong working tree trước đợt này được giữ lại.

## 3. Nguyên nhân và cách sửa header

Wrapper `.global-header` trước đây có gradient toàn chiều ngang, từ nền tối 78% xuống 8%. Nó và `.global-header-inner` mặc định nhận pointer trên cả các khoảng trống. Trong phép đo trước sửa, điểm `(1200, 50)` trên phần bản đồ nằm dưới khoảng trống header trả về `global-header-inner`, thay vì canvas bản đồ.

Đã bỏ gradient, đặt `pointer-events: none` trên hai wrapper và bật lại `pointer-events: auto` cho logo, pill navigation, nút menu và skip link. Không tạo lớp phủ thay thế. Vị trí sticky, năm đích điều hướng, nhãn, active state và logic bàn phím giữ nguyên.

Sau sửa, cùng vùng kiểm tra trả về canvas Leaflet. Kiểm thử chuột thực tế đã mở dropdown, dùng wheel zoom và kéo bản đồ qua vùng header trống. Những phần được logo/pill thực sự che vẫn là vùng tương tác của logo/pill; các khoảng trống còn lại không chặn nội dung phía dưới.

## 4. Bộ lọc và KPI

Ba dropdown vẫn cùng một hàng trên desktop, dùng nguyên giá trị, ID, icon và callback. “Cụm phát thải là gì?” và reset nằm chung hàng phụ; khi mở giải thích, panel tăng chiều cao tự nhiên. Tablet cho phép wrap, mobile xếp các field dọc và giữ hàng phụ gọn khi giải thích đang đóng. Control mobile có vùng tương tác tối thiểu 44px.

Bốn KPI giữ icon, hierarchy và dữ liệu hiện có. Padding desktop giảm có kiểm soát; chiều cao thẻ ở 1440px giảm từ 110 xuống 102px. Grid dùng hàng có chiều cao cân bằng, kể cả khi label xuống dòng trên mobile. Chữ phụ mobile từ 9px trước đó lên 10px; số chính vẫn ít nhất 21px. KPI lĩnh vực vẫn hiển thị `07`, nhưng lấy độ dài từ danh sách `SECTORS` thay cho literal.

## 5. Bản đồ và số đo trước/sau

Bản đồ vẫn nằm gần toàn chiều rộng trong một panel, không tách thành “Map + sidebar”. Đã giảm khoảng cách đầu trang, bỏ các câu hướng dẫn lặp phía trên map và giảm khoảng cách các section. Chart và profile vẫn ở dưới bản đồ.

Chiều cao bản đồ desktop dùng `clamp(460px, 54vh, 560px)`; tablet tối đa 900px dùng 460px; mobile tối đa 630px dùng 420px. Chiều rộng còn lại do container hiện có quyết định. `WorldMap.jsx`, provider, URL tile, attribution, fallback, marker, sampling và cơ chế resize không thay đổi.

Đo tại viewport cao **1000px**, cùng dữ liệu mặc định:

| Rộng | Cao bộ lọc trước → sau | Vị trí đầu bản đồ trước → sau | Cao bản đồ trước → sau |
|---|---:|---:|---:|
| 1440px | 190,4 → 140px | 708,6 → 541,4px | 374 → 540px |
| 1024px | 190,4 → 140px | 685,8 → 522,6px | 345 → 540px |
| 768px | 272,4 → 220px | 775,3 → 614,2px | 345 → 460px |
| 390px | 344,4 → 314px | 985,5 → 875px | 340 → 420px |
| 320px | 344,4 → 314px | 1062,3 → 905px | 340 → 420px |

Đơn vị vị trí là CSS pixel tính từ đầu tài liệu; không bao gồm thanh công cụ trình duyệt.

## 6. Selector cụm

Selector vẫn nằm trong map, mặc định thu gọn với “Chọn cụm” và “Đang xem: …”. Nút native có `aria-expanded`, `aria-controls`, nhãn mở/thu gọn và hỗ trợ bàn phím. Trạng thái này chỉ là UI cục bộ, không thay đổi filter, camera, dữ liệu hoặc các đối tượng marker; đã kiểm tra lặp nhiều lần.

Khi mở, cả bốn lựa chọn đều có cùng cấp: Tất cả 3 cụm, Cụm 0 — Dân cư - Giao thông, Cụm 1 — Công nghiệp, Cụm 2 — Năng lượng. Giữ nguyên ba màu `#50AEFF`, `#FFBE61`, `#39DEAA`, nền/viền selected và checkmark. Desktop dùng chiều rộng mở 240px; mobile dùng hai cột trong phần map còn trống cạnh zoom controls. Không thêm blur vào selector hoặc từng option.

Chỉ cụm cụ thể đang chọn có số đô thị. Chọn All không hiện số; các cụm không chọn không hiện số. Không còn phần trăm trong selector. Sau chọn, panel giữ trạng thái mở trên cả desktop và mobile, nên người dùng có thể đổi tiếp hoặc chủ động thu gọn.

Chọn từ selector vẫn gọi callback filter hiện có; chọn từ dropdown hoặc chart vẫn cập nhật selector và profile. All giữ cơ chế đặc biệt cũ: hiển thị cả ba cụm trên bản đồ nhưng không xóa hồ sơ cụm đang phân tích.

## 7. Nguồn số lượng và chú thích

- Số đô thị trong option lấy từ `/api/overview` → `clusters[].city_count`, tức quy mô toàn bộ cụm. Không lấy từ số marker đang vẽ và không hardcode các con số ví dụ.
- Chú thích dòng đầu lấy `shown` và `total_matching` từ `/api/cities/map`. Mẫu mặc định là “Đang hiển thị 5.000/11.422 đô thị.”, tự cập nhật khi đổi filter hoặc kết quả rỗng.
- `total_matching` của API map là các đô thị phù hợp có tọa độ hợp lệ. Tooltip của chú thích làm rõ phạm vi này; nó không phải tổng quy mô cụm ở selector.
- Dòng hai giữ “Nhấn vào một điểm để xem hồ sơ đô thị.”

Đã bỏ các dòng giải thích lấy mẫu/kết nối Internet thường trực. Trạng thái đang tải, lỗi dữ liệu, thông báo rỗng, nút tải lại và fallback tile cũ vẫn còn. Phần trăm ở profile và biểu đồ được giữ nguyên.

## 8. Biểu đồ, Gemini và phương pháp

Giữ biểu đồ so sánh bên trái và profile bên phải ở desktop; xếp dọc theo breakpoint cũ khi màn hình hẹp. `SectorCharts.jsx` không đổi: màu bảy lĩnh vực, dữ liệu, selected highlight và dimming 0,4 của cụm không chọn được giữ nguyên. Nhãn expandable đổi đúng thành “GHG, cơ cấu phát thải và tâm K-Means”; nội dung giải thích không đổi.

Gemini chưa có báo cáo nay có heading/icon cũ, lời giải thích, một thông báo chưa có báo cáo và nút tạo báo cáo trong panel gọn. Đã bỏ câu nhắc bấm nút lặp ở dưới. Khi có kết quả, giữ toàn bộ section, đoạn và danh sách của báo cáo; container tăng tự nhiên theo nội dung, không fixed height hoặc tạo vùng cuộn bên trong.

Không sửa `analyze`, endpoint, prompt hoặc phương pháp. Đã kiểm tra tạo lại khi báo cáo cũ còn hiển thị, lỗi/thử lại, cache theo từng cụm và phản hồi cũ sau khi chuyển cụm. Nội dung cụm 0 không bị hiển thị dưới cụm 1.

Khối cuối trang nay là panel “Nguồn dữ liệu & lưu ý phương pháp”, có heading/icon, khoảng cách rõ và chiều rộng đọc tối đa 110ch. Giữ EDGAR 2024, K-Means, bảy tỷ trọng ngành, giải thích nguồn expandable và nguyên văn cảnh báo rằng cơ cấu phát thải không đủ để kết luận nguyên nhân hoặc tính khả thi giải pháp công nghệ.

## 9. Build và kiểm thử

`npm run build` thành công. Còn cảnh báo chunk Three.js khoảng 588 KB từ prototype trước đó.

**45 kiểm thử riêng biệt đã chạy đạt:**

| Bộ kiểm thử | Số ca |
|---|---:|
| UI/UX Overview mới, selector, caption, pointer và Gemini giả lập | 8 |
| Overview hiện có: dữ liệu, đồng bộ, camera, filter/reset, hover/click/touch, rỗng/lỗi | 11 |
| Điều hướng và header dùng chung, URL, refresh, Back/Forward, menu mobile | 9 |
| Video, vòng lặp, cuộn, chuyển trang, fallback và giảm chuyển động | 7 |
| Khám phá thị trường và Gemini giả lập | 9 |
| Home không tải prototype 3D | 1 |

Sau tinh chỉnh cuối cùng để hàng phụ bộ lọc mobile gọn hơn, đã build lại, chạy lại ca responsive gồm đủ năm kích thước, mở/đóng giải thích, selector và báo cáo dài, rồi chụp/đo lại toàn bộ năm kích thước. Không bỏ các assertion chức năng để làm test pass.

Dữ liệu UI tests dùng FastAPI TestClient và CSV thật. Phản hồi Gemini được giả lập; không gọi hoặc xác nhận Gemini live. Lần kiểm tra trực quan tải được tile Stadia thật. Không phát hiện lỗi JavaScript, tràn ngang hoặc báo cáo bị cắt; video giữ cùng phần tử, tốc độ 1× và không phát sinh tải lại trong chuỗi chụp.

Đã đối chiếu snapshot: App, routing, GlobalHeader JSX, WorldMap, video component, SectorCharts, color constants, CSS Phase 1, Home, City, Khám phá thị trường và About không đổi nội dung trong Phase 2B. Không sửa API/backend/dataset.

## 10. Ảnh và số đo

Ảnh và JSON lưu trong `.local/phase-2b/`, không được Git theo dõi:

- [Trước — Overview 1440px](../.local/phase-2b/before/overview-1440.png).
- [Sau — Overview 1440px](../.local/phase-2b/visual/overview-1440.png).
- [Sau — Overview 390px](../.local/phase-2b/visual/overview-390.png).
- [Header trên bản đồ](../.local/phase-2b/visual/header-over-map.png).
- [Selector thu gọn](../.local/phase-2b/visual/selector-collapsed-1440.png), [mở và chọn cụm](../.local/phase-2b/visual/selector-selected-1440.png), [320px](../.local/phase-2b/visual/selector-selected-320.png).
- [Chart và profile](../.local/phase-2b/visual/chart-profile.png).
- [Gemini rỗng](../.local/phase-2b/visual/gemini-empty.png), [đang tải](../.local/phase-2b/visual/gemini-loading.png), [lỗi](../.local/phase-2b/visual/gemini-error.png), [báo cáo giả lập](../.local/phase-2b/visual/gemini-report-1440.png).
- [Số đo trước](../.local/phase-2b/before/measurements.json), [kiểm tra sau](../.local/phase-2b/visual/verification.json).

Ảnh trước được chụp với tile bị chặn để đo layout ổn định; ảnh trực quan sau dùng tile thật. Ảnh full-page của Chrome có thể chỉ ghi video fixed ở vùng viewport đầu; kiểm tra cuộn đã xác nhận video vẫn phủ viewport thực tế.

## 11. Giới hạn và phần giữ lại cho giai đoạn sau

Đã kiểm tra trên Chrome/Windows, chưa kiểm tra Safari, Firefox hoặc GPU thiết bị mobile thật; chưa thực hiện đánh giá WCAG toàn diện. Bố cục màu basemap, độ phân giải/điểm nối video và cấu hình domain Stadia production tiếp tục như trước. Không tái thiết kế Home hoặc layout chi tiết các trang khác. Không còn vấn đề chức năng chưa xử lý được phát hiện trong các kiểm tra đã thực hiện.
