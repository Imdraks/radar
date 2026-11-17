"""Real worker/broker round trips, restricted to explicitly local disposable services."""

import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.workers.celery_app import celery_app
from app.core.config import settings


def run():
    if os.environ.get("TESTING") != "true" or urlparse(
        settings.celery_broker_url
    ).hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError(
            "Queue smoke requires TESTING=true and a disposable loopback broker"
        )
    required = sorted(
        {"celery"} | {route["queue"] for route in celery_app.conf.task_routes.values()}
    )
    with open("/tmp/radar-test-worker.log", "w") as log:
        worker = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "celery",
                "-A",
                "app.workers.celery_app",
                "worker",
                "--pool=solo",
                "--concurrency=1",
                "--loglevel=warning",
                "--queues=" + ",".join(required),
                "--hostname=radar-queue-test@%h",
            ],
            cwd=ROOT / "backend",
            env=os.environ,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            for attempt in range(15):
                if worker.poll() is not None:
                    raise RuntimeError(
                        "Queue test worker failed to start; inspect /tmp/radar-test-worker.log"
                    )
                queues = celery_app.control.inspect(timeout=1).active_queues() or {}
                active = {q["name"] for rows in queues.values() for q in rows}
                if set(required) <= active:
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError("No consumers for all expected queues")
            for name in required:
                task = celery_app.send_task(
                    "celery.accumulate", args=["radar-queue-test", name], queue=name
                )
                assert task.get(timeout=15) == ["radar-queue-test", name]
                print("PASS broker/worker round trip:", name, flush=True)
        finally:
            worker.terminate()
            try:
                worker.wait(timeout=15)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait()


if __name__ == "__main__":
    run()
