"""Real browser + real API/PostgreSQL/Redis: copied cookies and request replay fail."""

import asyncio, json, os, secrets, subprocess, time, signal
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
FRONT = "http://127.0.0.1:3109"
BACK = "http://127.0.0.1:8018"


async def exercise(opportunity_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=os.environ.get("RADAR_BROWSER_PATH"), args=["--no-sandbox"]
        )
        context = await browser.new_context(viewport={"width": 1440, "height": 1000})
        await context.add_init_script(
            "window.__radarXss=0;localStorage.setItem('opportunities-radar-welcome-shown-v2','true');localStorage.setItem('cookie-consent',JSON.stringify({version:'2026-11-13',chosenAt:new Date().toISOString(),analytics:'denied'}));"
        )
        page = await context.new_page()
        beacons = []
        proof = []
        page.on(
            "request",
            lambda r: beacons.append(r.url) if "collector.invalid" in r.url else None,
        )
        page.on(
            "request",
            lambda r: (
                proof.append((r.url, r.headers))
                if "/api/v1/auth/me" in r.url and r.headers.get("x-radar-proof")
                else None
            ),
        )
        await page.goto(FRONT + "/login", wait_until="networkidle")
        await page.get_by_label("Email", exact=False).first.fill(
            "browser-security@example.com"
        )
        await page.locator("input[type=password]").first.fill(
            "Security-Test-Password-84!"
        )
        await page.get_by_role("button", name="Se connecter", exact=True).click()
        await page.wait_for_url(lambda url: "/login" not in str(url), timeout=30000)
        first = await page.evaluate(
            "async()=>{const r=await fetch('/api/v1/auth/me');return {status:r.status,body:await r.json()}}"
        )
        assert first["status"] == 200, first
        storage = await page.evaluate("({...localStorage})")
        assert storage["access_token"].startswith("cookie-session.") and storage[
            "refresh_token"
        ].startswith("cookie-session.")
        assert all(
            not (isinstance(v, str) and v.startswith("eyJ"))
            for k, v in storage.items()
            if k in {"access_token", "refresh_token"}
        )
        assert "radar_access" not in await page.evaluate("document.cookie")
        key_state = await page.evaluate(
            """async()=>{const db=await new Promise((res,rej)=>{const r=indexedDB.open('radar-device-proof-v1');r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});const pair=await new Promise((res,rej)=>{const r=db.transaction('keys').objectStore('keys').get('origin');r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});db.close();let blocked=false;try{await crypto.subtle.exportKey('jwk',pair.privateKey)}catch{blocked=true}return {extractable:pair.privateKey.extractable,blocked}}"""
        )
        assert key_state == {"extractable": False, "blocked": True}, key_state
        cookies = await context.cookies()
        assert any(c["httpOnly"] and "radar_access" in c["name"] for c in cookies)
        assert proof
        copied = await browser.new_context(
            user_agent=await page.evaluate("navigator.userAgent")
        )
        await copied.add_cookies(cookies)
        thief = await copied.new_page()
        # Static public page avoids the normal auth UI clearing rejected markers before the attack.
        await thief.goto(FRONT + "/privacy", wait_until="networkidle")
        denied = await thief.evaluate(
            "async()=>{const r=await fetch('/api/v1/auth/me');return r.status}"
        )
        assert denied == 401, denied
        await thief.evaluate(
            "(s)=>Object.entries(s).forEach(([k,v])=>localStorage.setItem(k,v))",
            storage,
        )
        denied = await thief.evaluate(
            "async()=>{const r=await fetch('/api/v1/auth/me');return r.status}"
        )
        assert denied == 401, denied
        # Exact valid proof already consumed on the first browser cannot be replayed.
        headers = {k: v for k, v in proof[-1][1].items() if k.startswith("x-radar-")}
        replay = await thief.evaluate(
            "async(data)=>{const r=await fetch(data.url,{headers:data.headers});return r.status}",
            {"url": proof[-1][0], "headers": headers},
        )
        assert replay == 401, replay
        assert (
            await page.evaluate("async()=> (await fetch('/api/v1/auth/me')).status")
        ) == 200
        await page.goto(
            FRONT + "/leads/" + str(opportunity_id), wait_until="networkidle"
        )
        await expect(page.get_by_text("SAFE-CONTENT", exact=False)).to_be_visible()
        assert await page.evaluate("window.__radarXss||0") == 0
        assert not beacons, beacons
        assert await page.locator('a[href^="javascript:"]').count() == 0
        # Refresh still works, with fresh proof and the existing device key.
        r = await page.evaluate(
            "async()=>{const r=await fetch('/api/v1/auth/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({refresh_token:'cookie-session'})});return r.status}"
        )
        assert r == 200, r
        # Exercise the application's Axios refresh interceptor with a rejected access cookie.
        access = next(c for c in await context.cookies() if c["name"] == "radar_access")
        await context.add_cookies([{**access, "value": "invalid-expired-access"}])
        async with page.expect_response(
            lambda r: "/api/v1/auth/refresh" in r.url and r.request.method == "POST"
        ) as renewed:
            await page.goto(FRONT + "/settings", wait_until="networkidle")
        renewal = await renewed.value
        assert renewal.status == 200, await renewal.text()
        assert renewal.request.headers.get("x-radar-proof"), renewal.request.headers
        assert (
            await page.evaluate("async()=> (await fetch('/api/v1/auth/me')).status")
        ) == 200
        assert (await page.evaluate("localStorage.getItem('access_token')")).startswith(
            "cookie-session."
        )
        await copied.close()
        await context.close()
        await browser.close()
        print(
            "PASS real browser: login, HttpOnly cookies, marker-only storage, copied cookies + identical UA rejected, cloned marker rejected, replay rejected, original session works, stored XSS removed, signed refresh works",
            flush=True,
        )


