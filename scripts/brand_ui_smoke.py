"""Local browser QA of Radar public identity; all API replies are explicit fixtures."""
import asyncio,json,os,sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.core.subscription import PLAN_CONFIGS,Plan,get_plan_features
BASE=os.environ.get('RADAR_UI_BASE_URL','http://localhost:3000')
if urlparse(BASE).hostname not in {'localhost','127.0.0.1'}:
 raise RuntimeError('Brand UI fixtures may only target a local instance')

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(args=['--no-sandbox'],executable_path=os.environ.get('RADAR_BROWSER_PATH'))
  for width,height in [(1440,1000),(768,1024),(390,844)]:
   context=await browser.new_context(viewport={'width':width,'height':height},locale='fr-FR')
   async def api(route):
    path=urlparse(route.request.url).path
    if path.endswith('/subscription/plans'):
     data=[{**vars(c),'included_packs':[v.value for v in c.included_packs],'included_addons':[],'available_features':sorted(f.value for f in get_plan_features(Plan(c.name))),'is_current':False,'is_recommended':False} for c in PLAN_CONFIGS.values()]
    elif path.endswith('/auth/setup-check'):data={'needs_setup':False,'user_count':1}
    elif path.endswith('/auth/sso/providers'):data={'providers':[{'id':'google','name':'Google','enabled':True}] if width==768 else []}
    elif route.request.method=='POST' and path.endswith('/auth/login'):
     await route.fulfill(status=401,content_type='application/json',body=json.dumps({'detail':'TEST — identifiants refusés'}));return
    else:data=[]
    await route.fulfill(status=200,content_type='application/json',body=json.dumps(data))
   await context.route('**/api/**',api)
   await context.route('https://www.googletagmanager.com/**',lambda r:r.abort())
   page=await context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   for path in ['/','/pricing','/contact','/legal','/contracts','/retention','/privacy','/terms','/sales-terms','/cookies','/data-processing','/subprocessors','/reversibility','/accessibility','/login']:
    await page.goto(BASE+path,wait_until='networkidle')
    if await page.get_by_role('button',name='Tout refuser',exact=True).is_visible():
     await page.get_by_role('button',name='Tout refuser',exact=True).click()
    assert await page.get_by_role('img',name='Radar',exact=True).count()>0,path
    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(path,width)
    assert await page.locator('a button').count()==0,(path,'nested buttons')
    if path=='/':
     await page.get_by_role('heading',name='Gardez le cap.',exact=False).wait_for()
     assert await page.get_by_role('link',name='Découvrir les offres',exact=True).get_attribute('href')=='/pricing'
     assert await page.locator('.radar-orbit-panel .radar-field').evaluate('(e)=>getComputedStyle(e).position')=='absolute'
     assert 'Veille concurrentielle' not in await page.locator('body').inner_text()
     await page.screenshot(path=f'/tmp/radar-brand-home-{width}.png',full_page=True)
     if width<1024:
      trigger=page.get_by_role('button',name='Ouvrir le menu du site',exact=True)
      await trigger.click();await page.get_by_role('dialog').wait_for()
      await page.keyboard.press('Escape');await page.get_by_role('dialog').wait_for(state='hidden')
    if path=='/contact':
     assert await page.get_by_role('option',name='Radar Premium',exact=True).count()==1
     assert await page.get_by_role('option',name='Radar Talents',exact=True).count()==0
    if path=='/login':
     assert await page.get_by_role('button',name='Continuer avec Google',exact=True).count()==(1 if width==768 else 0)
     await page.get_by_label('Email',exact=True).fill('test@radar.example')
     await page.get_by_label('Mot de passe',exact=True).fill('TEST-invalid-password')
     await page.get_by_role('button',name='Se connecter',exact=True).click()
     await page.get_by_text('TEST — identifiants refusés',exact=True).wait_for()
     await page.screenshot(path=f'/tmp/radar-brand-login-{width}.png',full_page=True)
    assert not errors,(path,errors)
    print(f'{width}px {path}: brand, links, form, no JS error or overflow OK',flush=True)
   await context.close()
  await browser.close()
asyncio.run(main())
