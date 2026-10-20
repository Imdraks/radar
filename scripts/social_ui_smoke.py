"""Local browser regression with explicitly simulated API responses and test counts."""
import asyncio,json,os,sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.core.subscription import NAV_SECTIONS,Plan,get_plan_features

async def main():
    base=os.environ.get('RADAR_UI_BASE_URL','http://127.0.0.1:3100')
    if urlparse(base).hostname not in {'localhost','127.0.0.1'}:raise RuntimeError('Local server required')
    async with async_playwright() as p:
        browser=await p.chromium.launch(args=['--no-sandbox'])
        for width,terminal in [(1440,'DONE'),(390,'PARTIAL')]:
            context=await browser.new_context(locale='fr-FR',viewport={'width':width,'height':1000})
            await context.add_init_script("localStorage.setItem('access_token','explicit-ui-fixture-only');localStorage.setItem('current_workspace_id','1');localStorage.setItem('opportunities-radar-welcome-shown-v2','true')")
            await context.route('https://www.googletagmanager.com/**',lambda route:route.abort())
            completed=False; saved=[]
            async def api_route(route):
                nonlocal completed
                path=urlparse(route.request.url).path
                if path.endswith('/auth/me'):
                    data={'id':1,'email':'test@example.com','full_name':'TEST LOCAL','role':'pm','is_superuser':False,'is_active':True,'is_whitelisted':True}
                elif path.endswith('/subscription/current'):
                    data={'workspace_id':1,'workspace_name':'TEST LOCAL','plan':'premium','available_features':[f.value for f in get_plan_features(Plan.PREMIUM)]}
                elif path.endswith('/subscription/navigation'):
                    data={'sections':{s:[{'label':i.label,'path':i.path,'icon':i.icon,'available':True,'locked':False,'admin_only':i.admin_only} for i in items if not i.admin_only] for s,items in NAV_SECTIONS.items()}}
                elif path.endswith('/social-profiles'):
                    saved.append(route.request.post_data_json);data={'instagram':'https://www.instagram.com/test.artist/'}
                elif path.endswith('/refresh'):
                    data={'id':'ui-job','status':'QUEUED'}
                elif path.endswith('/job/ui-job'):
                    completed=True;data={'status':terminal,'current_step':'COMPUTE','progress':100}
                elif '/discovery/artist/' in path:
                    display='1.3M' if completed else '1.2M'
                    data={'id':'00000000-0000-0000-0000-000000000001','name':'Artiste TEST LOCAL','normalized_name':'test','score':0,
                          'genres':[],'drivers':[],'risks':[],'patterns':[],'signals':[],'created_at':'2026-10-20T00:00:00',
                          'evidence':[],'social_profiles':{'instagram':'https://www.instagram.com/test.artist/'},
                          'social_observations':{'instagram':{'status':'collected','value':1300000 if completed else 1200000,'display_value':display,'precision':'rounded_public_display','source_url':'https://www.instagram.com/test.artist/','collected_at':'2026-10-20T00:00:00Z'},
                                                 'youtube':{'status':'configuration_required','value':None,'error_code':'YOUTUBE_API_KEY_REQUIRED'}}}
                else:data=[]
                await route.fulfill(status=200,content_type='application/json',body=json.dumps(data))
            await context.route('**/api/**',api_route)
            page=await context.new_page();errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            await page.goto(base+'/discovery/00000000-0000-0000-0000-000000000001',wait_until='domcontentloaded')
            await page.get_by_text('≈ 1.2M abonnés',exact=False).wait_for()
            await page.get_by_text('Connexion YouTube à configurer par l’administrateur',exact=False).wait_for()
            # Refuse optional cookies as a normal user.
            refuse=page.get_by_role('button',name='Tout refuser',exact=True)
            if await refuse.is_visible():await refuse.click()
            await page.locator('input[name=instagram]').fill('https://www.instagram.com/test.artist/')
            await page.get_by_role('button',name='Enregistrer les profils',exact=True).click()
            assert saved and saved[-1]['instagram_url']=='https://www.instagram.com/test.artist/'
            await page.get_by_role('button',name='Enrichir les données',exact=True).click()
            try:
                await page.get_by_text('≈ 1.3M abonnés',exact=False).wait_for(timeout=15000)
            except Exception:
                print('ERRORS',errors,'BODY',(await page.locator('body').inner_text())[-6000:],flush=True)
                await page.screenshot(path='/tmp/radar-social-ui-failure.png',full_page=True)
                raise
            await page.get_by_role('button',name='Enrichir les données',exact=True).wait_for(state='visible',timeout=15000)
            assert not errors,errors
            assert await page.get_by_role('heading',name='Artiste TEST LOCAL',exact=True).is_visible()
            await page.screenshot(path=f'/tmp/radar-social-ui-{width}.png',full_page=True)
            if await page.evaluate('document.documentElement.scrollWidth > innerWidth+1'):
                print('OVERFLOW',await page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,12).map(e=>({tag:e.tagName,cls:e.className,text:e.innerText?.slice(0,90),right:e.getBoundingClientRect().right}))"),flush=True)
                raise AssertionError('Horizontal overflow')
            print(f'UI {width}px: rounding, missing configuration, profile save, {terminal} refresh completion: OK',flush=True)
            await context.close()
        await browser.close()

if __name__=='__main__':asyncio.run(main())
