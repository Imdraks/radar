"""Local-only legal workflow browser regression. Every server response is an explicit fixture."""

import asyncio, json, os, io
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile
from playwright.async_api import async_playwright, expect

BASE = os.environ.get("RADAR_UI_BASE_URL", "http://127.0.0.1:3000")
if urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
    raise RuntimeError("Legal fixtures only target a local test instance")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--no-sandbox"], executable_path=os.environ.get("RADAR_BROWSER_PATH")
        )
        for width, height in [(1440, 1000), (390, 844)]:
            context = await browser.new_context(
                viewport={"width": width, "height": height}, locale="fr-FR"
            )
            await context.add_init_script(
                "localStorage.setItem('access_token','TEST-UI-ONLY');localStorage.setItem('current_workspace_id','1');localStorage.setItem('opportunities-radar-welcome-shown-v2','true');localStorage.setItem('cookie-consent',JSON.stringify({version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}))"
            )
            bundle = {
                "id": 7,
                "version": "TEST-2026.1",
                "content_hash": "a" * 64,
                "publisher": {"name": "TEST publisher"},
                "published_at": "2026-11-13T12:00:00",
                "documents": {
                    k: ("TEST — fixture de contrat, ne pas publier. " * 5)
                    for k in [
                        "sales_terms",
                        "dpa",
                        "retention",
                        "reversibility",
                        "security",
                        "subprocessors",
                    ]
                },
            }
            proofs = []
            notes = []
            requests = []
            decided = False
            invoice = {
                "id": 10,
                "reference": "FAC-2026-0001",
                "title": "TEST invoice",
                "status": "SENT",
                "issue_date": "2026-11-13",
                "due_date": "2026-12-13",
                "client_id": None,
                "subtotal": 100,
                "tax_rate": 20,
                "tax_amount": 20,
                "discount_percent": 0,
                "discount_amount": 0,
                "total": 120,
                "amount_paid": 0,
                "credited_at": None,
                "items": [
                    {
                        "id": 1,
                        "description": "TEST service",
                        "quantity": 1,
                        "unit_price": 100,
                        "line_total": 100,
                        "unit": "jour",
                        "position": 0,
                    }
                ],
                "created_at": "2026-11-13T12:00:00",
                "updated_at": "2026-11-13T12:00:00",
            }

            async def api(route):
                nonlocal decided
                path = urlparse(route.request.url).path
                method = route.request.method
                if method == "POST":
                    body = route.request.post_data_json
                    requests.append((path, body))
                    if path.endswith("/legal-contracts/acceptances"):
                        proofs.append(
                            {
                                "id": 12,
                                "bundle_id": 7,
                                "plan": body["plan"],
                                "commercial_reference": body["commercial_reference"],
                                "representative": {"email": "TEST@radar.example"},
                                "accepted_at": "2026-11-13T12:00:00",
                            }
                        )
                        data = {
                            **proofs[-1],
                            "rights_activated": False,
                            "payment_confirmed": False,
                        }
                    elif path.endswith("/credit-notes"):
                        notes.append(
                            {
                                "id": 3,
                                "reference": "AVO-2026-0001",
                                "reason": body["reason"],
                                "total": "120.00",
                            }
                        )
                        invoice["credited_at"] = "2026-11-13T12:00:00"
                        data = notes[-1]
                    elif path.endswith("/decision"):
                        decided = True
                        data = {"status": "approved"}
                    elif path.endswith("/admin/publish"):
                        data = bundle
                    else:
                        raise AssertionError("Unspecified fixture mutation " + path)
                    await route.fulfill(
                        status=201,
                        content_type="application/json",
                        body=json.dumps(data),
                    )
                    return
                if path.endswith("/auth/me"):
                    data = {
                        "id": 1,
                        "email": "TEST@radar.example",
                        "full_name": "TEST operator",
                        "role": "admin",
                        "is_superuser": True,
                        "is_active": True,
                        "is_whitelisted": True,
                        "created_at": "2026-01-01T00:00:00",
                    }
                elif path.endswith("/workspaces"):
                    data = {
                        "items": [
                            {
                                "id": 1,
                                "name": "TEST legal workspace",
                                "role": "admin",
                                "members_count": 1,
                            }
                        ]
                    }
                elif path.endswith("/subscription/current"):
                    data = {
                        "workspace_id": 1,
                        "workspace_name": "TEST legal workspace",
                        "plan": "business",
                        "plan_display_name": "Radar Business",
                        "available_features": ["invoices", "quotes", "cockpit"],
                        "enabled_packs": [],
                        "addons": [],
                        "max_seats": 3,
                        "current_seats": 1,
                    }
                elif path.endswith("/subscription/navigation"):
                    data = {"sections": {}}
                elif path.endswith("/subscription/admin/requests"):
                    data = (
                        []
                        if decided
                        else [
                            {
                                "id": 4,
                                "workspace_id": 1,
                                "kind": "plan",
                                "requested_value": "business",
                                "status": "pending",
                            }
                        ]
                    )
                elif (
                    "/legal-contracts/current" in path
                    or "/legal-contracts/versions/" in path
                ):
                    data = bundle
                elif path.endswith("/legal-contracts/acceptances") or path.endswith(
                    "/legal-contracts/admin/acceptances"
                ):
                    data = proofs
                elif path.endswith("/privacy/requests"):
                    data = []
                elif path.endswith("/privacy/retention-inventory"):
                    data = {
                        "datasets": [
                            {
                                "label": "Projets",
                                "count": 2,
                                "oldest_record_at": "2026-01-01T00:00:00",
                            }
                        ],
                        "automatic_erasure_enabled": False,
                    }
                elif path.endswith("/privacy/workspace-export"):
                    output = io.BytesIO()
                    with ZipFile(output, "w") as z:
                        z.writestr("manifest.json", '{"fixture":true}')
                    await route.fulfill(
                        status=200,
                        content_type="application/zip",
                        body=output.getvalue(),
                    )
                    return
                elif path.endswith("/billing/invoices/10"):
                    # Exercise an actual delayed refetch after the successful credit response.
                    if invoice["credited_at"]:
                        await asyncio.sleep(0.15)
                    data = invoice
                elif path.endswith("/billing/invoices/10/credit-notes"):
                    data = notes
                elif path.endswith("/billing/credit-notes/3/pdf"):
                    await route.fulfill(
                        status=200,
                        content_type="application/pdf",
                        body=b"%PDF-TEST-FIXTURE",
                    )
                    return
                else:
                    data = []
                await route.fulfill(
                    status=200, content_type="application/json", body=json.dumps(data)
                )

            await context.route("**/api/**", api)
            page = await context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(BASE + "/contracts?version=7", wait_until="networkidle")
            await page.get_by_role(
                "button", name="Télécharger cette version", exact=True
            ).wait_for()
            async with page.expect_download() as contract_download:
                await page.get_by_role(
                    "button", name="Télécharger cette version", exact=True
                ).click()
            contract_file = await contract_download.value
            assert (
                contract_file.suggested_filename == "radar-contracts-TEST-2026.1.json"
            )
            downloaded = json.loads(Path(await contract_file.path()).read_text())
            assert downloaded["documents"] == bundle["documents"]
            assert await page.get_by_text("TEST publisher", exact=False).count() > 0
            assert await page.evaluate(
                "document.documentElement.scrollWidth<=innerWidth"
            )
            await page.goto(BASE + "/settings/contracts", wait_until="networkidle")
            await page.get_by_label("Offre concernée", exact=True).select_option(
                "business"
            )
            await page.get_by_label(
                "Référence de l’offre ou du bon de commande", exact=True
            ).fill("TEST-OFFER-1")
            await page.get_by_role(
                "button", name="Enregistrer mon acceptation", exact=True
            ).click()
            assert not proofs
            await page.get_by_role("checkbox").check()
            await page.get_by_role(
                "button", name="Enregistrer mon acceptation", exact=True
            ).click()
            await page.get_by_text(
                "Acceptation n°12 enregistrée.", exact=False
            ).wait_for()
            assert requests[-1][1]["accepted"] is True
            assert not any(path.endswith("/decision") for path, _ in requests)
            assert await page.evaluate(
                "document.documentElement.scrollWidth<=innerWidth"
            )
            await page.goto(BASE + "/settings/privacy", wait_until="networkidle")
            await page.get_by_role(
                "button", name="Consulter l’inventaire de conservation", exact=True
            ).click()
            await page.get_by_text("Projets : 2", exact=False).wait_for()
            async with page.expect_download() as export:
                await page.get_by_role(
                    "button",
                    name="Télécharger l’archive métier du workspace",
                    exact=True,
                ).click()
            assert (await export.value).suggested_filename == "radar-workspace-1.zip"
            assert await page.evaluate(
                "document.documentElement.scrollWidth<=innerWidth"
            )
            await page.goto(BASE + "/factures/10", wait_until="networkidle")
            await page.get_by_label("Motif de l’avoir total", exact=True).fill(
                "TEST correction intégrale validée"
            )
            await page.get_by_role("checkbox").check()
            await page.get_by_role(
                "button", name="Émettre l’avoir total", exact=True
            ).click()
            await page.get_by_text(
                "Avoir total émis. Aucun remboursement exécuté.", exact=True
            ).wait_for()
            assert notes and invoice["credited_at"]
            await expect(
                page.get_by_role("button", name="Enregistrer paiement", exact=True)
            ).to_have_count(0)
            async with page.expect_download() as credit:
                await page.get_by_role(
                    "button", name="Télécharger l’avoir PDF", exact=True
                ).click()
            assert (await credit.value).suggested_filename == "AVO-2026-0001.pdf"
            assert await page.evaluate(
                "document.documentElement.scrollWidth<=innerWidth"
            )
            await page.goto(
                BASE + "/admin/subscription-requests", wait_until="networkidle"
            )
            await page.get_by_label(
                "Acceptation contractuelle pour cette offre", exact=True
            ).select_option("12")
            await page.get_by_label("Référence d’autorisation", exact=True).fill(
                "TEST verified agreement"
            )
            await page.locator('select[name="decision"]').select_option("approve")
            await page.get_by_role(
                "button", name="Enregistrer la décision", exact=True
            ).click()
            await page.get_by_text("Décision enregistrée.", exact=True).wait_for()
            assert requests[-1][1]["contract_acceptance_id"] == 12
            assert await page.evaluate(
                "document.documentElement.scrollWidth<=innerWidth"
            )
            await page.goto(BASE + "/admin/legal", wait_until="networkidle")
            await page.get_by_label("Dossier JSON validé", exact=True).fill(
                json.dumps(
                    {
                        "version": bundle["version"],
                        "publisher": {
                            "name": "TEST publisher",
                            "legal_form": "EI",
                            "registration": "TEST RNE",
                            "siret": "12345678901234",
                            "address": "1 TEST street",
                            "email": "TEST@example.com",
                            "phone": "0123456789",
                            "publication_director": "TEST operator",
                            "hosting_name": "TEST hosting",
                            "hosting_address": "2 TEST street",
                            "hosting_contact": "hosting@example.com",
                        },
                        "documents": bundle["documents"],
                        "review_reference": "TEST review only",
                        "reviewed_for_publication": True,
                    }
                )
            )
            await page.get_by_role(
                "button", name="Publier cette version validée", exact=True
            ).click()
            await page.get_by_text(
                "Version TEST-2026.1 publiée", exact=False
            ).wait_for()
            assert await page.evaluate(
                "document.documentElement.scrollWidth<=innerWidth"
            )
            assert not errors, errors
            await page.screenshot(
                path=f"/tmp/radar-legal-workflows-{width}.png", full_page=True
            )
            print(
                f"PASS {width}px: published texts, explicit acceptance, archive, retention inventory, credit, audited approval, operator publication (API fixtures)",
                flush=True,
            )
            await context.close()
        await browser.close()


asyncio.run(main())
