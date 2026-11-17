"""Contact slides on local builds only; delivery responses are explicit fixtures."""
import asyncio
import json
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright, expect

BASE = os.environ.get('RADAR_UI_BASE_URL', 'http://127.0.0.1:3000')
if urlparse(BASE).hostname not in {'localhost', '127.0.0.1'}:
    raise RuntimeError('Contact fixtures must target a local instance')


async def next_step(page):
    await page.get_by_role('button', name='Continuer', exact=True).click()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'],
                                         executable_path=os.environ.get('RADAR_BROWSER_PATH'))
        for width in [1440, 390]:
            context = await browser.new_context(viewport={'width': width, 'height': 950},
                                                locale='fr-FR', reduced_motion='reduce' if width == 390 else 'no-preference')
            await context.add_init_script('''localStorage.setItem('cookie-consent', JSON.stringify({
              version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}));''')
            posts = []
            async def api(route):
                if urlparse(route.request.url).path == '/api/v1/contact':
                    posts.append(route.request.post_data_json)
                    await asyncio.sleep(.25)
                    status, data = (503, {'detail': 'TEST delivery unavailable'}) if len(posts) == 1 else (200, {}) if len(posts) == 2 else (200, {'status': 'ok'})
                    await route.fulfill(status=status, content_type='application/json', body=json.dumps(data))
                else:
                    await route.fulfill(status=200, content_type='application/json', body='[]')
            await context.route('**/api/**', api)
            page = await context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.goto(BASE + '/contact?plan=premium', wait_until='networkidle')
            progress = page.get_by_role('progressbar', name='Progression du formulaire')
            name = page.get_by_label('Nom complet', exact=True)
            await expect(name).to_be_visible()
            await next_step(page)
            await expect(progress).to_have_attribute('aria-valuenow', '1')
            await name.fill('  ')
            await next_step(page)
            await expect(page.locator('main').get_by_role('alert')).to_be_visible()
            await name.fill('TEST Camille Martin')
            await name.press('Enter')
            email = page.get_by_label('Email professionnel', exact=True)
            await expect(email).to_be_focused()
            await email.fill('invalid-email')
            await next_step(page)
            await expect(progress).to_have_attribute('aria-valuenow', '2')
            assert not posts
            await email.fill('contact@example.com')
            await page.get_by_role('button', name='Précédent', exact=True).click()
            await expect(name).to_have_value('TEST Camille Martin')
            await next_step(page)
            await expect(email).to_have_value('contact@example.com')
            await next_step(page)
            await page.get_by_label('Société', exact=False).fill('TEST Atelier')
            await page.get_by_label('Téléphone', exact=False).fill('+33 6 00 00 00 00')
            await next_step(page)
            plan = page.get_by_label('Offre qui vous intéresse, facultatif', exact=True)
            await expect(plan).to_have_value('premium')
            assert await page.get_by_role('option', name='Radar Premium', exact=True).count() == 1
            assert await page.get_by_role('option', name='Radar Talents', exact=True).count() == 0
            await next_step(page)
            message = page.get_by_label('Votre message', exact=True)
            await message.fill('TEST — Un projet de production pour notre agence.\nAvec plusieurs lignes.')
            await next_step(page)
            await expect(progress).to_have_attribute('aria-valuenow', '6')
            assert not posts
            await page.get_by_role('button', name='Modifier : Nom', exact=True).click()
            await name.fill('TEST Camille Modifiée')
            await page.get_by_role('button', name='Valider la modification', exact=True).click()
            await expect(progress).to_have_attribute('aria-valuenow', '6')
            await expect(page.get_by_text('TEST Camille Modifiée', exact=True)).to_be_visible()
            if width == 390:
                await expect(page.locator('.radar-contact-step')).to_have_css('animation-name', 'none')
            await page.screenshot(path=f'/tmp/radar-contact-review-{width}.png', full_page=True)
            send = page.get_by_role('button', name='Envoyer le message', exact=True)
            await send.dblclick()
            await expect(page.locator('main').get_by_role('alert')).to_be_visible()
            assert len(posts) == 1
            await expect(page.get_by_text('TEST Camille Modifiée', exact=True)).to_be_visible()
            await send.click()
            await expect(page.locator('main').get_by_role('alert')).to_be_visible()
            await expect(send).to_be_enabled()
            assert len(posts) == 2
            assert await page.get_by_text('Message envoyé.', exact=False).count() == 0
            await send.click()
            await page.get_by_role('heading', name='Message envoyé.', exact=False).wait_for()
            assert len(posts) == 3
            assert posts[-1] == {'name': 'TEST Camille Modifiée', 'email': 'contact@example.com',
                'company': 'TEST Atelier', 'phone': '+33 6 00 00 00 00', 'plan': 'premium',
                'message': 'TEST — Un projet de production pour notre agence.\nAvec plusieurs lignes.',
                'privacy_notice_version': '2026-11-13'}
            assert await page.locator('a button').count() == 0
            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not errors, errors
            print(f'{width}px: validation, keyboard, back/edit, payload, single send, errors and confirmed success OK', flush=True)
            # Optional steps remain optional; MCP context survives all slides.
            await page.goto(BASE + '/contact?offer=mcp', wait_until='networkidle')
            await name.fill('TEST MCP')
            await next_step(page)
            await email.fill('contact@example.com')
            await next_step(page)
            await next_step(page)
            await expect(plan).to_have_value('custom')
            await next_step(page)
            assert 'ChatGPT / MCP' in await message.input_value()
            await next_step(page)
            assert await page.get_by_text('Non renseignés', exact=True).count() == 1
            await page.goto(BASE + '/contact?plan=unknown', wait_until='networkidle')
            await expect(name).to_be_visible()
            await page.screenshot(path=f'/tmp/radar-contact-start-{width}.png', full_page=True)
            await context.close()
        context = await browser.new_context(java_script_enabled=False)
        page = await context.new_page()
        await page.goto(BASE + '/contact')
        await expect(page.get_by_role('button', name='Continuer', exact=True)).to_be_disabled()
        await expect(page.locator('noscript p')).to_be_visible()
        await expect(page.locator('noscript p')).to_contain_text('Ce formulaire par étapes nécessite JavaScript.')
        assert await page.locator('noscript a[href="/legal"]').count() == 1
        await expect(page.locator('form')).to_have_attribute('method', 'post')
        await context.close()
        print('No JavaScript: clear fallback, no implicit submission of personal data', flush=True)
        await browser.close()


asyncio.run(main())
