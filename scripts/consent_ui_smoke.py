"""A fresh visitor and a refusing visitor must never load third-party analytics."""

import asyncio
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright

BASE = os.getenv("RADAR_UI_BASE_URL", "http://localhost:3000")
if urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
    raise RuntimeError("Local test only")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=os.getenv("RADAR_BROWSER_PATH"), args=["--no-sandbox"]
        )
        context = await browser.new_context()
        requests = []

        async def intercept(route):
            requests.append(route.request.url)
            await route.abort()

        await context.route("https://www.googletagmanager.com/**", intercept)
        page = await context.new_page()
        await page.goto(BASE + "/login", wait_until="networkidle")
        await page.get_by_role("button", name="Tout refuser", exact=True).wait_for()
        assert not requests, "Analytics loaded before a choice"
        await page.get_by_role("button", name="Tout refuser", exact=True).click()
        await page.reload(wait_until="networkidle")
        assert not requests, "Analytics loaded after refusal"
        await page.get_by_role("button", name="Préférences cookies", exact=True).click()
        await page.get_by_role("button", name="Tout refuser", exact=True).wait_for()
        print(
            "PASS consent: no analytics before choice/after refusal; preferences can reopen",
            flush=True,
        )
        await browser.close()


asyncio.run(main())
