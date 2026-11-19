**Báo cáo triển khai Phase 2C — Tra cứu đô thị**

Đã triển khai trực tiếp trong workspace ngày 18/11/2026. Trang được tổ chức theo hồ sơ đô thị, với công cụ tìm kiếm ngữ cảnh bên trái và nội dung phân tích bên phải. Phạm vi thay đổi là giao diện City Explorer và màu của hai chuỗi biểu đồ so sánh.

**Các tệp thay đổi trong Phase 2C**

| Tệp | Thay đổi |
| --- | --- |
| `web/src/pages/CityExplorer.jsx` | Tiêu đề tiếng Việt, đo khoảng trống sticky, hồ sơ/KPI, tóm tắt chênh lệch từng dòng, nhãn phân vị, trạng thái Gemini chưa có báo cáo. |
| `web/src/components/SectorCharts.jsx` | Thêm `clusterId` cho `CitySectorChart`; áp dụng hai sắc độ theo cụm cho cột và chú giải. |
| `web/src/main.jsx` | Nạp stylesheet riêng cho City Explorer. |
| `web/src/city-explorer.css` | Tệp mới: bố cục, danh sách cuộn riêng, bảng trên điện thoại, thẻ thống kê và căn giữa trạng thái Gemini. |
| `web/src/components/CentroidDistanceHelp.jsx` | Tệp mới: tooltip khoảng cách đến tâm cụm. |
| `tests/ui_city_explorer.py` | Tệp mới: 11 kiểm thử giao diện bằng Chrome/Playwright, dùng dữ liệu thật và phản hồi Gemini giả lập. |
| `docs/phase-2c-city-explorer.md` | Báo cáo này. |

Workspace có sẵn các thay đổi từ những giai đoạn trước. Danh sách trên chỉ mô tả phần thực hiện trong lần này. Không thêm thư viện.

**Tìm kiếm ngữ cảnh và cuộn trang**

Ở màn hình rộng trên 900px, trang giữ hai cột. Cột tìm kiếm dùng chiều rộng linh hoạt khoảng 27%, giới hạn từ 250px đến 340px; cột hồ sơ nhận phần diện tích còn lại. Tên đô thị trong danh sách được xuống dòng thay vì bị cắt bằng dấu ba chấm.

Sticky lấy chiều cao thật của `.global-header` cộng 16px. Chiều cao tối đa của panel tính theo vị trí hiện tại và chiều cao viewport, chừa thêm 16px phía dưới. Khi mới mở trang, phép đo tính cả phần giới thiệu phía trên; khi cuộn xuống, danh sách có thể tận dụng phần không gian lớn hơn. `ResizeObserver` và cập nhật qua `requestAnimationFrame` xử lý thay đổi kích thước, cuộn và kết thúc hiệu ứng xuất hiện trang.

Chỉ danh sách kết quả cuộn bên trong; tiêu đề, ô nhập, số kết quả và phân trang nằm ngoài vùng cuộn. Không thay đổi header, không tăng lớp phủ lên trên điều hướng và không khóa cuộn trang. Từ 900px trở xuống, tìm kiếm nằm trước hồ sơ, bỏ sticky và giới hạn danh sách ở chiều cao phù hợp cho tablet/điện thoại.

Giữ nguyên tìm theo tên/quốc gia, độ trễ 200ms, thứ tự kết quả, 10 kết quả mỗi trang, Trước/Sau, callback chọn đô thị và URL `#/city?city=...`.

**Hồ sơ đô thị và tooltip**

Tiêu đề trang là “Tra cứu đô thị”; mô tả khoa học hiện có được giữ nguyên. Tên đô thị là thành phần nổi bật, tiếp theo là quốc gia/mã đô thị và nguồn EDGAR 2024. Badge cụm ở phía trên bên phải trên desktop, dùng màu cụm thực tế.

Giữ đúng ba KPI: Tổng GHG 2024, Lĩnh vực lớn nhất, Khoảng cách đến tâm cụm. Ba thẻ cùng hàng trên desktop và xếp dọc trên điện thoại. Giá trị, tỷ trọng lĩnh vực lớn nhất, cách làm tròn và ghi chú “Đơn vị gốc EDGAR*” được giữ nguyên; không suy đoán hoặc chuyển đổi đơn vị.

Một nút thông tin nhỏ cạnh nhãn khoảng cách mở nội dung:

“Khoảng cách Euclid giữa cơ cấu tỷ trọng phát thải của đô thị và tâm cụm K-Means trong không gian 7 lĩnh vực. Đây không phải khoảng cách địa lý.”

