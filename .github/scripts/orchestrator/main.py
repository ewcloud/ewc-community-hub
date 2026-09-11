#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from json import dumps as json_dumps
from os import environ, getenv, path
from queue import Queue, Empty
from pathlib import Path
from requests import request, Response
from time import sleep
from threading import Event, Semaphore, Lock
from typing import Any
from yaml import safe_load as yaml_safe_load

# --- Input Environmental Variables ---

GH_API_TOKEN = environ["GH_API_TOKEN"]
GH_DOWNSTREAM_WORKFLOW_FILE = environ["GH_DOWNSTREAM_WORKFLOW_FILE"]
ITEM_NAMES = getenv("ITEM_NAMES", "")
EXCLUDED_ITEM_NAMES = getenv("EXCLUDED_ITEM_NAMES", "")
ITEM_TECHNOLOGY_ANNOTATIONS = getenv("ITEM_TECHNOLOGY_ANNOTATIONS", "Ansible Playbook")
ITEM_OTHERS_ANNOTATIONS = getenv("ITEM_OTHERS_ANNOTATIONS", "Deployable")
POLLING_INTERVAL_SECONDS = int(environ["POLLING_INTERVAL_SECONDS"])
RUN_TIMEOUT_MINUTES = int(environ["RUN_TIMEOUT_MINUTES"])
TOTAL_TIMEOUT_MINUTES = int(environ["TOTAL_TIMEOUT_MINUTES"])
MAX_CONCURRENT_WORKFLOWS = int(environ["MAX_CONCURRENT_WORKFLOWS"])

#  --- Global Static/Variable Defaults ---

API_BASE = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GH_API_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

REPO_ROOT_DIR = path.dirname(path.dirname(path.dirname(Path(__file__).parent.resolve())))
GH_WORKSPACE = getenv("GITHUB_WORKSPACE", REPO_ROOT_DIR)
CATALOG_FILE = f"{GH_WORKSPACE}/items.yaml"
SUMMARY_TEMPLATE_FILE = f"{GH_WORKSPACE}/.github/scripts/orchestrator/summary.template.md"

print(f"GH_WORKSPACE: {GH_WORKSPACE}")

EWCCLI_ANNOTATION = "EWCCLI-compatible"
EWCCLI_GH_API_REPO_ENDPOINT = "ewcloud/ewccli"

RED_LIGHT = "🔴"
YELLOW_LIGHT = "🟡"
GREEN_LIGHT = "🟢"
GRAY_LIGHT = "⚫"
TIME_FORMAT = "%Y-%m-%dT%H:%H:%SZ"

#  --- Global Runtime State ---


class Item:
    def __init__(self, raw: dict):
        self.key = raw["key"]
        self.name = raw["name"]
        self.owner = raw["repo_owner"]
        self.repo = raw["repo_name"]
        self.git_ref = raw["git_ref"]
        self.version = raw["version"]
        self.values = raw["values"]
        self.state = "PLANNED"
        self.dispatch_time: datetime | None = None
        self.run_id: int | None = None
        self.conclusion: str | None = None
        self.error: str | None = None

    def __repr__(self) -> str:
        return f"<Item {self.key} state={self.state}>"


class ThreadSafeDict:
    def __init__(self) -> None:
        self._dict: dict[str, Item] = dict({})
        self._lock: Lock = Lock()

    def add(self, item: Item) -> None:
        self._lock.acquire()
        self._dict.update({item.key: item})
        self._lock.release()

    def get(self, key: str) -> Item | None:
        self._lock.acquire()
        item = self._dict.get(key, None)
        self._lock.release()
        return item

    def pop(self, key: str) -> Item | None:
        self._lock.acquire()
        item = self._dict.pop(key, None)
        self._lock.release()
        return item

    def keys(self) -> list[str]:
        self._lock.acquire()
        keys = [key for key in self._dict.keys()]
        self._lock.release()
        return keys


pending: Queue = Queue()
concurrency_counter: Semaphore = Semaphore(MAX_CONCURRENT_WORKFLOWS)
in_progress: ThreadSafeDict = ThreadSafeDict()
done: Queue = Queue()
stop: Event = Event()

