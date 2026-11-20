"""Explicit local fixtures for the activity journal; never contacts production."""

import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright, expect

BASE = os.environ.get("RADAR_UI_BASE_URL", "http://127.0.0.1:3000")
if urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
    raise RuntimeError("Journal fixtures require localhost")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=os.environ.get("RADAR_BROWSER_PATH"), args=["--no-sandbox"]
        )
        for width in [1440, 390, 320]:
            context = await browser.new_context(
                viewport={"width": width, "height": 960}, locale="fr-FR"
            )
            await context.add_init_script(
                "localStorage.setItem('access_token','explicit-journal-fixture');localStorage.setItem('cookie-consent',JSON.stringify({version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}))"
            )
            fail = True
            queries = []

            async def api(route):
                nonlocal fail
                url = urlparse(route.request.url)
                status = 200
                if url.path.endswith("/auth/me"):
                    data = dict(
                        id=99,
                        full_name="TEST Admin",
                        email="admin@example.com",
                        role="viewer",
                        is_superuser=True,
                        is_active=True,
                        is_whitelisted=True,
                    )
                elif url.path.endswith("/logs/filters"):
                    data = dict(
                        authors=[
                            dict(id=1, name="TEST Client", email="client@example.com")
                        ],
                        actions=["client.deleted", "contact.opened"],
                        resource_types=["workspace"],
                    )
                elif url.path.endswith("/logs/search"):
                    queries.append(parse_qs(url.query))
                    if fail:
                        status, data = 503, {"detail": "TEST — journal indisponible"}
                    else:
                        params = parse_qs(url.query)
                        page = int(params.get("page", ["1"])[0])
                        empty = params.get("q") == ["introuvable"]
                        data = dict(
                            items=(
                                []
                                if empty
                                else [
                                    dict(
                                        id=str(page),
                                        user_id=1,
                                        user_tracking_id="TEST001",
                                        user_name="TEST Client",
                                        user_email="client@example.com",
                                        action=(
                                            "client.deleted"
                                            if page == 1
                                            else "contact.opened"
                                        ),
                                        resource_type="workspace",
                                        resource_id="42",
                                        created_at="2026-11-20T10:00:00",
                                        details={
                                            "reason": "<script>TEST</script>",
                                            "token": "[credential excluded]",
                                        },
                                        ip_address="127.0.0.1",
                                    )
                                ]
                            ),
                            total=0 if empty else 26,
                            page=page,
                            limit=25,
                            summary=dict(
                                authors=0 if empty else 1, logins=0, last_event_at=None
                            ),
                        )
                else:
                    data = []
                await route.fulfill(
                    status=status,
                    content_type="application/json",
                    body=json.dumps(data),
                )

            await context.route("**/api/**", api)
            page = await context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(BASE + "/admin/activity", wait_until="networkidle")
            await page.get_by_role("button", name="Réessayer", exact=True).wait_for()
            assert not await page.get_by_role(
                "switch", name="Actualisation automatique"
            ).is_checked()
            fail = False
            await page.get_by_role("button", name="Réessayer", exact=True).click()
            await page.get_by_role(
                "button", name="Détails : Espace retiré du produit", exact=True
            ).click()
            dialog = page.get_by_role("dialog")
            await expect(dialog.locator("pre")).to_contain_text("<script>TEST</script>")
            await expect(dialog.locator("pre")).to_contain_text("[credential excluded]")
            await page.keyboard.press("Escape")
            await page.get_by_role("button", name="Suivant", exact=True).click()
            await expect(page.get_by_text("Page 2 sur 2", exact=False)).to_be_visible()
            await page.get_by_label("Période", exact=True).select_option("custom")
            before = len(queries)
            await page.get_by_role("button", name="Appliquer les filtres").click()
            await expect(
                page.get_by_role("alert").filter(has_text="Renseignez les deux dates")
            ).to_contain_text("Renseignez les deux dates")
            assert len(queries) == before
            await page.get_by_role("button", name="Réinitialiser").click()
            await expect(page.get_by_text("Page 1 sur 2", exact=False)).to_be_visible()
            fail = True
            await page.get_by_role("button", name="Actualiser", exact=True).click()
            await expect(
                page.get_by_role("alert").filter(has_text="L’actualisation a échoué")
            ).to_contain_text(
                "Les données du dernier chargement réussi restent affichées"
            )
            await expect(
                page.get_by_role("button", name="Détails : Espace retiré du produit")
            ).to_be_visible()
            fail = False
            await page.get_by_role("button", name="Réessayer", exact=True).click()
            await page.get_by_label("Nom, e-mail, action ou identifiant").fill(
                "introuvable"
            )
            await page.get_by_role("button", name="Appliquer les filtres").click()
            await expect(
                page.get_by_text("Aucun événement pour ces critères", exact=True)
            ).to_be_visible()
            await page.get_by_role("button", name="Réinitialiser").click()
            await expect(
                page.get_by_role("button", name="Détails : Espace retiré du produit")
            ).to_be_visible()
            await page.screenshot(
                path=f"/tmp/activity-{width}-light.png", full_page=True
            )
            await page.evaluate("document.documentElement.classList.add('dark')")
            await page.screenshot(
                path=f"/tmp/activity-{width}-dark.png", full_page=True
            )
            assert await page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            ), f"Horizontal overflow at {width}"
            await page.screenshot(
                path=f"/tmp/radar-activity-{width}.png", full_page=True
            )
            assert not errors, errors
            print(
                f"PASS activity journal {width}px: errors, filters, paging, details, stale data, dark theme",
                flush=True,
            )
            await context.close()
        await browser.close()


asyncio.run(main())
