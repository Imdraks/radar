"""Explicit UI fixtures, no production API or fabricated live observations."""
import asyncio,json,os,sys
from urllib.parse import urlparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'backend'))
from app.core.subscription import PLAN_CONFIGS,Plan,NAV_SECTIONS,get_plan_features
from playwright.async_api import async_playwright
BASE=os.environ.get('RADAR_UI_BASE_URL','http://localhost:3000')
if urlparse(BASE).hostname not in {'localhost','127.0.0.1'}:
 raise RuntimeError('UI fixtures may only target a local test instance')

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(args=['--no-sandbox'])
  for plan,width,height in [('business',1440,1000),('premium',1440,1000),('core',1440,1000),('business',768,1024),('business',390,844)]:
   context=await browser.new_context(viewport={'width':width,'height':height},locale='fr-FR')
   await context.add_init_script("localStorage.setItem('access_token','ui-test-only');localStorage.setItem('current_workspace_id','1');localStorage.setItem('opportunities-radar-welcome-shown-v2','true')")
   requests=[]
   features={f.value for f in get_plan_features(Plan(plan))}
   async def api(route):
    path=urlparse(route.request.url).path
    if route.request.method=='POST':
     requests.append((path,route.request.post_data_json))
     await route.fulfill(status=202,content_type='application/json',body=json.dumps({'id':1,'status':'pending'}));return
    if path.endswith('/auth/me'):
     data={'id':1,'email':'preview@radar.example','full_name':'Camille Martin','role':'admin','is_superuser':False,'is_active':True,'is_whitelisted':True,'created_at':'2026-01-01T00:00:00'}
    elif path.endswith('/subscription/current'):
     data={'workspace_id':1,'workspace_name':'TEST — Atelier communication','plan':plan,'plan_display_name':'Radar '+plan.title(),'enabled_packs':[],'addons':[],'max_seats':3,'current_seats':1,'available_features':sorted(features)}
    elif path.endswith('/subscription/navigation'):
     data={'sections':{section:[{'label':i.label,'path':i.path,'icon':i.icon,'available':True,'locked':False,'admin_only':i.admin_only} for i in items if not i.admin_only and (not i.feature or i.feature.value in features)] for section,items in NAV_SECTIONS.items()}}
    elif path.endswith('/subscription/plans'):
     data=[{**vars(c),'included_packs':[v.value for v in c.included_packs],'included_addons':[],'available_features':sorted(f.value for f in get_plan_features(Plan(c.name))),'is_current':False,'is_recommended':False} for c in PLAN_CONFIGS.values()]
    elif path.endswith('/agency/dashboard'):
     data={'todos':[],'todos_count':0,'urgencies':[],'urgencies_count':0,'business':[],'business_count':0,'active_projects':0,'pending_validations':0,'hot_leads':0 if plan=='business' else None,'monthly_revenue':0 if plan=='business' else None}
    elif path.endswith('/workspaces'):
     data={'items':[{'id':1,'name':'TEST — Atelier communication','role':'admin','members_count':1}]}
    elif path.endswith('/inbox'):
     data={'items':[]}
    elif path.endswith('/events'):
     await route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST — fournisseur indisponible'}));return
    else:data=[]
    await route.fulfill(status=200,content_type='application/json',body=json.dumps(data))
   await context.route('**/api/**',api)
   await context.route('https://www.googletagmanager.com/**',lambda r:r.abort())
   page=await context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   await page.goto(BASE+'/settings/subscription')
   await page.get_by_role('heading',name='Radar Business',exact=True).wait_for()
   refuse=page.get_by_role('button',name='Tout refuser',exact=True)
   if await refuse.is_visible():await refuse.click()
   expected={'business':2,'premium':1,'core':0}[plan]
   assert await page.get_by_text('Déjà inclus',exact=True).count()==expected
   assert await page.get_by_text('Abonnement actif',exact=True).count()==1
   assert await page.get_by_role('button',name='Demander cet abonnement',exact=True).count()==2-expected
   for item in await page.get_by_text('Déjà inclus',exact=True).all():
    assert await item.evaluate('(e)=>getComputedStyle(e).color')=='rgb(21, 128, 61)'
   await page.get_by_label('Besoin d’une extension spécifique ?',exact=True).fill('TEST — intégration spécifique')
   await page.get_by_role('button',name='Envoyer une demande Radar Addons',exact=True).click()
   await page.get_by_text('Demande Radar Addons enregistrée.',exact=True).wait_for()
   assert requests[-1][0].endswith('/addon-requests')
   assert requests[-1][1]['description']=='TEST — intégration spécifique'
   if plan=='core':
    await page.get_by_role('button',name='Demander cet abonnement',exact=True).first.click()
    await page.get_by_text('Demande enregistrée. Votre abonnement actif reste inchangé en attendant sa validation.',exact=True).wait_for()
    assert requests[-1][1]['plan']=='premium'
   if width<1024:
    trigger=page.get_by_role('button',name='Ouvrir le menu',exact=True)
    await trigger.click();dialog=page.get_by_role('dialog',name='Navigation Radar')
    await dialog.wait_for()
    assert await dialog.get_by_role('navigation',name='Navigation principale').is_visible()
    await page.keyboard.press('Escape');await dialog.wait_for(state='hidden')
    await trigger.focus();await page.keyboard.press('Enter');await dialog.wait_for()
    await dialog.get_by_role('button',name='Fermer le menu',exact=True).click();await dialog.wait_for(state='hidden')
    assert await trigger.evaluate('(e)=>e===document.activeElement')
   assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   await page.screenshot(path=f'/tmp/radar-refresh-subscription-{plan}-{width}.png',full_page=True)
   await page.goto(BASE+'/today')
   await page.get_by_role('heading',name=', Camille',exact=False).wait_for()
   await page.get_by_role('heading',name='Tout est clair !',exact=True).wait_for()
   assert await page.get_by_role('button',name='Actualiser l’activité',exact=True).is_visible()
   assert await page.locator('a button').count()==0
   assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   await page.screenshot(path=f'/tmp/radar-refresh-today-{plan}-{width}.png',full_page=True)
   if plan=='business':
    await page.goto(BASE+'/events')
    await page.get_by_text('Impossible de charger les événements.',exact=True).wait_for()
    await page.get_by_label('Nom',exact=True).fill('TEST — événement')
    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   assert not errors,errors
   print(f'{plan} {width}px: catalogue, requests, accueil, formulaire, menu clavier, responsive OK',flush=True)
   await context.close()
  await browser.close()
asyncio.run(main())
