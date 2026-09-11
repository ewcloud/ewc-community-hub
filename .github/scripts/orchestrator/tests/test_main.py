import pytest

from time import sleep, monotonic
from random import seed, uniform, randint, choice
from os import environ
from sys import path
from re import search
from pathlib import Path
from queue import Queue
from threading import Event, Semaphore, Lock, Thread
from unittest import mock
from unittest.mock import Mock


# The orchestrator reads several env vars at import time via environ[...], so they must exist before the module is imported
_REQUIRED_ENV_DEFAULTS = {
    "GH_API_TOKEN": "test-token",
    "GH_DOWNSTREAM_WORKFLOW_FILE": "downstream.yml",
    "POLLING_INTERVAL_SECONDS": "1",
    "RUN_TIMEOUT_MINUTES": "20",
    "TOTAL_TIMEOUT_MINUTES": "190",
    "MAX_CONCURRENT_WORKFLOWS": "1",
    "GITHUB_REF_NAME": "main",
}
for _key, _value in _REQUIRED_ENV_DEFAULTS.items():
    environ.setdefault(_key, _value)

# Make the directory that contains main.py importable
path.insert(0, str(Path(__file__).resolve().parent.parent))

import main as orchestrator  # noqa: E402

_REAL_SLEEP = sleep  # captured before any module monkey patching

# --- Fixtures & Mocks ---


@pytest.fixture(autouse=True)
def reset_orchestrator_state(monkeypatch):
    monkeypatch.setattr(orchestrator, "pending", Queue())
    monkeypatch.setattr(orchestrator, "in_progress", orchestrator.ThreadSafeDict())
    monkeypatch.setattr(orchestrator, "done", Queue())
    monkeypatch.setattr(orchestrator, "stop", Event())
    monkeypatch.setattr(orchestrator, "concurrency_counter", Semaphore(1))
    monkeypatch.setattr(orchestrator, "POLLING_INTERVAL_SECONDS", 0.02)
    monkeypatch.setattr(orchestrator, "RUN_TIMEOUT_MINUTES", 20)

    def clamped_sleep(seconds=0, *_args, **_kwargs):
        _REAL_SLEEP(min(seconds, 0.01) if seconds else 0)

    monkeypatch.setattr(orchestrator, "sleep", clamped_sleep)
    yield


def make_item(key="item-1"):
    return orchestrator.Item(
        {
            "key": key,
            "name": f"acme-{key}",
            "repo_owner": "acme",
            "repo_name": "repo",
            "git_ref": "refs/tags/v1.0.0",
            "version": "v1.0.0",
            "values": {},
        }
    )


def make_fake_github_api(jitter_seconds=0.005, min_polls=0, max_polls=2):
    register_calls = {}
    register_calls_lock = Lock()
    next_run_id = iter(range(1, 10_000))
    counter_lock = Lock()

    def _next_run_id():
        with counter_lock:
            return next(next_run_id)

    def fake_github_api(method, path_, payload=None):
        _REAL_SLEEP(uniform(0, jitter_seconds))

        if method == "POST" and "/dispatches" in path_:
            res = Mock(status_code=204)
            res.raise_for_status = Mock()
            return res

        if method == "GET" and "/runs?event=workflow_dispatch" in path_:
            run_id = _next_run_id()
            with register_calls_lock:
                register_calls[run_id] = {
                    "polls_remaining": randint(min_polls, max_polls),
                    "conclusion": choice(["success", "success", "success", "failure"]),
                }

            res = Mock(status_code=200)
            res.raise_for_status = Mock()
            res.json = Mock(return_value={"workflow_runs": [{"id": run_id}]})
            return res

        match = search(r"/actions/runs/(\d+)$", path_)
        if method == "GET" and match:
            run_id = int(match.group(1))
            with register_calls_lock:
                state = register_calls[run_id]
                if state["polls_remaining"] > 0:
                    state["polls_remaining"] -= 1
                    status, conclusion = "in_progress", None
                else:
                    status, conclusion = "completed", state["conclusion"]
            res = Mock(status_code=200)
            res.raise_for_status = Mock()
            res.json = Mock(return_value={"status": status, "conclusion": conclusion})
            return res

        raise AssertionError(f"Unexpected github_api call: {method} {path_}")

    return fake_github_api


