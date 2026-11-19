"""Phase 2A routing, Home, keyboard navigation and responsive-shell acceptance checks.

Run against Vite dev/preview: python tests/ui_navigation.py.
NAVIGATION_UI_URL defaults to http://127.0.0.1:5173. Uses real CSV-backed GET APIs;
external tiles are blocked and Gemini must never be invoked.
"""
import os
from pathlib import Path
import re
import sys
import unittest
from urllib.parse import urlsplit
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from fastapi.testclient import TestClient
from playwright.sync_api import expect, sync_playwright
from api import advisor_service as advisor
from api.main import app
from ui_overview import CAPTURE_LEAFLET

URL = os.environ.get('NAVIGATION_UI_URL', 'http://127.0.0.1:5173').rstrip('/')
LABELS = ['Trang chủ', 'Tổng quan', 'Tra cứu đô thị', 'Khám phá thị trường', 'Giới thiệu']
PAGES = {'Trang chủ': '.home-page', 'Tổng quan': '.overview-page', 'Tra cứu đô thị': '.city-explorer',
         'Khám phá thị trường': '.market-explorer', 'Giới thiệu': '.about-hero'}
OUT = Path(os.environ.get('NAVIGATION_UI_SCREENSHOTS', str(ROOT / '.local/phase-2a/screenshots')))


