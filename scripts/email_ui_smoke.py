"""Browser rendering of generated local emails. No delivery, no live accounts."""

import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
from email_preview import previews

OUT = Path("/tmp/radar-email-previews")


async def main():
    OUT.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=os.environ.get("RADAR_BROWSER_PATH"), args=["--no-sandbox"]
        )
        for width in [800, 390, 320]:
            context = await browser.new_context(
                viewport={"width": width, "height": 900}, device_scale_factor=1
            )
            errors, requests = [], []
            await context.route("**/*", lambda route: route.abort())
            page = await context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            for name, html in previews().items():
                await page.set_content(html)
                assert await page.locator("h1").count() == 1
                assert await page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                ), f"Overflow {name} at {width}"
                assert await page.locator("script,iframe,form,img").count() == 0
                for anchor in await page.locator("a").all():
                    assert (await anchor.get_attribute("href")).startswith(
                        ("https://", "http://")
                    )
                await page.screenshot(
                    path=str(OUT / f"{name}-{width}.png"), full_page=True
                )
            assert not errors, errors
            assert not requests, requests
            print(
                f"PASS 9 Radar emails at {width}px — no overflow, no external assets",
                flush=True,
            )
            await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