def main():
    url = make_url(os.environ["RADAR_TEST_DATABASE_URL"])
    if (
        os.environ.get("TESTING") != "true"
        or url.host not in {"127.0.0.1", "localhost"}
        or "test" not in url.database
    ):
        raise RuntimeError("Explicit disposable test DB required")
    redis_url = os.environ["RADAR_TEST_REDIS_URL"]
    if urlparse(redis_url).hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("Local disposable Redis required")
    schema = "browser_security_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as c:
        c.execute(text(f"CREATE SCHEMA {schema}"))
    scoped = url.update_query_dict({"options": "-csearch_path=" + schema})
    engine = create_engine(scoped)
    from app.db.base import Base
    from app.db import models
    from app.db.models.user import User, Role
    from app.db.models.workspace import Workspace
    from app.db.models.opportunity import Opportunity, SourceType
    from app.core.security import get_password_hash

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(
            email="browser-security@example.com",
            full_name="TEST Browser",
            hashed_password=get_password_hash("Security-Test-Password-84!"),
            role=Role.ADMIN,
            is_active=True,
            is_whitelisted=True,
        )
        db.add(user)
        db.flush()
        workspace = Workspace(
            name="TEST Security Space",
            owner_user_id=user.id,
            plan="business",
            enabled_packs=["core"],
            addons=[],
            max_seats=3,
        )
        db.add(workspace)
        db.flush()
        opportunity = Opportunity(
            workspace_id=workspace.id,
            external_id="security-browser-fixture",
            title="TEST Secure HTML",
            description='<p><strong>SAFE-CONTENT</strong></p><img src="https://collector.invalid/pixel" onerror="window.__radarXss=1"><a href="javascript:window.__radarXss=1">Unsafe link</a><script>window.__radarXss=1</script>',
            source_type=SourceType.API,
            source_name="TEST",
        )
        db.add(opportunity)
        db.commit()
        id = opportunity.id
    env = {
        **os.environ,
        "DATABASE_URL": scoped.render_as_string(hide_password=False),
        "FRONTEND_URL": FRONT,
        "APP_ENV": "development",
        "DEBUG": "false",
        "SECRET_KEY": secrets.token_hex(32),
        "JWT_SECRET_KEY": secrets.token_hex(32),
        "REDIS_URL": redis_url,
        "CELERY_BROKER_URL": redis_url,
        "CELERY_RESULT_BACKEND": redis_url,
        "TESTING": "true",
    }
    logs = []
    processes = []
    try:
        for name, cmd, cwd in [
            (
                "backend",
                [
                    "python",
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8018",
                ],
                ROOT / "backend",
            ),
            (
                "frontend",
                [
                    "npm",
                    "run",
                    "start",
                    "--",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    "3109",
                ],
                ROOT / "frontend",
            ),
        ]:
            log = open("/tmp/radar-security-" + name + ".log", "w")
            logs.append(log)
            if name == "backend":
                cmd[0] = (
                    str(ROOT / ".venv/bin/python")
                    if (ROOT / ".venv/bin/python").exists()
                    else "python"
                )
            processes.append(
                subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            )
        import urllib.request

        for port, path in [(8018, "/health"), (3109, "/login")]:
            for attempt in range(60):
                if any(p.poll() is not None for p in processes):
                    raise RuntimeError(
                        "Test server stopped; inspect /tmp/radar-security-*.log"
                    )
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}{path}", timeout=1
                    ):
                        break
                except Exception:
                    time.sleep(0.5)
            else:
                raise RuntimeError("Test server unavailable")
        asyncio.run(exercise(id))
    finally:
        for p in processes:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for p in processes:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
        for f in logs:
            f.close()
        engine.dispose()
        with admin.begin() as c:
            c.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()


if __name__ == "__main__":
    main()