Tooltip mở bằng hover, focus bàn phím hoặc nhấn/chạm; có thể đóng bằng Escape, nhấn/chạm lại hoặc nhấn bên ngoài. Có liên kết `aria-describedby`, trạng thái `aria-expanded`, đặt lại vị trí khi cuộn/resize và giới hạn trong viewport. Nội dung được hiển thị qua portal để tránh bị surface có hiệu ứng kính cắt mất.

**Biểu đồ và bảng dữ liệu**

Giữ tiêu đề “Đô thị và tâm K-Means”; mô tả chính xác là “So sánh 7 tỷ trọng GHG với tâm mô hình”. Hai màu tự động lấy theo `current.cluster_id`:

| Cụm | Đô thị | Tâm K-Means | Đô thị thật đã kiểm tra |
| --- | --- | --- | --- |
| 0 | `#50AEFF` | `#A8D8FF` | Los Angeles — 2007 |
| 1 | `#FFBE61` | `#FFE0A7` | Shanghai — 11345 |
| 2 | `#39DEAA` | `#A2F5D9` | Nagoya — 5213 |

Chú giải dùng cùng màu với các cột. Không điều chỉnh các mã màu đã duyệt. Giữ đủ bảy lĩnh vực, thứ tự, tỷ trọng, tâm mô hình, trục 0–100% và tooltip biểu đồ. Không thêm radio chuyển cụm. Bảng màu bảy lĩnh vực ở các thành phần khác được giữ nguyên.

Tóm tắt “Chênh lệch nổi bật so với tâm cụm” trình bày mỗi lĩnh vực trên một dòng, tên bên trái và chênh lệch bên phải. Vẫn dùng `notable_differences`, thứ tự hiện có, dấu cộng/trừ, hàm làm tròn và đơn vị điểm phần trăm. Giữ câu “Đây là mô tả, không phải kiểm định thống kê.”

Bảng phát thải giữ bảy dòng và năm cột, tất cả giá trị và ghi chú. Điều chỉnh khoảng cách hàng và căn phải số liệu. Ở màn hình hẹp, bảng có vùng cuộn ngang riêng, có thể focus bằng bàn phím; không ép cả năm cột vào chiều rộng điện thoại.

**Khoảng cách và thống kê mở rộng**

Giữ ba thống kê chính, diễn giải vị trí trong cụm, số thành viên tham chiếu và toàn bộ cảnh báo khoa học. Phần “Xem thống kê mở rộng của cụm” vẫn đóng mặc định và dùng hành vi mở/đóng hiện có.

Bốn nhãn đầy đủ là Tứ phân vị thứ nhất (Q1), Tứ phân vị thứ ba (Q3), Phân vị thứ 90 (P90), Phân vị thứ 95 (P95). Bốn thẻ cùng hàng khi đủ rộng; từ 1200px trở xuống là bố cục 2 × 2. Có thêm câu giải thích các mốc mô tả phân bố khoảng cách của các đô thị cùng cụm tới tâm K-Means. Giá trị phân vị và bảng thống kê bảy lĩnh vực với trung bình, trung vị, độ lệch chuẩn, IQR được giữ nguyên.

**Gemini và các chức năng được bảo toàn**

Khi chưa có báo cáo, icon tài liệu, thông báo cho đô thị đang chọn và một nút “Phân tích bằng Gemini” được căn giữa theo nhóm dọc. Giữ tiêu đề, mô tả khoa học và thông tin kiểm tra/làm tròn dữ liệu hiện có. Vì giữ phần mô tả này, panel có thêm dòng thông tin so với ảnh minh họa ngắn.

Phần mã trình bày báo cáo đã tạo được đối chiếu với bản lưu trước khi sửa và giữ nguyên. Các effect tìm kiếm/tải hồ sơ, hàm gọi Gemini, trạng thái theo từng đô thị, hủy yêu cầu, lỗi, thử lại và tạo lại báo cáo cũng được đối chiếu và giữ nguyên. Báo cáo của đô thị trước không xuất hiện trong hồ sơ đô thị mới.

Không thay đổi backend, API, dữ liệu EDGAR, phân cụm K-Means, công thức thống kê, route, header, các trang khác, màu theo lĩnh vực hoặc video nền. Hai hàm biểu đồ dùng ở nơi khác là `ClusterStackedChart` và `SectorProgress` được đối chiếu và không đổi trong lần này.

Ảnh mẫu ba lĩnh vực và các nút radio chỉ minh họa màu. Bản triển khai giữ bảy lĩnh vực và cụm do dữ liệu quyết định, theo yêu cầu bằng văn bản.

**Kết quả kiểm chứng thực tế**

