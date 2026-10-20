"""Browser audit against an explicitly started local test instance; no API mocks.
RADAR_TEST_ACCOUNT_FILE must contain credentials for a disposable test account.
"""
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

BASE = os.environ.get('RADAR_UI_BASE_URL', 'http://127.0.0.1:3100')
if urlparse(BASE).hostname not in {'localhost', '127.0.0.1'}:
    raise RuntimeError('This test runner only accepts a local instance')
PAGES = ['/', '/pricing', '/contact', '/terms', '/privacy', '/legal', '/today',
         '/projects', '/production', '/agency-calendar', '/assets', '/events',
         '/discovery', '/comparison', '/shortlist', '/clients', '/pipeline',
         '/devis', '/factures', '/transactions', '/leads', '/leads/calendar',
         '/leads/kanban', '/dossiers', '/briefs', '/profiles', '/scoring',
         '/deadlines', '/analytics', '/intelligence', '/map', '/inbox',
         '/settings', '/workspace/settings', '/settings/subscription',
         '/workspaces', '/users', '/sources', '/source-health', '/predictions',
         '/competitive', '/dashboard', '/cockpit', '/artists', '/artist',
         '/spotify-search', '/quotes', '/invoices', '/admin', '/admin/members',
         '/admin/activity', '/admin/subscription-requests']

async def main():
    account = json.loads(Path(os.environ['RADAR_TEST_ACCOUNT_FILE']).read_text())
    results = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(viewport={'width':1440, 'height':1000}, locale='fr-FR')
        page = await context.new_page()
        await context.route('https://www.googletagmanager.com/**', lambda route: route.abort())
        await page.goto(BASE+'/login', wait_until='domcontentloaded')
        await page.get_by_role('button', name='Tout refuser', exact=True).click()
        await page.locator('input[type=email]').fill(account['email'])
        await page.locator('input[type=password]').fill(account['password'])
        await page.get_by_role('button', name='Se connecter', exact=True).click()
        await page.wait_for_url(lambda url: '/login' not in urlparse(url).path, timeout=30000)
        paths = os.environ.get('RADAR_CHECK_PATHS', '').split(',') if os.environ.get('RADAR_CHECK_PATHS') else PAGES
        redirects = {'/dashboard':'/today','/cockpit':'/today','/artists':'/discovery','/artist':'/discovery','/spotify-search':'/discovery','/quotes':'/devis','/invoices':'/factures'}
        for path in paths:
            errors, failures = [], []
            def page_error(error): errors.append(str(error))
            def response_error(response):
                if '/api/' in response.url and response.status >= 400:
                    failures.append({'status':response.status, 'path':urlparse(response.url).path})
            page.on('pageerror', page_error)
            page.on('response', response_error)
            try:
                response = await page.goto(BASE+path, wait_until='domcontentloaded', timeout=45000)
                canonical = redirects.get(path, '/today' if path.startswith('/admin') or path in ['/workspaces','/users','/sources','/source-health'] else path)
                await page.wait_for_url(lambda url: urlparse(url).path == canonical, timeout=15000, wait_until='domcontentloaded')
                try:
                    await page.wait_for_load_state('networkidle', timeout=5000)
                except Exception:
                    pass
                await page.wait_for_timeout(500)
                body = (await page.locator('body').inner_text())[:2000]
                result = {'path':path,'status':response.status, 'final':urlparse(page.url).path,
                          'errors':errors,'api_failures':failures,
                          'overflow':await page.evaluate('document.documentElement.scrollWidth > innerWidth+1'),
                          'body':body}
            except Exception as error:
                result = {'path':path,'exception':str(error), 'errors':errors, 'api_failures':failures}
            page.remove_listener('pageerror',page_error)
            page.remove_listener('response',response_error)
            results.append(result)
            print(json.dumps({k:v for k,v in result.items() if k!='body'}), flush=True)
        for width in [768,390]:
            await page.set_viewport_size({'width':width,'height':900})
            for path in ['/today','/projects','/events','/discovery','/settings/subscription']:
                await page.goto(BASE+path)
                await page.wait_for_timeout(500)
                results.append({'path':path,'width':width,'overflow':await page.evaluate('document.documentElement.scrollWidth > innerWidth+1')})
            await page.screenshot(path=f'/tmp/radar-local-{width}.png',full_page=True)
        await browser.close()
    Path('/tmp/radar-site-results.json').write_text(json.dumps(results,indent=2))

if __name__ == '__main__':
    asyncio.run(main())
