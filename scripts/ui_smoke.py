import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'backend'))
from app.core.subscription import PLAN_CONFIGS,Plan,NAV_SECTIONS,get_plan_features

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
        for width,height in [(1440,1000),(768,1024),(390,844)]:
            context=await browser.new_context(viewport={'width':width,'height':height},locale='fr-FR')
            await context.add_init_script("localStorage.setItem('access_token','ui-test-only');localStorage.setItem('current_workspace_id','1');localStorage.setItem('opportunities-radar-welcome-shown-v2','true')")
            async def route_request(route):
                path=route.request.url.split('?',1)[0]
                if path.endswith('/auth/me'):
                    data={'id':1,'email':'local-ui-test@radar.invalid','full_name':'Test local explicite','role':'pm','is_superuser':False,'is_active':True,'is_whitelisted':True,'created_at':'2026-01-01T00:00:00'}
                elif path.endswith('/subscription/current'):
                    data={'workspace_id':1,'workspace_name':'Workspace de test local','plan':'business','plan_display_name':'Radar Business','enabled_packs':[],'addons':[],'max_seats':3,'current_seats':1,'available_features':[f.value for f in get_plan_features(Plan.BUSINESS)]}
                elif path.endswith('/subscription/navigation'):
                    data={'sections':{section:[{'label':i.label,'path':i.path,'icon':i.icon,'available':True,'locked':False,'admin_only':i.admin_only} for i in items if not i.admin_only] for section,items in NAV_SECTIONS.items()}}
                elif path.endswith('/subscription/plans'):
                    data=[{**vars(c),'included_packs':[x.value for x in c.included_packs],'included_addons':[],'is_current':False,'is_recommended':False} for c in PLAN_CONFIGS.values()]
                elif path.endswith('/events'):
                    await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'Indisponibilité simulée pour test local'}));return
                else:
                    data=[]
                await route.fulfill(status=200,content_type='application/json',body=json.dumps(data))
            await context.route('**/api/**',route_request)
            await context.route('https://www.googletagmanager.com/**',lambda route:route.abort())
            page=await context.new_page()
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            await page.goto(os.environ.get('RADAR_UI_BASE_URL','http://localhost:3000')+'/settings/subscription')
            await page.get_by_role('heading',name='Abonnement',exact=True).wait_for()
            await page.get_by_role('heading',name='Radar Core',exact=True).wait_for()
            await page.get_by_role('heading',name='Radar Premium',exact=True).wait_for()
            await page.get_by_role('heading',name='Radar Business',exact=True).wait_for()
            await page.wait_for_load_state('networkidle',timeout=10000)
            assert await page.get_by_role('heading',name='Radar Premium',exact=True).is_visible()
            assert await page.get_by_role('heading',name='Radar Business',exact=True).is_visible()
            if width<1024:
                await page.get_by_role('button',name='Ouvrir le menu',exact=True).click()
                await page.get_by_role('navigation',name='Navigation principale').wait_for(state='visible')
                await page.get_by_role('button',name='Fermer le menu',exact=True).last.click()
            assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            await page.screenshot(path=f'/tmp/radar-ui-{width}.png',full_page=True)
            await page.goto(os.environ.get('RADAR_UI_BASE_URL','http://localhost:3000')+'/events')
            await page.get_by_role('heading',name='Événements',exact=True).wait_for()
            await page.get_by_text('Impossible de charger les événements.',exact=True).wait_for()
            assert not errors,errors
            print(f'UI {width}x{height}: catalogue, navigation, absence de débordement, erreur événement explicite: OK')
            await context.close()
        await browser.close()
asyncio.run(main())
