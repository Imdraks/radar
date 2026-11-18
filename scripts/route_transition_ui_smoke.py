"""Client navigation and delayed protected pages; local API fixtures only."""
import asyncio
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright, expect
from theme_ui_smoke import fixture

BASE = os.environ.get('RADAR_UI_BASE_URL', 'http://127.0.0.1:3000')
if urlparse(BASE).hostname not in {'localhost', '127.0.0.1'}:
    raise RuntimeError('Route transition fixtures may only target a local instance')


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'],
                                         executable_path=os.environ.get('RADAR_BROWSER_PATH'))
        for width, reduced in [(1440, 'no-preference'), (390, 'no-preference'), (390, 'reduce')]:
            context = await browser.new_context(viewport={'width': width, 'height': 950},
                                                reduced_motion=reduced, locale='fr-FR')
            await context.add_init_script('''
              localStorage.setItem('access_token','route-test-only');
              localStorage.setItem('current_workspace_id','1');
              localStorage.setItem('opportunities-radar-welcome-shown-v2','true');
              localStorage.setItem('cookie-consent', JSON.stringify({version:'2026-11-13',
                chosenAt:new Date().toISOString(),analytics:'denied'}));
              window.__routeSession = Math.random();
              window.__routeAnimations = [];
              const animate = Element.prototype.animate;
              Element.prototype.animate = function(frames, options) {
                if (this.tagName === 'MAIN') window.__routeAnimations.push({
                  path:location.pathname, busy:this.getAttribute('aria-busy'),
                  title:!!this.querySelector('h1:not(.sr-only),h2'), frames});
                return animate.call(this, frames, options);
              };
            ''')
            async def api(route):
                # Exercise a main that is absent during auth, then explicitly busy
                # while the subscription and navigation permissions are fetched.
                if urlparse(route.request.url).path.endswith(('/auth/me', '/subscription/current', '/subscription/navigation')):
                    await asyncio.sleep(.35)
                await fixture(route)
            await context.route('**/api/**', api)
            page = await context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.goto(BASE + '/projects', wait_until='networkidle')
            await page.get_by_role('heading', name='TEST Theme Project', exact=True).wait_for()
            session = await page.evaluate('window.__routeSession')
            await page.get_by_role('link', name='Documentation Radar', exact=True).click()
            await page.wait_for_url('**/doc')
            await page.get_by_role('heading', name='Bien prendre Radar en main.', exact=True).wait_for()
            assert await page.evaluate('window.__routeSession') == session, 'Expected client navigation'
            await page.go_back(wait_until='networkidle')
            await page.get_by_role('heading', name='TEST Theme Project', exact=True).wait_for()
            await expect(page.locator('#radar-main')).to_have_attribute('aria-busy', 'false')
            assert await page.evaluate('window.__routeSession') == session
            records = await page.evaluate('window.__routeAnimations')
            if reduced == 'reduce':
                assert not records, records
            else:
                assert any(r['path'] == '/doc' for r in records), records
                assert any(r['path'] == '/projects' and r['busy'] == 'false' and r['title'] for r in records), records
                assert all('transform' not in frame and 'translate' not in frame for r in records for frame in r['frames'])
            # Fixed project overlays must continue to use viewport coordinates.
            await page.get_by_role('button', name='Nouveau projet', exact=True).click()
            overlay = page.locator('main .fixed.inset-0').first
            bounds = await overlay.bounding_box()
            await expect(overlay).to_have_css('position', 'fixed')
            margin = await overlay.evaluate('e => parseFloat(getComputedStyle(e).marginTop) || 0')
            assert abs(bounds['x']) < 1 and abs(bounds['y'] - margin) < 1 and abs(bounds['width'] - width) < 1, bounds
            await page.get_by_role('button', name='Annuler', exact=True).click()
            await page.get_by_role('link', name='Documentation Radar', exact=True).click()
            await page.wait_for_url('**/doc')
            await page.get_by_role('link', name='Contacter l’équipe', exact=True).click()
            await page.wait_for_url('**/contact')
            name = page.get_by_label('Nom complet', exact=True)
            await name.fill('TEST Navigation')
            await name.evaluate('element => window.__contactField = element')
            await page.emulate_media(reduced_motion='reduce')
            await expect(name).to_have_value('TEST Navigation')
            assert await name.evaluate('element => element === window.__contactField')
            await page.wait_for_function('document.getAnimations().every(a => a.playState !== "running")')
            assert not errors, errors
            print(f'{width}px/{reduced}: client/back navigation, delayed main, reduced motion, forms and fixed overlays OK', flush=True)
            await context.close()
        await browser.close()


asyncio.run(main())
