"""Public header session/photo behavior. Fixtures run on a local site only."""
import asyncio
import base64
import json
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright, expect
from theme_ui_smoke import fixture

BASE = os.environ.get('RADAR_UI_BASE_URL', 'http://127.0.0.1:3000')
if urlparse(BASE).hostname not in {'127.0.0.1', 'localhost'}:
    raise RuntimeError('Avatar fixtures require a local instance')
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
PHOTO = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAQABADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDzSiiivpT7A//Z'
USER = {'id': 1, 'email': 'avatar@example.com', 'full_name': 'TEST Avatar', 'is_active': True,
        'role': 'admin', 'is_superuser': True, 'avatar_url': 'https://lh3.googleusercontent.com/radar-test'}
CONSENT = '''localStorage.setItem('cookie-consent',JSON.stringify({version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}));'''


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'], executable_path=os.environ.get('RADAR_BROWSER_PATH'))
        cases = [(1440, 'guest'), (1440, 'invalid'), (1440, 'core'), (1440, 'premium'), (1440, 'business'),
                 (390, 'business'), (390, 'broken-photo'), (390, 'expired'), (390, 'billing-failure'), (390, 'refresh')]
        for width, mode in cases:
            context = await browser.new_context(viewport={'width': width, 'height': 950})
            await context.add_init_script(CONSENT)
            if mode != 'guest':
                await context.add_init_script('''localStorage.setItem('access_token','test-avatar-only');localStorage.setItem('current_workspace_id','1');''')
            if mode == 'refresh':
                await context.add_init_script("localStorage.setItem('refresh_token','test-refresh-only')")
            # A persisted authenticated flag is deliberately untrusted.
            if mode == 'invalid':
                await context.add_init_script('''localStorage.setItem('auth-storage',JSON.stringify({state:{user:{id:1,full_name:'STALE',is_active:true},isAuthenticated:true},version:0}));''')
            calls = []
            async def api(route):
                path = urlparse(route.request.url).path
                calls.append((path, route.request.method))
                if path.endswith('/auth/me'):
                    rejected = mode == 'invalid' or (mode == 'refresh' and route.request.headers.get('authorization') != 'Bearer test-renewed')
                    await route.fulfill(status=401 if rejected else 200, content_type='application/json', body=json.dumps({'detail':'expired'} if rejected else USER))
                elif path.endswith('/auth/refresh'):
                    await route.fulfill(status=200, content_type='application/json', body=json.dumps({'access_token':'test-renewed','refresh_token':'test-refresh-renewed'}))
                elif path.endswith('/subscription/current'):
                    tier = mode if mode in ['core','premium','business'] else 'business'
                    await route.fulfill(status=503 if mode == 'billing-failure' else 200, content_type='application/json', body=json.dumps({'workspace_id':1,'plan':tier,'plan_expires_at':'2020-01-01T00:00:00' if mode == 'expired' else None}))
                elif path.endswith('/auth/logout'):
                    await route.fulfill(status=200, content_type='application/json', body='{}')
                else:
                    await fixture(route)
            await context.route('**/api/**', api)
            await context.route('https://lh3.googleusercontent.com/**', lambda route: route.fulfill(status=404) if mode == 'broken-photo' else route.fulfill(status=200, content_type='image/png', body=PNG))
            page = await context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error) + str(error.stack)))
            await page.goto(BASE, wait_until='networkidle')
            header = page.locator('header').first
            if mode in ['guest','invalid']:
                await expect(header.get_by_role('link', name='Se connecter', exact=True)).to_be_visible()
                assert await header.locator('.radar-account-ring').count() == 0
                assert page.url.rstrip('/') == BASE.rstrip('/'), 'Optional session must not redirect public visitors'
                if mode == 'guest':
                    assert not any('/auth/me' in path for path, _ in calls)
            else:
                button = header.get_by_role('button', name='Ouvrir le menu du compte TEST Avatar', exact=True)
                await expect(button).to_be_visible()
                assert await header.get_by_role('link', name='Se connecter', exact=True).count() == 0
                assert await header.get_by_role('link', name='Parlons de votre agence', exact=True).count() == 0
                expected = 'core' if mode == 'expired' else 'unknown' if mode == 'billing-failure' else mode if mode in ['core','premium','business'] else 'business'
                ring = header.locator('.radar-account-ring')
                await expect(ring).to_have_attribute('data-tier', expected)
                animation = await ring.evaluate("e => getComputedStyle(e,'::before').animationName")
                assert animation == ('radar-account-sheen' if expected == 'premium' else 'radar-account-spectrum' if expected == 'business' else 'none'), animation
                gradient = await ring.evaluate("e => getComputedStyle(e,'::before').backgroundImage")
                assert ('conic-gradient' in gradient) == (expected in ['premium','business'])
                assert await ring.evaluate("e => getComputedStyle(e,'::after').content") == 'none'
                await expect(ring).to_have_css('width','56px')
                if mode == 'broken-photo':
                    await expect(ring).to_have_text('TA')
                else:
                    await expect(ring.locator('img')).to_have_attribute('referrerpolicy','no-referrer')
                    await expect(ring.locator('img')).to_have_css('transform','none')
                await page.emulate_media(reduced_motion='reduce')
                await expect(ring).to_have_css('position','relative')
                assert await ring.evaluate("e => getComputedStyle(e,'::before').animationName") == 'none'
                assert await ring.evaluate("e => getComputedStyle(e,'::after').animationName") == 'none'
                await button.focus()
                await page.keyboard.press('Enter')
                await expect(page.get_by_role('menuitem',name='Paramètres du compte',exact=True)).to_be_visible()
                await page.keyboard.press('Escape')
                await expect(button).to_be_focused()
                if width == 1440 and mode == 'business':
                    await page.screenshot(path='/tmp/radar-account-business.png')
                    await button.click()
                    await page.get_by_role('menuitem', name='Se déconnecter', exact=True).click()
                    await expect(header.get_by_role('link', name='Se connecter', exact=True)).to_be_visible()
                    assert await page.evaluate("localStorage.getItem('access_token')") is None
                if mode == 'refresh':
                    assert sum(path.endswith('/auth/refresh') for path, _ in calls) == 1
            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not errors, errors
            print(f'{width}px/{mode}: verified session, photo, tier, keyboard, reduced motion OK', flush=True)
            await context.close()
        # Settings: invalid files stay local; failed uploads preserve the existing photo.
        context = await browser.new_context(viewport={'width':390,'height':950})
        await context.add_init_script(CONSENT + "localStorage.setItem('access_token','test-avatar-only');localStorage.setItem('current_workspace_id','1');localStorage.setItem('opportunities-radar-welcome-shown-v2','true');")
        uploads = []
        successful = False
        current_photo = USER['avatar_url']
        async def settings_api(route):
            nonlocal current_photo
            path = urlparse(route.request.url).path
            if path.endswith('/auth/me'):
                await route.fulfill(status=200,content_type='application/json',body=json.dumps({**USER,'avatar_url':current_photo}))
            elif path.endswith('/auth/me/avatar'):
                uploads.append(route.request.method)
                if successful:
                    current_photo = PHOTO if route.request.method == 'POST' else USER['avatar_url']
                    await route.fulfill(status=200,content_type='application/json',body=json.dumps({**USER,'avatar_url':current_photo}))
                else:
                    await route.fulfill(status=422,content_type='application/json',body=json.dumps({'detail':'TEST — image refusée'}))
            else:
                await fixture(route)
        await context.route('**/api/**',settings_api)
        await context.route('https://lh3.googleusercontent.com/**',lambda r:r.fulfill(status=200,content_type='image/png',body=PNG))
        page = await context.new_page()
        await page.goto(BASE + '/settings',wait_until='networkidle')
        await expect(page.locator('#radar-main')).to_have_attribute('aria-busy','false')
        picker = page.get_by_label('Photo de profil à importer',exact=True)
        await picker.set_input_files({'name':'fake.svg','mimeType':'image/svg+xml','buffer':b'<svg/>'})
        await expect(page.locator('main').get_by_role('alert')).to_contain_text('JPEG, PNG ou WebP')
        assert not uploads
        await picker.set_input_files({'name':'test.png','mimeType':'image/png','buffer':PNG})
        await expect(page.locator('main').get_by_role('alert')).to_contain_text('TEST — image refusée')
        assert uploads == ['POST']
        await expect(page.locator('main img').first).to_have_attribute('src',USER['avatar_url'])
        successful = True
        await picker.set_input_files({'name':'test.png','mimeType':'image/png','buffer':PNG})
        await expect(page.get_by_text('Votre photo a été mise à jour.',exact=True)).to_be_visible()
        await expect(page.locator('main img').first).to_have_attribute('src',PHOTO)
        await page.goto(BASE,wait_until='networkidle')
        await expect(page.locator('header .radar-account-ring img')).to_have_attribute('src',PHOTO)
        await page.goto(BASE + '/settings',wait_until='networkidle')
        await page.get_by_role('button',name='Retirer la photo personnalisée',exact=True).click()
        await expect(page.locator('main img').first).to_have_attribute('src',USER['avatar_url'])
        assert uploads == ['POST','POST','DELETE']
        print('Settings: successful upload/removal, local type validation and failed upload preserve the original photo OK',flush=True)
        await context.close()
        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
