"""Local-only user administration fixtures; no production account is changed."""

import asyncio, json, os
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright, expect

BASE = os.environ.get("RADAR_UI_BASE_URL", "http://127.0.0.1:3000")
if urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
    raise RuntimeError("User admin fixtures must be local")
OUT = Path("/tmp/radar-admin-users-ui")
OUT.mkdir(exist_ok=True)
ADMIN = dict(
    id=99,
    email="platform@example.com",
    full_name="TEST Super-admin",
    role="viewer",
    is_superuser=True,
    is_collaborator=False,
    is_active=True,
    is_whitelisted=True,
    created_at="2026-11-19T00:00:00",
)
TARGET = dict(
    id=1,
    email="owner@example.com",
    full_name="TEST Client",
    role="pm",
    is_superuser=False,
    is_collaborator=False,
    is_active=True,
    created_at="2026-11-19T00:00:00",
    auth_provider="google",
    linked_accounts=[{"provider": "google", "email": "owner@example.com"}],
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
                "localStorage.setItem('access_token','explicit-users-fixture');localStorage.setItem('cookie-consent',JSON.stringify({version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}))"
            )
            users = [ADMIN.copy(), TARGET.copy()]
            calls = []
            errors = []
            fail_load = True
            fail_update = True

            async def api(route):
                nonlocal fail_load, fail_update
                path = urlparse(route.request.url).path
                method = route.request.method
                body = (
                    route.request.post_data_json
                    if method in {"POST", "PATCH"}
                    else None
                )
                calls.append((method, path, body))
                status = 200
                if path.endswith("/auth/me"):
                    data = users[0]
                elif path.endswith("/auth/password-policy"):
                    data = POLICY
                elif path.endswith("/users/1") and method == "PATCH":
                    assert (
                        "password" not in body
                    ), "An ordinary profile update must not reset a password"
                    if fail_update:
                        fail_update = False
                        status, data = 409, {"detail": "TEST — modification refusée"}
                    else:
                        users[1].update(body)
                        data = users[1]
                elif path.endswith("/users") and method == "POST":
                    assert body["password"] == "New-Test-Password-57!"
                    data = {
                        **body,
                        "id": 2,
                        "is_superuser": False,
                        "created_at": "2026-11-19T00:00:00",
                    }
                    users.append(data)
                    status = 200
                elif path.endswith("/users"):
                    if fail_load:
                        fail_load = False
                        status, data = 503, {"detail": "TEST unavailable"}
                    else:
                        data = users
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
            await page.goto(BASE + "/users", wait_until="networkidle")
            await page.get_by_role("alert").filter(
                has_text="Les comptes n’ont pas pu être chargés"
            ).wait_for()
            await page.get_by_role("button", name="Réessayer", exact=True).click()
            await page.get_by_role(
                "button", name="Modifier TEST Client", exact=True
            ).click()
            dialog = page.get_by_role("dialog")
            await dialog.get_by_role(
                "heading", name="Modifier l’utilisateur", exact=True
            ).wait_for()
            assert await dialog.locator("input[type=password]").count() == 0
            await dialog.get_by_role(
                "switch", name="Compte collaborateur", exact=True
            ).check()
            await dialog.screenshot(path=str(OUT / f"edit-user-{width}.png"))
            await dialog.get_by_role(
                "button", name="Appliquer les modifications", exact=True
            ).click()
            await dialog.get_by_role("alert").filter(
                has_text="TEST — modification refusée"
            ).wait_for()
            assert not users[1]["is_collaborator"]
            await dialog.get_by_role(
                "button", name="Appliquer les modifications", exact=True
            ).click()
            await expect(dialog).not_to_be_visible()
            await page.get_by_label("Mode du compte", exact=True).select_option(
                "collaborator"
            )
            await page.get_by_role("status").filter(
                has_text="1 compte affiché sur 2"
            ).wait_for()
            assert users[1]["is_collaborator"]
            assert await page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth + 1"
            )
            await page.screenshot(path=str(OUT / f"users-{width}.png"), full_page=True)
            await page.get_by_role(
                "button", name="Désactiver TEST Client", exact=True
            ).click()
            await dialog.get_by_role(
                "button", name="Confirmer la désactivation", exact=True
            ).click()
            await expect(dialog).not_to_be_visible()
            assert not users[1]["is_active"]
            await page.get_by_role(
                "button", name="Réactiver TEST Client", exact=True
            ).click()
            await dialog.get_by_role(
                "button", name="Confirmer la réactivation", exact=True
            ).click()
            await expect(dialog).not_to_be_visible()
            await page.get_by_label("Mode du compte", exact=True).select_option("all")
            await page.get_by_role(
                "button", name="Modifier TEST Super-admin", exact=True
            ).click()
            await expect(
                dialog.get_by_role("switch", name="Compte actif", exact=True)
            ).to_be_disabled()
            assert await dialog.locator("input[type=password]").count() == 0
            await dialog.get_by_role(
                "link", name="la sécurité de votre compte", exact=True
            ).wait_for()
            await dialog.get_by_role("button", name="Annuler", exact=True).click()
            await page.get_by_role(
                "button", name="Nouvel utilisateur", exact=True
            ).click()
            await dialog.get_by_label("Nom complet", exact=True).fill(
                "TEST New Account"
            )
            await dialog.get_by_label("Adresse e-mail", exact=True).fill(
                "new@example.com"
            )
            await dialog.get_by_label("Nouveau mot de passe", exact=True).fill(
                "New-Test-Password-57!"
            )
            await dialog.get_by_label(
                "Confirmer le nouveau mot de passe", exact=True
            ).fill("New-Test-Password-57!")
            await dialog.get_by_role(
                "button", name="Créer le compte", exact=True
            ).click()
            await expect(dialog).not_to_be_visible()
            await page.get_by_label("Nom ou adresse e-mail", exact=True).fill(
                "new@example.com"
            )
            await page.get_by_role("status").filter(
                has_text="1 compte affiché sur 3"
            ).wait_for()
            if width == 390:
                await page.evaluate("localStorage.setItem('theme','dark')")
                await page.reload(wait_until="networkidle")
                await expect(page.locator("html")).to_have_class(
                    __import__("re").compile(r".*dark.*")
                )
                await page.get_by_role(
                    "button", name="Modifier TEST Client", exact=True
                ).click()
                await page.get_by_role("dialog").screenshot(
                    path=str(OUT / "edit-user-dark.png")
                )
            assert not errors, errors
            assert all(method != "DELETE" for method, _, _ in calls)
            await context.close()
            print(
                f"PASS users {width}px: filters, explicit collaborator save, error/retry, preserved password, deactivate/reactivate, self protection, create and no overflow"
            )
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
