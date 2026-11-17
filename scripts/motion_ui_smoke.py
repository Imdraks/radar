"""Motion/accessibility regression on a local build with explicit API fixtures."""
import asyncio
import json
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright, expect

BASE = os.environ.get('RADAR_UI_BASE_URL', 'http://127.0.0.1:3000')
if urlparse(BASE).hostname not in {'localhost', '127.0.0.1'}:
    raise RuntimeError('Motion fixtures may only target a local instance')


async def fixture(route):
    path = urlparse(route.request.url).path
    if path.endswith('/auth/setup-check'):
        data = {'needs_setup': False, 'user_count': 1}
    elif path.endswith('/auth/sso/providers'):
        data = {'providers': []}
    elif path.endswith('/auth/login'):
        await route.fulfill(status=401, content_type='application/json',
                            body=json.dumps({'detail': 'TEST — connexion refusée'}))
        return
    else:
        data = []
    await route.fulfill(status=200, content_type='application/json', body=json.dumps(data))


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'],
                                         executable_path=os.environ.get('RADAR_BROWSER_PATH'))
        for width, reduced in [(1440, 'no-preference'), (390, 'no-preference'),
                               (1440, 'reduce'), (390, 'reduce')]:
            context = await browser.new_context(viewport={'width': width, 'height': 900},
                                                reduced_motion=reduced, locale='fr-FR')
            await context.route('**/api/**', fixture)
            page = await context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.goto(BASE, wait_until='networkidle')
            refuse = page.get_by_role('button', name='Tout refuser', exact=True)
            # A fresh context has no consent. Wait for hydration before deciding
            # whether the cookie panel needs dismissing, especially on mobile.
            await expect(refuse).to_be_visible()
            await refuse.click()
            field = page.locator('.radar-orbit-panel .radar-field')
            await expect(field).to_have_css('animation-name',
                                          'none' if reduced == 'reduce' else 'radar-signal-sweep')
            await page.locator('#workflow').scroll_into_view_if_needed()
            assert await page.locator('#workflow').is_visible()
            if reduced == 'reduce':
                assert await page.evaluate('getComputedStyle(document.documentElement).scrollBehavior') == 'auto'
                assert await page.evaluate('document.getAnimations().filter(a => a.playState === "running").length') == 0
            if width < 1024:
                trigger = page.get_by_role('button', name='Ouvrir le menu du site')
                await trigger.click()
                dialog = page.get_by_role('dialog')
                await expect(dialog).to_be_visible()
                await page.keyboard.press('Escape')
                await expect(dialog).to_be_hidden()
                await expect(trigger).to_be_focused()
                await trigger.click()
                await dialog.get_by_role('link', name='Abonnements', exact=True).click()
            else:
                await page.get_by_role('navigation', name='Navigation du site', exact=True).get_by_role('link', name='Abonnements', exact=True).click()
            await page.wait_for_url('**/pricing')
            await expect(page.locator('main')).to_be_visible()
            await page.goto(BASE + '/login', wait_until='networkidle')
            email = page.get_by_label('Email', exact=True)
            password = page.get_by_label('Mot de passe', exact=True)
            await email.fill('motion@radar.invalid')
            await password.fill('TEST-invalid-password')
            await email.evaluate('(element) => element.dataset.motionProbe = "preserved"')
            # Changing accessibility settings must cancel motion, not remount forms.
            await page.emulate_media(reduced_motion='reduce')
            await expect(page.locator('.radar-auth-card')).to_have_css('animation-name', 'none')
            await expect(email).to_have_attribute('data-motion-probe', 'preserved')
            await expect(email).to_have_value('motion@radar.invalid')
            await expect(password).to_have_value('TEST-invalid-password')
            await page.get_by_role('button', name='Se connecter', exact=True).click()
            await page.get_by_text('TEST — connexion refusée', exact=True).wait_for()
            await expect(email).to_have_value('motion@radar.invalid')
            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not errors, errors
            print(f'{width}px / {reduced}: motion, keyboard, form preservation OK', flush=True)
            await context.close()
        context = await browser.new_context(java_script_enabled=False)
        page = await context.new_page()
        await page.goto(BASE)
        await expect(page.get_by_role('heading', name='Gardez le cap.', exact=False)).to_be_visible()
        await expect(page.locator('#workflow')).to_be_visible()
        print('No JavaScript: public content remains visible', flush=True)
        await context.close()
        await browser.close()


asyncio.run(main())
