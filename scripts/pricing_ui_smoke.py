"""Local pricing UX: real catalog definitions, isolated browser API fixtures."""
import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright, expect

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.core.subscription import PLAN_CONFIGS, Plan, get_plan_features

BASE = os.environ.get('RADAR_UI_BASE_URL', 'http://127.0.0.1:3000')
if urlparse(BASE).hostname not in {'localhost', '127.0.0.1'}:
    raise RuntimeError('Pricing fixtures may only target a local instance')


def catalog():
    return [{**vars(config), 'included_packs': [p.value for p in config.included_packs],
             'included_addons': [], 'is_current': False, 'is_recommended': False,
             'available_features': sorted(f.value for f in get_plan_features(plan))}
            for plan, config in PLAN_CONFIGS.items()]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'],
                                         executable_path=os.environ.get('RADAR_BROWSER_PATH'))
        for width in [1440, 1024, 768, 390, 320]:
            context = await browser.new_context(viewport={'width': width, 'height': 1000}, locale='fr-FR')
            await context.add_init_script('''localStorage.setItem('cookie-consent',JSON.stringify({
              version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}));''')
            async def api(route):
                await route.fulfill(status=200, content_type='application/json', body=json.dumps(catalog()))
            await context.route('**/api/v1/subscription/plans*', api)
            page = await context.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.goto(BASE + '/pricing', wait_until='networkidle')
            await expect(page.get_by_role('heading', name='Radar Premium', exact=True)).to_be_visible()
            for plan in Plan:
                article = page.get_by_role('article', name=PLAN_CONFIGS[plan].display_name, exact=True)
                await expect(article.get_by_role('link', name='Parlons de ' + plan.value.capitalize(), exact=True)).to_have_attribute('href', '/contact?plan=' + plan.value)
                assert str(PLAN_CONFIGS[plan].max_seats) in await article.inner_text()
            table = page.get_by_role('table')
            for label, feature in [('Projets', 'projects'), ('Gestion événementielle', 'events'), ('Devis', 'quotes'), ('Factures & suivi des paiements', 'invoices')]:
                row = table.get_by_role('row').filter(has=page.get_by_role('rowheader', name=label, exact=False))
                cells = row.get_by_role('cell')
                for index, plan in enumerate(Plan):
                    expected = 'Inclus' if feature in {f.value for f in get_plan_features(plan)} else 'Non inclus'
                    assert (await cells.nth(index).inner_text()).strip() == expected
            body = await page.locator('main').inner_text()
            assert '€' not in body and 'Le plus populaire' not in body
            assert 'Connexion bancaire' not in body
            if not await page.evaluate('document.documentElement.scrollWidth <= innerWidth'):
                print(await page.evaluate('''() => ({width:innerWidth,scroll:document.documentElement.scrollWidth,elements:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right > innerWidth).map(e=>[e.tagName,e.className,e.getBoundingClientRect().x,e.getBoundingClientRect().width]).slice(0,20)})'''), flush=True)
                await page.screenshot(path='/tmp/pricing-overflow.png',full_page=True)
                raise AssertionError(width)
            await page.get_by_role('link', name='Voir le comparatif détaillé', exact=True).click()
            await page.wait_for_url('**/pricing#comparatif')
            summary = page.locator('summary').filter(has_text='Radar Addons est-il un quatrième abonnement ?')
            await summary.focus()
            await page.keyboard.press('Enter')
            await expect(page.get_by_text('Non. Radar Addons complète', exact=False)).to_be_visible()
            if width in [1440, 390]:
                await page.goto(BASE + '/pricing', wait_until='networkidle')
                await page.screenshot(path=f'/tmp/radar-pricing-{width}.png', full_page=True)
            if width == 1440:
                await page.get_by_role('link', name='Parlons de Premium', exact=True).click()
                await page.wait_for_url('**/contact?plan=premium')
                await page.get_by_label('Nom complet', exact=True).fill('TEST Tarifs')
                await page.get_by_role('button', name='Continuer', exact=True).click()
                await page.get_by_label('Email professionnel', exact=True).fill('test@example.com')
                await page.get_by_role('button', name='Continuer', exact=True).click()
                await page.get_by_role('button', name='Continuer', exact=True).click()
                await expect(page.get_by_label('Offre qui vous intéresse, facultatif', exact=True)).to_have_value('premium')
            assert not errors, errors
            print(f'{width}px: backend inclusions, limits, contact choice, keyboard FAQ, no overflow OK', flush=True)
            await context.close()
        context = await browser.new_context()
        await context.add_init_script('''localStorage.setItem('cookie-consent',JSON.stringify({version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}));''')
        mode = 'failure'
        async def changing_api(route):
            if mode == 'failure':
                await route.fulfill(status=503, body='unavailable')
            elif mode == 'empty':
                await route.fulfill(status=200, content_type='application/json', body='[]')
            else:
                data = catalog()
                # Deliberately change server rights/limits: the UI must follow.
                data[2]['available_features'].remove('quotes')
                data[2]['max_seats'] = 42
                await route.fulfill(status=200, content_type='application/json', body=json.dumps(data))
        await context.route('**/api/v1/subscription/plans*', changing_api)
        page = await context.new_page()
        await page.goto(BASE + '/pricing', wait_until='networkidle')
        await expect(page.locator('main').get_by_role('alert')).to_contain_text('momentanément indisponibles')
        assert await page.get_by_role('article').count() == 0
        mode = 'empty'
        await page.get_by_role('button', name='Réessayer', exact=True).click()
        await expect(page.locator('main').get_by_role('alert')).to_contain_text('momentanément indisponibles')
        mode = 'success'
        await page.get_by_role('button', name='Réessayer', exact=True).click()
        await expect(page.get_by_role('article', name='Radar Business', exact=True)).to_contain_text('42 membres')
        row = page.get_by_role('table').get_by_role('row').filter(has=page.get_by_role('rowheader', name='Devis', exact=False))
        await expect(row.get_by_role('cell').nth(2)).to_have_text('Non inclus')
        assert await page.locator('main').get_by_role('alert').count() == 0
        print('503/empty catalog/retry and changed backend rights/limits: no fabricated fallback OK', flush=True)
        await context.close()
        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
