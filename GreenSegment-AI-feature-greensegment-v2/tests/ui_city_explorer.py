"""Phase 2C acceptance: real CSV-backed GETs, explicit Gemini mocks, installed Chrome.

Run against Vite dev/preview with CITY_UI_URL (default http://127.0.0.1:5173).
Screenshots are saved under .local/phase-2c/after; no live Gemini requests.
"""
import copy
import os
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from fastapi.testclient import TestClient
from playwright.sync_api import expect, sync_playwright
from api import advisor_service as advisor, data_service as data
from api.main import app
import test_city_explorer as fixtures

OUT = ROOT / '.local/phase-2c/after'
PALETTE = {0: ('#50AEFF', '#A8D8FF'), 1: ('#FFBE61', '#FFE0A7'), 2: ('#39DEAA', '#A2F5D9')}
TOOLTIP = 'Khoảng cách Euclid giữa cơ cấu tỷ trọng phát thải của đô thị và tâm cụm K-Means trong không gian 7 lĩnh vực. Đây không phải khoảng cách địa lý.'


class CityExplorerBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=os.environ.get('MARKET_CHROME', r'C:\Program Files\Google\Chrome\Application\chrome.exe'), headless=True)
        cls.api = TestClient(app)
        OUT.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.api.close()
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce', has_touch=True)
        self.page = self.context.new_page()
        self.errors, self.gets, self.ai_calls, self.pending_ai, self.pending_get = [], [], [], [], []
        self.hold, self.api_failures = set(), {}
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.route('**/api/**', self.api_route)
        self.base_url = os.environ.get('CITY_UI_URL', 'http://127.0.0.1:5173').rstrip('/')

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def api_route(self, route):
        request = route.request
        url = urlsplit(request.url)
        if request.method == 'POST':
            self.assertRegex(url.path, r'^/api/cities/[^/]+/interpret$')
            city_id = url.path.split('/')[3]
            self.ai_calls.append(city_id)
            self.pending_ai.append((route, city_id))
            return
        self.assertEqual(request.method, 'GET')
        self.gets.append((url.path, parse_qs(url.query)))
        if url.path in self.api_failures:
            route.fulfill(status=self.api_failures[url.path], json={'detail': 'Lỗi dữ liệu trong kiểm thử.'})
            return
        with patch.object(advisor, '_advisor', side_effect=AssertionError('No live Gemini')):
            response = self.api.get(url.path + ('?' + url.query if url.query else ''))
        if url.path in self.hold:
            self.pending_get.append((route, response))
            return
        route.fulfill(status=response.status_code, content_type='application/json', body=response.content)

    def open(self, city_id='2007'):
        self.page.goto(self.base_url + '/#/city' + (f'?city={city_id}' if city_id else ''))
        expect(self.page.get_by_role('heading', name='Tra cứu đô thị', exact=True)).to_be_visible()
        if city_id:
            self.wait_city(city_id)

    def wait_city(self, city_id):
        expect(self.page.locator('.city-hero h2')).to_have_text(data.city_details(city_id)['city_name'])
        expect(self.page.locator('.city-emissions-table tbody tr')).to_have_count(7)

    def select(self, city_id):
        self.page.evaluate("id => { location.hash = '#/city?city=' + id; }", city_id)
        self.wait_city(city_id)

    def number(self, value, digits=0):
        return self.page.evaluate("([v,d]) => Number(v).toLocaleString('vi-VN', {minimumFractionDigits:d,maximumFractionDigits:d})", [value, digits])

    def signed(self, value):
        magnitude = self.page.evaluate('v => Math.round(Math.abs(v) * 100) / 100', value)
        return ('−' if value < 0 and magnitude != 0 else '+') + self.number(magnitude, 2)

    def assert_in_viewport(self, locator):
        box = locator.bounding_box()
        size = self.page.viewport_size
        self.assertGreaterEqual(box['x'], 0)
        self.assertGreaterEqual(box['y'], 0)
        self.assertLessEqual(box['x'] + box['width'], size['width'] + 1)
        self.assertLessEqual(box['y'] + box['height'], size['height'] + 1)

    def finish_ai(self, *, status=200, label='Báo cáo kiểm thử'):
        route, city_id = self.pending_ai.pop(0)
        if status != 200:
            route.fulfill(status=status, json={'detail': 'Gemini chưa sẵn sàng trong kiểm thử.'})
            return None
        report = copy.deepcopy(fixtures.CityExplorerTests.report_fixture())
        report['summary'] = f'{label} {city_id}. ' + report['summary']
        route.fulfill(json={'city_id': city_id, 'model': 'mock-city', 'report': report})
        return report

    def test_three_clusters_preserve_values_chart_geometry_and_legend(self):
        self.open()
        for city_id, name, country, cid in fixtures.CityExplorerTests.CITIES:
            with self.subTest(city=city_id):
                self.select(city_id)
                details = data.city_details(city_id)
                analysis = details['analysis']
                expect(self.page.locator('.city-hero')).to_contain_text(f'{country} · Mã đô thị {city_id}')
                expect(self.page.locator('.cluster-chip')).to_contain_text(f'Cụm {cid}')
                expect(self.page.locator('.city-metrics > div')).to_have_count(3)
                expect(self.page.locator('.city-metrics strong').nth(0)).to_have_text(self.number(details['ghg_total_2024']))
                expect(self.page.locator('.city-metrics strong').nth(2)).to_have_text(self.number(analysis['distance_to_centroid'], 4))
                expect(self.page.locator('.city-metrics')).to_contain_text('Đơn vị gốc EDGAR*')
                expect(self.page.get_by_text('So sánh 7 tỷ trọng GHG với tâm mô hình', exact=True)).to_be_visible()
                expect(self.page.locator('.city-sector-chart .recharts-yAxis .recharts-cartesian-axis-tick')).to_have_count(7)
                labels = self.page.locator('.city-sector-chart .recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value').evaluate_all("els => els.map(e => [...e.querySelectorAll('tspan')].map(t => t.textContent).join(' '))")
                self.assertEqual(labels, [data.SECTOR_LABELS[s] for s in data.SECTORS])
                expect(self.page.locator('.city-explorer input[type=radio]')).to_have_count(0)
                self.page.wait_for_timeout(1400)  # Recharts' existing entrance animation.
                bars = self.page.locator('.city-sector-chart .recharts-bar')
                expect(bars).to_have_count(2)
                for series, key, color in ((0, 'shares_percent', PALETTE[cid][0]), (1, None, PALETTE[cid][1])):
                    paths = bars.nth(series).locator('path.recharts-rectangle')
                    expect(paths).to_have_count(7)
                    values = analysis[key] if key else analysis['cluster']['centroid_percent']
                    dimensions = paths.evaluate_all("els => els.map(e => ({width:Number(e.getAttribute('width')),fill:e.getAttribute('fill')}))")
                    ratios = []
                    for sector, actual in zip(data.SECTORS, dimensions):
                        self.assertEqual(actual['fill'].upper(), color)
                        if values[sector] > 0:
                            ratios.append(actual['width'] / values[sector])
                    self.assertLess(max(ratios) - min(ratios), 0.001)
                legend = self.page.locator('.city-sector-chart .recharts-legend-item')
                self.assertEqual(legend.all_text_contents(), ['Đô thị', 'Tâm K-Means'])
                self.assertEqual([v.upper() for v in legend.locator('svg path').evaluate_all("els => els.map(e=>e.getAttribute('fill'))")], list(PALETTE[cid]))
                ticks = self.page.locator('.city-sector-chart .recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value').all_text_contents()
                self.assertEqual([ticks[0], ticks[-1]], ['0%', '100%'])
                bars.nth(0).locator('path.recharts-rectangle').nth(5).hover()
                expect(self.page.locator('.city-sector-chart .recharts-tooltip-wrapper')).to_contain_text('Giao thông')
                self.page.mouse.move(0, 0)
                rows = self.page.locator('.city-emissions-table tbody tr')
                for i, sector in enumerate(data.SECTORS):
                    self.assertEqual(rows.nth(i).locator('th').inner_text(), data.SECTOR_LABELS[sector])
                    cells = rows.nth(i).locator('td')
                    ghg_label = cells.nth(0).get_by_role('button').get_attribute('aria-label')
                    value = ghg_label.removeprefix(f'GHG {data.SECTOR_LABELS[sector]}: ').removesuffix(' tấn/năm')
                    self.assertEqual(float(value.replace('.', '').replace(',', '.')), analysis['emissions_by_sector'][sector])
                    self.assertEqual(cells.nth(1).inner_text(), self.number(analysis['shares_percent'][sector], 2) + '%')
                    self.assertEqual(cells.nth(2).inner_text(), self.number(analysis['cluster']['centroid_percent'][sector], 2) + '%')
                    expect(cells.nth(3).locator('strong')).to_have_text(self.signed(analysis['comparison_to_centroid_pp'][sector]))
                difference_rows = self.page.locator('.city-difference-summary dl > div')
                expect(difference_rows).to_have_count(len(analysis['notable_differences']))
                for i, item in enumerate(analysis['notable_differences']):
                    expect(difference_rows.nth(i).locator('dt')).to_have_text(data.SECTOR_LABELS[item['sector']])
                    expect(difference_rows.nth(i).locator('dd')).to_have_text(self.signed(item['difference_pp']) + ' điểm phần trăm')
                expect(self.page.locator('.city-difference-summary')).to_contain_text('Đây là mô tả, không phải kiểm định thống kê.')
                self.page.evaluate('scrollTo(0,0)')
                self.page.screenshot(path=str(OUT / f'cluster-{cid}.png'), full_page=True)
        self.assertEqual(self.ai_calls, [])

    def test_ghg_table_formats_boundaries_and_unavailable_values(self):
        fixture = self.api.get('/api/cities/2007').json()
        examples = (
            [(850.25, '850,25'), (0, '0'), (0.0004, '<0,01'), (999.999, '999,99'),
             (1000, '1,00 nghìn'), (999999.999, '999,99 nghìn'), (1000000, '1,00 triệu')],
            [(None, '—'), ('NaN', '—'), ('Infinity', '—'), (-1, '—'),
             ('', '—'), (155500858.90, '155,50 triệu'), (967148.72, '967,15 nghìn')],
        )
        for batch in examples:
            with self.subTest(batch=batch):
                self.page.goto('about:blank')
                fixture['analysis']['emissions_by_sector'] = dict(zip(data.SECTORS, (value for value, _ in batch)))
                self.page.route('**/api/cities/2007', lambda route: route.fulfill(json=fixture), times=1)
                self.open()
                cells = self.page.locator('.city-emissions-table tbody tr td:first-of-type')
                expect(cells).to_have_text([label for _, label in batch])
                expect(cells.get_by_role('button')).to_have_count(sum(label != '—' for _, label in batch))

    def test_ghg_table_shows_full_value_by_mouse_keyboard_and_touch(self):
        self.open('11345')
        panel = self.page.locator('.city-emissions-panel')
        expect(panel.locator('thead th')).to_have_text(['Lĩnh vực', 'GHG (tấn/năm)', 'Đô thị (%)', 'Tâm (%)', 'Chênh lệch với tâm'])
        expect(panel.locator('.panel-heading p')).to_have_count(0)
        expect(panel.locator('.data-note')).to_contain_text('đây không phải ngưỡng bất thường')
        value = self.page.get_by_role('button', name='GHG Năng lượng:', exact=False)
        expect(value).to_have_text('68,95 triệu')
        raw = data.city_details('11345')['analysis']['emissions_by_sector']['energy']
        tooltip = self.page.get_by_role('tooltip')

        def assert_full_value():
            expect(tooltip).to_contain_text(' tấn/năm')
            number = tooltip.inner_text().removesuffix(' tấn/năm').replace('.', '').replace(',', '.')
            self.assertEqual(float(number), raw)
            self.assert_in_viewport(tooltip)
            self.assertTrue(tooltip.evaluate('e => e.parentElement === document.body'))

        value.hover()
        assert_full_value()
        self.page.mouse.move(0, 0)
        expect(tooltip).to_have_count(0)
        value.focus()
        assert_full_value()
        self.assertEqual(value.get_attribute('aria-describedby'), tooltip.get_attribute('id'))
        value.press('Escape')
        expect(tooltip).to_have_count(0)
        value.press('Enter')
        assert_full_value()
        value.press('Tab')
        expect(tooltip).not_to_have_text(value.get_attribute('aria-label').split(': ', 1)[1])
        self.page.locator('.city-explorer h1').click()
        value.click()
        assert_full_value()
        value.click()
        expect(tooltip).to_have_count(0)

        for width in (390, 320):
            self.page.set_viewport_size({'width': width, 'height': 700})
            value.evaluate("e => {e.blur(); e.scrollIntoView({block: 'center', inline: 'center'});}")
            value.tap()
            assert_full_value()
            self.page.touchscreen.tap(4, 500)
            expect(tooltip).to_have_count(0)

    def test_search_country_pagination_selection_and_no_results(self):
        self.open('')
        results = self.page.locator('.city-result')
        expect(results).to_have_count(10)
        initial = results.locator('strong').all_text_contents()
        self.page.get_by_role('button', name='Sau', exact=True).click()
        expect(self.page.locator('.pagination')).to_contain_text('2 /')
        self.page.wait_for_function("names => [...document.querySelectorAll('.city-result strong')].map(e=>e.textContent).join('|') !== names.join('|')", arg=initial)
        self.page.get_by_role('button', name='Trước', exact=True).click()
        expect(results.locator('strong').first).to_have_text(initial[0])
        search = self.page.get_by_role('textbox', name='Tìm đô thị', exact=True)
        for term in ('Japan', 'Los Angeles'):
            search.fill(term)
            response = self.api.get('/api/cities', params={'search':term, 'page':1, 'page_size':10}).json()
            expect(self.page.locator('.result-count')).to_have_text(self.number(response['total']) + ' đô thị phù hợp')
            self.assertEqual(results.locator('strong').all_text_contents(), [c['city_name'] for c in response['items']])
        results.first.click()
        self.wait_city('2007')
        expect(self.page).to_have_url(self.base_url + '/#/city?city=2007')
        expect(results.first).to_have_attribute('aria-pressed', 'true')
        search.fill('zzzz-no-city-exists')
        expect(self.page.locator('.city-result-list .empty-state')).to_be_visible()
        expect(results).to_have_count(0)
        self.wait_city('2007')
        search.fill('')
        expect(results).to_have_count(10)
        for path, query in self.gets:
            if path == '/api/cities':
                self.assertEqual(query['page_size'], ['10'])
        self.assertEqual(self.ai_calls, [])

    def test_desktop_sticky_scroll_list_and_header_hit_testing(self):
        self.open()
        for width in (1440, 1024):
            self.page.set_viewport_size({'width': width, 'height': 780})
            self.page.evaluate('scrollTo(0,0)')
            self.page.wait_for_timeout(100)
            initial = self.page.locator('.city-search-panel').bounding_box()
            self.assertLessEqual(initial['y'] + initial['height'], 780 - 15)
            self.page.evaluate('scrollTo(0,800)')
            self.page.wait_for_timeout(100)
            panel = self.page.locator('.city-search-panel')
            header = self.page.locator('.global-header').bounding_box()
            box = panel.bounding_box()
            self.assertGreaterEqual(box['y'], header['y'] + header['height'] + 15)
            self.assertLessEqual(box['y'] + box['height'], 780 - 15)
            self.assert_in_viewport(self.page.locator('.pagination'))
            self.assert_in_viewport(self.page.get_by_role('textbox', name='Tìm đô thị', exact=True))
            self.assertEqual(panel.evaluate("e=>getComputedStyle(e).position"), 'sticky')
            listing = self.page.locator('.city-result-list')
            self.assertTrue(listing.evaluate('e=>e.scrollHeight>e.clientHeight'))
            old_y = self.page.evaluate('scrollY')
            listing.evaluate('e=>{e.scrollTop=0}')
            listing.hover()
            self.page.mouse.wheel(0, 150)
            self.page.wait_for_timeout(150)
            self.assertGreater(listing.evaluate('e=>e.scrollTop'), 0)
            self.assertEqual(self.page.evaluate('scrollY'), old_y)
            button = self.page.locator('.city-search-panel .pagination button').last
            self.assertTrue(button.evaluate('e=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))}'))
        self.page.locator('.global-header .navigation-link').filter(has_text='Giới thiệu').click()
        expect(self.page.locator('.about-hero')).to_be_visible()

    def test_responsive_widths_tables_percentiles_and_empty_state_composition(self):
        self.open()
        self.page.emulate_media(reduced_motion='no-preference')
        self.page.wait_for_function("document.querySelector('.video-background video')?.currentTime > .1")
        for width in (1440, 1024, 768, 390, 320):
            with self.subTest(width=width):
                self.page.set_viewport_size({'width':width, 'height':1000})
                self.page.evaluate('scrollTo(0,0)')
                self.page.wait_for_timeout(200)
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width)
                expect(self.page.locator('.city-emissions-table thead')).to_be_visible()
                self.assertTrue(self.page.locator('.city-ghg-value').evaluate_all('buttons => buttons.every(e => e.scrollWidth <= e.clientWidth)'))
                wrapper = self.page.get_by_role('region', name='Bảng phát thải và cơ cấu 7 lĩnh vực')
                if width <= 390:
                    self.assertTrue(wrapper.evaluate('e=>e.scrollWidth>e.clientWidth'))
                    wrapper.evaluate('e=>{e.scrollLeft=e.scrollWidth}')
                    self.assertGreater(wrapper.evaluate('e=>e.scrollLeft'), 0)
                    wrapper.evaluate('e=>{e.scrollLeft=0}')
                self.assertEqual(self.page.locator('.city-search-panel').evaluate('e=>getComputedStyle(e).position'), 'sticky' if width > 900 else 'static')
                empty = self.page.locator('.city-ai-empty-content')
                self.assertEqual(empty.locator('button').count(), 1)
                center = empty.bounding_box()
                for locator in (empty.locator('svg').first, empty.locator('p'), empty.locator('button')):
                    box = locator.bounding_box()
                    self.assertAlmostEqual(box['x']+box['width']/2, center['x']+center['width']/2, delta=2)
                details = self.page.locator('.city-extended-statistics')
                self.assertIsNone(details.get_attribute('open'))
                details.locator('summary').click()
                cards = self.page.locator('.city-distance-percentiles > div')
                expect(cards).to_have_count(4)
                positions = [cards.nth(i).bounding_box() for i in range(4)]
                if width > 1200:
                    self.assertEqual(len({round(b['y']) for b in positions}), 1)
                else:
                    self.assertEqual(len({round(b['y']) for b in positions}), 2)
                    self.assertAlmostEqual(positions[0]['width'], positions[1]['width'], delta=1)
                for card in cards.all():
                    self.assertLessEqual(card.evaluate('e=>e.scrollWidth'), card.evaluate('e=>e.clientWidth'))
                details.locator('summary').click()
                self.page.evaluate('scrollTo(0,0)')
                self.page.screenshot(path=str(OUT / f'city-{width}.png'), full_page=True)
        self.assertEqual(self.ai_calls, [])

    def test_tooltip_mouse_keyboard_touch_dismissal_and_viewport_bounds(self):
        self.open()
        button = self.page.get_by_role('button', name='Giải thích khoảng cách đến tâm cụm')
        tooltip = self.page.get_by_role('tooltip')
        button.hover()
        expect(tooltip).to_have_text(TOOLTIP)
        self.assert_in_viewport(tooltip)
        self.page.mouse.move(0, 900)
        expect(tooltip).to_have_count(0)
        button.focus()
        expect(tooltip).to_be_visible()
        self.assertEqual(button.get_attribute('aria-describedby'), tooltip.get_attribute('id'))
        self.page.keyboard.press('Escape')
        expect(tooltip).to_have_count(0)
        self.page.keyboard.press('Enter')
        expect(tooltip).to_be_visible()
        self.page.keyboard.press('Enter')
        expect(tooltip).to_have_count(0)
        for width in (390, 320):
            self.page.set_viewport_size({'width':width,'height':700})
            button.scroll_into_view_if_needed()
            button.tap()
            expect(tooltip).to_be_visible()
            self.assert_in_viewport(tooltip)
            self.page.screenshot(path=str(OUT / f'tooltip-{width}.png'))
            self.page.touchscreen.tap(3, 690)
            expect(tooltip).to_have_count(0)
        self.assertEqual(self.page.locator('.city-metrics .city-distance-help').count(), 1)

    def test_distance_statistics_values_and_scientific_cautions(self):
        self.open('5213')
        analysis = data.city_details('5213')['analysis']
        expected = [self.number(analysis['distance_to_centroid'],4), self.number(analysis['cluster']['distance_statistics']['median'],4), self.number(analysis['position_in_cluster']['percentile_rank_percent'],2)+'%']
        self.assertEqual(self.page.locator('.city-distance-summary dd').all_text_contents(), expected)
        expect(self.page.locator('.city-position-hero p').first).to_have_text(analysis['position_in_cluster']['summary'])
        expect(self.page.get_by_text('Khoảng cách được tính trên cơ cấu tương đối, không đánh giá chất lượng môi trường.', exact=False)).to_be_visible()
        self.page.locator('.city-extended-statistics summary').click()
        self.assertEqual(self.page.locator('.city-distance-percentiles dt').all_text_contents(), ['Tứ phân vị thứ nhất (Q1)', 'Tứ phân vị thứ ba (Q3)', 'Phân vị thứ 90 (P90)', 'Phân vị thứ 95 (P95)'])
        self.assertEqual(self.page.locator('.city-distance-percentiles dd').all_text_contents(), [self.number(analysis['cluster']['distance_statistics'][k],4) for k in ('q1','q3','p90','p95')])
        rows = self.page.locator('.city-cluster-table tbody tr')
        expect(rows).to_have_count(7)
        for i, sector in enumerate(data.SECTORS):
            self.assertEqual(rows.nth(i).locator('td').all_text_contents(), [self.number(analysis['cluster']['sector_statistics_percent'][sector][key],2) for key in ('mean','median','std','iqr')])
        self.page.screenshot(path=str(OUT / 'extended-statistics.png'), full_page=True)

    def test_no_selection_loading_unavailable_city_and_retry(self):
        self.open('')
        expect(self.page.get_by_role('heading', name='Chọn một đô thị để bắt đầu')).to_be_visible()
        self.hold.add('/api/cities/2007')
        self.page.evaluate("location.hash='#/city?city=2007'")
        expect(self.page.get_by_text('Đang đọc hồ sơ đô thị...', exact=True)).to_be_visible()
        expect(self.page.locator('.city-hero')).to_have_count(0)
        self.page.wait_for_timeout(50)
        route, response = self.pending_get.pop()
        self.hold.clear()
        route.fulfill(status=response.status_code, body=response.content, content_type='application/json')
        self.wait_city('2007')
        self.page.evaluate("location.hash='#/city?city=nonexistent'")
        expect(self.page.locator('.city-detail-stack [role=alert]')).to_be_visible()
        expect(self.page.locator('.city-hero')).to_have_count(0)
        self.api_failures['/api/cities/11345'] = 503
        self.page.evaluate("location.hash='#/city?city=11345'")
        expect(self.page.locator('.city-detail-stack [role=alert]')).to_contain_text('Lỗi dữ liệu')
        self.api_failures.clear()
        self.page.get_by_role('button', name='Tải lại hồ sơ').click()
        self.wait_city('11345')

    def test_search_error_and_loading_results_recovery(self):
        self.api_failures['/api/cities'] = 503
        self.open('')
        expect(self.page.locator('.city-search-panel [role=alert]')).to_be_visible()
        self.api_failures.clear()
        self.page.get_by_role('textbox', name='Tìm đô thị', exact=True).fill('Shanghai')
        expect(self.page.locator('.city-result strong').first).to_have_text('Shanghai')
        expect(self.page.locator('.city-search-panel [role=alert]')).to_have_count(0)

    def test_rapid_city_switch_does_not_show_stale_details(self):
        self.open()
        self.hold.add('/api/cities/11345')
        self.page.evaluate("location.hash='#/city?city=11345'")
        expect(self.page.locator('.city-hero')).to_have_count(0)
        expect(self.page.get_by_text('Đang đọc hồ sơ đô thị...', exact=True)).to_be_visible()
        self.select('5213')
        route, response = self.pending_get.pop()
        route.fulfill(status=response.status_code, body=response.content, content_type='application/json')
        self.page.wait_for_timeout(100)
        self.wait_city('5213')
        expect(self.page.locator('.cluster-chip')).to_contain_text('Cụm 2')

    def test_gemini_empty_loading_error_retry_report_cache_and_regeneration(self):
        self.open()
        panel = self.page.locator('section.panel').filter(has=self.page.get_by_role('heading', name='Phân tích hồ sơ đô thị bằng Gemini', exact=True))
        expect(panel.locator('.panel-heading p')).to_have_text('Tập trung diễn giải cơ cấu và mức độ tương đồng với cụm')
        expect(panel.get_by_text('Dữ liệu được Python kiểm tra và làm tròn trước khi gửi.', exact=True)).to_have_count(0)
        empty = self.page.locator('.city-ai-empty-content')
        expect(empty.locator('p')).to_have_text('Chưa có báo cáo cho đô thị đang chọn.')
        expect(self.page.get_by_role('button', name='Phân tích bằng Gemini', exact=True)).to_have_count(1)
        self.page.get_by_role('button', name='Phân tích bằng Gemini', exact=True).click()
        expect(self.page.get_by_role('button', name='Đang phân tích…', exact=True)).to_be_disabled()
        expect(self.page.get_by_text('Gemini đang phân tích Los Angeles…', exact=True)).to_be_visible()
        self.finish_ai(status=503)
        expect(self.page.get_by_role('alert')).to_contain_text('Gemini chưa sẵn sàng')
        self.page.get_by_role('button', name='Phân tích bằng Gemini', exact=True).click()
        expect(self.page.get_by_role('button', name='Đang phân tích…', exact=True)).to_be_disabled()
        report = self.finish_ai()
        expect(self.page.locator('.ce-report .city-report-name')).to_have_text('Los Angeles')
        self.assertEqual(self.page.locator('.ce-report > p').all_text_contents(), [report['summary'], report['dispersion_and_representativeness']])
        expect(panel.get_by_text('Dữ liệu được Python kiểm tra và làm tròn trước khi gửi.', exact=True)).to_have_count(0)
        expect(self.page.locator('.ce-report')).not_to_contain_text('mock-city')
        expect(self.page.locator('.ce-report')).not_to_contain_text('Nội dung AI cần đối chiếu thống kê')
        styles = self.page.locator('.city-report-name').evaluate("e => ({size:parseFloat(getComputedStyle(e).fontSize), weight:Number(getComputedStyle(e).fontWeight), color:getComputedStyle(e).color, body:parseFloat(getComputedStyle(e.nextElementSibling.nextElementSibling).fontSize), primary:getComputedStyle(document.querySelector('.city-hero h2')).color})")
        self.assertGreater(styles['size'], styles['body'])
        self.assertGreaterEqual(styles['weight'], 600)
        self.assertLessEqual(styles['weight'], 700)
        self.assertEqual(styles['color'], styles['primary'])
        expect(empty).to_have_count(0)
        self.assertEqual(self.page.locator('.ce-report h3:not(.city-report-name)').all_text_contents(), ['Cơ cấu phát thải nổi bật', 'So sánh với đặc trưng cụm', 'Mức độ điển hình và tính đại diện', 'Hạn chế và hướng nghiên cứu'])
        self.assertEqual(self.page.locator('.ce-report li').all_text_contents(), report['comparisons'] + report['limitations'] + report['research_questions'])
        self.page.screenshot(path=str(OUT / 'gemini-report.png'), full_page=True)
        self.select('5213')
        expect(self.page.locator('.ce-report')).to_have_count(0)
        expect(self.page.locator('.city-report-name')).to_have_count(0)
        expect(empty).to_be_visible()
        self.select('2007')
        expect(self.page.locator('.city-report-name')).to_have_text('Los Angeles')
        expect(self.page.locator('.ce-report')).to_contain_text('Báo cáo kiểm thử 2007')
        self.assertEqual(self.ai_calls, ['2007','2007'])
        self.page.get_by_role('button', name='Phân tích bằng Gemini', exact=True).click()
        expect(self.page.get_by_role('button', name='Đang phân tích…', exact=True)).to_be_disabled()
        self.finish_ai(label='Báo cáo tạo lại')
        expect(self.page.locator('.ce-report')).to_contain_text('Báo cáo tạo lại 2007')
        expect(self.page.locator('.city-report-name')).to_have_text('Los Angeles')
        self.assertEqual(self.ai_calls, ['2007','2007','2007'])

    def test_gemini_switching_city_cancels_stale_request(self):
        self.open()
        self.page.get_by_role('button', name='Phân tích bằng Gemini', exact=True).click()
        expect(self.page.get_by_role('button', name='Đang phân tích…', exact=True)).to_be_disabled()
        self.select('11345')
        self.finish_ai(label='Không được hiện ở Shanghai')
        self.page.wait_for_timeout(100)
        expect(self.page.locator('.ce-report')).to_have_count(0)
        expect(self.page.locator('.city-report-name')).to_have_count(0)
        expect(self.page.get_by_role('button', name='Phân tích bằng Gemini', exact=True)).to_be_enabled()
        self.page.get_by_role('button', name='Phân tích bằng Gemini', exact=True).click()
        expect(self.page.get_by_role('button', name='Đang phân tích…', exact=True)).to_be_disabled()
        report = self.finish_ai(label='Báo cáo Shanghai')
        expect(self.page.locator('.ce-report')).to_contain_text('Báo cáo Shanghai 11345')
        expect(self.page.locator('.city-report-name')).to_have_text('Shanghai')
        self.assertEqual(self.page.locator('.ce-report > p').all_text_contents(), [report['summary'], report['dispersion_and_representativeness']])
        self.select('2007')
        expect(self.page.locator('.city-report-name')).to_have_count(0)
        self.select('11345')
        expect(self.page.locator('.city-report-name')).to_have_text('Shanghai')
        self.assertEqual(self.ai_calls, ['2007','11345'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