class SemaphoreTracker:
    # Wraps a real Semaphore's acquire/release to record peak concurrent holders

    def __init__(self, semaphore: Semaphore):
        self._real_acquire = semaphore.acquire
        self._real_release = semaphore.release
        self._lock = Lock()
        self.current = 0
        self.peak = 0

    def acquire(self, blocking=True):
        acquired = self._real_acquire(blocking=blocking)
        if acquired:
            with self._lock:
                self.current += 1
                self.peak = max(self.peak, self.current)
        return acquired

    def release(self):
        with self._lock:
            self.current -= 1
        self._real_release()


# --- Tests ---


@pytest.mark.parametrize("max_concurrency", [1, 2, 5])
def test_concurrency_stress_drains_and_respects_concurrency_counter(
    reset_orchestrator_state, monkeypatch, max_concurrency
):
    seed(1000 + max_concurrency)

    item_count = 3 * max_concurrency + 2  # always more items than the concurrency level
    for i in range(item_count):
        orchestrator.pending.put(make_item(key=f"item-{i}"))

    monkeypatch.setattr(orchestrator, "concurrency_counter", Semaphore(max_concurrency))
    permits = SemaphoreTracker(orchestrator.concurrency_counter)

    fake_api = make_fake_github_api()

    dispatcher_thread = Thread(target=orchestrator.dispatcher, args=("dispatcher",), daemon=True)
    tracker_thread = Thread(target=orchestrator.tracker, args=("tracker",), daemon=True)

    with mock.patch.object(orchestrator.concurrency_counter, "acquire", side_effect=permits.acquire), mock.patch.object(
        orchestrator.concurrency_counter, "release", side_effect=permits.release
    ), mock.patch.object(orchestrator, "github_api", side_effect=fake_api):

        try:
            dispatcher_thread.start()
            tracker_thread.start()

            deadline = monotonic() + 15
            drained = False
            while monotonic() < deadline:
                if (
                    orchestrator.pending.empty()
                    and len(orchestrator.in_progress.keys()) == 0
                    and orchestrator.done.qsize() == item_count
                ):
                    drained = True
                    break
                _REAL_SLEEP(0.02)

            if not drained:
                pytest.fail(
                    f"orchestrator failed to drain all {item_count} items within the bounded "
                    f"time window at MAX_CONCURRENT_WORKFLOWS={max_concurrency}: "
                    f"pending={orchestrator.pending.qsize()}, "
                    f"in_progress={len(orchestrator.in_progress.keys())}, "
                    f"done={orchestrator.done.qsize()}"
                )
        finally:
            orchestrator.stop.set()
            dispatcher_thread.join(timeout=5)
            tracker_thread.join(timeout=5)

    assert not dispatcher_thread.is_alive(), "dispatcher thread did not exit after the stop event"
    assert not tracker_thread.is_alive(), "tracker thread did not exit after the stop event"

    assert orchestrator.pending.empty()
    assert len(orchestrator.in_progress.keys()) == 0
    assert orchestrator.done.qsize() == item_count

    assert (
        permits.peak <= max_concurrency
    ), f"observed {permits.peak} concurrently held concurrency_counter permits, exceeding MAX_CONCURRENT_WORKFLOWS={max_concurrency}"
    assert permits.current == 0, "a concurrency_counter permit was leaked (acquired but never released)"

    completed_items = list(orchestrator.done.queue)
    assert all(item.state in ("COMPLETED", "FAILED") for item in completed_items), (
        "some items reached an unexpected terminal state: "
        f"{[(item.key, item.state) for item in completed_items if item.state not in ('COMPLETED', 'FAILED')]}"
    )