# --- Subroutines ---


def github_api(method: str, path: str, payload: dict | Any = None, verbose: bool = True) -> Response:

    if verbose:
        print(
            f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - Making HTTP {method} request to '{API_BASE}{path}' with payload: '{payload}'",
            flush=True,
        )

    response = request(
        method,
        f"{API_BASE}{path}",
        headers=HEADERS,
        json=payload,
        timeout=15,
    )
    return response


def move_to_done(item: Item, state: str, error: str | None = None) -> None:
    item.state = state
    if error:
        item.error = error
    done.put(item)


def read_spec_items(thread_id: str = "main") -> dict:
    with open(CATALOG_FILE) as f:
        catalog = yaml_safe_load(f)

    filtered_item_names = set()
    if ITEM_NAMES:
        filtered_item_names = set(item_name.strip() for item_name in ITEM_NAMES.split(","))
        print(
            f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Reading Items with names: {filtered_item_names}",
            flush=True,
        )

    excluded_item_names = set()
    if EXCLUDED_ITEM_NAMES:
        excluded_item_names = set(item_name.strip() for item_name in EXCLUDED_ITEM_NAMES.split(","))
        print(
            f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Excluding Items with names: {excluded_item_names}",
            flush=True,
        )

    filtered_item_technology_annotations = set(
        technology_annotation.strip() for technology_annotation in ITEM_TECHNOLOGY_ANNOTATIONS.split(",")
    )
    print(
        f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Reading Items with technology annotations: {filtered_item_technology_annotations}",
        flush=True,
    )

    filtered_item_others_annotations = set(
        others_annotation.strip() for others_annotation in ITEM_OTHERS_ANNOTATIONS.split(",")
    )
    print(
        f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Reading Items with others annotations: {filtered_item_others_annotations}",
        flush=True,
    )

    spec_items = {}

    for key, item in catalog["spec"]["items"].items():

        name = item.get("name")
        if ITEM_NAMES and name not in filtered_item_names:
            continue

        if EXCLUDED_ITEM_NAMES and name in excluded_item_names:
            continue

        values = item.get("values", {})
        if not values:
            continue

        others_annotations = set(item.get("annotations", {}).get("others", "").split(","))
        if not filtered_item_others_annotations == others_annotations:
            continue

        technology_annotations = set(item.get("annotations", {}).get("technology", "").split(","))
        if not filtered_item_technology_annotations == technology_annotations:
            continue

        spec_item = {subkey: item[subkey] for subkey in ["name", "version", "values", "sources"]}

        spec_items.update({key: spec_item})

    if len(spec_items) < 1:
        print(
            f"::warning::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Item name and annotation filtering returned no matches!",
            flush=True,
        )

    return spec_items


def parse_items(spec_items: dict) -> list[Item]:

    items: list[Item] = []

    for key, item in spec_items.items():

        values = item.get("values", {})
        if "inputSpec" in values:
            input_spec = {i["name"]: i.get("default") for i in values["inputSpec"]}
            values["inputSpecJson"] = json_dumps(input_spec)
            del values["inputSpec"]

        repo_url = item["sources"][0]
        owner, repo = repo_url.split("/")[-2:]
        repo = repo.replace(".git", "")

        items.append(
            Item(
                {
                    "key": key,
                    "name": item["name"],
                    "repo_owner": owner,
                    "repo_name": repo,
                    "git_ref": f"refs/tags/{item['version']}",
                    "version": item["version"],
                    "values": values,
                }
            )
        )

    return items


