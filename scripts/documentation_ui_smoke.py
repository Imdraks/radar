"""Public documentation QA. API replies are explicit local fixtures, not real data."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlparse
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('RADAR_UI_BASE_URL', 'http://127.0.0.1:3000')
if urlparse(BASE).hostname not in {'localhost', '127.0.0.1'}:
    raise RuntimeError('Documentation fixtures may only target a local instance')
ARTIFACTS = Path(os.environ.get('RADAR_DOCS_ARTIFACT_DIR', '/tmp/radar-docs-smoke'))
ARTIFACTS.mkdir(parents=True, exist_ok=True)


async def main():
    module = (ROOT / 'frontend/src/content/documentation.ts').as_uri()
    output = subprocess.run(['node', '--experimental-strip-types', '--input-type=module', '-e',
                             f'import {{ documentation }} from {json.dumps(module)}; console.log(JSON.stringify(documentation));'],
                            capture_output=True, text=True, check=True)
    articles = json.loads(output.stdout)
    slugs = {article['slug'] for article in articles}
    assert len(slugs) == len(articles)
    for article in articles:
        assert len(article['sections']) >= 3, article['slug']
        for link in article['links']:
            assert link['href'].startswith('/'), link
            if link['href'].startswith('/doc/'):
                assert link['href'].split('/')[2] in slugs, link

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'], executable_path=os.environ.get('RADAR_BROWSER_PATH'))
        for width, height in [(1440, 1000), (1024, 900), (768, 1024), (390, 844)]:
            context = await browser.new_context(viewport={'width': width, 'height': height}, locale='fr-FR')
            async def api(route):
                data = {'needs_setup': False} if route.request.url.endswith('/auth/setup-check') else []
                await route.fulfill(status=200, content_type='application/json', body=json.dumps(data))
            await context.route('**/api/**', api)
            await context.route('https://www.googletagmanager.com/**', lambda route: route.abort())
            page = await context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))

            async def visit(path):
                response = await page.goto(BASE + path, wait_until='networkidle')
                assert response.status == 200, (path, response.status)
                reject = page.get_by_role('button', name='Tout refuser', exact=True)
                if await reject.is_visible():
                    await reject.click()
                assert await page.get_by_role('heading', level=1).count() == 1, path
                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (path, width)
                assert await page.locator('a button').count() == 0, path
                assert not errors, (path, errors)

            await visit('/mcp')
            assert await page.locator('link[rel=canonical]').get_attribute('href') == 'https://radarapp.fr/mcp'
            await page.get_by_text('Extension payante', exact=True).wait_for()
            assert await page.get_by_role('link', name='Explorer la documentation', exact=True).get_attribute('href') == '/doc'
            await page.screenshot(path=str(ARTIFACTS / f'mcp-{width}.png'), full_page=True)
            await page.get_by_role('link', name='Demander l’extension', exact=True).click()
            await page.wait_for_url('**/contact?offer=mcp')
            await page.wait_for_function("document.querySelector('#contact-plan')?.value === 'custom'")
            assert 'connecteur ChatGPT / MCP' in await page.locator('#contact-message').input_value()
            assert await page.locator('#contact-email').input_value() == ''

            await visit('/doc')
            if width < 1024:
                await page.get_by_role('button', name='Afficher les guides', exact=True).click()
            search = page.get_by_role('searchbox', name='Rechercher dans les guides', exact=True)
            await search.fill('facturation electronique')
            await page.get_by_role('status').filter(has_text='guide').wait_for()
            nav = page.get_by_role('navigation', name='Sommaire de la documentation', exact=True)
            await nav.get_by_role('link', name='Factures, avoirs et paiements', exact=True).wait_for()
            await search.fill('zzzintrouvablezzz')
            await page.get_by_text('Aucun guide trouvé.', exact=False).wait_for()
            assert await nav.get_by_role('link').count() == 0
            await search.fill('  ARTISTE  ')
            await nav.get_by_role('link', name='Rechercher et enrichir un artiste', exact=True).click()
            await page.wait_for_url('**/doc/discovery')
            await page.get_by_role('heading', name='Rechercher et enrichir un artiste', exact=True).wait_for()
            assert await page.locator('link[rel=canonical]').get_attribute('href') == 'https://radarapp.fr/doc/discovery'
            assert await page.get_by_role('navigation', name='Dans ce guide', exact=True).get_by_role('link').count() >= 3
            await page.screenshot(path=str(ARTIFACTS / f'doc-{width}.png'), full_page=True)
            await visit('/doc/mcp')
            assert 'radar:write' in await page.locator('main').inner_text()
            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')

            if width == 1440:
                for article in articles:
                    await visit('/doc/' + article['slug'])
                    assert await page.get_by_role('heading', name=article['title'], exact=True).count() == 1
                response = await page.goto(BASE + '/doc/guide-inexistant-test', wait_until='networkidle')
                assert response.status == 404, response.status
                await page.get_by_role('heading', name='Ce guide n’existe pas.', exact=True).wait_for()
                sitemap = await context.request.get(BASE + '/sitemap.xml')
                sitemap_text = await sitemap.text()
                for path in ['/mcp', '/doc', *['/doc/' + article['slug'] for article in articles]]:
                    assert f'<loc>https://radarapp.fr{path}</loc>' in sitemap_text, path
            print(f'{width}px: MCP, documentation, search, consent contact, links, no overflow/JS errors OK', flush=True)
            await context.close()
        await browser.close()
    print(f'{len(articles)} guides and public sitemap verified', flush=True)


asyncio.run(main())
