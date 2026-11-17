"""Password UI regression with explicit simulated APIs; no real e-mail is sent."""
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
BASE = os.environ.get('RADAR_UI_BASE_URL', 'http://127.0.0.1:3000')
if urlparse(BASE).hostname not in {'localhost', '127.0.0.1'}:
    raise RuntimeError('Password fixtures may only target localhost')
ARTIFACTS = Path(os.environ.get('RADAR_PASSWORD_ARTIFACT_DIR', '/tmp/radar-password-smoke'))
ARTIFACTS.mkdir(parents=True, exist_ok=True)
POLICY = {'min_length': 12, 'max_bytes': 72, 'uppercase': True, 'lowercase': True, 'digit': True, 'special': True, 'reset_expiry_minutes': 15}
USER = {'id': 1, 'email': 'password-ui@example.com', 'full_name': 'TEST Password', 'role': 'admin', 'is_superuser': False, 'is_active': True, 'is_whitelisted': True, 'created_at': '2026-11-17T00:00:00'}
TOKEN = 'explicit-reset-fixture-' + 'x'*32
OLD, NEW = 'Old-Password-42!', 'New-Password-57!'


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=os.environ.get('RADAR_BROWSER_PATH'), args=['--no-sandbox'])
        for width, height in [(1440, 1000), (390, 844)]:
            context = await browser.new_context(viewport={'width': width, 'height': height}, locale='fr-FR')
            await context.add_init_script("localStorage.setItem('opportunities-radar-welcome-shown-v2','true');localStorage.setItem('current_workspace_id','1')")
            calls, errors = [], []
            has_password = True
            async def api(route):
                path = urlparse(route.request.url).path
                body = route.request.post_data_json if route.request.method == 'POST' else None
                calls.append((path, body))
                status = 200
                if path.endswith('/password-policy'): data = POLICY
                elif path.endswith('/password/status'): data = {'has_password': has_password}
                elif path.endswith('/forgot-password'):
                    if body['email'] == 'off@example.com': status, data = 503, {'detail': 'TEST — envoi indisponible'}
                    else: status, data = 202, {'accepted': True, 'message': 'Si un compte éligible correspond à cette adresse, une demande sera traitée.'}
                elif path.endswith('/reset-password'):
                    if body['token'] == TOKEN: status, data = 400, {'detail': 'Ce lien est invalide, a expiré ou a déjà été utilisé.'}
                    else: data = {'message': 'Mot de passe réinitialisé. Reconnectez-vous.'}
                elif path.endswith('/mfa/reauth/start'):
                    if body['password'] != OLD: status, data = 401, {'detail': 'Mot de passe Radar incorrect.'}
                    else: data = {'requires_2fa': True, 'challenge_token': TOKEN, 'methods': ['totp', 'recovery'], 'destinations': {}}
                elif path.endswith('/mfa/reauth/complete'):
                    if body['code'] != '123456': status, data = 401, {'detail': 'Code invalide ou déjà utilisé.'}
                    else: data = {'management_token': TOKEN + '-verified'}
                elif path.endswith('/password/change'): data = {'access_token': 'explicit-new-access', 'refresh_token': 'explicit-new-refresh', 'message': 'Mot de passe modifié. Les autres sessions ont été déconnectées.'}
                elif path.endswith('/auth/setup-check'): data = {'needs_setup': False}
                elif path.endswith('/auth/sso/providers'): data = {'providers': []}
                elif path.endswith('/auth/me'): data = USER
                elif path.endswith('/workspaces'): data = {'items': [{'id': 1, 'name': 'TEST workspace', 'members_count': 1}]}
                elif path.endswith('/subscription/current'): data = {'workspace_id': 1, 'plan': 'core', 'plan_display_name': 'Radar Core', 'available_features': ['cockpit', 'projects'], 'max_seats': 3, 'current_seats': 1}
                elif path.endswith('/subscription/navigation'): data = {'sections': {'Administration': [{'label': 'Paramètres', 'path': '/settings', 'icon': 'settings', 'context_links': []}]}}
                else: data = []
                await route.fulfill(status=status, content_type='application/json', body=json.dumps(data))
            await context.route('**/api/**', api)
            await context.route('https://www.googletagmanager.com/**', lambda route: route.abort())
            page = await context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.goto(BASE + '/forgot-password', wait_until='networkidle')
            reject = page.get_by_role('button', name='Tout refuser', exact=True)
            if await reject.is_visible(): await reject.click()
            await page.get_by_label('Adresse e-mail du compte Radar', exact=True).fill('off@example.com')
            await page.get_by_role('button', name='Demander un lien par e-mail', exact=True).click()
            await page.get_by_role('alert').filter(has_text='TEST — envoi indisponible').wait_for()
            await page.get_by_label('Adresse e-mail du compte Radar', exact=True).fill(USER['email'])
            await page.get_by_role('button', name='Demander un lien par e-mail', exact=True).click()
            await page.get_by_role('status').filter(has_text='Si un compte éligible').wait_for()
            await page.goto(BASE + '/reset-password#token=' + TOKEN, wait_until='networkidle')
            assert await page.evaluate('location.hash') == ''
            await page.get_by_label('Nouveau mot de passe', exact=True).fill('weak')
            await page.get_by_label('Confirmer le nouveau mot de passe', exact=True).fill('weak')
            submit = page.get_by_role('button', name='Enregistrer le nouveau mot de passe', exact=True)
            assert await submit.is_disabled()
            await page.get_by_label('Nouveau mot de passe', exact=True).fill(NEW)
            await page.get_by_label('Confirmer le nouveau mot de passe', exact=True).fill('different')
            assert await submit.is_disabled()
            await page.get_by_label('Confirmer le nouveau mot de passe', exact=True).fill(NEW)
            await submit.click()
            await page.get_by_role('alert').filter(has_text='a expiré').wait_for()
            await page.goto(BASE + '/reset-password#token=' + TOKEN + '-new', wait_until='networkidle')
            await page.get_by_label('Nouveau mot de passe', exact=True).fill(NEW)
            await page.get_by_label('Confirmer le nouveau mot de passe', exact=True).fill(NEW)
            await submit.click()
            await page.get_by_role('status').filter(has_text='Mot de passe réinitialisé').wait_for()
            assert TOKEN not in await page.evaluate('JSON.stringify(localStorage)')
            await page.evaluate("localStorage.setItem('access_token','explicit-access');localStorage.setItem('refresh_token','explicit-refresh')")
            await page.goto(BASE + '/settings', wait_until='networkidle')
            await page.get_by_label('Ancien mot de passe Radar', exact=True).fill('wrong')
            await page.get_by_label('Nouveau mot de passe', exact=True).fill(NEW)
            await page.get_by_label('Confirmer le nouveau mot de passe', exact=True).fill(NEW)
            await page.get_by_role('button', name='Continuer pour changer le mot de passe', exact=True).click()
            await page.get_by_role('alert').filter(has_text='Mot de passe Radar incorrect.').wait_for()
            assert not [path for path, _ in calls if path.endswith('/auth/refresh') or path.endswith('/password/change')]
            await page.get_by_label('Ancien mot de passe Radar', exact=True).fill(OLD)
            await page.get_by_role('button', name='Continuer pour changer le mot de passe', exact=True).click()
            await page.get_by_label('Code à 6 chiffres', exact=True).fill('000000')
            await page.get_by_role('button', name='Vérifier', exact=True).click()
            await page.get_by_role('alert').filter(has_text='Code invalide ou déjà utilisé.').wait_for()
            assert not [path for path, _ in calls if path.endswith('/password/change')]
            await page.get_by_label('Code à 6 chiffres', exact=True).fill('123456')
            await page.get_by_role('button', name='Vérifier', exact=True).click()
            await page.get_by_role('status').filter(has_text='Mot de passe modifié.').wait_for()
            changes = [body for path, body in calls if path.endswith('/password/change')]
            assert len(changes) == 1 and changes[0] == {'current_password': OLD, 'new_password': NEW, 'confirm_password': NEW, 'management_token': TOKEN + '-verified'}
            storage = await page.evaluate('JSON.stringify(localStorage)')
            assert OLD not in storage and NEW not in storage and TOKEN not in storage
            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            await page.screenshot(path=str(ARTIFACTS / f'password-settings-{width}.png'), full_page=True)
            has_password = False
            await page.reload(wait_until='networkidle')
            await page.get_by_role('link', name='Recevoir un lien par e-mail pour en définir un', exact=True).wait_for()
            assert not errors, errors
            print(f'{width}px: recovery, expiry error, criteria, confirmation, old password, required MFA before change, SSO password setup, no persistent secrets/JS errors/overflow OK', flush=True)
            await context.close()
        await browser.close()


asyncio.run(main())
