"""MFA browser regression using explicitly simulated APIs; never sends a message."""
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

BASE = os.environ.get('RADAR_UI_BASE_URL', 'http://127.0.0.1:3000')
if urlparse(BASE).hostname not in {'127.0.0.1', 'localhost'}:
    raise RuntimeError('MFA browser fixtures may target only localhost')
ARTIFACTS = Path(os.environ.get('RADAR_MFA_ARTIFACT_DIR', '/tmp/radar-mfa-smoke'))
ARTIFACTS.mkdir(parents=True, exist_ok=True)
USER = {'id': 1, 'email': 'mfa-ui@example.com', 'full_name': 'TEST MFA user', 'role': 'admin', 'is_superuser': False, 'is_active': True, 'is_whitelisted': True, 'created_at': '2026-11-16T00:00:00'}
TOKEN = 'explicit-fixture-challenge-' + 'x' * 32
CODES = ['TEST-ABCD-1234-EFFF', 'TEST-BCDE-2345-FFFF']


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'], executable_path=os.environ.get('RADAR_BROWSER_PATH'))
        for width, height in [(1440, 1000), (390, 844)]:
            context = await browser.new_context(viewport={'width': width, 'height': height}, locale='fr-FR')
            await context.add_init_script("localStorage.setItem('opportunities-radar-welcome-shown-v2','true');localStorage.setItem('current_workspace_id','1')")
            calls = []
            sessions = [{'id': 'current', 'label': 'TEST Chrome', 'created_at': '2026-11-16T12:00:00Z', 'expires_at': '2026-11-23T12:00:00Z', 'is_current': True}, {'id': 'other', 'label': 'TEST Firefox', 'created_at': '2026-11-16T11:00:00Z', 'expires_at': '2026-11-23T11:00:00Z', 'is_current': False}]
            active = ['totp', 'recovery']
            send_failure = True
            async def api(route):
                nonlocal send_failure
                path = urlparse(route.request.url).path
                body = route.request.post_data_json if route.request.method == 'POST' else None
                calls.append((path, body))
                status = 200
                if path.endswith('/auth/setup-check'): data = {'needs_setup': False}
                elif path.endswith('/auth/sso/providers'): data = {'providers': []}
                elif path.endswith('/auth/login'): data = {'requires_2fa': True, 'temp_token': TOKEN, 'methods': ['totp', 'email', 'sms', 'recovery'], 'destinations': {'email': 'm•••@example.com', 'sms': '••••5678'}}
                elif path.endswith('/auth/mfa/send'):
                    if send_failure:
                        status, data, send_failure = 503, {'detail': 'TEST — envoi temporairement indisponible'}, False
                    else: data = {'sent': True, 'destination': 'm•••@example.com', 'retry_after_seconds': 60}
                elif path.endswith('/auth/mfa/complete'):
                    if body['code'] == '000000': status, data = 401, {'detail': 'TEST — code refusé'}
                    else: data = {'access_token': 'explicit-fixture-access', 'refresh_token': 'explicit-fixture-refresh'}
                elif path.endswith('/auth/mfa/trusted/complete'): data = {'trusted': False}
                elif path.endswith('/auth/sessions'): data = {'items': sessions.copy()}
                elif path.endswith('/auth/sessions/revoke-others'):
                    sessions[:] = [row for row in sessions if row['is_current']]
                    data = {'revoked': 1}
                elif path.endswith('/auth/trusted-devices'): data = {'items': []}
                elif path.endswith('/auth/mfa/options'): data = {'methods': ['totp', 'recovery'], 'destinations': {}, 'available': {'totp': True}}
                elif path.endswith('/auth/mfa/status'): data = {'enabled': bool(active), 'methods': active.copy(), 'available': {'totp': True, 'email': True, 'sms': False}, 'destinations': {'email': 'm•••@example.com'}, 'has_backup_codes': bool(active)}
                elif path.endswith('/auth/mfa/reauth/start'):
                    if body.get('password') == 'wrong': status, data = 401, {'detail': 'Mot de passe Radar incorrect.'}
                    else: data = {'requires_2fa': True, 'challenge_token': TOKEN + '-management', 'methods': ['totp', 'recovery'], 'destinations': {}} if active else {'requires_2fa': False, 'management_token': TOKEN + '-verified'}
                elif path.endswith('/auth/mfa/reauth/complete'): data = {'management_token': TOKEN + '-verified'}
                elif path.endswith('/auth/mfa/enroll/start'):
                    data = {'challenge_token': TOKEN + '-enroll', 'method': body['method']}
                    if body['method'] == 'totp':
                        data.update(secret='EXPLICIT-UI-FIXTURE-ONLY', qr_code='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
                    else:
                        data.update(destination='m•••@example.com', sent=True)
                elif path.endswith('/auth/mfa/enroll/complete'):
                    active[:] = list(dict.fromkeys([method for method in active if method != 'recovery'] + [body['method'], 'recovery']))
                    data = {'enabled': True, 'backup_codes': CODES, 'access_token': 'explicit-fixture-updated-access', 'refresh_token': 'explicit-fixture-updated-refresh'}
                elif path.endswith('/auth/me'): data = USER
                elif path.endswith('/workspaces'): data = {'items': [{'id': 1, 'name': 'TEST workspace', 'members_count': 1}]}
                elif path.endswith('/subscription/current'): data = {'workspace_id': 1, 'plan': 'core', 'plan_display_name': 'Radar Core', 'available_features': ['cockpit', 'projects'], 'max_seats': 3, 'current_seats': 1}
                elif path.endswith('/subscription/navigation'): data = {'sections': {'Accueil': [{'label': 'Vue d’ensemble', 'path': '/today', 'icon': 'home', 'context_links': []}], 'Administration': [{'label': 'Paramètres', 'path': '/settings', 'icon': 'settings', 'context_links': []}]}}
                elif path.endswith('/agency/dashboard'): data = {'todos': [], 'todos_count': 0, 'urgencies': [], 'urgencies_count': 0, 'business': [], 'business_count': 0, 'active_projects': 0, 'pending_validations': 0, 'hot_leads': None, 'monthly_revenue': None}
                else: data = []
                await route.fulfill(status=status, content_type='application/json', body=json.dumps(data))
            await context.route('**/api/**', api)
            await context.route('https://www.googletagmanager.com/**', lambda route: route.abort())
            page = await context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.goto(BASE + '/login', wait_until='networkidle')
            reject = page.get_by_role('button', name='Tout refuser', exact=True)
            if await reject.is_visible(): await reject.click()
            await page.get_by_label('Email', exact=True).fill(USER['email'])
            await page.get_by_label('Mot de passe', exact=True).fill('Explicit-UI-Test-Password!')
            await page.get_by_role('button', name='Se connecter', exact=True).click()
            await page.get_by_role('heading', name='Vérification 2FA', exact=True).wait_for()
            assert await page.evaluate("localStorage.getItem('access_token')") is None
            assert 'Explicit-UI-Test-Password!' not in await page.evaluate('JSON.stringify(localStorage)')
            await page.get_by_label('Méthode de vérification', exact=True).select_option('email')
            await page.get_by_role('button', name='Envoyer un code', exact=True).click()
            await page.get_by_role('alert').filter(has_text='TEST — envoi temporairement indisponible').wait_for()
            assert await page.get_by_text('Code envoyé', exact=False).count() == 0
            await page.get_by_role('button', name='Envoyer un code', exact=True).click()
            await page.get_by_role('status').filter(has_text='Code envoyé').wait_for()
            trust = page.get_by_role('checkbox', name='Faire confiance à cet appareil pendant 30 jours', exact=False)
            assert not await trust.is_checked()
            await page.get_by_label('Code à 6 chiffres', exact=True).fill('000000')
            await page.get_by_role('button', name='Vérifier', exact=True).click()
            await page.get_by_role('alert').filter(has_text='TEST — code refusé').wait_for()
            assert await page.evaluate("localStorage.getItem('access_token')") is None
            await page.get_by_label('Méthode de vérification', exact=True).select_option('recovery')
            if width == 1440: await trust.check()
            await page.get_by_label('Code de secours', exact=True).fill(CODES[0])
            await page.screenshot(path=str(ARTIFACTS / f'login-{width}.png'), full_page=True)
            await page.get_by_role('button', name='Vérifier', exact=True).click()
            await page.wait_for_url('**/today')
            assert len([call for call in calls if call[0].endswith('/auth/login')]) == 1
            completions = [call[1] for call in calls if call[0].endswith('/auth/mfa/complete')]
            assert all(set(body) == {'challenge_token', 'method', 'code', 'trust_device'} for body in completions)
            assert completions[0]['trust_device'] is False
            assert completions[-1]['trust_device'] is (width == 1440)

            await page.goto(BASE + '/settings', wait_until='networkidle')
            await page.get_by_role('tab', name='Sécurité', exact=True).click()
            await page.get_by_role('heading', name='Authentification à deux facteurs', exact=True).wait_for()
            await page.get_by_text('TEST Firefox', exact=True).wait_for()
            assert await page.get_by_role('button', name='Fermer la session', exact=True).count() == 1
            page.once('dialog', lambda dialog: dialog.accept())
            await page.get_by_role('button', name='Fermer toutes les autres sessions', exact=True).click()
            await page.get_by_text('TEST Firefox', exact=True).wait_for(state='detached')
            assert await page.get_by_text('Session actuelle', exact=True).is_visible()
            assert await page.get_by_role('button', name='Fermer toutes les autres sessions', exact=True).is_disabled()
            await page.screenshot(path=str(ARTIFACTS / f'sessions-{width}.png'), full_page=True)
            sms = page.locator('article').filter(has=page.get_by_role('heading', name='Code par SMS', exact=True))
            assert await sms.get_by_role('button', name='Configurer', exact=True).is_disabled()
            email = page.locator('article').filter(has=page.get_by_role('heading', name='Code par e-mail', exact=True))
            await email.get_by_role('button', name='Configurer', exact=True).click()
            dialog = page.get_by_role('dialog')
            await dialog.get_by_text('Compte vérifié :', exact=False).wait_for()
            assert await dialog.get_by_text(USER['email'], exact=True).is_visible()
            await dialog.get_by_label('Mot de passe Radar', exact=True).fill('wrong')
            await dialog.get_by_role('button', name='Continuer', exact=True).click()
            await dialog.get_by_role('alert').filter(has_text='Mot de passe Radar incorrect.').wait_for()
            assert len([body for path, body in calls if path.endswith('/auth/mfa/reauth/start') and body.get('password') == 'wrong']) == 1
            assert not [path for path, _ in calls if path.endswith('/auth/refresh')]
            await dialog.get_by_label('Mot de passe Radar', exact=True).fill('Explicit-UI-Test-Password!')
            await dialog.get_by_role('button', name='Continuer', exact=True).click()
            await dialog.get_by_label('Code à 6 chiffres', exact=True).fill('123456')
            await dialog.get_by_role('button', name='Vérifier', exact=True).click()
            await dialog.get_by_text('Code envoyé.', exact=False).wait_for()
            await dialog.get_by_label('Code à 6 chiffres', exact=True).fill('654321')
            await dialog.get_by_role('button', name='Activer la méthode', exact=True).click()
            await page.get_by_role('heading', name='Enregistrez ces codes maintenant', exact=True).wait_for()
            assert CODES[0] not in await page.evaluate('JSON.stringify(localStorage)')
            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not [path for path, _ in calls if '/auth/2fa/' in path]
            assert not errors, errors
            await page.screenshot(path=str(ARTIFACTS / f'settings-{width}.png'), full_page=True)
            await page.goto(BASE + '/login#mfa_token=' + TOKEN, wait_until='networkidle')
            await page.get_by_role('heading', name='Vérification 2FA', exact=True).wait_for()
            assert await page.evaluate('location.hash') == ''
            assert await page.evaluate("localStorage.getItem('access_token')") is None
            await page.get_by_label('Code à 6 chiffres', exact=True).fill('123456')
            await page.get_by_role('button', name='Vérifier', exact=True).click()
            await page.wait_for_url('**/today')
            assert len([call for call in calls if call[0].endswith('/auth/login')]) == 1
            await page.goto(BASE + '/auth/callback#access_token=explicit-fixture-sso&refresh_token=explicit-fixture-refresh', wait_until='networkidle')
            await page.wait_for_url('**/today')

            # Separate explicit account-state fixture for initial app enrollment.
            active[:] = []
            await page.goto(BASE + '/settings', wait_until='networkidle')
            await page.get_by_role('tab', name='Sécurité', exact=True).click()
            app = page.locator('article').filter(has=page.get_by_role('heading', name='Application d’authentification', exact=True))
            await app.get_by_role('button', name='Configurer', exact=True).click()
            dialog = page.get_by_role('dialog')
            await dialog.get_by_label('Mot de passe Radar', exact=True).fill('Explicit-UI-Test-Password!')
            await dialog.get_by_role('button', name='Continuer', exact=True).click()
            qr = dialog.get_by_role('img', name='QR code de configuration de votre application d’authentification', exact=True)
            await qr.wait_for()
            assert 'EXPLICIT-UI-FIXTURE-ONLY' not in await page.evaluate('JSON.stringify(localStorage)')
            await dialog.get_by_label('Code à 6 chiffres', exact=True).fill('123456')
            await dialog.get_by_role('button', name='Activer la méthode', exact=True).click()
            await page.get_by_role('heading', name='Enregistrez ces codes maintenant', exact=True).wait_for()
            assert await page.get_by_text('EXPLICIT-UI-FIXTURE-ONLY', exact=True).count() == 0
            assert not errors, errors
            print(f'{width}px: MFA login/send/recovery, management, email/app enrollment, SMS unavailable, SSO fragments, no persistent proofs/overflow/JS errors OK', flush=True)
            await context.close()
        await browser.close()


asyncio.run(main())