def dispatch_and_register(thread_id: str) -> None:
    try:
        item = pending.get_nowait()
    except Empty:
        return

    if not concurrency_counter.acquire(blocking=False):
        pending.put(item)
        print(
            f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Max concurrency reached. Will wait before dispatching new workflows...",
            flush=True,
        )
        sleep(10)
        return

    acquired = True
    item.dispatch_time = datetime.now(timezone.utc)
    try:

        # dispatch
        if EWCCLI_ANNOTATION in ITEM_OTHERS_ANNOTATIONS:
            dispatch = github_api(
                "POST",
                f"/repos/{EWCCLI_GH_API_REPO_ENDPOINT}/actions/workflows/{GH_DOWNSTREAM_WORKFLOW_FILE}/dispatches",
                {"ref": "main", "inputs": {"itemName": item.name, "catalogRef": f"{environ['GITHUB_REF_NAME']}"}},
            )
        else:
            dispatch = github_api(
                "POST",
                f"/repos/{item.owner}/{item.repo}/actions/workflows/{GH_DOWNSTREAM_WORKFLOW_FILE}/dispatches",
                {
                    "ref": item.git_ref,
                    "inputs": item.values,
                },
            )

        print(
            f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Sent dispatch request for '{item}'",
            flush=True,
        )

        dispatch_failed = False
        dispatch_error = ""
        try:
            dispatch.raise_for_status()
        except Exception:
            dispatch_failed = True
            dispatch_error = f"Failed to dispatch workload run with HTTP error code {dispatch.status_code}"
            print(
                f"::warning::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - {dispatch_error}",
                flush=True,
            )

        if dispatch_failed:
            move_to_done(
                item,
                "DISPATCH_FAILED",
                dispatch_error,
            )
            return  # returns through the `finally` statement at the bottom, which reduces the concurrency count

        dispatch_delay_seconds = 5
        max_dispatch_time = item.dispatch_time + timedelta(seconds=dispatch_delay_seconds)

        runs = None
        register_failed = False
        register_error = ""
        workflow_runs = []
        workflow_runs_count = 0

        register_max_attempts = 3
        register_retry_delay_seconds = 3
        for attempt in range(1, register_max_attempts + 1):

            if EWCCLI_ANNOTATION in ITEM_OTHERS_ANNOTATIONS:
                runs = github_api(
                    "GET",
                    f"/repos/{EWCCLI_GH_API_REPO_ENDPOINT}/actions/workflows/{GH_DOWNSTREAM_WORKFLOW_FILE}/runs?event=workflow_dispatch&created={item.dispatch_time.isoformat().replace("+00:00", "Z")}..{max_dispatch_time.isoformat().replace("+00:00", "Z")}",
                )
            else:
                runs = github_api(
                    "GET",
                    f"/repos/{item.owner}/{item.repo}/actions/workflows/{GH_DOWNSTREAM_WORKFLOW_FILE}/runs?event=workflow_dispatch&created={item.dispatch_time.isoformat().replace("+00:00", "Z")}..{max_dispatch_time.isoformat().replace("+00:00", "Z")}",
                )

            print(
                f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Sent register request for '{item}' (attempt {attempt}/{register_max_attempts})",
                flush=True,
            )

            try:
                runs.raise_for_status()
                runs_json = runs.json()
                workflow_runs = runs_json.get("workflow_runs", [])
                workflow_runs_count = len(workflow_runs)

                print(
                    f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Registering {workflow_runs_count} run(s): '{json_dumps(workflow_runs, indent=4)[:1000]}...'",
                    flush=True,
                )

            except Exception:
                register_failed = True
                register_error = f"Failed to register workload run with HTTP error code {runs.status_code}"
                print(
                    f"::warning::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - {register_error}",
                    flush=True,
                )
                sleep(register_retry_delay_seconds)

            if workflow_runs_count >= 1:
                break  # got a response with HTTP 200 code, no need to loop anymore

            if attempt < register_max_attempts:
                print(
                    f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - No runs visible yet for '{item}', retrying in {register_retry_delay_seconds}s ({attempt}/{register_max_attempts})...",
                    flush=True,
                )

        if not register_failed:
            if workflow_runs_count == 0:
                register_failed = True
                register_error = f"No runs match registration criteria for {item.name}"
                print(
                    f"::warning::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - {register_error}",
                    flush=True,
                )

            if workflow_runs_count > 1:
                register_failed = True
                register_error = f"Multiple possible runs for {item.name}"
                print(
                    f"::warning::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - {register_error}",
                    flush=True,
                )

        if register_failed:
            move_to_done(item, "REGISTER_FAILED", register_error)
            return  # returns through the `finally` statement at the bottom, which reduces the concurrency count

        item.run_id = workflow_runs[0]["id"]
        item.state = "REGISTERED"
        in_progress.add(item)
        acquired = False

    finally:
        if acquired:
            concurrency_counter.release()