| Kiểm tra | Kết quả |
| --- | --- |
| `npm run build` trong `web` | Thành công; Vite 6.4.5, 2001 module, lần build cuối 5,78 giây. |
| `tests/test_city_explorer.py` | 9/9 đạt: đối chiếu CSV thật, phép tính khoảng cách/tỷ trọng, tìm kiếm và xử lý Gemini giả lập. |
| `tests/ui_city_explorer.py` | 11/11 đạt. |
| `tests/ui_overview_ux.py` | 10/10 đạt. |
| `tests/ui_overview.py` | 11/11 đạt. |
| `tests/ui_navigation.py` | 9/9 đạt. |
| `tests/ui_video_background.py` | 7/7 đạt. |
| `tests/ui_market_search.py` | 9/9 đạt. |
| Kiểm thử Trang chủ không tải nội dung 3D | 1/1 đạt. |

Tổng cộng: 9 kiểm thử City Explorer hiện có và 58 kiểm thử giao diện đạt, gồm 11 kiểm thử City Explorer mới và 47 kiểm thử hồi quy. Không có lỗi JavaScript trong các kiểm thử này.

Kiểm thử giao diện chạy trên bản build qua Vite preview với Chrome headless. Các GET được xử lý bằng FastAPI TestClient với dữ liệu CSV thật; mọi POST Gemini đều được giả lập, không gọi dịch vụ Gemini thật.

Đã kiểm tra tên/quốc gia, số lượng kết quả, phân trang, chọn/highlight đô thị, URL trực tiếp, chưa chọn đô thị, đang tải, không có kết quả, hồ sơ không tồn tại, lỗi dữ liệu và thử tải lại. Có giữ phản hồi cũ rồi chuyển sang đô thị mới để xác nhận phản hồi chậm không thay thế hồ sơ hiện tại.

Đã kiểm tra sticky và khả năng nhấn điều hướng/phân trang, cuộn riêng danh sách, tooltip bằng chuột/bàn phím/chạm, bounds tooltip ở 320/390px, ba cụm màu, chiều dài tương đối của cột, chú giải, nhãn/trục và tooltip biểu đồ. Các ô dữ liệu bảy lĩnh vực, chênh lệch, ba KPI khoảng cách và thống kê mở rộng được đối chiếu với API thật.

Đã kiểm tra Gemini chưa có báo cáo, đang tải, lỗi, thử lại, thành công, tạo lại, bộ nhớ theo đô thị và hủy yêu cầu khi chuyển đô thị. Báo cáo giả lập giữ đúng các phần và nội dung danh sách theo cấu trúc hiện có.

Đã chụp và xem giao diện ở 1440, 1024, 768, 390 và 320px. Ảnh responsive được chụp khi video nền chạy. Không có tràn ngang toàn trang tại các kích thước kiểm tra; điện thoại cuộn ngang bên trong bảng. Bố cục thẻ phân vị được kiểm tra ở cả năm kích thước.

**Ảnh và nhật ký trong workspace**

- [Desktop trước thay đổi](../.local/phase-2c/before/city-1440.png) và [desktop sau thay đổi](../.local/phase-2c/after/city-1440.png).
- [1024px](../.local/phase-2c/after/city-1024.png), [768px](../.local/phase-2c/after/city-768.png), [390px](../.local/phase-2c/after/city-390.png), [320px](../.local/phase-2c/after/city-320.png).
- [Cụm 0](../.local/phase-2c/after/cluster-0.png), [Cụm 1](../.local/phase-2c/after/cluster-1.png), [Cụm 2](../.local/phase-2c/after/cluster-2.png).
- [Panel tìm kiếm khi cuộn](../.local/phase-2c/after/sticky-search.png), [tooltip trên điện thoại](../.local/phase-2c/after/tooltip-320.png).
- [Thống kê mở rộng](../.local/phase-2c/after/extended-statistics.png), [báo cáo Gemini giả lập](../.local/phase-2c/after/gemini-report.png).
- [Kết quả nghiệm thu](../.local/phase-2c/acceptance-results.json), [nhật ký City Explorer](../.local/phase-2c/city-ui.log), [đối chiếu phạm vi mã nguồn](../.local/phase-2c/scope-audit.json).

Các ảnh, bản lưu trước khi sửa và nhật ký nằm trong `.local`, đang được Git bỏ qua. Đây là bằng chứng cục bộ để xem lại, không phải tài nguyên đưa lên website.

**Giới hạn còn lại**

Chưa kiểm tra trực tiếp Safari/Firefox hoặc điện thoại vật lý; thao tác chạm được mô phỏng bằng Playwright. Không kiểm tra chất lượng phản hồi từ dịch vụ Gemini thật trong lần này. Build còn cảnh báo có chunk lớn hơn 500kB: chunk cảnh 3D của trang thử nghiệm Living Earth vẫn là 588,39kB; đây là cảnh báo sẵn có, không làm build thất bại. Không phát hiện lỗi chức năng còn tồn tại trong phạm vi Phase 2C đã kiểm tra.
