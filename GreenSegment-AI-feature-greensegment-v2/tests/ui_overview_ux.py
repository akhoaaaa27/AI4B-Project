"""Phase 2B UI checks: real CSV/Leaflet, with explicit Gemini response mocks only."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from playwright.sync_api import expect
import ui_overview as overview_ui
from api import data_service as data
import test_cluster_explorer as cluster_fixtures

OUT = ROOT / '.local/phase-2b/after'
def number(value):
    return f'{value:,}'.replace(',', '.')


class OverviewUXBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        overview_ui.OverviewBrowserTests.setUpClass()
        OUT.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        overview_ui.OverviewBrowserTests.tearDownClass()

    def setUp(self):
        self.base = overview_ui.OverviewBrowserTests()
        self.base.setUp()
        self.page = self.base.page
        self.gemini_calls = []
        self.pending = []
        self.page.route('**/api/cluster-explorer/*/interpret', self.mock_gemini)

    def tearDown(self):
        self.base.tearDown()

    def mock_gemini(self, route):
        self.assertEqual(route.request.method, 'POST')
        cluster_id = int(route.request.url.split('/cluster-explorer/')[1].split('/')[0])
        self.gemini_calls.append(cluster_id)
        self.pending.append((route, cluster_id))

    def finish_report(self, *, label='Kiểm thử báo cáo', status=200):
        route, cluster_id = self.pending.pop(0)
        if status != 200:
            route.fulfill(status=status, json={'detail':'Gemini chưa sẵn sàng trong kiểm thử.'})
            return None
        report = copy.deepcopy(cluster_fixtures.ClusterExplorerTests.report_fixture())
        report['summary'] = f'{label} cho cụm {cluster_id}. ' + report['summary'] * 3
        route.fulfill(status=200, json={'cluster_id':cluster_id, 'report':report})
        return report

    def generate(self):
        selected = self.page.locator('.ce-profile-id').inner_text().split()[-1]
        self.page.locator('.ce-ai-panel').get_by_role('button', name=f'Diễn giải cụm {selected}', exact=True).click()
        expect(self.page.locator('.ce-ai-panel .loading')).to_be_visible()

    def assert_caption(self):
        country = self.page.locator('#country-filter').input_value() or None
        cluster = self.page.locator('#cluster-filter').input_value()
        sector = self.page.locator('#sector-filter').input_value() or None
        result = data.map_points(country, int(cluster) if cluster else None, sector)
        lines = self.page.locator('.overview-map-caption p')
        expect(lines).to_have_count(2)
        expect(lines.nth(0)).to_have_text(f"Đang hiển thị {number(result['shown'])}/{number(result['total_matching'])} đô thị.")
        expect(lines.nth(1)).to_have_text('Nhấn vào một điểm để xem hồ sơ đô thị.')

    def test_collapsed_selector_toggles_only_ui_and_preserves_map_nodes(self):
        toggle = self.page.locator('.map-selector-toggle')
        expect(toggle).to_have_attribute('aria-expanded','false')
        expect(self.page.locator('.map-selector-summary')).to_have_text('Đang xem: Tất cả 3 cụm')
        self.page.evaluate('() => { window.originalMarkers=testMarkers(); }')
        before = self.base.camera()
        calls = list(self.base.calls)
        for _ in range(3):
            toggle.focus()
            self.page.keyboard.press('Enter')
            expect(toggle).to_have_attribute('aria-expanded','true')
            expect(self.page.locator('.map-selector .ce-selector button')).to_have_count(4)
            expect(self.page.locator('.ce-cluster-size')).to_have_count(0)
            self.assertNotIn('%',self.page.locator('.map-selector').inner_text())
            self.page.keyboard.press('Space')
            expect(toggle).to_have_attribute('aria-expanded','false')
            self.base.assert_camera(before)
            self.assertEqual(self.base.calls,calls)
            self.assertTrue(self.page.evaluate('testMarkers().every((m,i)=>m===originalMarkers[i])'))

    def test_selected_count_is_global_and_all_sources_stay_synchronized(self):
        clusters = {c['cluster_id']:c for c in data.all_clusters()}
        self.base.open_selector()
        for cluster_id in (0,1,2):
            self.base.map_choice(cluster_id).click()
            self.base.wait_data()
            expect(self.page.locator('.map-selector-toggle')).to_have_attribute('aria-expanded','true')
            sizes = self.page.locator('.ce-cluster-size')
            expect(sizes).to_have_count(1)
            expect(sizes).to_have_text(f"{number(clusters[cluster_id]['city_count'])} đô thị")
            expect(self.page.locator('.map-selector .selected .map-selection-check')).to_be_visible()
            self.base.assert_selection(cluster_id,cluster_id)
            self.assertNotIn('%',self.page.locator('.map-selector').inner_text())
        self.base.choose_country('Japan')
        self.base.choose_cluster(0)
        self.assertLess(len(self.base.markers()),clusters[0]['city_count'])
        expect(self.page.locator('.ce-cluster-size')).to_have_text(f"{number(clusters[0]['city_count'])} đô thị")
        self.page.locator('.map-selector-toggle').click()
        expect(self.page.locator('.map-selector-summary')).to_have_text('Đang xem: Cụm 0')
        self.page.get_by_role('button', name='Chọn Cụm 1', exact=True).focus()
        self.page.keyboard.press('Enter')
        self.base.wait_data()
        expect(self.page.locator('.map-selector-summary')).to_have_text('Đang xem: Cụm 1')
        self.base.map_choice('').click()
        self.base.wait_data()
        expect(self.page.locator('.ce-cluster-size')).to_have_count(0)
        self.base.assert_selection('',1)
        expect(self.page.locator('.ce-profile-kpis dd').nth(1)).to_contain_text('%')

    def test_map_captions_use_actual_filtered_and_sampled_counts(self):
        self.assert_caption()
        for country,cluster,sector in [('','0',''),('Japan','1',''),('Cuba','0','agriculture')]:
            self.base.choose_country(country)
            self.base.choose_cluster(cluster)
            self.page.locator('#sector-filter').select_option(sector)
            self.base.wait_data()
            self.assert_caption()
        expect(self.page.locator('.map-panel .empty-state')).to_be_visible()
        self.assertNotIn('Nền bản đồ cần kết nối Internet.',self.page.locator('.map-panel').inner_text())
        self.assertNotIn('Bản đồ lấy mẫu tối đa',self.page.locator('.map-panel').inner_text())

    def test_transparent_header_allows_real_filter_map_wheel_and_drag_interactions(self):
        self.assertEqual(self.page.locator('.global-header').evaluate('e=>getComputedStyle(e).backgroundImage'),'none')
        self.assertEqual(self.page.locator('.global-header').evaluate('e=>getComputedStyle(e).pointerEvents'),'none')
        self.page.evaluate("scrollTo(0,document.querySelector('#sector-filter').getBoundingClientRect().top+scrollY-30)")
        rect = self.page.locator('#sector-filter').bounding_box()
        x,y = rect['x']+rect['width']-24,rect['y']+20
        self.assertTrue(self.page.evaluate('p=>document.elementFromPoint(p.x,p.y)===document.querySelector("#sector-filter")',{'x':x,'y':y}))
        self.page.mouse.click(x,y)
        self.page.keyboard.press('Escape')
        self.page.evaluate("scrollTo(0,document.querySelector('.worldmap').getBoundingClientRect().top+scrollY-25)")
        rect = self.page.locator('.worldmap').bounding_box()
        x,y = rect['x']+rect['width']-120,50
        self.assertTrue(self.page.evaluate('p=>!!document.elementFromPoint(p.x,p.y)?.closest(".worldmap")',{'x':x,'y':y}))
        zoom = self.base.camera()['zoom']
        self.page.mouse.move(x,y)
        self.page.mouse.wheel(0,-180)
        self.page.wait_for_function('z=>testMap().getZoom()>z',arg=zoom)
        self.page.wait_for_function('!testMap()._animatingZoom')
        before = self.base.camera()
        self.page.mouse.move(x,y)
        self.page.mouse.down()
        self.page.mouse.move(x-80,y+15,steps=8)
        self.page.mouse.up()
        self.page.wait_for_timeout(350)
        self.assertNotEqual(before,self.base.camera())
        self.page.get_by_role('navigation',name='Điều hướng chính').get_by_role('link',name='Trang chủ',exact=True).click()
        expect(self.page.locator('.home-page')).to_be_visible()

    def test_gemini_empty_loading_full_report_and_regeneration(self):
        panel = self.page.locator('.ce-ai-panel')
        expect(panel.locator('.overview-report-empty')).to_have_text('Chưa có báo cáo cho cụm đang chọn.')
        self.generate()
        report = self.finish_report()
        expect(panel.locator('.ce-report')).to_contain_text(report['summary'])
        expect(panel.locator('.ce-report h3')).to_have_text(['Đặc điểm nổi bật','So sánh các cụm','Mức độ tương đồng trong cụm','Hạn chế và hướng nghiên cứu'])
        expect(panel.locator('.overview-report-empty')).to_have_count(0)
        geometry = panel.locator('.ce-report').evaluate('e=>({height:e.clientHeight,scroll:e.scrollHeight,max:getComputedStyle(e).maxHeight,overflow:getComputedStyle(e).overflowY})')
        self.assertGreater(geometry['height'],500)
        self.assertLessEqual(geometry['scroll']-geometry['height'],1)
        self.assertEqual(geometry['max'],'none')
        self.assertNotIn(geometry['overflow'],['scroll','auto','hidden'])
        panel.locator('.ce-report li').last.scroll_into_view_if_needed()
        expect(panel.locator('.ce-report li').last).to_contain_text(report['research_questions'][-1])
        self.generate()
        expect(panel.locator('.ce-report')).to_contain_text(report['summary'])
        updated = self.finish_report(label='Báo cáo tạo lại')
        expect(panel.locator('.ce-report')).to_contain_text(updated['summary'])

    def test_gemini_error_retry_and_cached_report_per_cluster(self):
        self.generate()
        self.finish_report(status=503)
        expect(self.page.locator('.ce-ai-panel [role="alert"]')).to_contain_text('Gemini chưa sẵn sàng')
        self.generate()
        report = self.finish_report(label='Báo cáo được giữ')
        expect(self.page.locator('.ce-report')).to_contain_text(report['summary'])
        self.base.choose_cluster(1)
        expect(self.page.locator('.ce-report')).to_have_count(0)
        expect(self.page.locator('.overview-report-empty')).to_be_visible()
        self.base.choose_cluster(0)
        expect(self.page.locator('.ce-report')).to_contain_text(report['summary'])
        self.assertEqual(self.gemini_calls,[0,0])

    def test_gemini_late_response_never_appears_under_another_cluster(self):
        self.generate()
        self.base.choose_cluster(1)
        self.finish_report(label='Phản hồi cũ của cụm 0')
        expect(self.page.locator('.ce-report')).to_have_count(0)
        self.generate()
        current = self.finish_report(label='Phản hồi đúng cụm 1')
        expect(self.page.locator('.ce-report')).to_contain_text(current['summary'])
        expect(self.page.locator('.ce-report')).not_to_contain_text('Phản hồi cũ của cụm 0')
        self.base.choose_cluster(0)
        expect(self.page.locator('.ce-report')).to_have_count(0)

    def test_dynamic_cta_tracks_profile_for_chart_filters_selector_and_all(self):
        stats_calls = sum(path == '/api/cluster-explorer' for _,path in self.base.calls)
        for cluster_id in (0,1,2):
            self.page.get_by_role('button',name=f'Chọn Cụm {cluster_id}',exact=True).focus()
            self.page.keyboard.press('Enter')
            self.base.wait_data()
            expect(self.page.locator('.ce-ai-panel button')).to_have_text(f'Diễn giải cụm {cluster_id}')
            self.base.map_choice('').click()
            self.base.wait_data()
            expect(self.page.locator('.ce-profile-id')).to_have_text(f'Cụm {cluster_id}')
            expect(self.page.locator('.ce-ai-panel button')).to_have_text(f'Diễn giải cụm {cluster_id}')
            self.base.choose_cluster((cluster_id+1)%3)
            expect(self.page.locator('.ce-ai-panel button')).to_have_text(f'Diễn giải cụm {(cluster_id+1)%3}')
            self.base.map_choice(cluster_id).click()
            self.base.wait_data()
            expect(self.page.locator('.ce-ai-panel button')).to_have_text(f'Diễn giải cụm {cluster_id}')
            self.base.choose_cluster('')
            expect(self.page.locator('.ce-ai-panel button')).to_have_text(f'Diễn giải cụm {cluster_id}')
        self.assertEqual(self.gemini_calls,[],'Changing the label must never generate a report')
        self.assertEqual(sum(path == '/api/cluster-explorer' for _,path in self.base.calls),stats_calls)
        self.generate()
        self.assertEqual(self.gemini_calls,[2],'All map clusters must still interpret profile 2')
        report = self.finish_report()
        expect(self.page.locator('.ce-report')).to_contain_text(report['summary'])
        expect(self.page.locator('.ce-ai-action button')).to_have_text('Diễn giải cụm 2')

    def test_centered_empty_group_and_research_cards_responsive(self):
        panel=self.page.locator('.ce-ai-panel')
        description='Gemini hỗ trợ diễn giải đặc điểm cơ cấu phát thải và sự khác biệt giữa các cụm dựa trên số liệu thống kê của hệ thống.'
        for width in (1440,1024,768,390,320):
            self.page.set_viewport_size({'width':width,'height':1000})
            self.page.wait_for_function('document.documentElement.scrollWidth<=innerWidth')
            expect(panel.locator('.panel-heading h2')).to_have_text('Gemini diễn giải cụm')
            expect(panel.locator('.ce-ai-copy p')).to_have_text(description)
            expect(panel.locator('button')).to_have_count(1)
            expect(panel.locator('.ce-ai-action button')).to_have_count(0)
            boxes=[panel.locator(s).bounding_box() for s in ('.ce-ai-document-icon','.overview-report-empty','.ce-ai-empty-content button')]
            center=panel.bounding_box()['x']+panel.bounding_box()['width']/2
            self.assertTrue(all(abs(b['x']+b['width']/2-center)<1 for b in boxes),boxes)
            self.assertLess(boxes[0]['y']+boxes[0]['height'],boxes[1]['y'])
            self.assertLess(boxes[1]['y']+boxes[1]['height'],boxes[2]['y'])
            cards=self.page.locator('.research-card')
            expect(cards).to_have_count(2)
            expect(cards.nth(0)).to_contain_text('EDGAR 2024')
            expect(cards.nth(1)).to_contain_text('K-Means · 3 cụm')
            expect(cards.nth(1)).to_contain_text('Phân nhóm theo cơ cấu phát thải của 7 lĩnh vực.')
            a,b=[e.bounding_box() for e in cards.all()]
            if width>630:
                self.assertLess(a['x'],b['x'])
                self.assertLess(abs(a['height']-b['height']),1)
            else:
                self.assertLess(a['y'],b['y'])
            caution=self.page.locator('.research-caution')
            expect(caution).to_be_visible()
            expect(caution).to_contain_text('Đặc điểm cơ cấu phát thải không đủ cơ sở để kết luận nguyên nhân phát thải hoặc tính khả thi của các giải pháp công nghệ.')
            self.assertFalse(caution.evaluate("e=>!!e.closest('details')"))
            summary=self.page.locator('.overview-methodology summary')
            summary.click()
            expect(self.page.locator('.overview-methodology details p')).to_have_text('EDGAR là cơ sở dữ liệu phát thải được sử dụng trong nghiên cứu, cung cấp số liệu phát thải khí nhà kính năm 2024 của dự án.')
            summary.click()
            expect(caution).to_be_visible()
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))

    def test_responsive_layout_selector_report_and_research_notes(self):
        report = None
        for width in (1440,1024,768,390,320):
            self.page.set_viewport_size({'width':width,'height':1000})
            self.page.wait_for_function('document.documentElement.scrollWidth<=innerWidth')
            self.page.evaluate('scrollTo(0,0)')
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            panel = self.page.locator('.data-filters-inline').bounding_box()
            if width>=1024:
                self.assertLessEqual(panel['height'],150)
            if width<=630:
                self.assertLessEqual(panel['height'],340)
            help_summary = self.page.locator('.filters-footer summary')
            help_summary.click()
            expect(self.page.locator('.filters-footer details p')).to_be_visible()
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            help_summary.click()
            cards = [e.bounding_box() for e in self.page.locator('.stat-card').all()]
            self.assertEqual(len(cards),4)
            self.assertTrue(all(abs(r['height']-cards[0]['height'])<2 for r in cards),cards)
            map_box = self.page.locator('.worldmap').bounding_box()
            self.assertGreaterEqual(map_box['height'],420)
            self.assertGreaterEqual(map_box['width'],self.page.locator('.map-panel').bounding_box()['width']-60)
            self.page.screenshot(path=str(OUT/f'overview-{width}.png'),full_page=True)
            self.base.open_selector()
            self.page.locator('.worldmap').scroll_into_view_if_needed()
            for button in self.page.locator('.map-selector button').all():
                self.assertGreaterEqual(button.bounding_box()['height'],44)
            self.page.screenshot(path=str(OUT/f'selector-expanded-{width}.png'))
            self.page.locator('.map-selector-toggle').click()
            self.page.locator('.ce-exploration-grid').scroll_into_view_if_needed()
            chart = self.page.locator('.ce-overview-chart').bounding_box()
            profile = self.page.locator('.ce-cluster-profile').bounding_box()
            if width>=1024:
                self.assertLess(chart['x'],profile['x'])
                self.assertLess(abs(chart['y']-profile['y']),2)
            summary = self.page.locator('.overview-chart-help summary')
            expect(summary).to_have_text('GHG, cơ cấu phát thải và tâm K-Means')
            summary.click()
            expect(self.page.locator('.overview-chart-help dl')).to_be_visible()
            summary.click()
            expect(self.page.locator('.overview-methodology')).to_contain_text('EDGAR 2024')
            expect(self.page.locator('.overview-methodology')).to_contain_text('không đủ cơ sở để kết luận nguyên nhân phát thải hoặc tính khả thi')
            if report is None:
                self.generate()
                report = self.finish_report()
            article = self.page.locator('.ce-report')
            expect(article).to_contain_text(report['research_questions'][-1])
            self.assertTrue(article.evaluate('e=>e.scrollHeight<=e.clientHeight+1'))
            article.scroll_into_view_if_needed()
            self.page.screenshot(path=str(OUT/f'gemini-report-{width}.png'),full_page=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