class NavigationBrowserTests(unittest.TestCase):
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
        self.context = self.browser.new_context(viewport={'width':1440, 'height':1000}, reduced_motion='no-preference')
        self.context.add_init_script(CAPTURE_LEAFLET)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(error.stack or str(error)))
        self.page.route('**/api/**', self.api_route)
        self.page.route('https://tiles.stadiamaps.com/**', lambda route: route.abort())
        self.page.route('https://*.tile.openstreetmap.org/**', lambda route: route.abort())
        self.page.goto(URL + '/')
        expect(self.page.locator('.home-page')).to_be_visible()

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def api_route(self, route):
        request = route.request
        self.assertEqual(request.method, 'GET', 'Navigation must never call Gemini')
        url = urlsplit(request.url)
        with patch.object(advisor, '_advisor', side_effect=AssertionError('No Gemini during navigation')):
            response = self.api.get(url.path + ('?' + url.query if url.query else ''))
        route.fulfill(status=response.status_code, content_type='application/json', body=response.content)

    def nav(self, label):
        if self.page.locator('.navigation-toggle').is_visible():
            toggle = self.page.locator('.navigation-toggle')
            if toggle.get_attribute('aria-expanded') != 'true':
                toggle.click()
        self.page.get_by_role('navigation', name='Điều hướng chính').get_by_role('link', name=label, exact=True).click()
        expect(self.page.locator(PAGES[label])).to_be_visible()

    def assert_active(self, label):
        active = self.page.locator('.floating-navigation [aria-current="page"]')
        expect(active).to_have_count(1)
        expect(active).to_have_text(label)

    def test_home_structure_independent_brand_and_exact_destinations(self):
        nav = self.page.get_by_role('navigation', name='Điều hướng chính')
        self.assertEqual(nav.get_by_role('link').all_text_contents(), LABELS)
        self.assertFalse(self.page.locator('.global-brand').evaluate("brand => !!brand.closest('nav')"))
        expect(self.page.locator('.sidebar, .mobile-topbar')).to_have_count(0)
        expect(self.page.get_by_role('heading', name='GreenSegment Artificial Intelligence', exact=True)).to_be_visible()
        expect(self.page.locator('.home-eyebrow')).to_have_count(0)
        expect(self.page.locator('.home-description')).to_have_text('Nền tảng phân tích cơ cấu phát thải khí nhà kính của các đô thị, hỗ trợ khám phá dữ liệu khoa học, so sánh các nhóm đô thị và tìm hiểu thị trường công nghệ xanh.')
        expect(self.page.locator('.home-hero').get_by_role('link', name='Khám phá dữ liệu')).to_have_count(1)
        expect(self.page.locator('.global-header').get_by_role('link', name='Khám phá dữ liệu')).to_have_count(0)
        expect(self.page.locator('.home-feature-card')).to_have_count(3)
        self.assertEqual(self.page.locator('.home-feature-card h2').all_text_contents(), LABELS[1:4])
        expect(self.page.locator('.home-page .stat-grid, .home-page input')).to_have_count(0)
        self.assert_active('Trang chủ')

    def test_hero_cards_logo_and_stable_header_navigate(self):
        self.page.locator('.home-cta').focus()
        self.page.keyboard.press('Enter')
        expect(self.page.locator('.overview-page')).to_be_visible()
        self.assert_active('Tổng quan')
        for destination in LABELS[1:4]:
            self.page.get_by_role('link', name='GSAI — Trang chủ', exact=True).click()
            expect(self.page.locator('.home-page')).to_be_visible()
            original = self.page.locator('.floating-navigation').bounding_box()
            self.page.locator('.home-features').get_by_role('link', name=destination, exact=True).focus()
            self.page.keyboard.press('Enter')
            expect(self.page.locator(PAGES[destination])).to_be_visible()
            self.assert_active(destination)
            current = self.page.locator('.floating-navigation').bounding_box()
            self.assertTrue(all(abs(current[key]-original[key]) < 1 for key in current), [original,current])
            expect(self.page.locator('.global-header').get_by_role('link', name='Khám phá dữ liệu')).to_have_count(0)
        self.nav('Giới thiệu')
        self.assert_active('Giới thiệu')

    def test_direct_links_refresh_back_forward_and_city_profile(self):
        for route, selector in [('overview','.overview-page'),('market','.market-explorer'),('about','.about-hero')]:
            self.page.goto(URL + '/#/' + route)
            expect(self.page.locator(selector)).to_be_visible()
            self.page.reload()
            expect(self.page.locator(selector)).to_be_visible()
        city = self.api.get('/api/cities?page_size=1').json()['items'][0]
        self.page.goto(URL + '/#/city?city=' + str(city['city_id']))
        expect(self.page.locator('.city-hero h2')).to_have_text(city['city_name'])
        self.page.reload()
        expect(self.page.locator('.city-hero h2')).to_have_text(city['city_name'])
        self.nav('Trang chủ')
        self.nav('Tổng quan')
        self.page.go_back()
        expect(self.page.locator('.home-page')).to_be_visible()
        self.page.go_back()
        expect(self.page.locator('.city-hero h2')).to_have_text(city['city_name'])
        self.page.go_forward()
        expect(self.page.locator('.home-page')).to_be_visible()

    def test_history_retains_overview_scope_and_persistent_media(self):
        self.page.wait_for_function("document.querySelector('.video-background video')?.currentTime > .1")
        self.page.evaluate("""() => { window.savedVideo=document.querySelector('.video-background video');
          window.savedHeader=document.querySelector('.global-header');window.loads=0;
          savedVideo.addEventListener('loadstart',()=>window.loads++); }""")
        self.nav('Tổng quan')
        self.page.locator('#country-filter').select_option('Japan')
        self.page.locator('#cluster-filter').select_option('2')
        expect(self.page.locator('.ce-profile-id')).to_have_text('Cụm 2')
        self.nav('Giới thiệu')
        self.page.go_back()
        expect(self.page.locator('#country-filter')).to_have_value('Japan')
        expect(self.page.locator('#cluster-filter')).to_have_value('2')
        expect(self.page.locator('.ce-profile-id')).to_have_text('Cụm 2')
        self.page.go_forward()
        expect(self.page.locator('.about-hero')).to_be_visible()
        self.nav('Trang chủ')
        self.assertTrue(self.page.evaluate("savedVideo===document.querySelector('.video-background video') && savedHeader===document.querySelector('.global-header') && !savedVideo.paused && loads===0"))

    def test_mobile_menu_keyboard_escape_outside_and_all_destinations(self):
        self.page.set_viewport_size({'width':390,'height':844})
        toggle = self.page.locator('.navigation-toggle')
        expect(toggle).to_have_attribute('aria-expanded', 'false')
        toggle.focus()
        self.page.keyboard.press('Enter')
        expect(toggle).to_have_attribute('aria-expanded','true')
        expect(self.page.locator('.floating-navigation a').first).to_be_focused()
        self.page.keyboard.press('Tab')
        self.page.keyboard.press('Enter')
        expect(self.page.locator('.overview-page')).to_be_visible()
        expect(toggle).to_have_attribute('aria-expanded','false')
        toggle.click()
        self.page.keyboard.press('Escape')
        expect(toggle).to_be_focused()
        expect(toggle).to_have_attribute('aria-expanded','false')
        toggle.click()
        self.page.locator('.page-intro h1').click()
        expect(toggle).to_have_attribute('aria-expanded','false')
        for label in LABELS:
            self.nav(label)
            self.assert_active(label)
            expect(toggle).to_have_attribute('aria-expanded','false')
            brand = self.page.get_by_role('link', name='GSAI — Trang chủ', exact=True)
            expect(brand).to_have_text('GSAI')
            expect(brand.locator('img')).to_have_attribute('alt', '')
            self.assertTrue(brand.locator('img').evaluate('img => img.complete && img.naturalWidth > 0'))
        about = self.page.locator('.about-hero')
        expect(about.get_by_role('heading', name='GreenSegment AI', exact=True)).to_be_visible()
        self.assertEqual(about.locator('img').get_attribute('src'), brand.locator('img').get_attribute('src'))

    def test_responsive_home_and_menu_do_not_overlap_content(self):
        for width in (1440,1024,768,390,320):
            self.page.set_viewport_size({'width':width,'height':1000})
            self.page.wait_for_function('document.documentElement.scrollWidth <= innerWidth')
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            brand = self.page.locator('.global-brand').bounding_box()
            logo = self.page.locator('.global-brand-logo').bounding_box()
            self.assertAlmostEqual(logo['width'], logo['height'], delta=0.5)
            self.assertGreaterEqual(logo['y'], brand['y'])
            self.assertLessEqual(logo['y'] + logo['height'], brand['y'] + brand['height'])
            self.assertTrue(self.page.locator('#home-title').evaluate('e => e.scrollWidth <= e.clientWidth'))
            if width > 900:
                nav = self.page.locator('.floating-navigation').bounding_box()
                self.assertLessEqual(brand['x']+brand['width'], nav['x'])
                for link in self.page.locator('.floating-navigation a').all():
                    self.assertGreaterEqual(link.bounding_box()['height'],44)
            else:
                self.page.locator('.navigation-toggle').click()
                nav = self.page.locator('.floating-navigation').bounding_box()
                main = self.page.locator('main').bounding_box()
                self.assertGreaterEqual(main['y'], nav['y']+nav['height'])
                self.page.screenshot(path=str(OUT/f'menu-{width}.png'))
                self.page.keyboard.press('Escape')
            cards = [card.bounding_box() for card in self.page.locator('.home-feature-card').all()]
            if width > 630:
                self.assertTrue(all(abs(card['y']-cards[0]['y']) < 1 for card in cards))
            else:
                self.assertTrue(cards[0]['y'] < cards[1]['y'] < cards[2]['y'])
            self.assertGreaterEqual(self.page.locator('.home-cta').bounding_box()['height'],44)
            self.page.screenshot(path=str(OUT/f'home-{width}.png'),full_page=True)
            self.nav('Giới thiệu')
            about = self.page.locator('.about-hero')
            about_logo = about.locator('img')
            bounds = about_logo.bounding_box()
            self.assertAlmostEqual(bounds['width'], bounds['height'], delta=0.5)
            self.assertLessEqual(bounds['x'] + bounds['width'], about.locator('h2').bounding_box()['x'])
            self.assertTrue(about_logo.evaluate('img => img.complete && img.naturalWidth === img.naturalHeight && img.naturalWidth > 0'))
            about.screenshot(path=str(OUT/f'about-brand-{width}.png'))
            self.page.get_by_role('link', name='GSAI — Trang chủ', exact=True).click()
            expect(self.page.locator('.home-page')).to_be_visible()

    def test_map_and_city_list_write_refreshable_profile_urls(self):
        self.nav('Tổng quan')
        self.page.locator('#country-filter').select_option('Singapore')
        self.page.locator('#cluster-filter').select_option('2')
        self.page.wait_for_function('window.testMap() && testMarkers().length === 1')
        self.page.evaluate("() => { testMarkers()[0].fire('click'); }")
        expect(self.page).to_have_url(re.compile(r'/#/city\?city='))
        expect(self.page.locator('.city-hero h2')).to_be_visible()
        name = self.page.locator('.city-hero h2').inner_text()
        self.page.reload()
        expect(self.page.locator('.city-hero h2')).to_have_text(name)
        first = self.page.locator('.city-result').first
        expect(first).to_be_visible()
        next_name = first.locator('strong').inner_text()
        first.click()
        expect(self.page.locator('.city-hero h2')).to_have_text(next_name)
        self.page.reload()
        expect(self.page.locator('.city-hero h2')).to_have_text(next_name)

    def test_skip_link_and_unknown_route_fallback(self):
        self.page.keyboard.press('Tab')
        expect(self.page.locator('.skip-link')).to_be_focused()
        self.page.keyboard.press('Enter')
        expect(self.page.locator('#main-content')).to_be_focused()
        expect(self.page.locator('.home-page')).to_be_visible()
        self.assertEqual(urlsplit(self.page.url).fragment, '')
        self.page.goto(URL+'/#/unknown')
        expect(self.page.locator('.home-page')).to_be_visible()
        self.assert_active('Trang chủ')

    def test_leaving_during_animated_map_zoom_cleans_up_canvas_and_zoom(self):
        for _ in range(3):
            self.nav('Tổng quan')
            self.page.locator('#country-filter').select_option('Japan')
            self.page.wait_for_function("window.testMap() && testMarkers().length > 0 && document.querySelector('.stat-grid').getAttribute('aria-busy')==='false'")
            self.page.wait_for_timeout(350)
            # Start a known zoom rather than race a short auto-fit that may have already finished.
            self.page.evaluate("() => { const map=testMap(); map.setZoom(map.getZoom()+1,{animate:true}); }")
            self.page.wait_for_function('testMap()._animatingZoom', timeout=5000)
            self.nav('Giới thiệu')
            self.page.wait_for_timeout(350)  # Leaflet's delayed zoom completion is 250ms.
            self.nav('Trang chủ')
        self.assertEqual(self.errors, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
