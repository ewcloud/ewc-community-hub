#!/usr/bin/env python3
# Orchestration for downstream concurrent test deployment workflows.

# Filtering Methods
# Items to be tested are filtered by a combination (logical AND operation) of the following conditions:
# 1. the value of the `ITEM_TECHNOLOGY_ANNOTATIONS`env var is equivalent to the `annotations[].technology` attribute values
# 2. the value of the `ITEM_OTHERS_ANNOTATIONS`env var is equivalent of the `annotations[].others` attribute values
# 3. the presence of the `values` attribute in the Item's metadata
# 4. (optional) the `items.<item key>.name` attribute values is in the list of names in the `ITEM_NAMES`env var, if set
#
# Deployment Methods
# Tests are dispatched according to the metadata annotations `others`. The deployment options include Items' native (Ansible CLI,
# Terraform CLI, etc.) OR EWCCLI:
#
# 1. Native: If deploying Items via their native method, the orchestrator forwards as input any attributes/values of the
# `items.<item key>.values` metadata within `items.yaml` BUT adding a mutation: `inputSpec` attributed is serialized and
# forwarded downstream as JSON-string with attribute name `inputSpecJson`. See example compatible downstream workflow file at
# https://github.com/ewcloud/ewc-ansible-playbook-flavours-and-provisioning/blob/76abcbad92b9122866c91d9ed1d9a0b35dc490e3/.github/workflows/test-ecmwf.yml#L1-L95
#
# 2. EWCCLI: If deploying via the EWCCLI, the orchestrator only forwards the Item name and the git ref of the branch where the
# orchestrator was triggered. Any additional attributes/values are parsed by the EWCCLI directly from the catalog in the downstream
# workflow. See example compatible downstream workflow file at
# https://github.com/ewcloud/ewccli/blob/3405f8bf2aa458c5efaca8d646dff0a54d7191ee/.github/workflows/test-deployment-ansible-ecmwf.yml#L1-L63


from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from json import dumps as json_dumps
from os import environ, getenv
from queue import Queue, Empty
from pathlib import Path
from requests import request, Response
from time import sleep
from threading import Event
from typing import Any
from yaml import safe_load as yaml_safe_load

GH_API_TOKEN = environ["GH_API_TOKEN"]
GH_DOWNSTREAM_WORKFLOW_FILE = environ["GH_DOWNSTREAM_WORKFLOW_FILE"]
ITEM_NAMES = getenv("ITEM_NAMES", "")
ITEM_TECHNOLOGY_ANNOTATIONS = getenv("ITEM_TECHNOLOGY_ANNOTATIONS", "Ansible Playbook")
ITEM_OTHERS_ANNOTATIONS = getenv("ITEM_OTHERS_ANNOTATIONS", "Deployable")
POLLING_INTERVAL_SECONDS = int(environ["POLLING_INTERVAL_SECONDS"])
RUN_TIMEOUT_MINUTES = int(environ["RUN_TIMEOUT_MINUTES"])
TOTAL_TIMEOUT_MINUTES = int(environ["TOTAL_TIMEOUT_MINUTES"])
MAX_CONCURRENT_WORKFLOWS = int(environ["MAX_CONCURRENT_WORKFLOWS"])

API_BASE = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GH_API_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

CATALOG_FILE = f"{environ['GITHUB_WORKSPACE']}/items.yaml"
SUMMARY_TEMPLATE_FILE = f"{environ['GITHUB_WORKSPACE']}/.github/scripts/orchestrator/summary.template.md"

EWCCLI_ANNOTATION = "EWCCLI-compatible"
EWCCLI_GH_API_REPO_ENDPOINT = "ewcloud/ewccli"

RED_LIGHT = "🔴"
YELLOW_LIGHT = "🟡"
GREEN_LIGHT = "🟢"
GRAY_LIGHT = "⚫"

#  --- Global Runtime State ---

pending: Queue = Queue()
in_progress: Queue = Queue(maxsize=MAX_CONCURRENT_WORKFLOWS)
done: Queue = Queue()
stop: Event = Event()

# --- Utilities ---


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


def github_api(method: str, path: str, payload: dict | Any = None) -> Response:
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


# --- Subroutines ---


