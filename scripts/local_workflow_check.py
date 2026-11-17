"""Create disposable business records through the local UI; no external sends."""
import asyncio,json,os
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from local_site_check import BASE

async def main():
    account=json.loads(Path(os.environ['RADAR_TEST_ACCOUNT_FILE']).read_text())
    async with async_playwright() as p:
        browser=await p.chromium.launch(args=['--no-sandbox'])
        context=await browser.new_context(locale='fr-FR',viewport={'width':1440,'height':1000})
        await context.route('https://www.googletagmanager.com/**',lambda r:r.abort())
        page=await context.new_page()
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        await page.goto(BASE+'/login',wait_until='domcontentloaded')
        await page.get_by_role('button',name='Tout refuser',exact=True).click()
        await page.locator('input[type=email]').fill(account['email'])
        await page.locator('input[type=password]').fill(account['password'])
        async with page.expect_response(lambda r:'/auth/login' in r.url) as login_response:
            await page.get_by_role('button',name='Se connecter',exact=True).click()
        print('Login HTTP', (await login_response.value).status, flush=True)
        await page.wait_for_url('**/today',timeout=60000,wait_until='domcontentloaded')
        await page.wait_for_timeout(1000)
        skip=page.get_by_role('button',name='Passer et explorer par moi-même')
        if await skip.is_visible(): await skip.click()
        name='TEST LOCAL '+datetime.now().strftime('%H%M%S')
        await page.goto(BASE+'/projects',wait_until='domcontentloaded')
        await page.get_by_role('button',name='Nouveau projet',exact=True).click()
        await page.get_by_placeholder('Ex: Campagne Summer 2025').fill(name+' projet')
        async with page.expect_response(lambda r:'/agency/projects' in r.url and r.request.method=='POST') as response:
            await page.get_by_role('button',name='Créer le projet',exact=True).click()
        created=await response.value
        assert created.status==200,(created.status,await created.text())
        project=await created.json()
        await page.goto(BASE+f'/projects/{project["id"]}',wait_until='domcontentloaded')
        await page.get_by_text(name+' projet',exact=True).first.wait_for()
        print('Project creation and detail: OK',flush=True)
        await page.goto(BASE+'/events',wait_until='domcontentloaded')
        await page.locator('input[name=name]').fill(name+' événement')
        await page.locator('input[name=venue]').fill('Salle de test locale')
        await page.locator('input[name=start]').fill('2026-11-20T18:00')
        await page.locator('input[name=end]').fill('2026-11-20T23:00')
        await page.locator('input[name=budget]').fill('1200')
        async with page.expect_response(lambda r:'/api/v1/events' in r.url and r.request.method=='POST') as response:
            await page.get_by_role('button',name='Créer l’événement',exact=True).click()
        created=await response.value
        assert created.status==201,(created.status,await created.text())
        await page.get_by_role('heading',name=name+' événement',exact=True).wait_for()
        print('Event creation and listing: OK',flush=True)
        await page.goto(BASE+'/clients',wait_until='domcontentloaded')
        await page.get_by_role('button',name='Nouveau client',exact=True).click()
        await page.get_by_placeholder('Acme Inc.').fill(name+' client')
        async with page.expect_response(lambda r:'/agency/clients' in r.url and r.request.method=='POST') as response:
            await page.get_by_role('button',name='Créer',exact=True).click()
        created=await response.value
        assert created.status==200,(created.status,await created.text())
        print('Client creation: OK',flush=True)
        await page.goto(BASE+'/devis',wait_until='domcontentloaded')
        await page.get_by_role('button',name='Nouveau Devis',exact=True).click()
        await page.get_by_placeholder('Ex: Prestation événementielle').fill(name+' devis')
        async with page.expect_response(lambda r:'/billing/quotes' in r.url and r.request.method=='POST') as response:
            await page.get_by_role('button',name='Créer le devis',exact=True).click()
        created=await response.value
        assert created.status in (200,201),(created.status,await created.text())
        quote=await created.json()
        await page.goto(BASE+f'/devis/{quote["id"]}',wait_until='domcontentloaded')
        await page.get_by_text(name+' devis',exact=True).first.wait_for()
        print('Draft quote creation and detail: OK',flush=True)
        assert not errors,errors
        await browser.close()

if __name__=='__main__': asyncio.run(main())
