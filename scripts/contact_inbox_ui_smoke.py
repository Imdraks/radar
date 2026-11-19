"""Explicit local inbox fixtures; no real request, email or worker is used."""

import asyncio, json, os
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright, expect

BASE = os.environ.get("RADAR_UI_BASE_URL", "http://127.0.0.1:3000")
if urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
    raise RuntimeError("Contact inbox fixtures must be local")
OUT = Path("/tmp/radar-contact-inbox-ui")
OUT.mkdir(exist_ok=True)
ID = "00000000-0000-4000-8000-000000000001"
ADMIN = {
    "id": 99,
    "email": "platform@example.com",
    "full_name": "TEST Platform",
    "role": "viewer",
    "is_superuser": True,
    "is_active": True,
    "is_whitelisted": True,
    "created_at": "2026-11-19T00:00:00",
}


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=os.environ.get("RADAR_BROWSER_PATH"), args=["--no-sandbox"]
        )
        for width, height in [(1440, 1000), (390, 844), (320, 740)]:
            context = await browser.new_context(
                viewport={"width": width, "height": height}, locale="fr-FR"
            )
            await context.add_init_script(
                "localStorage.setItem('access_token','explicit-inbox-fixture');localStorage.setItem('cookie-consent',JSON.stringify({version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}))"
            )
            row = {
                "id": ID,
                "name": "TEST Client",
                "email": "visitor@example.com",
                "company": "TEST Agency",
                "phone": "0102030405",
                "plan": "premium",
                "message": "TEST besoin réel <script>window.inquiryAttack=true</script>",
                "status": "new",
                "created_at": "2026-11-19T00:00:00",
                "opened_at": None,
                "acknowledgement_status": "not_requested",
                "privacy_notice_version": "2026-11-13",
            }
            queued = 0
            errors = []

            async def api(route):
                nonlocal queued
                path = urlparse(route.request.url).path
                method = route.request.method
                if path.endswith("/auth/me"):
                    data = ADMIN
                elif path.endswith("/admin/contact-requests/count"):
                    data = {"new_count": int(row["status"] == "new")}
                elif path.endswith("/admin/contact-requests"):
                    data = {
                        "items": [row],
                        "total": 1,
                        "new_count": int(row["status"] == "new"),
                        "page": 1,
                        "limit": 25,
                    }
                elif path.endswith("/" + ID + "/open"):
                    if not row["opened_at"]:
                        row.update(
                            status="opened",
                            opened_at="2026-11-19T12:00:00",
                            opened_by=99,
                            acknowledgement_status="pending",
                        )
                        queued += 1
                    data = row
                elif path.endswith("/" + ID + "/retry-acknowledgement"):
                    assert row["acknowledgement_status"] == "failed"
                    row["acknowledgement_status"] = "pending"
                    queued += 1
                    data = row
                elif path.endswith("/" + ID) and method == "PATCH":
                    row["status"] = route.request.post_data_json["status"]
                    data = row
                else:
                    data = []
                await route.fulfill(
                    status=200, content_type="application/json", body=json.dumps(data)
                )

            await context.route("**/api/**", api)
            page = await context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(BASE + "/admin/contact-requests", wait_until="networkidle")
            await page.get_by_role(
                "heading", name="Demandes de contact", exact=True
            ).wait_for()
            assert queued == 0
            await page.get_by_role("link", name="Ouvrir le dossier", exact=True).click()
            await page.get_by_role("heading", name="TEST Client", exact=True).wait_for()
            await page.get_by_role("status").filter(
                has_text="En attente du service d’envoi"
            ).wait_for()
            assert queued == 1
            assert await page.evaluate("window.inquiryAttack") is None
            await page.get_by_text(row["message"], exact=True).wait_for()
            assert await page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth + 1"
            )
            row["acknowledgement_status"] = "failed"
            await page.get_by_role(
                "button", name="Actualiser l’état", exact=True
            ).click()
            await page.get_by_role(
                "button", name="Relancer l’accusé d’ouverture", exact=True
            ).click()
            await page.get_by_role("status").filter(
                has_text="En attente du service d’envoi"
            ).wait_for()
            assert queued == 2
            row["acknowledgement_status"] = "sent"
            row["acknowledgement_sent_at"] = "2026-11-19T12:01:00"
            await page.get_by_role(
                "button", name="Actualiser l’état", exact=True
            ).click()
            await page.get_by_role("status").filter(
                has_text="Transmis au service d’envoi"
            ).wait_for()
            assert not await page.get_by_role(
                "button", name="Relancer l’accusé d’ouverture", exact=True
            ).count()
            await page.get_by_role(
                "button", name="Clôturer le dossier", exact=True
            ).click()
            await page.get_by_role(
                "button", name="Rouvrir le dossier", exact=True
            ).click()
            assert queued == 2
            await page.screenshot(
                path=str(OUT / f"dossier-{width}.png"), full_page=True
            )
            await page.goto(BASE + "/admin/contact-requests", wait_until="networkidle")
            await page.get_by_role("link", name="Ouvrir le dossier", exact=True).click()
            await page.get_by_role("heading", name="TEST Client", exact=True).wait_for()
            assert queued == 2
            assert not errors, errors
            await context.close()
            print(
                f"PASS inbox {width}px: first opening, honest async status, controlled retry, no repeat on revisit, close/reopen, escaped content"
            )
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