def read_spec_items() -> dict:
    with open(CATALOG_FILE) as f:
        catalog = yaml_safe_load(f)

    if ITEM_NAMES:
        filtered_item_names = set(item_name.strip() for item_name in ITEM_NAMES.split(","))
        print(f"main thread - Reading Items with names: {filtered_item_names}", flush=True)

    filtered_item_technology_annotations = set(
        technology_annotation.strip() for technology_annotation in ITEM_TECHNOLOGY_ANNOTATIONS.split(",")
    )
    print(
        f"main thread - Reading Items with technology annotations: {filtered_item_technology_annotations}", flush=True
    )

    filtered_item_others_annotations = set(
        others_annotation.strip() for others_annotation in ITEM_OTHERS_ANNOTATIONS.split(",")
    )
    print(f"main thread - Reading Items with others annotations: {filtered_item_others_annotations}", flush=True)

    spec_items = {}

    for key, item in catalog["spec"]["items"].items():

        name = item.get("name")
        if ITEM_NAMES and name not in filtered_item_names:
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
        print("::warning::main thread - Item name and annotation filtering returned no matches!", flush=True)

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
        owner, repo = repo_url.rstrip(".git").split("/")[-2:]

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
        item = pending.get(timeout=1)
    except Empty:
        return

    dispatch_delay_seconds = 5
    item.dispatch_time = datetime.now(timezone.utc)
    max_dispatch_time = item.dispatch_time + timedelta(seconds=dispatch_delay_seconds)

    if EWCCLI_ANNOTATION in ITEM_OTHERS_ANNOTATIONS:
        dispatch = github_api(
            "POST",
            f"/repos/{EWCCLI_GH_API_REPO_ENDPOINT}/actions/workflows/{GH_DOWNSTREAM_WORKFLOW_FILE}/dispatches",
            {"ref": "main", "inputs": {"itemName": item.name, "catalogRef": f"{environ['GITHUB_HEAD_REF']}"}},
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
        f"{thread_id} thread - Sent dispatch request for '{item}'",
        flush=True,
    )

    try:
        dispatch.raise_for_status()
    except Exception as e:
        print(
            f"::warning::{thread_id} thread - Failed to dispatch workflow for '{item}' with exception '{e}'", flush=True
        )
        move_to_done(
            item,
            "DISPATCH_FAILED",
            f"HTTP request failed with code {dispatch.status_code}",
        )
        return

    buffer_seconds = 1
    sleep(dispatch_delay_seconds + buffer_seconds)

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
        f"{thread_id} thread - Sent register request for '{item}'",
        flush=True,
    )

    try:
        runs.raise_for_status()
    except Exception as e:
        print(
            f"::warning::{thread_id} thread - Failed to register workflow run for '{item}' with exception: '{e}'",
            flush=True,
        )
        move_to_done(item, "REGISTER_FAILED", f"HTTP request failed with code {runs.status_code}")
        return

    runs = runs.json()
    runs = runs.get("workflow_runs", [])
    runs_count = len(runs)

    print(
        f"{thread_id} thread - Registering {runs_count} run(s): '{json_dumps(runs, indent=4)[:1000]}...'",
        flush=True,
    )

    match runs_count:

        case 0:
            print(f"::warning::{thread_id} thread - Failed to register workflow for item '{item}'", flush=True)
            move_to_done(item, "REGISTER_FAILED", f"No runs match registration criteria for {item.name}")

        case 1:
            item.run_id = runs[0]["id"]
            item.state = "REGISTERED"
            in_progress.put(item)

        case _:
            print(
                f"::warning::{thread_id} thread - Multiple runs match registration criteria for '{item}'",
                flush=True,
            )
            move_to_done(item, "REGISTER_FAILED", f"Multiple possible runs for {item.name}")


def check_status(thread_id: str) -> None:
    try:
        item = in_progress.get(timeout=1)
    except Empty:
        return

    item.state = "RUNNING"

    if stop.is_set():
        move_to_done(item, "TIMED_OUT", "Total deadline reached")
        return

    run_deadline = item.dispatch_time + timedelta(minutes=RUN_TIMEOUT_MINUTES)
    if datetime.now(timezone.utc) >= run_deadline:
        move_to_done(item, "TIMED_OUT", "Per-run deadline reached")
        return

    if EWCCLI_ANNOTATION in ITEM_OTHERS_ANNOTATIONS:
        run = github_api("GET", f"/repos/{EWCCLI_GH_API_REPO_ENDPOINT}/actions/runs/{item.run_id}")
    else:
        run = github_api("GET", f"/repos/{item.owner}/{item.repo}/actions/runs/{item.run_id}")

    print(
        f"{thread_id} thread - Sent check request for '{item}'",
        flush=True,
    )

    try:
        run.raise_for_status()
    except Exception as e:
        print(
            f"::warning::{thread_id} thread - Failed to check status for {item.name} (run ID: '{item.run_id}') with exception: '{e}'",
            flush=True,
        )
        in_progress.put(item)
        return

    run = run.json()

    print(
        f"{thread_id} thread - Checking run: '{json_dumps(run, indent=4)[:1000]}...'",
        flush=True,
    )

    status = run["status"]
    conclusion = run["conclusion"]

    if status == "completed":
        item.conclusion = conclusion
        move_to_done(item, "COMPLETED" if conclusion == "success" else "FAILED")
    else:
        in_progress.put(item)


