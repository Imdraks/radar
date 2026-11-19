"""Local browser regressions using explicit fixtures; never sends a real invitation."""

import asyncio, json, os
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright, expect

BASE = os.environ.get("RADAR_UI_BASE_URL", "http://127.0.0.1:3000")
if urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
    raise RuntimeError("Admin fixtures must remain local")
OUT = Path("/tmp/radar-admin-clients-ui")
OUT.mkdir(exist_ok=True)
USER = dict(
    id=99,
    full_name="TEST Platform",
    email="platform@example.com",
    role="viewer",
    is_superuser=True,
    is_active=True,
    is_whitelisted=True,
    created_at="2026-11-19T00:00:00",
)
OWNER = dict(
    user_id=1,
    name="TEST Owner",
    email="owner@example.com",
    must_change_password=True,
    is_active=True,
)
CLIENT = dict(
    id=1,
    name="TEST agence",
    owner_user_id=1,
    owner_name=OWNER["name"],
    owner_email=OWNER["email"],
    owner_last_login_at=None,
    plan="core",
    plan_display_name="Radar Core",
    max_seats=3,
    current_seats=1,
    is_suspended=False,
    suspension_reason=None,
    suspended_at=None,
    pending_orders=1,
    created_at="2026-11-19T00:00:00",
    plan_expires_at=None,
    company={},
    owner=OWNER,
    members=[],
    invitations=[],
    orders=[],
    acceptances=[],
    history=[],
    subscription={"available_features": []},
    integrations={"drive_url": None, "calendar_id": None},
    quotes=[],
    external_contracts=[],
)
POLICY = dict(
    min_length=12,
    max_bytes=72,
    uppercase=True,
    lowercase=True,
    digit=True,
    special=True,
    reset_expiry_minutes=15,
)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=os.environ.get("RADAR_BROWSER_PATH"), args=["--no-sandbox"]
        )
        for width, height in [(1440, 1000), (768, 1024), (390, 844), (320, 740)]:
            context = await browser.new_context(
                viewport={"width": width, "height": height}, locale="fr-FR"
            )
            await context.add_init_script(
                "localStorage.setItem('access_token','explicit-admin-fixture');localStorage.setItem('cookie-consent',JSON.stringify({version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}));localStorage.setItem('opportunities-radar-welcome-shown-v2','true')"
            )
            user = USER.copy()
            detail = json.loads(json.dumps(CLIENT))
            calls = []
            errors = []
            fail_creation = True

            async def api(route):
                nonlocal fail_creation
                path = urlparse(route.request.url).path
                method = route.request.method
                status = 200
                body = (
                    route.request.post_data_json
                    if method in {"POST", "PATCH"}
                    else None
                )
                calls.append((method, path, body))
                if path.endswith("/auth/me"):
                    data = user
                elif path.endswith("/auth/password-policy"):
                    data = POLICY
                elif path.endswith("/auth/password/status"):
                    data = {"has_password": True}
                elif path.endswith("/auth/mfa/reauth/start"):
                    data = {
                        "requires_2fa": False,
                        "management_token": "explicit-management-fixture",
                    }
                elif path.endswith("/auth/password/change"):
                    user["must_change_password"] = False
                    data = {
                        "access_token": "fixture-new-access",
                        "refresh_token": "fixture-new-refresh",
                        "message": "Mot de passe modifié.",
                    }
                elif path.endswith("/auth/mfa/status"):
                    data = {
                        "enabled": False,
                        "methods": [],
                        "destinations": {},
                        "available": {"totp": True, "email": True, "sms": False},
                        "has_backup_codes": False,
                    }
                elif path.endswith("/auth/account/setup/complete"):
                    assert not user.get("must_change_password")
                    user["security_setup_pending"] = False
                    data = {"completed": True}
                elif path.endswith("/auth/account/workspaces"):
                    data = [{"id": 1, "name": detail["name"], "is_suspended": False}]
                elif path.endswith("/auth/setup-check"):
                    data = {"needs_setup": False}
                elif path.endswith("/admin/clients") and method == "POST":
                    if fail_creation:
                        status, data = 503, {"detail": "TEST — envoi non configuré"}
                        fail_creation = False
                    else:
                        data = {
                            **detail,
                            "invitation": {"id": "fixture", "status": "pending"},
                        }
                elif path.endswith("/admin/clients"):
                    data = {"items": [detail], "total": 1, "page": 1, "limit": 25}
                elif path.endswith("/admin/clients/1/suspension"):
                    detail["is_suspended"] = body["suspended"]
                    detail["suspension_reason"] = body["reason"]
                    data = {"updated": True}
                elif path.endswith("/admin/clients/1/quotes"):
                    assert body["lines"] == [
                        {
                            "description": "TEST accompagnement",
                            "quantity": "2",
                            "unit_price": "150",
                            "vat_rate": "20",
                        }
                    ]
                    detail["quotes"] = [
                        {
                            "id": 7,
                            "reference": "RAD-DEV-2026-000007",
                            "status": "draft",
                            "total_ht": "300.00",
                            "total_tax": "60.00",
                            "total_ttc": "360.00",
                            "valid_until": "2027-12-31",
                            "created_at": "2026-11-19T00:00:00",
                            "order_id": None,
                        }
                    ]
                    data = detail["quotes"][0]
                    status = 201
                elif path.endswith("/quotes/7/pdf"):
                    await route.fulfill(
                        status=200,
                        content_type="application/pdf",
                        body=b"%PDF-1.4\n%explicit-browser-fixture\n",
                    )
                    return
                elif path.endswith("/admin/clients/1"):
                    data = detail
                elif path.endswith("/subscription/navigation"):
                    data = {"sections": {}}
                elif path.endswith("/subscription/current"):
                    data = {
                        "workspace_id": 1,
                        "plan": "core",
                        "plan_display_name": "Radar Core",
                        "available_features": [],
                        "max_seats": 3,
                        "current_seats": 1,
                    }
                elif path.endswith("/agency/dashboard"):
                    data = {
                        "todos": [],
                        "todos_count": 0,
                        "urgencies": [],
                        "urgencies_count": 0,
                        "business": [],
                        "business_count": 0,
                        "active_projects": 0,
                        "pending_validations": 0,
                        "hot_leads": None,
                        "monthly_revenue": None,
                    }
                elif path.endswith("/workspaces"):
                    data = {
                        "items": [{"id": 1, "name": "TEST agence", "members_count": 1}]
                    }
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
            await page.goto(BASE + "/admin/clients", wait_until="networkidle")
            await page.get_by_role(
                "heading", name="Entreprises clientes", exact=True
            ).wait_for()
            assert await page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth + 1"
            )
            await page.get_by_role(
                "button", name="Créer une entreprise", exact=True
            ).click()
            dialog = page.get_by_role("dialog")
            await dialog.get_by_label("Nom de l’entreprise", exact=True).fill(
                "TEST agence"
            )
            await dialog.get_by_label("Nom du responsable", exact=True).fill(
                "TEST Owner"
            )
            await dialog.get_by_label("E-mail du responsable", exact=True).fill(
                "owner@example.com"
            )
            await dialog.get_by_role(
                "button", name="Créer et inviter", exact=True
            ).click()
            await dialog.get_by_role("alert").filter(
                has_text="TEST — envoi non configuré"
            ).wait_for()
            assert await dialog.is_visible()
            await dialog.get_by_role("button", name="Annuler", exact=True).click()
            await page.goto(BASE + "/admin/clients/1", wait_until="networkidle")
            await page.get_by_role(
                "heading", name=CLIENT["name"], exact=True
            ).wait_for()
            for tab in [
                "Équipe et invitations",
                "Commandes et accès",
                "Devis et contrats",
                "Historique",
                "Vue d’ensemble",
            ]:
                await page.get_by_role("tab", name=tab, exact=True).click()
                assert await page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth + 1"
                ), (width, tab)
            await page.get_by_role("button", name="Créer un devis", exact=True).click()
            dialog = page.get_by_role("dialog")
            await dialog.get_by_label("Valable jusqu’au", exact=True).fill("2027-12-31")
            for label, value in [
                ("Prestation 1", "TEST accompagnement"),
                ("Quantité", "2"),
                ("Prix unitaire HT (€)", "150"),
                ("TVA (%)", "20"),
            ]:
                await dialog.get_by_label(label, exact=True).fill(value)
            await dialog.get_by_label(
                "Durée, règlement et conditions", exact=True
            ).fill("TEST règlement et durée convenus manuellement.")
            await dialog.get_by_role(
                "button", name="Créer le devis", exact=True
            ).click()
            await expect(dialog).not_to_be_visible()
            await page.get_by_role("tab", name="Devis et contrats", exact=True).click()
            async with page.expect_download() as downloaded:
                await page.get_by_role(
                    "button", name="Télécharger le PDF", exact=True
                ).click()
            download = await downloaded.value
            assert download.suggested_filename.endswith(".pdf")
            await download.save_as(OUT / f"quote-{width}.pdf")
            await page.screenshot(
                path=str(OUT / f"documents-{width}.png"), full_page=True
            )
            # A platform role alone must never bypass the explicit superuser check.
            user["is_superuser"] = False
            await page.goto(BASE + "/admin/clients", wait_until="domcontentloaded")
            await page.wait_for_url("**/today")
            # Mandatory credential replacement precedes the optional factor step.
            user.update(must_change_password=True, security_setup_pending=True)
            await page.goto(BASE + "/account/workspaces", wait_until="networkidle")
            await page.wait_for_url("**/account/setup")
            await page.get_by_role(
                "heading", name="Choisissez votre mot de passe.", exact=True
            ).wait_for()
            assert not await page.get_by_role(
                "button", name="Plus tard", exact=True
            ).count()
            for label, value in [
                ("Ancien mot de passe Radar", "Temporary-Password-42!"),
                ("Nouveau mot de passe", "New-Password-57!"),
                ("Confirmer le nouveau mot de passe", "New-Password-57!"),
            ]:
                await page.get_by_label(label, exact=True).fill(value)
            await page.get_by_role(
                "button", name="Continuer pour changer le mot de passe", exact=True
            ).click()
            await page.get_by_role("button", name="Plus tard", exact=True).wait_for()
            await page.get_by_role("button", name="Plus tard", exact=True).click()
            await page.wait_for_url("**/account/workspaces")
            assert any(
                path.endswith("/auth/account/setup/complete")
                and body == {"security": "later"}
                for _, path, body in calls
            )
            assert not errors, errors
            await context.close()
            print(f"PASS admin + quote download + first login: {width}px")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