def track_status(thread_id: str) -> None:

    keys = in_progress.keys()

    for key in keys:
        item = in_progress.get(key)
        if item is None:
            continue

        item.state = "RUNNING"

        if stop.is_set():
            item = in_progress.pop(key)
            if item is None:
                continue

            move_to_done(item, "TIMED_OUT", "Total deadline reached")
            concurrency_counter.release()
            continue

        run_deadline = item.dispatch_time + timedelta(minutes=RUN_TIMEOUT_MINUTES)  # type: ignore
        if datetime.now(timezone.utc) >= run_deadline:  # type: ignore
            item = in_progress.pop(key)
            if item is None:
                continue

            move_to_done(item, "TIMED_OUT", "Per-run deadline reached")
            concurrency_counter.release()
            continue

        if EWCCLI_ANNOTATION in ITEM_OTHERS_ANNOTATIONS:
            run = github_api("GET", f"/repos/{EWCCLI_GH_API_REPO_ENDPOINT}/actions/runs/{item.run_id}")
        else:
            run = github_api("GET", f"/repos/{item.owner}/{item.repo}/actions/runs/{item.run_id}")

        print(
            f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Sent check request for '{item}'",
            flush=True,
        )

        try:
            run.raise_for_status()
        except Exception as e:
            print(
                f"::warning::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Failed to check status for {item.name} (run ID: '{item.run_id}') with exception: '{e}'",
                flush=True,
            )
            continue

        run = run.json()

        print(
            f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Checking run: '{json_dumps(run, indent=4)[:1000]}...'",
            flush=True,
        )

        status = run["status"]
        conclusion = run["conclusion"]

        if status == "completed":
            item = in_progress.pop(key)
            if item is None:
                continue

            item.conclusion = conclusion
            move_to_done(item, "COMPLETED" if conclusion == "success" else "FAILED")
            concurrency_counter.release()


def reduce_summarize(spec_items: dict, thread_id: str = "main") -> None:
    print(
        f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - {pending.qsize()} pending, {len(in_progress.keys())} in progress, {done.qsize()} done"
    )

    while not pending.empty():
        item = pending.get_nowait()
        move_to_done(item, "TIMED_OUT", "Total deadline reached")

    for key in in_progress.keys():
        item = in_progress.pop(key)
        if item is None:
            continue

        move_to_done(item, "TIMED_OUT", "Total deadline reached")
        concurrency_counter.release()

    items: list[Item] = []
    while not done.empty():
        item = done.get_nowait()
        items.append(item)

    if "ECMWF" in GH_DOWNSTREAM_WORKFLOW_FILE.upper():
        site = "ECMWF"
    elif "EUMETSAT" in GH_DOWNSTREAM_WORKFLOW_FILE.upper():
        site = "EUMETSAT"
    else:
        site = "UNKNOWN"
        print(
            f"::warning::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Unable to parse site from GH_DOWNSTREAM_WORKFLOW_FILE. By convention, the workflow filename should include any of: ['ecmwf', 'eumetsat']. Got: '{GH_DOWNSTREAM_WORKFLOW_FILE}'"
        )

    status_rows = []
    is_any_failed_or_timeout = False
    for item in items:
        state_viz = {
            "PLANNED": f"`planning` {GRAY_LIGHT}",
            "DISPATCH_FAILED": f"`dispatching denied` {GRAY_LIGHT}",
            "REGISTER_FAILED": f"`registering` {GRAY_LIGHT}",
            "COMPLETED": f" `passing` {GREEN_LIGHT}",
            "FAILED": f" `failing` {RED_LIGHT}",
            "TIMED_OUT": f"`timing out` {YELLOW_LIGHT}",
        }.get(item.state, f"`unknown` {GRAY_LIGHT}")

        is_any_failed_or_timeout = is_any_failed_or_timeout | ("COMPLETED" not in item.state)

        if not item.run_id:
            run_link = "—"
        elif EWCCLI_ANNOTATION in ITEM_OTHERS_ANNOTATIONS:
            run_link = f"[{item.run_id}](https://github.com/{EWCCLI_GH_API_REPO_ENDPOINT}/actions/runs/{item.run_id})"
        else:
            run_link = f"[{item.run_id}](https://github.com/{item.owner}/{item.repo}/actions/runs/{item.run_id})"

        row = (
            f"| {state_viz} **{item.name}** "
            f"| `{item.version}` "
            f"| `{item.owner}/{item.repo}` "
            f"| {run_link} "
            f"| {item.error.replace('|', '\\|') if item.error else '—'} |"
        )
        status_rows.append(row)

    status_table_content = "\n".join(status_rows) if status_rows else "| - | - | - | - | - |"

    template_path = Path(SUMMARY_TEMPLATE_FILE)
    if not template_path.is_file():
        print(
            f"::error::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Cannot find summary template at {template_path}",
            flush=True,
        )
        return

    try:
        template_content = template_path.read_text(encoding="utf-8")
    except Exception as e:
        print(
            f"::error::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Failed to read template: {e}",
            flush=True,
        )
        return

    summary_contents = template_content.format(
        github_run_id=environ["GITHUB_RUN_ID"],
        github_ref_name=environ["GITHUB_REF_NAME"],
        site=site,
        status_row=status_table_content,
        execution_plan=json_dumps(spec_items, indent=2),
    )

    summary_path = Path(environ["GITHUB_STEP_SUMMARY"])
    try:
        summary_path.write_text(summary_contents, encoding="utf-8")
    except Exception as e:
        print(
            f"::error::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Failed to write summary: {e}",
            flush=True,
        )

    if is_any_failed_or_timeout:
        raise SystemExit(
            f"::error::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Deployment test(s) FAILING! Check the Summary for details"
        )


