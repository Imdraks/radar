"""Explicit UI fixtures, no production API or fabricated live observations."""
import asyncio,json,os,sys
from urllib.parse import urlparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'backend'))
from app.core.subscription import PLAN_CONFIGS,Plan,NAV_SECTIONS,get_plan_features
from playwright.async_api import async_playwright, expect
BASE=os.environ.get('RADAR_UI_BASE_URL','http://localhost:3000')
if urlparse(BASE).hostname not in {'localhost','127.0.0.1'}:
 raise RuntimeError('UI fixtures may only target a local test instance')

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(args=['--no-sandbox'], executable_path=os.environ.get('RADAR_BROWSER_PATH'))
  for plan,width,height in [('business',1440,1000),('premium',1440,1000),('core',1440,1000),('business',768,1024),('business',390,844)]:
   context=await browser.new_context(viewport={'width':width,'height':height},locale='fr-FR')
   if width<1024:await context.add_init_script("localStorage.setItem('radar-sidebar-collapsed','true')")
   await context.add_init_script("localStorage.setItem('access_token','ui-test-only');localStorage.setItem('current_workspace_id','1');localStorage.setItem('opportunities-radar-welcome-shown-v2','true')")
   requests=[]
   rights=[]
   invoice={'id':10,'reference':'BROUILLON-'+'a'*32,'title':'TEST invoice','status':'DRAFT','issue_date':'2026-11-13','due_date':None,'client_id':None,'subtotal':100,'tax_rate':20,'tax_amount':20,'discount_percent':0,'discount_amount':0,'total':120,'amount_paid':0,'items':[{'id':1,'description':'TEST service','quantity':1,'unit_price':100,'line_total':100,'unit':'jour','position':0}],'created_at':'2026-11-13T12:00:00','updated_at':'2026-11-13T12:00:00'}
   features={f.value for f in get_plan_features(Plan(plan))}
   async def api(route):
    path=urlparse(route.request.url).path
    if path.endswith('/privacy/requests'):
     if route.request.method=='POST':
      body=route.request.post_data_json;requests.append((path,body))
      rights.append({'id':1,'workspace_id':None,'scope':'personal','status':'received','created_at':'2026-11-13T12:00:00','updated_at':'2026-11-13T12:00:00','response_due_at':'2026-12-13T12:00:00','response':None,**body})
      await route.fulfill(status=201,content_type='application/json',body=json.dumps(rights[-1]));return
     await route.fulfill(status=200,content_type='application/json',body=json.dumps(rights));return
    if path.endswith('/billing/invoices/10'):
     if route.request.method=='PATCH':
      body=route.request.post_data_json;requests.append((path,body));invoice.update(body);invoice['updated_at']='2026-11-13T12:01:00'
     await route.fulfill(status=200,content_type='application/json',body=json.dumps(invoice));return
    if route.request.method=='POST':
     requests.append((path,route.request.post_data_json))
     await route.fulfill(status=202,content_type='application/json',body=json.dumps({'id':1,'status':'pending'}));return
    if path.endswith('/auth/me'):
     data={'id':1,'email':'preview@radar.example','full_name':'Camille Martin','role':'admin','is_superuser':False,'is_active':True,'is_whitelisted':True,'created_at':'2026-01-01T00:00:00'}
    elif path.endswith('/subscription/current'):
     data={'workspace_id':1,'workspace_name':'TEST — Atelier communication','plan':plan,'plan_display_name':'Radar '+plan.title(),'enabled_packs':[],'addons':[],'max_seats':3,'current_seats':1,'available_features':sorted(features)}
    elif path.endswith('/subscription/navigation'):
     data={'sections':{section:[{'label':i.label,'path':i.path,'icon':i.icon,'available':True,'locked':False,'admin_only':i.admin_only,'context_links':[{'label':child.label,'path':child.path,'icon':child.icon} for child in i.context_links if not child.feature or child.feature in get_plan_features(Plan(plan))]} for i in items if not i.admin_only and (not i.feature or i.feature.value in features)] for section,items in NAV_SECTIONS.items()}}
    elif path.endswith('/subscription/plans'):
     data=[{**vars(c),'included_packs':[v.value for v in c.included_packs],'included_addons':[],'available_features':sorted(f.value for f in get_plan_features(Plan(c.name))),'is_current':False,'is_recommended':False} for c in PLAN_CONFIGS.values()]
    elif path.endswith('/agency/dashboard'):
     data={'todos':[],'todos_count':0,'urgencies':[],'urgencies_count':0,'business':[],'business_count':0,'active_projects':0,'pending_validations':0,'hot_leads':0 if plan=='business' else None,'monthly_revenue':0 if plan=='business' else None}
    elif path.endswith('/workspaces'):
     data={'items':[{'id':1,'name':'TEST — Atelier communication','role':'admin','members_count':1}]}
    elif path.endswith('/inbox'):
     data={'items':[]}
    elif '/discovery/feed/' in path:
     data={'artists':[],'total':0,'page':1,'limit':20,'has_more':False}
    elif path.endswith('/discovery/queue'):
     data={'jobs':[],'running':0,'pending':0,'completed_24h':0}
    elif path.endswith('/agency/pipeline'):
     data={'columns':[],'total_deals':0,'total_value':0}
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
   sidebar=page.locator('aside[data-onboarding=sidebar]')
   if width>=1024:
    assert await sidebar.locator('a[href="/settings/subscription"]').count()==1
    await page.get_by_role('button',name='Rétracter la barre latérale',exact=True).click()
    await expect(sidebar).to_have_css('width','80px')
    assert await page.get_by_role('button',name='Déplier la barre latérale',exact=True).get_attribute('aria-expanded')=='false'
    assert await sidebar.get_by_role('link',name='Projets',exact=True).locator('svg').is_visible()
    await sidebar.get_by_role('link',name='Projets',exact=True).hover()
    await page.get_by_role('tooltip',name='Projets',exact=True).wait_for()
    await page.reload(wait_until='networkidle')
    await page.get_by_role('heading',name='Abonnement',exact=True).wait_for()
    await expect(sidebar).to_have_css('width','80px')
    assert await page.evaluate("localStorage.getItem('radar-sidebar-collapsed')")=='true'
    assert await sidebar.locator('a[href="/settings/subscription"]').count()==1
    if plan=='business':await page.screenshot(path='/tmp/radar-sidebar-collapsed.png')
    expand=page.get_by_role('button',name='Déplier la barre latérale',exact=True)
    await expand.focus();await page.keyboard.press('Enter')
    await expect(sidebar).to_have_css('width','280px')
    assert await page.evaluate("localStorage.getItem('radar-sidebar-collapsed')")=='false'
    assert await page.get_by_text('Votre abonnement',exact=True).count()==0
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
    assert await dialog.get_by_role('link',name='Projets',exact=True).locator('span').last.get_attribute('class')!='sr-only'
    assert await dialog.locator('a[href="/settings/subscription"]').count()==1
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
   if plan=='business':
    workflows=[('/discovery','Discovery','Recherche et analyse'),('/comparison','Discovery','Sélections et comparaison'),('/clients','Clients et prospects','Clients et contacts'),('/pipeline','Clients et prospects','Pipeline commercial'),('/devis','Devis et factures','Devis'),('/factures','Devis et factures','Factures et paiements')]
    for path,group,label in workflows:
     await page.goto(BASE+path,wait_until='networkidle')
     tabs=page.get_by_role('navigation',name='Parcours '+group,exact=True)
     await tabs.wait_for()
     assert await tabs.get_by_role('link',name=label,exact=True).get_attribute('aria-current')=='page'
     if path=='/discovery':assert await page.get_by_text('Accès rapide',exact=True).count()==0
     if path=='/comparison':assert await page.get_by_role('button',name='Nouvelle sélection',exact=True).count()==1
     if plan=='business' and width==1440 and path in ['/comparison','/factures']:
      await page.screenshot(path='/tmp/radar-simplified-'+path.strip('/')+'.png',full_page=True)
     if width>=1024:
      nav=page.get_by_role('navigation',name='Navigation principale',exact=True)
      assert await nav.get_by_role('link',name=group,exact=True).get_attribute('aria-current')=='page'
      assert await nav.get_by_role('link',name='Pipeline commercial',exact=True).count()==0
      assert await nav.get_by_role('link',name='Sélections artistiques',exact=True).count()==0
     assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth'),path
     assert not errors,(path,errors)
    await page.goto(BASE+'/settings/tools',wait_until='networkidle')
    await page.get_by_role('heading',name='Outils historiques',exact=True).wait_for()
    assert await page.get_by_role('link',name='Profils de recherche',exact=False).count()==1
    await page.goto(BASE+'/settings',wait_until='networkidle')
    await page.get_by_role('heading',name='Paramètres',exact=True).wait_for()
    assert await page.get_by_role('button',name='Enregistrer',exact=True).count()==0
    assert await page.get_by_role('button',name='Changer le mot de passe',exact=True).count()==0
    assert await page.get_by_role('tab',name='Dashboard',exact=True).count()==0
   await page.goto(BASE+'/settings/privacy',wait_until='networkidle')
   await page.get_by_role('heading',name='Données et droits',exact=True).wait_for()
   await page.get_by_label('Objet',exact=True).select_option('access')
   await page.get_by_role('button',name='Enregistrer la demande',exact=True).click()
   await page.get_by_text('Demande n°1 enregistrée.',exact=False).wait_for()
   assert rights[-1]['scope']=='personal'
   assert requests[-1][1]['details']==''
   assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   if plan=='business' and width in [1440,390]:
    await page.goto(BASE+'/factures/10',wait_until='networkidle')
    await page.get_by_role('heading',name='Informations avant émission',exact=True).wait_for()
    await page.get_by_label('Date de prestation',exact=True).fill('2026-11-13')
    await page.get_by_label('Échéance de paiement',exact=True).fill('2026-12-13')
    await page.get_by_label('Type de client',exact=True).select_option('professional')
    await page.get_by_label('Conditions d’escompte',exact=True).fill('Aucun escompte convenu')
    await page.get_by_label('Formule de pénalités prévue au contrat',exact=True).select_option('ecb_plus_10')
    await page.get_by_role('button',name='Enregistrer les informations d’émission',exact=True).click()
    await page.wait_for_timeout(300)
    assert invoice['legal_details']['customer_type']=='professional'
    assert invoice['due_date']=='2026-12-13'
    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   if plan!='business':
    await page.goto(BASE+'/today',wait_until='networkidle')
    assert await page.get_by_text('Leads chauds',exact=True).count()==0
    assert await page.get_by_text('Ce mois',exact=True).count()==0
   assert not errors,errors
   print(f'{plan} {width}px: catalogue, requests, accueil, formulaire, menu clavier, responsive OK',flush=True)
   await context.close()
  await browser.close()
asyncio.run(main())
