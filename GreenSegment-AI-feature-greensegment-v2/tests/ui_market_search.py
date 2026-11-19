"""Browser integration checks. Start Vite, then run python tests/ui_market_search.py.

Uses installed Chrome and the real FastAPI query engine through intercepted /api
requests. Only Gemini responses are mocked; no credentials or external API calls.
Requires Python playwright. Override MARKET_UI_URL / MARKET_CHROME if needed.
"""
import csv
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright, expect

from api import advisor_service as advisor, data_service as data, market_service as market
from api.main import app
import test_market_explorer as fixtures


class MarketSearchBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=os.environ.get("MARKET_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            headless=True,
        )
        cls.api = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000}, has_touch=True, reduced_motion="reduce")
        self.page = self.context.new_page()
        self.page_errors = []
        self.page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        self.calls = []
        self.parse_failure = False
        self.unsupported = []
        self.defer_parse = False
        self.held_parse = None
        self.held_search = None
        self.defer_search = False
        self.defer_report = False
        self.held_report = None
        self.parse_context = {}
        self.parsed_query = market.MarketQuery(sector="industry", countries=["Japan"],
                                                min_sector_share_percent=30).model_dump()
        self.page.route("**/api/**", self.api_route)
        self.page.route("https://*.tile.openstreetmap.org/**", lambda route: route.abort())
        self.page.route("https://tiles.stadiamaps.com/**", lambda route: route.abort())
        self.page.goto(os.environ.get("MARKET_UI_URL", "http://127.0.0.1:5174").rstrip('/') + '/#/market')
        expect(self.page.locator("#market-request")).to_be_visible()

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.page_errors, [])

    def api_route(self, route):
        request = route.request
        path = request.url.split("/api", 1)[1]
        payload = request.post_data_json if request.method == "POST" else None
        self.calls.append((path, payload))
        if path == "/market/parse":
            if self.defer_parse:
                self.held_parse = route
                return
            if self.parse_failure:
                with patch.object(advisor._advisor(), "call_gemini", side_effect=RuntimeError("Chưa đặt GEMINI_API_KEY")):
                    response = self.api.post("/api" + path, json=payload)
            else:
                parsed = {"query": self.parsed_query, "interpretation": "Phạm vi nghiên cứu.",
                          "assumptions": [], "unsupported_criteria": self.unsupported, **self.parse_context}
                with patch.object(advisor._advisor(), "call_gemini", return_value=parsed):
                    response = self.api.post("/api" + path, json=payload)
        elif path == "/market/report":
            if self.defer_report:
                self.defer_report = False
                self.held_report = route
                return
            context = market.report_context(market.ReportRequest.model_validate(payload))
            with patch.object(advisor._advisor(), "call_gemini", return_value=fixtures.MarketExplorerTests.report_fixture(context)):
                response = self.api.post("/api" + path, json=payload)
        else:
            # Searching must work even if the Gemini module cannot initialize.
            with patch.object(advisor, "_advisor", side_effect=AssertionError("No Gemini for search")):
                response = self.api.request(request.method, "/api" + path, **({"json": payload} if payload is not None else {}))
        if path == "/market/search" and self.defer_search:
            self.defer_search = False
            self.held_search = (route, response)
            return
        route.fulfill(status=response.status_code, content_type="application/json", body=response.content)

    def manual(self):
        self.page.locator('.market-mode-switch button').nth(1).click()
        expect(self.page.locator("#market-request")).to_have_count(0)
        expect(self.page.locator("#market-sector")).to_be_visible()

    def search(self):
        self.page.locator('#market-search-panel button[type="submit"]').click()
        expect(self.page.locator(".market-results")).to_be_visible()

    def ids(self):
        return self.page.locator(".market-table tbody th").all_text_contents()

    def test_manual_offline_same_ai_query_and_report_for_both_modes(self):
        self.manual()
        self.page.locator("#market-countries").select_option(["Japan"])
        self.page.locator("#market-min").fill("30")
        self.search()
        manual_names = self.ids()
        expect(self.page.locator(".stat-card").first.locator("strong")).to_have_text("40")
        self.assertEqual(len(manual_names), 10)
        self.assertFalse(any(path == "/market/parse" for path, _ in self.calls))
        self.page.get_by_role("button", name="Tạo báo cáo thị trường", exact=True).click()
        expect(self.page.locator(".ce-report")).to_be_visible()
        self.assertEqual([p for route, p in self.calls if route == "/market/report"][-1]["business_request"], "")
        self.page.locator('.market-mode-switch button').first.click()
        expect(self.page.locator(".market-results")).to_have_count(0)
        expect(self.page.locator("#market-sector")).to_have_count(0)
        self.page.locator("#market-request").fill("Tìm 10 đô thị Nhật Bản có tỷ trọng công nghiệp từ 30%")
        self.search()
        self.assertEqual(self.ids(), manual_names)
        expect(self.page.locator(".market-applied")).to_contain_text("30%")
        self.assertEqual([p for path, p in self.calls if path == "/market/search"][-2:],
                         [self.parsed_query, self.parsed_query])
        expect(self.page.get_by_text("Cách hiểu sơ bộ", exact=False)).to_have_count(0)
        expect(self.page.locator('input[type="checkbox"]')).to_have_count(0)
        self.page.get_by_role("button", name="Tạo báo cáo thị trường", exact=True).click()
        expect(self.page.locator(".ce-report")).to_be_visible()
        self.page.locator("#market-request").fill("Yêu cầu mới chưa tìm kiếm")
        expect(self.page.locator(".market-results")).to_have_count(0)

    def test_unsupported_ai_request_blocks_search_and_can_be_revised(self):
        self.unsupported = ["Chưa có dữ liệu ngân sách mua sắm"]
        self.page.locator("#market-request").fill("Tìm đô thị có ngân sách mua sắm lớn")
        self.page.locator('#market-search-panel button[type="submit"]').click()
        expect(self.page.get_by_text("Chưa thể tìm kiếm.", exact=False)).to_be_visible()
        expect(self.page.locator(".market-applied")).to_have_count(0)
        self.assertFalse(any(path == "/market/search" for path, _ in self.calls))
        self.unsupported = []
        self.page.locator("#market-request").fill("Tìm 10 đô thị Nhật Bản có tỷ trọng công nghiệp từ 30%")
        self.search()

    def test_solar_lamp_business_context_searches_vietnam_without_buyer_claims(self):
        self.unsupported = ["Lọc theo nhu cầu mua hàng, ngân sách hoặc quy mô doanh thu."]
        self.page.locator("#market-request").fill("Tôi muốn bán đèn năng lượng mặt trời ở Việt Nam.")
        self.search()
        expect(self.page.locator(".market-applied")).to_contain_text("đèn năng lượng mặt trời")
        expect(self.page.locator(".market-applied")).to_contain_text("Khám phá chung theo tổng GHG")
        query = [payload for path, payload in self.calls if path == "/market/search"][-1]
        self.assertEqual(query["countries"], ["Vietnam"])
        self.assertEqual(query["sector"], "all")
        self.assertEqual(query["sort_by"], "total_ghg")
        expect(self.page.locator(".market-table tbody tr")).to_have_count(10)
        self.assertTrue(all(country == "Vietnam" for country in self.page.locator(".market-table tbody td:first-of-type").all_text_contents()))

    def test_manual_still_works_after_gemini_failure(self):
        self.parse_failure = True
        self.page.locator("#market-request").fill("Tìm đô thị công nghiệp")
        self.page.locator('#market-search-panel button[type="submit"]').click()
        expect(self.page.get_by_text("Chưa đặt GEMINI_API_KEY", exact=False)).to_be_visible()
        self.manual()
        self.search()
        expect(self.page.locator(".market-table tbody tr")).to_have_count(10)

    def test_switching_mode_cancels_pending_ai_request(self):
        self.defer_parse = True
        self.page.locator("#market-request").fill("Tìm đô thị công nghiệp ở Nhật Bản")
        self.page.locator('#market-search-panel button[type="submit"]').click()
        expect(self.page.locator('#market-search-panel button[type="submit"]')).to_be_disabled()
        self.manual()
        self.assertIsNotNone(self.held_parse)
        expect(self.page.locator('#market-search-panel button[type="submit"]')).to_be_enabled()
        self.search()
        # Complete the held route after cancellation; this late response must not
        # start an AI search or overwrite the manual results.
        self.held_parse.fulfill(status=200, json={"query": self.parsed_query,
                                                "unsupported_criteria": [], "assumptions": [],
                                                "interpretation": "Phạm vi nghiên cứu."})
        expect(self.page.locator(".market-table tbody tr")).to_have_count(10)
        self.assertEqual([path for path, _ in self.calls if path.startswith("/market/")],
                         ["/market/parse", "/market/search"])

    def test_filters_stale_results_validation_reset_and_empty_state(self):
        self.manual()
        self.page.locator("#market-countries").select_option(["Japan"])
        self.page.locator("#market-min").fill("30")
        self.page.locator("#market-cluster").select_option("0")
        self.page.locator("#market-limit").select_option("5")
        self.search()
        expect(self.page.locator(".market-table tbody tr")).to_have_count(5)
        expect(self.page.get_by_role("heading", name="Thống kê riêng Top 5", exact=True)).to_be_visible()
        expect(self.page.locator(".market-research-context")).to_have_count(0)
        expect(self.page.locator(".stat-card").first.locator("strong")).to_have_text("9")
        self.page.locator("#market-sort").select_option("sector_share")
        expect(self.page.locator(".market-results")).to_have_count(0)
        self.search()
        shares = self.page.locator(".market-table tbody tr td:nth-child(4)").all_text_contents()
        values = [float(v.replace("%", "").replace(",", ".")) for v in shares]
        self.assertEqual(values, sorted(values, reverse=True))
        for n in [10, 20, 50]:
            self.page.locator("#market-limit").select_option(str(n))
            self.search()
            expect(self.page.locator(".market-table tbody tr")).to_have_count(9)
            expect(self.page.get_by_role("heading", name="Thống kê riêng Top 9", exact=True)).to_be_visible()
        self.page.locator("#market-min").fill("101")
        before = len(self.calls)
        self.page.locator('#market-search-panel button[type="submit"]').click()
        self.assertFalse(self.page.locator("#market-min").evaluate("el => el.checkValidity()"))
        self.assertEqual(len(self.calls), before)
        self.page.locator("#market-min").fill("100")
        self.search()
        expect(self.page.get_by_text("Không có đô thị đáp ứng tiêu chí.", exact=False)).to_be_visible()
        expect(self.page.get_by_role("button", name="Tạo báo cáo thị trường", exact=True)).to_have_count(0)
        expect(self.page.locator(".market-top-summary")).to_have_count(0)
        self.page.get_by_role("button", name="Đặt lại bộ lọc").click()
        expect(self.page.locator("#market-sector")).to_have_value("industry")
        expect(self.page.locator("#market-min")).to_be_empty()
        self.assertEqual(self.page.locator("#market-countries").evaluate("el => el.selectedOptions.length"), 0)
        expect(self.page.locator(".market-results")).to_have_count(0)

    def test_all_sectors_clears_dependencies_and_report_works(self):
        self.manual()
        self.page.locator("#market-min").fill("30")
        self.page.locator("#market-sector").select_option("all")
        expect(self.page.locator("#market-min")).to_be_disabled()
        expect(self.page.locator("#market-min")).to_be_empty()
        expect(self.page.locator("#market-sort")).to_have_value("total_ghg")
        expect(self.page.locator('#market-sort option[value="sector_emissions"]')).to_have_attribute("disabled", "")
        self.search()
        query = [p for path, p in self.calls if path == "/market/search"][-1]
        self.assertIsNone(query["min_sector_share_percent"])
        self.assertEqual(query["sector"], "all")
        expect(self.page.locator(".market-table tbody tr").first.locator("td").nth(2)).to_have_text("—")
        self.page.get_by_role("button", name="Tạo báo cáo thị trường", exact=True).click()
        expect(self.page.locator(".ce-report")).to_be_visible()

    def test_market_markers_share_theme_colors_and_preserve_geometry(self):
        self.page.evaluate("() => { L.Map.addInitHook(function() { window.__marketMap = this; }); }")
        self.manual()
        self.search()
        self.page.wait_for_function("window.__marketMap && Object.values(__marketMap._layers).some(layer => layer instanceof L.CircleMarker)")
        styles = self.page.evaluate("""() => Object.values(__marketMap._layers).filter(layer => layer instanceof L.CircleMarker)
          .map(marker => ({radius: marker.getRadius(), color: marker.options.color, fillColor: marker.options.fillColor,
                           weight: marker.options.weight, fillOpacity: marker.options.fillOpacity, opacity: marker.options.opacity}))""")
        self.assertEqual({style["fillColor"] for style in styles}, {"#50AEFF", "#FFBE61", "#39DEAA"})
        for style in styles:
            self.assertEqual(style, {"radius": 3.2, "color": style["fillColor"], "fillColor": style["fillColor"],
                                     "weight": 0.35, "fillOpacity": 0.78, "opacity": 0.9})

    def test_applied_summary_example_and_actual_top_subset(self):
        self.parse_context = {"product": "Công nghệ thu hồi nhiệt thải công nghiệp", "business_goal": "Kinh doanh", "sector_basis": "explicit_filter"}
        self.page.get_by_role("button", name="Dùng yêu cầu mẫu").click()
        expect(self.page.locator("#market-request")).to_have_value(re.compile("thu hồi nhiệt thải"))
        expect(self.page.get_by_text('Nếu yêu cầu có điều kiện chưa hỗ trợ, hãy chỉnh sửa trước khi tìm kiếm.', exact=True)).to_be_visible()
        expect(self.page.get_by_text('Nhập yêu cầu · Gemini xác định bộ lọc · Python truy vấn dữ liệu', exact=True)).to_have_count(0)
        self.search()
        expect(self.page.get_by_role("heading", name="Phạm vi nghiên cứu", exact=True)).to_be_visible()
        self.assertEqual(self.page.locator(".market-applied-fields dd").all_text_contents(),
                         ["Japan", "Công nghiệp", "Tất cả 3 cụm", "30%", "GHG Công nghiệp giảm dần", "Top 10"])
        expect(self.page.locator(".market-research-context")).to_contain_text("Công nghệ thu hồi nhiệt thải công nghiệp")
        expect(self.page.locator(".market-research-context")).to_contain_text("Mục tiêu: Kinh doanh")
        expect(self.page.locator(".market-top-heading")).to_contain_text("Thống kê riêng Top 10")
        self.assert_market_scopes()
        if os.environ.get('MARKET_UI_SCREENSHOTS'):
            directory = Path(os.environ['MARKET_UI_SCREENSHOTS'])
            directory.mkdir(parents=True, exist_ok=True)
            self.page.evaluate('scrollTo(0,0)')
            self.page.screenshot(path=str(directory / 'market-ai-japan.png'), full_page=True)
            for name, selector in [('conditions', '.market-applied'), ('top10', '.market-top-summary'), ('gemini-empty', '.market-report-panel')]:
                self.page.locator(selector).screenshot(path=str(directory / f'{name}.png'))
        self.parsed_query['limit'] = 9
        self.page.locator("#market-request").fill("Tìm 9 đô thị Nhật Bản có tỷ trọng công nghiệp từ 30%")
        self.search()
        expect(self.page.locator(".market-top-heading")).to_contain_text("Thống kê riêng Top 9")

        self.manual()
        self.page.locator("#market-countries").select_option(["Japan"])
        self.page.locator("#market-cluster").select_option("0")
        eligible = market.search(market.MarketQuery(sector="industry", countries=["Japan"], cluster_id=0, sort_by="sector_share", limit=10))["items"]
        seventh, eighth = [item["sector_share_percent"] for item in eligible[6:8]]
        self.page.locator("#market-min").fill(str((seventh + eighth) / 2))
        self.search()
        expect(self.page.locator(".market-top-heading")).to_contain_text("Thống kê riêng Top 7")
        expect(self.page.locator(".market-top-heading > span")).to_have_text("7 đô thị")
        expect(self.page.locator(".market-applied")).to_contain_text("Top 10")
        expect(self.page.locator(".market-research-context")).to_have_count(0)
        self.assert_market_scopes()
        self.assertEqual(sum(path == "/market/search" for path, _ in self.calls), 3)

    def last_search(self):
        query = [payload for path, payload in self.calls if path == '/market/search'][-1]
        return market.search(market.MarketQuery.model_validate(query))

    def assert_market_scopes(self):
        result = self.last_search()
        whole, top = result['matching_summary'], result['top_summary']
        stat_values = self.page.locator('.market-research-scope .stat-card strong').all_text_contents()
        self.assertEqual(stat_values, [str(whole['city_count']), str(whole['country_count']),
                                      f"{whole['mean_sector_share_percent']:.2f}%".replace('.', ','), str(len(result['items']))])
        self.assertEqual(self.page.locator('.market-top-values dd').all_text_contents(),
                         [str(top['country_count']), f"{top['mean_sector_share_percent']:.2f}%".replace('.', ',')])
        self.assertEqual(self.page.locator('.market-top-clusters strong').all_text_contents(), list(map(str, top['cluster_counts'].values())))
        self.assertEqual(self.page.locator('.market-visuals .market-cluster-counts strong').all_text_contents(), list(map(str, whole['cluster_counts'].values())))

    def test_table_disclosure_csv_and_chart_follow_actual_ranking(self):
        self.manual()
        self.page.locator("#market-countries").select_option(["Japan"])
        self.page.locator("#market-min").fill("30")
        self.search()
        ranking = self.page.locator('.market-ranking-panel')
        expect(ranking.get_by_role('heading')).to_have_text('Top 10 đô thị theo phát thải Công nghiệp')
        expect(ranking.locator('.panel-heading p')).to_have_text('Đơn vị: tấn/năm')
        rows = self.last_search()['items']
        self.assertEqual(self.ids(), [row['city_name'] for row in rows])
        expect(ranking.locator('.recharts-yAxis-tick-labels text')).to_have_count(10)
        first = ranking.locator('path.recharts-rectangle').first
        first.hover()
        chart_tooltip = ranking.locator('.recharts-tooltip-wrapper')
        expect(chart_tooltip).to_contain_text(rows[0]['city_name'])
        chart_number = chart_tooltip.locator('.recharts-tooltip-item-value').inner_text()
        self.assertEqual(float(chart_number.removesuffix(' tấn/năm').replace('.', '').replace(',', '.')), rows[0]['sector_emissions'])

        table = self.page.locator('.market-table')
        for label in ('GHG lĩnh vực (tấn/năm)', 'Tổng GHG (tấn/năm)'):
            expect(table.get_by_role('button', name=label, exact=True)).to_be_visible()
        tooltip = self.page.locator('.city-value-tooltip[role="tooltip"]')
        first_row = table.locator('tbody tr').first
        sector_value, total_value = first_row.locator('.city-ghg-value').all()
        expect(sector_value).to_contain_text('triệu')
        sector_value.hover()
        expect(tooltip).to_be_visible()
        self.assertEqual(float(tooltip.inner_text().removesuffix(' tấn/năm').replace('.', '').replace(',', '.')), rows[0]['sector_emissions'])
        total_value.focus()
        expect(tooltip).to_be_visible()
        self.assertEqual(float(tooltip.inner_text().removesuffix(' tấn/năm').replace('.', '').replace(',', '.')), rows[0]['ghg_total_2024'])
        self.page.keyboard.press('Escape')
        expect(tooltip).to_have_count(0)
        self.page.set_viewport_size({'width': 320, 'height': 800})
        total_value.evaluate("e => e.scrollIntoView({block: 'center', inline: 'center'})")
        total_value.tap()
        expect(tooltip).to_be_visible()
        self.assertTrue(tooltip.evaluate('e => { const b = e.getBoundingClientRect(); return b.left >= 0 && b.right <= innerWidth && b.top >= 0 && b.bottom <= innerHeight; }'))
        self.page.touchscreen.tap(3, 700)
        expect(tooltip).to_have_count(0)
        self.page.set_viewport_size({'width': 1440, 'height': 1000})

        for button, scope in [('CSV Top N', 'top'), ('CSV toàn bộ (40)', 'matching')]:
            with self.page.expect_download() as event:
                self.page.get_by_role('button', name=button, exact=True).click()
            with event.value.path().open(encoding='utf-8-sig', newline='') as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(len(csv_rows), 10 if scope == 'top' else 40)
            self.assertEqual([row['city_id'] for row in csv_rows[:10]], [row['city_id'] for row in rows])
            self.assertEqual(float(csv_rows[0]['sector_emissions_original_edgar_unit']), rows[0]['sector_emissions'])
            self.assertEqual(float(csv_rows[0]['ghg_total_2024_original_edgar_unit']), rows[0]['ghg_total_2024'])

        table.get_by_role('button', name='Tổng GHG (tấn/năm)', exact=True).click()
        expect(ranking.get_by_role('heading')).to_have_text('Top 10 đô thị theo tổng GHG')
        total_rows = self.last_search()['items']
        self.assertEqual(self.ids(), [row['city_name'] for row in total_rows])
        first.hover()
        expect(chart_tooltip).to_contain_text(total_rows[0]['city_name'])
        total_number = chart_tooltip.locator('.recharts-tooltip-item-value').inner_text()
        self.assertEqual(float(total_number.removesuffix(' tấn/năm').replace('.', '').replace(',', '.')), total_rows[0]['ghg_total_2024'])
        table.get_by_role('button', name='Tỷ trọng (%)', exact=True).click()
        expect(ranking.get_by_role('heading')).to_have_text('Tỷ trọng phát thải Công nghiệp của Top 10 đô thị')
        expect(ranking.locator('.panel-heading p')).to_have_text('Đơn vị: % · Không phải điểm tiềm năng')
        self.assertEqual(self.ids(), [row['city_name'] for row in self.last_search()['items']])
        self.page.locator('#market-min').fill('0')
        self.page.locator('#market-sector').select_option('energy')
        self.page.locator('#market-sort').select_option('sector_emissions')
        self.search()
        expect(ranking.get_by_role('heading')).to_have_text('Top 10 đô thị theo phát thải Năng lượng')
        city = self.last_search()['items'][0]
        first_row.get_by_role('button', name='Mở hồ sơ').click()
        expect(self.page.locator('.city-hero h2')).to_have_text(city['city_name'])

    def test_country_and_multi_country_fit_keeps_markers_visible_and_can_pan(self):
        self.page.evaluate("() => { L.Map.addInitHook(function() { window.__marketMap = this; }); }")
        self.manual()
        for countries in (['Japan'], ['Vietnam'], ['Japan', 'Vietnam']):
            self.page.locator('#market-countries').select_option(countries)
            self.search()
            result = self.last_search()
            self.page.wait_for_function("shown => window.__marketMap && Object.values(__marketMap._layers).filter(l => l instanceof L.CircleMarker).length === shown", arg=result['map']['shown'])
            expect(self.page.locator('.market-visuals .map-caption')).to_have_text(f"Hiển thị {result['map']['shown']}/{result['map']['total_matching']} đô thị phù hợp.")
            camera = self.page.evaluate("""() => {
                const m = __marketMap, size = m.getSize();
                const visible = Object.values(m._layers).filter(l => l instanceof L.CircleMarker).every(l => {
                  const p = m.latLngToContainerPoint(l.getLatLng());
                  return p.x >= 10 && p.x <= size.x - 10 && p.y >= 10 && p.y <= size.y - 10;
                });
                return {visible, zoom: m.getZoom()};
              }""")
            self.assertTrue(camera['visible'], countries)
            self.assertGreaterEqual(camera['zoom'], 3)
        old_zoom = self.page.evaluate('__marketMap.getZoom()')
        self.page.locator('.leaflet-control-zoom-in').click()
        self.page.wait_for_function('zoom => __marketMap.getZoom() === zoom + 1 && !__marketMap._animatingZoom', arg=old_zoom)
        self.page.evaluate('() => { __marketMap.panBy([45, 25], {animate:false}); }')
        camera = self.page.evaluate('() => [__marketMap.getZoom(), ...Object.values(__marketMap.getCenter())]')
        self.page.get_by_role('button', name='Tạo báo cáo thị trường', exact=True).click()
        expect(self.page.locator('.market-report-panel .ce-report')).to_be_visible()
        self.assertEqual(self.page.evaluate('() => [__marketMap.getZoom(), ...Object.values(__marketMap.getCenter())]'), camera)
        self.page.evaluate('() => { Object.values(__marketMap._layers).find(l => l instanceof L.CircleMarker).fire("click"); }')
        expect(self.page.locator('.city-hero h2')).to_have_text(result['map']['points'][0]['city_name'])

    def test_map_missing_coordinates_antimeridian_and_stale_search_response(self):
        self.page.evaluate("() => { L.Map.addInitHook(function() { window.__marketMap = this; }); }")
        self.manual()
        result = market.search(market.MarketQuery(sector='industry', countries=['United States']))
        points = result['map']['points'][:2]
        def map_fixture(points, route):
            route.fulfill(json={**result, 'map': {**result['map'], 'points': points, 'shown': len(points), 'valid_coordinates': len(points)}})

        self.page.route('**/api/market/search', lambda route: map_fixture([], route), times=1)
        self.page.locator('#market-countries').select_option(['United States'])
        self.search()
        expect(self.page.get_by_text('Chưa có tọa độ hợp lệ để hiển thị trên bản đồ.', exact=True)).to_be_visible()
        expect(self.page.locator('.market-visuals .map-caption')).to_contain_text('Hiển thị 0/')

        points = [{**point, 'latitude': 52, 'longitude': longitude} for point, longitude in zip(points, [179, -179])]
        self.page.route('**/api/market/search', lambda route: map_fixture(points, route), times=1)
        self.search()
        self.page.wait_for_function("Math.abs(__marketMap.getCenter().lng) > 170 && __marketMap.getZoom() >= 5")
        self.assertTrue(self.page.evaluate("""() => Object.values(__marketMap._layers).filter(l => l instanceof L.CircleMarker)
            .every(l => __marketMap.getBounds().contains(l.getLatLng()))"""))

        self.defer_search = True
        self.page.locator('#market-search-panel button[type="submit"]').click()
        expect(self.page.get_by_text('Python đang lọc và xếp hạng toàn bộ tập phù hợp…')).to_be_visible()
        self.page.locator('.market-mode-switch button').first.click()
        self.page.locator('#market-request').fill('Tìm 10 đô thị ở Nhật Bản có tỷ trọng công nghiệp từ 30%')
        self.search()
        route, response = self.held_search
        route.fulfill(status=response.status_code, content_type='application/json', body=response.content)
        expect(self.page.locator('.market-applied-fields dd').first).to_have_text('Japan')
        self.page.wait_for_function('Math.abs(__marketMap.getCenter().lng - 137) < 20')

    def test_report_empty_error_retry_regeneration_and_new_query(self):
        self.manual()
        self.page.locator('#market-countries').select_option(['Japan'])
        self.search()
        panel = self.page.locator('.market-report-panel')
        empty = panel.locator('.market-report-empty')
        expect(empty.locator('svg')).to_have_count(1)
        expect(empty.locator('p')).to_have_text('Chưa có báo cáo cho phạm vi nghiên cứu hiện tại.')
        expect(panel.locator('.panel-heading p')).to_have_count(0)
        generate = panel.get_by_role('button', name='Tạo báo cáo thị trường', exact=True)
        expect(generate).to_have_count(1)
        self.defer_report = True
        generate.click()
        expect(panel.get_by_role('button', name='Đang tạo báo cáo…', exact=True)).to_be_disabled()
        expect(panel.get_by_text('Gemini đang tổng hợp dữ liệu nghiên cứu…', exact=True)).to_be_visible()
        self.held_report.fulfill(status=503, json={'detail': 'Gemini tạm thời không sẵn sàng.'})
        expect(panel.get_by_role('alert')).to_contain_text('Gemini tạm thời không sẵn sàng')
        generate.click()
        expect(panel.locator('article.ce-report')).to_be_visible()
        expect(empty).to_have_count(0)
        panel.get_by_role('button', name='Tạo lại báo cáo thị trường', exact=True).click()
        expect(panel.get_by_role('button', name='Tạo lại báo cáo thị trường', exact=True)).to_be_enabled()
        self.page.locator('#market-countries').select_option(['Vietnam'])
        self.search()
        expect(panel.locator('article.ce-report')).to_have_count(0)
        expect(generate).to_be_visible()
        self.assertEqual([payload['query']['countries'] for path, payload in self.calls if path == '/market/report'], [['Japan']] * 3)

    def test_mobile_and_desktop_layouts(self):
        for width in [1440, 1024, 768, 390, 320]:
            self.page.set_viewport_size({"width": width, "height": 900})
            self.manual()
            expect(self.page.locator("#market-sector")).to_be_visible()
            self.search()
            self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Horizontal overflow at {width}px")
            expect(self.page.locator(".worldmap")).to_be_visible()
            expect(self.page.locator(".market-report-empty button")).to_be_visible()
            self.assertTrue(self.page.locator(".market-visuals").evaluate("e => { const [map, chart] = e.children; return (map.offsetTop === chart.offsetTop) === (innerWidth > 900); }"))
            expect(self.page.locator('.market-ranking-panel .recharts-yAxis-tick-labels text')).to_have_count(10)
            self.assertTrue(self.page.locator('.market-ranking-scroll').evaluate('e => e.scrollWidth <= e.clientWidth'))
            if width <= 768:
                self.assertTrue(self.page.locator(".market-table-scroll").evaluate("e => e.scrollWidth > e.clientWidth"))
            if os.environ.get("MARKET_UI_SCREENSHOTS"):
                directory = Path(os.environ["MARKET_UI_SCREENSHOTS"])
                directory.mkdir(parents=True, exist_ok=True)
                self.page.locator(".market-mode-switch").scroll_into_view_if_needed()
                self.page.screenshot(path=str(directory / f"market-{width}.png"), full_page=True)
            self.page.locator('.market-mode-switch button').first.click()
            expect(self.page.locator("#market-request")).to_be_visible()
            self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"AI overflow at {width}px")


if __name__ == "__main__":
    unittest.main(verbosity=2)
