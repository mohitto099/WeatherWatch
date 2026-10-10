"""
status.py
---------
Turns Airflow's run + task states into the simple stage model the React
step-tracker displays. Pure logic (no network), so it is easy to test.

Airflow task            -> user-facing stage
extract_validate        -> "Fetching weather data"
transform_quality_check -> "Cleaning and validating"
load                    -> "Saving to database"
log_result              -> "Finalizing"
"""

STAGES = [
    ("extract_validate", "fetching", "Fetching weather data"),
    ("transform_quality_check", "cleaning", "Cleaning and validating"),
    ("load", "saving", "Saving to database"),
    ("log_result", "finalizing", "Finalizing"),
]

# Airflow task state -> stage state shown in the UI
_ACTIVE = {"running", "restarting", "up_for_retry", "up_for_reschedule", "deferred"}
_FAILED = {"failed"}
_SKIPPED = {"upstream_failed", "skipped"}


def _stage_state(airflow_state: str | None) -> str:
    if airflow_state == "success":
        return "done"
    if airflow_state in _ACTIVE:
        return "active"
    if airflow_state in _FAILED:
        return "failed"
    if airflow_state in _SKIPPED:
        return "skipped"
    return "pending"   # queued, scheduled, none, no_status, not created yet


def build_status(run_state: str, task_instances: list[dict]) -> dict:
    by_task = {ti["task_id"]: ti.get("state") for ti in task_instances}

    stages = [
        {"id": stage_id, "label": label, "state": _stage_state(by_task.get(task_id))}
        for task_id, stage_id, label in STAGES
    ]

    if run_state == "success":
        for s in stages:
            s["state"] = "done"
        return {"status": "done", "current_stage": None, "message": "Done", "stages": stages}

    failed = next((s for s in stages if s["state"] == "failed"), None)

    # A failed task means the run is lost, even in the moment before Airflow flips the run state.
    if run_state == "failed" or failed:
        where = failed["label"].lower() if failed else "the pipeline"
        return {
            "status": "failed",
            "current_stage": failed["id"] if failed else None,
            "message": f"Something went wrong while {where}",
            "stages": stages,
        }

    # queued / running: the current stage is the active one, else the first not-yet-done one
    current = next((s for s in stages if s["state"] == "active"), None)
    if current is None:
        current = next((s for s in stages if s["state"] == "pending"), None)

    if run_state == "queued" and not any(s["state"] in ("active", "done") for s in stages):
        return {"status": "queued", "current_stage": None, "message": "Starting pipeline...", "stages": stages}

    return {
        "status": "running",
        "current_stage": current["id"] if current else None,
        "message": f"{current['label']}..." if current else "Working...",
        "stages": stages,
    }
