"""Contextual help and genuine feedback, against explicit local API fixtures only."""
import asyncio
import json
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright, expect
from mascot_ui_smoke import setup, BASE


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'], executable_path=os.environ.get('RADAR_BROWSER_PATH'))
        for width in [1440, 390]:
            context, mutations = await setup(browser, width, 'business', True)
            page = await context.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            for path, title, slug in [('/projects','Piloter un projet','projets'), ('/devis','Préparer et suivre un devis','devis'), ('/factures','Factures, avoirs et paiements','factures-paiements')]:
                await page.goto(BASE+path, wait_until='networkidle')
                button = page.get_by_role('button', name='Ouvrir l’aide Radar', exact=True)
                await button.click()
                help = page.get_by_role('dialog', name=title, exact=True)
                await expect(help).to_be_visible()
                assert await help.get_by_role('link', name='Lire le guide complet').get_attribute('href')=='/doc/'+slug
                assert await help.locator('ol li').count()>0
                assert await help.evaluate('e=>e.scrollWidth<=innerWidth')
                await page.keyboard.press('Escape')
                await expect(help).to_be_hidden()
                await expect(button).to_be_focused()
            assert not mutations, mutations
            assert not errors, errors
            print(f'{width}px: contextual projects/quotes/invoices help, public docs, keyboard and zero writes OK',flush=True)
            await context.close()

        for status in [201, 403]:
            context, _ = await setup(browser, 1440, 'business', True)
            posted = asyncio.Event()
            release = asyncio.Event()
            writes = []
            async def projects(route):
                if urlparse(route.request.url).path.endswith('/agency/projects') and route.request.method=='POST':
                    writes.append(route.request.post_data_json)
                    posted.set()
                    await release.wait()
                    await route.fulfill(status=status,content_type='application/json',body=json.dumps({'id':99,'name':'TEST — Companion project'} if status==201 else {'detail':'TEST — forbidden'}))
                else:
                    await route.fallback()
            await context.route('**/api/**',projects)
            page=await context.new_page()
            await page.goto(BASE+'/projects',wait_until='networkidle')
            button=page.get_by_role('button',name='Ouvrir l’aide Radar',exact=True)
            await page.get_by_role('button',name='Nouveau projet',exact=True).click()
            await page.get_by_role('button',name='Créer le projet',exact=True).click()
            await expect(button).to_have_attribute('data-radar-reaction','intrigued')
            assert not writes
            await expect(button).to_have_attribute('data-radar-reaction','idle',timeout=5000)
            await page.get_by_placeholder('Ex: Campagne Summer 2025').fill('TEST — Companion project')
            await page.get_by_role('button',name='Créer le projet',exact=True).click()
            await asyncio.wait_for(posted.wait(),5)
            await expect(button).to_have_attribute('data-radar-reaction','idle')
            release.set()
            await expect(button).to_have_attribute('data-radar-reaction','satisfied' if status==201 else 'disappointed')
            await expect(page.get_by_text('Projet créé' if status==201 else 'Le projet n’a pas pu être créé',exact=True)).to_be_visible()
            assert len(writes)==1
            if status==403:
                await expect(page.get_by_placeholder('Ex: Campagne Summer 2025')).to_have_value('TEST — Companion project')
                await expect(page.get_by_text('Projet créé',exact=True)).to_have_count(0)
            await expect(button).to_have_attribute('data-radar-reaction','idle',timeout=5000)
            print(f'Project HTTP {status}: native validation, no early success, real result reaction and reset OK',flush=True)
            await context.close()

        context,_=await setup(browser,1440,'business',True)
        async def discovery(route):
            path=urlparse(route.request.url).path
            if '/discovery/feed/' in path:
                data={'artists':[],'total':0,'page':1,'limit':20,'has_more':False}
            elif path.endswith('/discovery/queue'):
                data={'jobs':[],'running':0,'pending':0,'completed_24h':0}
            elif path.endswith('/discovery/search'):
                assert route.request.method=='POST'
                data={'id':42,'input_value':'TEST Artist','status':'PENDING'}
            else:
                await route.fallback()
                return
            await route.fulfill(status=202 if path.endswith('/discovery/search') else 200,content_type='application/json',body=json.dumps(data))
        await context.route('**/api/**',discovery)
        page=await context.new_page()
        await page.goto(BASE+'/discovery',wait_until='networkidle')
        button=page.get_by_role('button',name='Ouvrir l’aide Radar',exact=True)
        await button.click()
        help=page.get_by_role('dialog',name='Rechercher et enrichir un artiste',exact=True)
        await expect(help).to_contain_text('sources')
        await page.keyboard.press('Escape')
        await page.get_by_placeholder('Rechercher un artiste par nom, URL Spotify ou Viberate...').fill('TEST Artist')
        await page.get_by_role('button',name='Rechercher',exact=True).click()
        await expect(button).to_have_attribute('data-radar-reaction','satisfied')
        await expect(page.get_by_text('Analyse lancée !',exact=True)).to_be_visible()
        # A queue acknowledgement is never presented as completed enrichment.
        assert await page.locator('#radar-main a[href^="/discovery/"]').count()==0
        await page.goto(BASE+'/projects',wait_until='networkidle')
        await expect(page.get_by_role('button',name='Ouvrir l’aide Radar',exact=True)).to_have_attribute('data-radar-reaction','idle')
        print('Discovery: existing Sonner notification, accepted job not completed analysis, route resets feedback OK',flush=True)
        await context.close()

        context,mutations=await setup(browser,390,'core',False)
        page=await context.new_page()
        await page.goto(BASE+'/discovery',wait_until='networkidle')
        await page.get_by_role('button',name='Ouvrir l’aide Radar',exact=True).click()
        help=page.get_by_role('dialog',name='Prendre ses repères',exact=True)
        await expect(help).to_be_visible()
        assert await help.get_by_role('link',name='Lire le guide complet').get_attribute('href')=='/doc/demarrer'
        assert not mutations
        print('Core: unavailable Discovery route uses general help, no bypass or writes OK',flush=True)
        await context.close()
        await browser.close()


if __name__=='__main__':
    asyncio.run(main())
