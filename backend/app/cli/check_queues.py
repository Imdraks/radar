"""Fail deployment when routed tasks have no active consumer."""

from app.workers.celery_app import celery_app


def main():
    queues = celery_app.control.inspect(timeout=5).active_queues() or {}
    active = {q["name"] for worker in queues.values() for q in worker}
    required = {"celery"} | {
        route["queue"] for route in celery_app.conf.task_routes.values()
    }
    missing = required - active
    if missing:
        raise RuntimeError("No worker consumes queues: " + ", ".join(sorted(missing)))
    print("All routed queues have an active worker")


if __name__ == "__main__":
    main()
