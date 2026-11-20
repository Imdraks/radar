"""Local fixtures verify selected-ID transport and stale-view/cache isolation on A/B switches."""

import asyncio, json, os
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright, expect

BASE = os.environ.get("RADAR_UI_BASE_URL", "http://127.0.0.1:3000")
if urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
    raise RuntimeError("Workspace fixtures must be local")
USER = {
    "id": 7,
    "full_name": "TEST Collaborator",
    "email": "collaborator@example.com",
    "role": "pm",
    "is_superuser": False,
    "is_collaborator": True,
    "is_active": True,
    "is_whitelisted": True,
    "created_at": "2026-11-19T00:00:00",
}


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=os.environ.get("RADAR_BROWSER_PATH"), args=["--no-sandbox"]
        )
        for width, height in [(1440, 1000), (390, 844)]:
            context = await browser.new_context(
                viewport={"width": width, "height": height}, locale="fr-FR"
            )
            await context.add_init_script(
                "localStorage.setItem('access_token','TEST-switch-only');localStorage.setItem('opportunities-radar-welcome-shown-v2','true');localStorage.setItem('cookie-consent',JSON.stringify({version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}));"
            )
            calls = []
            errors = []

            async def api(route):
                url = urlparse(route.request.url)
                path = url.path
                selected = parse_qs(url.query).get("workspace_id", [""])[0]
                calls.append((path, selected))
                if path.endswith("/auth/me"):
                    data = USER
                elif path.endswith("/auth/account/workspaces"):
                    data = [
                        {"id": 1, "name": "TEST Workspace A", "is_suspended": False},
                        {"id": 2, "name": "TEST Workspace B", "is_suspended": False},
                    ]
                elif path.endswith("/subscription/current"):
                    assert selected in {"1", "2"}
                    data = {
                        "workspace_id": int(selected),
                        "workspace_name": "TEST Workspace "
                        + ("A" if selected == "1" else "B"),
                        "plan": "business",
                        "plan_display_name": "Radar Business",
                        "available_features": ["cockpit", "projects", "clients"],
                        "max_seats": 3,
                        "current_seats": 1,
                    }
                elif path.endswith("/subscription/navigation"):
                    data = {
                        "sections": {
                            "Organisation": [
                                {
                                    "path": "/projects",
                                    "label": "Projets",
                                    "icon": "folder",
                                    "available": True,
                                    "locked": False,
                                    "admin_only": False,
                                }
                            ]
                        }
                    }
                elif path.endswith("/agency/projects"):
                    assert selected in {"1", "2"}
                    if selected == "1":
                        await asyncio.sleep(1.5)
                    label = "A" if selected == "1" else "B"
                    data = [
                        {
                            "id": int(selected) * 10,
                            "name": "TEST Project " + label,
                            "client_id": int(selected) * 100,
                            "client_name": "TEST Client " + label,
                            "status": "active",
                            "deadline": None,
                            "progress_percent": 0,
                            "deliverables_total": 0,
                            "deliverables_approved": 0,
                            "is_urgent": False,
                            "days_until_deadline": None,
                            "budget": None,
                        }
                    ]
                elif path.endswith("/agency/clients") or path.endswith("/agency/deals"):
                    data = []
                elif path.endswith("/agency/dashboard"):
                    data = {
                        "todos": [],
                        "todos_count": 0,
                        "urgencies": [],
                        "urgencies_count": 0,
                        "business": [],
                        "business_count": 0,
                        "active_projects": 1,
                        "pending_validations": 0,
                        "hot_leads": 0,
                        "monthly_revenue": None,
                    }
                elif path.endswith("/workspaces"):
                    data = {
                        "items": [
                            {"id": 1, "name": "TEST Workspace A", "members_count": 1},
                            {"id": 2, "name": "TEST Workspace B", "members_count": 1},
                        ]
                    }
                elif path.endswith("/inbox"):
                    data = {"items": [], "total": 0}
                else:
                    data = []
                await route.fulfill(
                    status=200, content_type="application/json", body=json.dumps(data)
                )

            await context.route("**/api/**", api)
            page = await context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))

            async def select(label):
                await page.get_by_role("listitem").filter(
                    has_text="TEST Workspace " + label
                ).get_by_role("button", name="Ouvrir l’espace", exact=True).click()
                await page.wait_for_url("**/today")
                if width < 1024:
                    await page.get_by_role(
                        "button", name="Ouvrir le menu", exact=True
                    ).click()
                await page.get_by_role("link", name="Projets", exact=True).click()
                await page.wait_for_url("**/projects")

            async def picker():
                if width < 1024:
                    await page.get_by_role(
                        "button", name="Ouvrir le menu", exact=True
                    ).click()
                await page.get_by_role(
                    "link", name="Changer de workspace", exact=True
                ).click()
                await page.wait_for_url("**/account/workspaces")

            await page.goto(BASE + "/account/workspaces", wait_until="networkidle")
            await select("B")
            await page.get_by_text("TEST Project B", exact=True).wait_for()
            assert not await page.get_by_text("TEST Project A", exact=True).count()
            initial_projects = [
                id for path, id in calls if path.endswith("/agency/projects")
            ]
            assert initial_projects and set(initial_projects) == {"2"}, initial_projects
            await picker()
            async with page.expect_request(
                lambda request: urlparse(request.url).path.endswith("/agency/projects")
                and parse_qs(urlparse(request.url).query).get("workspace_id") == ["1"]
            ):
                await select("A")
            await picker()
            await select("B")
            await page.get_by_text("TEST Project B", exact=True).wait_for()
            await page.wait_for_timeout(1800)
            assert not await page.get_by_text("TEST Project A", exact=True).count()
            assert (
                await page.evaluate("localStorage.getItem('current_workspace_id')")
                == "2"
            )
            assert [id for path, id in calls if path.endswith("/agency/projects")][
                -1
            ] == "2"
            assert not errors, errors
            await context.close()
            print(
                f"PASS workspace switch {width}px: cold B, client-side B/A/B, scoped requests and late A response never shown in B"
            )
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
