"""Explicit local fixtures for search, templates, integration states and external review."""

import asyncio, json, os
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright, expect

BASE = os.environ.get("RADAR_UI_BASE_URL", "http://127.0.0.1:3000")
if urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
    raise RuntimeError("Local fixtures only")
OUT = Path("/tmp/radar-workflows-ui")
OUT.mkdir(exist_ok=True)
USER = {
    "id": 7,
    "full_name": "TEST Owner",
    "email": "owner@example.com",
    "role": "pm",
    "is_active": True,
    "is_whitelisted": True,
    "is_superuser": False,
}


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
                "localStorage.setItem('access_token','TEST-workflows');localStorage.setItem('current_workspace_id','1');localStorage.setItem('opportunities-radar-welcome-shown-v2','true');localStorage.setItem('cookie-consent',JSON.stringify({version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}));"
            )
            templates = []
            errors = []
            made = []
            fail = True

            async def api(route):
                nonlocal fail
                url = urlparse(route.request.url)
                path = url.path
                status = 200
                if path.endswith("/auth/me"):
                    data = USER
                elif path.endswith("/subscription/current"):
                    data = {
                        "workspace_id": 1,
                        "workspace_name": "TEST Workspace",
                        "plan": "premium",
                        "plan_display_name": "Radar Premium",
                        "available_features": [
                            "cockpit",
                            "projects",
                            "production",
                            "events",
                            "discovery",
                            "assets",
                        ],
                        "max_seats": 10,
                        "current_seats": 1,
                    }
                elif path.endswith("/subscription/navigation"):
                    data = {
                        "sections": {
                            "Organisation": [
                                {
                                    "path": "/templates",
                                    "label": "Modèles de production",
                                    "icon": "FolderOpen",
                                    "available": True,
                                    "locked": False,
                                    "admin_only": False,
                                }
                            ]
                        }
                    }
                elif path.endswith("/workbench/templates"):
                    assert parse_qs(url.query).get("workspace_id") == ["1"]
                    if route.request.method == "POST":
                        body = route.request.post_data_json
                        assert body["definition"]["tasks"] == [
                            {"title": "Brief", "day": -2}
                        ]
                        templates.append({"id": 1, **body})
                        data = templates[0]
                        status = 201
                    elif fail:
                        status = 503
                        data = {"detail": "TEST indisponible"}
                    else:
                        data = templates
                elif path.endswith("/workbench/templates/1/instantiate"):
                    made.append(route.request.post_data_json)
                    data = {"url": "/events/42", "event_id": 42, "project_id": 12}
                    status = 201
                elif path.endswith("/workbench/search"):
                    assert parse_qs(url.query).get("workspace_id") == ["1"]
                    data = [
                        {
                            "id": "12",
                            "kind": "project",
                            "name": "TEST Production",
                            "url": "/projects/12",
                        }
                    ]
                elif path.endswith("/integrations/status"):
                    data = {
                        "checked_at": "2026-11-20T12:00:00",
                        "notice": "Configuration seule : aucun succès fournisseur présumé.",
                        "providers": [
                            {
                                "id": "spotify",
                                "name": "Spotify",
                                "state": "configured_unverified",
                                "scope": "plateforme",
                            },
                            {
                                "id": "drive",
                                "name": "Google Drive",
                                "state": "authorization_expired",
                                "scope": "mon compte",
                            },
                        ],
                        "observations": [],
                        "jobs": [],
                    }
                elif path.endswith("/review/resolve"):
                    data = {
                        "name": "TEST Film",
                        "link": "https://example.com/film",
                        "status": "pending",
                        "expires_at": "2026-11-27T12:00:00",
                    }
                elif path.endswith("/review/decide"):
                    assert (
                        route.request.post_data_json["feedback"] == "Changer le titre"
                    )
                    data = {"status": "changes"}
                else:
                    data = []
                await route.fulfill(
                    status=status,
                    content_type="application/json",
                    body=json.dumps(data),
                )

            await context.route("**/api/**", api)
            page = await context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(BASE + "/templates", wait_until="networkidle")
            fail = False
            await page.get_by_role("button", name="Réessayer", exact=True).click()
            await page.get_by_label("Nom du modèle", exact=True).fill("TEST Concert")
            await page.get_by_label("Usage", exact=True).select_option("event")
            await page.get_by_label("Tâches · une par ligne").fill("Brief | -2")
            await page.get_by_role("button", name="Enregistrer le modèle").click()
            await page.get_by_role("button", name="Utiliser ce modèle").click()
            await page.get_by_label("Démarrage · UTC", exact=True).fill(
                "2026-11-20T12:00"
            )
            await page.get_by_label("Fin · UTC", exact=True).fill("2026-11-20T23:00")
            await page.screenshot(
                path=str(OUT / f"templates-{width}.png"), full_page=True
            )
            await page.get_by_role("button", name="Créer la production").click()
            await page.wait_for_url("**/events/42")
            assert made[-1]["starts_at"] == "2026-11-20T12:00:00"
            await page.goto(BASE + "/integrations", wait_until="networkidle")
            await expect(
                page.get_by_text("Configuré · disponibilité à vérifier", exact=True)
            ).to_be_visible()
            await expect(
                page.get_by_text(
                    "Autorisation expirée · reconnexion possible", exact=True
                )
            ).to_be_visible()
            await page.get_by_role(
                "button", name="Rechercher dans cet espace", exact=True
            ).click()
            await page.get_by_label("Votre recherche", exact=True).fill("Production")
            await page.get_by_role("button", name="Rechercher", exact=True).click()
            await expect(
                page.get_by_role("link", name="Projet TEST Production", exact=False)
            ).to_be_visible()
            await page.keyboard.press("Escape")
            assert await page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth"
            ), f"Overflow at {width}"
            await page.goto(
                BASE + "/review#token=" + "x" * 43, wait_until="networkidle"
            )
            assert "#" not in page.url
            await page.get_by_label("Votre nom", exact=True).fill("TEST Client")
            await page.get_by_label("Votre retour", exact=True).fill("Changer le titre")
            await page.get_by_role(
                "button", name="Demander des modifications", exact=True
            ).click()
            await expect(
                page.get_by_text(
                    "Votre demande de modifications a été enregistrée.", exact=True
                )
            ).to_be_visible()
            await page.screenshot(path=str(OUT / f"review-{width}.png"), full_page=True)
            assert not errors, errors
            await context.close()
            print(
                f"PASS workflows {width}px: errors, templates, relative deadlines, integration honesty, scoped search, review and fragment removal",
                flush=True,
            )
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