# --- Worker Thread ---


def dispatcher(thread_id: str) -> None:

    print(f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Starting thread", flush=True)

    while not stop.is_set():
        try:
            dispatch_and_register(thread_id)
        except Exception as e:
            print(
                f"::error::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Failed to dispatch workflow due to an unexpected error: {e}",
                flush=True,
            )
            raise e

    print(
        f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Caught stop event. Exiting... ",
        flush=True,
    )


def tracker(thread_id: str) -> None:
    print(f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Starting thread", flush=True)

    while not stop.is_set():

        try:
            track_status(thread_id)
            sleep(POLLING_INTERVAL_SECONDS)
        except Exception as e:
            print(
                f"::error::{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Failed to check for workflow status due to an unexpected error: {e}",
                flush=True,
            )
            raise e

    print(
        f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Caught stop event. Exiting... ",
        flush=True,
    )


# --- Main Thread ---


def main() -> None:
    thread_id = "main"
    start_time = datetime.now(timezone.utc)
    buffer_minutes = 2
    total_deadline = (
        start_time + timedelta(minutes=TOTAL_TIMEOUT_MINUTES) - timedelta(minutes=buffer_minutes)
    )  # include few mins of buffer to have time for wrap up before the runtime force-quits

    spec_items = read_spec_items()
    items = parse_items(spec_items)

    while len(items) > 0:
        pending.put(items.pop())

    with ThreadPoolExecutor(max_workers=2) as executor:

        executor.submit(dispatcher, thread_id="dispatcher")
        executor.submit(tracker, thread_id="tracker")

        sleep(30)
        while not pending.empty() or len(in_progress.keys()) > 0:

            print(
                f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - {pending.qsize()} pending, {len(in_progress.keys())} in progress, {done.qsize()} done"
            )
            sleep(5)
            if datetime.now(timezone.utc) >= total_deadline:
                print(
                    f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Total timeout reached"
                )
                break

        stop.set()
        print(f"{datetime.now(timezone.utc).strftime(TIME_FORMAT)} - thread {thread_id:<12} - Raised stop event...")

    reduce_summarize(spec_items)


if __name__ == "__main__":
    main()
