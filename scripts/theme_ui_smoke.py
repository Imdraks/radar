"""Theme persistence, system changes, portals and legacy surfaces on local fixtures."""
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright, expect

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.core.subscription import Plan, PLAN_CONFIGS, NAV_SECTIONS, get_plan_features

BASE = os.environ.get('RADAR_UI_BASE_URL', 'http://127.0.0.1:3000')
if urlparse(BASE).hostname not in {'localhost', '127.0.0.1'}:
    raise RuntimeError('Theme fixtures may only target a local instance')


async def fixture(route):
    path = urlparse(route.request.url).path
    features = get_plan_features(Plan.BUSINESS)
    if path.endswith('/auth/me'):
        data = {'id': 1, 'email': 'theme@radar.invalid', 'full_name': 'TEST Theme',
                'role': 'admin', 'is_superuser': True, 'is_active': True, 'is_whitelisted': True}
    elif path.endswith('/subscription/current'):
        data = {'workspace_id': 1, 'workspace_name': 'TEST Theme Workspace', 'plan': 'business',
                'plan_display_name': 'Radar Business', 'enabled_packs': [], 'addons': [],
                'max_seats': 3, 'current_seats': 1, 'available_features': [f.value for f in features]}
    elif path.endswith('/subscription/navigation'):
        data = {'sections': {section: [{'label': i.label, 'path': i.path, 'icon': i.icon,
                'available': True, 'locked': False, 'admin_only': i.admin_only, 'context_links': []}
                for i in items if not i.feature or i.feature in features]
                for section, items in NAV_SECTIONS.items()}}
    elif path.endswith('/subscription/plans'):
        data = [{**vars(c), 'included_packs': [v.value for v in c.included_packs], 'included_addons': [],
                 'available_features': [f.value for f in get_plan_features(Plan(c.name))],
                 'is_current': False, 'is_recommended': False} for c in PLAN_CONFIGS.values()]
    elif path.endswith('/agency/projects'):
        data = [{'id': 1, 'name': 'TEST Theme Project', 'status': 'active', 'client_id': 1,
                 'client_name': 'TEST client', 'is_urgent': False, 'progress_percent': 0,
                 'deliverables_count': 0, 'deliverables_approved': 0}]
    else:
        data = []
    await route.fulfill(status=200, content_type='application/json', body=json.dumps(data))


async def theme(page, label, expected):
    await page.get_by_role('button', name='Changer le thème', exact=True).first.click()
    item = page.get_by_role('menuitemradio', name=label, exact=True)
    await item.click()
    await expect(page.locator('html')).to_have_class(re.compile(r'\b' + expected + r'\b'))


async def contrast(locator, minimum=4.5):
    result = await locator.evaluate('''element => {
      const rgb = value => (value.match(/[\\d.]+/g) || []).map(Number);
      const luminance = values => values.slice(0, 3).map(v => {
        v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
      }).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
      const foreground = rgb(getComputedStyle(element).color);
      let background = [255, 255, 255];
      let node = element;
      while (node) {
        const color = rgb(getComputedStyle(node).backgroundColor);
        if (color.length === 3 || color[3] === 1) { background = color; break; }
        node = node.parentElement;
      }
      const fg = luminance(foreground), bg = luminance(background);
      return { ratio: (Math.max(fg, bg) + .05) / (Math.min(fg, bg) + .05), foreground, background };
    }''')
    assert result['ratio'] >= minimum, result


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'],
                                         executable_path=os.environ.get('RADAR_BROWSER_PATH'))
        for width in [1440, 390]:
            context = await browser.new_context(viewport={'width': width, 'height': 1000},
                                                color_scheme='dark', locale='fr-FR')
            await context.add_init_script('''
              localStorage.setItem('access_token', 'theme-test-only');
              localStorage.setItem('current_workspace_id', '1');
              localStorage.setItem('opportunities-radar-welcome-shown-v2', 'true');
              if (!localStorage.getItem('theme')) localStorage.setItem('theme', 'dark');
              localStorage.setItem('cookie-consent', JSON.stringify({version:'2026-11-13',
                chosenAt:new Date().toISOString(), analytics:'denied'}));
            ''')
            await context.route('**/api/**', fixture)
            page = await context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.goto(BASE + '/settings/subscription', wait_until='networkidle')
            await page.get_by_role('heading', name='Abonnement', exact=True).wait_for()
            await expect(page.locator('html')).to_have_class(re.compile(r'\bdark\b'))
            await contrast(page.get_by_role('heading', name='Radar Business', exact=True))
            await contrast(page.get_by_role('button', name='Préférences cookies', exact=True))
            await page.get_by_role('button', name='Changer le thème').click()
            await contrast(page.get_by_role('menuitemradio', name='Clair', exact=True))
            await page.keyboard.press('Escape')
            await page.goto(BASE + '/projects', wait_until='networkidle')
            title = page.get_by_role('heading', name='TEST Theme Project', exact=True)
            await title.wait_for()
            await contrast(title)
            card = title.locator('..')
            # Historical bg-white cards must follow the theme too.
            assert await card.evaluate('e => getComputedStyle(e).backgroundColor') != 'rgb(255, 255, 255)'
            await contrast(page.get_by_role('button', name='Nouveau projet', exact=True))
            await page.get_by_role('button', name='Nouveau projet', exact=True).click()
            await contrast(page.get_by_role('heading', name='Nouveau projet', exact=True))
            field = page.get_by_placeholder('Ex: Campagne Summer 2025')
            await field.fill('TEST retained field')
            assert await field.evaluate('e => getComputedStyle(e).backgroundColor') != 'rgb(255, 255, 255)'
            await contrast(field)
            await page.get_by_role('button', name='Annuler', exact=True).click()
            await theme(page, 'Clair', 'light')
            await contrast(title)
            await page.reload(wait_until='networkidle')
            await page.get_by_role('heading', name='TEST Theme Project', exact=True).wait_for()
            await expect(page.locator('html')).to_have_class(re.compile(r'\blight\b'))
            await theme(page, 'Système', 'dark')
            await page.emulate_media(color_scheme='light')
            await expect(page.locator('html')).to_have_class(re.compile(r'\blight\b'))
            await page.emulate_media(color_scheme='dark')
            await expect(page.locator('html')).to_have_class(re.compile(r'\bdark\b'))
            await page.get_by_role('link', name='Documentation Radar', exact=True).click()
            await page.wait_for_url('**/doc')
            await expect(page.locator('html')).to_have_class(re.compile(r'\blight\b'))
            assert await page.evaluate('localStorage.getItem("theme")') == 'system'
            await page.go_back(wait_until='networkidle')
            await title.wait_for()
            await expect(page.locator('html')).to_have_class(re.compile(r'\bdark\b'))
            await page.screenshot(path=f'/tmp/radar-theme-dark-{width}.png', full_page=True)
            await page.goto(BASE + '/admin/privacy-requests', wait_until='networkidle')
            await page.get_by_role('heading', name='Demandes de droits et de réversibilité', exact=True).wait_for()
            await theme(page, 'Clair', 'light')
            await page.reload(wait_until='networkidle')
            await expect(page.locator('html')).to_have_class(re.compile(r'\blight\b'))
            await theme(page, 'Sombre', 'dark')
            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not errors, errors
            print(f'{width}px: light/dark/system, persistence, public return, portal, modal contrasts and admin OK', flush=True)
            await context.close()
        await browser.close()


asyncio.run(main())