def reduce_summarize(spec_items: dict) -> None:
    print(f"main thread - {pending.qsize()} pending, {in_progress.qsize()} in progress, {done.qsize()} done")

    for q in (pending, in_progress):
        while not q.empty():
            item = q.get_nowait()
            move_to_done(item, "TIMED_OUT", "Total deadline reached")

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
            f"::warning::main thread - Unable to parse site from GH_DOWNSTREAM_WORKFLOW_FILE. By convention, the workflow filename should include any of: ['ecmwf', 'eumetsat']. Got: '{GH_DOWNSTREAM_WORKFLOW_FILE}'"
        )

    status_rows = []
    for item in items:
        state_viz = {
            "PLANNED": f"`planning` {GRAY_LIGHT}",
            "DISPATCH_FAILED": f"`dispatching denied` {GRAY_LIGHT}",
            "REGISTER_FAILED": f"`registering` {GRAY_LIGHT}",
            "COMPLETED": f" `passing` {GREEN_LIGHT}",
            "FAILED": f" `failing` {RED_LIGHT}",
            "TIMED_OUT": f"`timing out` {YELLOW_LIGHT}",
        }.get(item.state, f"`unknown` {GRAY_LIGHT}")

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
        print(f"::error::main thread - Cannot find summary template at {template_path}", flush=True)
        return

    try:
        template_content = template_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"::error::main thread - Failed to read template: {e}", flush=True)
        return

    summary_contents = template_content.format(
        github_run_id=environ["GITHUB_RUN_ID"],
        github_ref_name=environ["GITHUB_HEAD_REF"],
        site=site,
        status_row=status_table_content,
        execution_plan=json_dumps(spec_items, indent=2),
    )

    summary_path = Path(environ["GITHUB_STEP_SUMMARY"])
    try:
        summary_path.write_text(summary_contents, encoding="utf-8")
    except Exception as e:
        print(f"::error::main thread - Failed to write summary: {e}", flush=True)


# --- Worker Thread ---


def dispatcher(thread_id: str) -> None:

    print(f"{thread_id} thread - Starting thread", flush=True)

    while not stop.is_set():

        if in_progress.full():
            print(
                f"{thread_id} thread - Max concurrency reached. Will wait before dispatching new workflows...",
                flush=True,
            )
            sleep(10)
            continue

        try:
            dispatch_and_register(thread_id)
        except Exception as e:
            print(
                f"::error::{thread_id} thread - Failed to dispatch workflow due to an unexpected error: {e}", flush=True
            )
            raise e

    print(f"{thread_id} thread - Caught stop event. Exiting... ", flush=True)


def checker(thread_id: str) -> None:
    print(f"{thread_id} thread - Starting thread", flush=True)

    while not stop.is_set():

        try:
            check_status(thread_id)
            sleep(POLLING_INTERVAL_SECONDS)
        except Exception as e:
            print(
                f"::error::{thread_id} thread - Failed to check for workflow status due to an unexpected error: {e}",
                flush=True,
            )
            raise e

    print(f"{thread_id} thread - Caught stop event. Exiting... ", flush=True)


# --- Main Thread ---


def main() -> None:
    start_time = datetime.now(timezone.utc)
    buffer_minutes = 2
    total_deadline = (
        start_time + timedelta(minutes=TOTAL_TIMEOUT_MINUTES) - timedelta(minutes=buffer_minutes)
    )  # include few mins of buffer to have time for wrap up before the runtime force-quits

    spec_items = read_spec_items()
    items = parse_items(spec_items)
    items_count = len(items)

    while len(items) > 0:
        pending.put(items.pop())

    max_workers = (
        min(MAX_CONCURRENT_WORKFLOWS, items_count) + 1
    )  # include 1 additional worker to take owner ship of workflow dispatching and run id retrieving
    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        executor.submit(dispatcher, thread_id="dispatcher-0")

        for i in range(max_workers - 1):
            executor.submit(checker, thread_id=f"checker-{i}")

        sleep(30)
        while not pending.empty() or not in_progress.empty():

            print(f"main thread - {pending.qsize()} pending, {in_progress.qsize()} in progress, {done.qsize()} done")
            sleep(5)
            if datetime.now(timezone.utc) >= total_deadline:
                print("main thread - Total timeout reached")
                break

        stop.set()
        print("main thread - Raised stop event...")
        sleep(30)

    reduce_summarize(spec_items)


if __name__ == "__main__":
    main()
