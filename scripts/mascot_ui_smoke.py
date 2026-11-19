"""Sphere behavior and honest, permission-aware guidance on local API fixtures."""
import asyncio
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse
from playwright.async_api import async_playwright, expect
from theme_ui_smoke import fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.core.subscription import Plan, get_plan_features, NAV_SECTIONS

BASE = os.environ.get('RADAR_UI_BASE_URL', 'http://127.0.0.1:3000')
if urlparse(BASE).hostname not in {'localhost', '127.0.0.1'}:
    raise RuntimeError('Mascot fixtures must use a local instance')


async def setup(browser, width, plan, admin, reduced='no-preference', welcome_seen=True):
    context = await browser.new_context(viewport={'width': width, 'height': 950}, reduced_motion=reduced, locale='fr-FR')
    seed = "localStorage.setItem('access_token','mascot-test-only');localStorage.setItem('current_workspace_id','1');localStorage.setItem('cookie-consent',JSON.stringify({version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}));"
    if welcome_seen:
        seed += "localStorage.setItem('opportunities-radar-welcome-shown-v2','true');"
    await context.add_init_script(seed)
    mutations = []
    features = get_plan_features(Plan(plan))
    async def api(route):
        path = urlparse(route.request.url).path
        if route.request.method not in ['GET','HEAD']:
            mutations.append((path, route.request.method))
        if path.endswith('/auth/me'):
            data = {'id':1,'email':'mascot@example.com','full_name':'TEST Mascot','is_active':True,'is_superuser':admin,'role':'admin' if admin else 'viewer','created_at':'2026-01-01T00:00:00'}
        elif path.endswith('/subscription/current'):
            data = {'workspace_id':1,'workspace_name':'TEST — Studio Radar','plan':plan,'plan_display_name':'Radar '+plan.title(),'available_features':[f.value for f in features], 'max_seats':3,'current_seats':1,'addons':[],'enabled_packs':[]}
        elif path.endswith('/subscription/navigation'):
            data = {'sections':{section:[{'label':item.label,'path':item.path,'icon':item.icon,'available':True,'locked':False,'admin_only':item.admin_only,'context_links':[{'label':child.label,'path':child.path,'icon':child.icon} for child in item.context_links if (not child.feature or child.feature in features) and (not child.admin_only or admin)]} for item in items if (not item.feature or item.feature in features) and (not item.admin_only or admin)] for section,items in NAV_SECTIONS.items()}}
        else:
            await fixture(route)
            return
        await route.fulfill(status=200,content_type='application/json',body=json.dumps(data))
    await context.route('**/api/**',api)
    return context, mutations


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'], executable_path=os.environ.get('RADAR_BROWSER_PATH'))
        for width, plan, admin in [(1440,'core',False),(390,'business',True)]:
            context, mutations = await setup(browser,width,plan,admin)
            page = await context.new_page()
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            await page.clock.install()
            await page.goto(BASE+'/projects',wait_until='networkidle')
            await expect(page.locator('#radar-main')).to_have_attribute('aria-busy','false')
            button = page.get_by_role('button',name='Ouvrir l’aide Radar',exact=True,include_hidden=True)
            sphere = button.locator('.radar-sphere')
            await expect(sphere).to_have_attribute('data-moving','true')
            await sphere.evaluate('''element => {
              window.__sphereChanges=[];
              new MutationObserver(records => records.forEach(record => window.__sphereChanges.push([record.attributeName,element.getAttribute(record.attributeName)]))).observe(element,{attributes:true,attributeFilter:['data-blink','data-expression']});
            }''')
            await page.clock.run_for(26000)
            changes=await page.evaluate('window.__sphereChanges')
            assert any(name=='data-blink' and value=='true' for name,value in changes),changes
            assert any(name=='data-expression' and value in ['dreamy','yawn','wink'] for name,value in changes),changes
            box=await sphere.bounding_box()
            await page.mouse.move(box['x']+box['width']+22,box['y']+box['height']/2)
            await page.clock.run_for(150)
            await expect(sphere).to_have_attribute('data-mood','curious')
            assert abs(float(await sphere.evaluate("e=>e.style.getPropertyValue('--look-x').replace('px','')")))>0
            await page.mouse.move(0,500)
            await page.clock.run_for(150)
            await button.focus()
            await expect(sphere).to_have_attribute('data-expression','awake')
            await page.keyboard.press('Enter')
            dialog=page.get_by_role('dialog',name='Bienvenue sur Radar',exact=True)
            await expect(dialog).to_be_visible()
            await expect(sphere).to_have_attribute('data-moving','false')
            guide_sphere=dialog.locator('.radar-sphere')
            await expect(guide_sphere).to_have_attribute('data-moving','true')
            await expect(dialog).to_contain_text('TEST — Studio Radar')
            await dialog.get_by_role('button',name='Continuer',exact=True).click()
            await expect(guide_sphere).to_have_attribute('data-mood','curious')
            assert await dialog.get_by_role('link',name='Configurer les intégrations',exact=True).count()==int(admin)
            assert not mutations,mutations
            await dialog.get_by_role('button',name='Continuer',exact=True).click()
            await expect(guide_sphere).to_have_attribute('data-mood','idea')
            assert await dialog.get_by_role('link',name='Discovery',exact=False).count()==int(plan!='core')
            assert await dialog.get_by_role('link',name='Factures',exact=False).count()==int(plan=='business')
            await dialog.get_by_role('button',name='Précédent',exact=True).click()
            await expect(dialog).to_contain_text('Reliez les outils de votre agence.')
            await dialog.get_by_role('button',name='Continuer',exact=True).click()
            await dialog.get_by_role('button',name='Continuer',exact=True).click()
            await expect(dialog).to_contain_text('Les premiers repères sont posés.')
            await page.clock.run_for(650)
            await expect(guide_sphere).to_have_css('background-color','rgb(142, 220, 237)')
            await page.screenshot(path=f'/tmp/radar-mascot-guide-{width}.png')
            await dialog.get_by_role('button',name='Continuer dans Radar',exact=True).click()
            await expect(dialog).to_be_hidden()
            await expect(button).to_be_focused()
            await expect(sphere).to_have_attribute('data-moving','true')
            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not mutations and not errors,(mutations,errors)
            await page.emulate_media(reduced_motion='reduce')
            await expect(sphere).to_have_attribute('data-moving','false')
            await expect(sphere).to_have_css('animation-name','none')
            await page.clock.run_for(20000)
            await expect(sphere).to_have_attribute('data-blink','false')
            await page.emulate_media(reduced_motion='no-preference')
            await expect(sphere).to_have_attribute('data-moving','true')
            await page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))")
            await expect(sphere).to_have_attribute('data-moving','false')
            await page.clock.run_for(10000)
            await expect(sphere).to_have_attribute('data-blink','false')
            await page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))")
            await expect(sphere).to_have_attribute('data-moving','true')
            print(f'{width}px/{plan}: idle expressions, blink, gaze, focus, guide rights and reduced motion OK',flush=True)
            await context.close()
        context,_=await setup(browser,390,'core',False,welcome_seen=False)
        page=await context.new_page()
        await page.goto(BASE+'/projects',wait_until='networkidle')
        dialog=page.get_by_role('dialog',name='Bienvenue sur Radar',exact=True)
        await expect(dialog).to_be_visible()
        await page.keyboard.press('Escape')
        await expect(dialog).to_be_hidden()
        await page.reload(wait_until='networkidle')
        await expect(page.locator('#radar-main')).to_have_attribute('aria-busy','false')
        await expect(dialog).to_be_hidden()
        print('First visit: one welcome dialog, Escape dismisses it and reload preserves the choice OK',flush=True)
        await context.close()
        await browser.close()


if __name__=='__main__':
    asyncio.run(main())
