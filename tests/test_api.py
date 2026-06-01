from pathlib import Path
import sys

import pandas as pd
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from main import app

client = TestClient(app)


def reset_state() -> None:
    app.state.project_data = None


def seed_project_data() -> None:
    tasks = pd.DataFrame(
        [
            {
                "task_id": 1,
                "task_name": "Design",
                "wbs_id": 10,
                "target_cost": 100.0,
                "planned_value": 40.0,
                "earned_value": 40.0,
                "total_float_days": 0.0,
                "constraint_type": "ASAP",
                "target_duration": 5.0,
                "last_recalc_date": pd.Timestamp("2026-02-15"),
                "act_end_date": pd.Timestamp("2026-02-10"),
            },
            {
                "task_id": 2,
                "task_name": "Build",
                "wbs_id": 10,
                "target_cost": 150.0,
                "planned_value": 60.0,
                "earned_value": 50.0,
                "total_float_days": 0.0,
                "constraint_type": "MSO",
                "target_duration": 10.0,
                "last_recalc_date": pd.Timestamp("2026-02-15"),
                "act_end_date": pd.Timestamp("2026-02-12"),
            },
            {
                "task_id": 3,
                "task_name": "Test",
                "wbs_id": 10,
                "target_cost": 80.0,
                "planned_value": 20.0,
                "earned_value": 10.0,
                "total_float_days": 0.0,
                "constraint_type": "ASAP",
                "target_duration": 4.0,
                "last_recalc_date": pd.Timestamp("2026-02-15"),
                "act_end_date": pd.Timestamp("2026-02-15"),
            },
            {
                "task_id": 4,
                "task_name": "Packaging",
                "wbs_id": 20,
                "target_cost": 60.0,
                "planned_value": 10.0,
                "earned_value": 5.0,
                "total_float_days": 3.0,
                "constraint_type": "ASAP",
                "target_duration": 3.0,
                "last_recalc_date": pd.Timestamp("2026-02-15"),
                "act_end_date": pd.Timestamp("2026-02-18"),
            },
        ]
    )
    app.state.project_data = {
        "original": None,
        "updated": {
            "filename": "updated.xer",
            "tables": {
                "TASK": tasks,
                "PROJWBS": pd.DataFrame(
                    [
                        {"wbs_id": 10, "wbs_name": "Civil"},
                        {"wbs_id": 20, "wbs_name": "Mechanical"},
                    ]
                ),
                "TASKACTV": pd.DataFrame(
                    [
                        {"task_id": 1, "activity_code": "CON"},
                        {"task_id": 2, "activity_code": "CON"},
                        {"task_id": 3, "activity_code": "CON"},
                        {"task_id": 4, "activity_code": "CIV"},
                    ]
                ),
                "TASKPRED": pd.DataFrame(
                    [
                        {"task_id": 2, "pred_task_id": 1},
                        {"task_id": 3, "pred_task_id": 2},
                    ]
                ),
            },
        },
    }


def test_critical_path_returns_400_before_upload():
    reset_state()
    response = client.get("/api/critical-path")
    assert response.status_code == 400
    assert response.json()["detail"] == "No project data uploaded yet."


def test_critical_path_returns_longest_chain_and_filters():
    reset_state()
    seed_project_data()

    response = client.get("/api/critical-path?date_window=all&activity_code=all")
    assert response.status_code == 200
    payload = response.json()

    assert payload["source"] == "updated_xer"
    assert payload["filters"] == {"date_window": "all", "activity_code": "all"}
    assert payload["summary"]["total_tasks"] == 4
    assert payload["summary"]["critical_path_duration_days"] == 19.0
    assert payload["summary"]["critical_path_task_count"] == 3
    assert payload["critical_path_task_ids"] == [1, 2, 3]
    assert payload["critical_path_task_names"] == ["Design", "Build", "Test"]
    assert payload["near_critical_task_ids"] == [4]
    assert payload["near_critical_task_names"] == ["Packaging"]


def test_critical_path_respects_activity_code_filter():
    reset_state()
    seed_project_data()

    response = client.get("/api/critical-path?date_window=all&activity_code=civ")
    assert response.status_code == 200
    payload = response.json()

    assert payload["filters"] == {"date_window": "all", "activity_code": "civ"}
    assert payload["summary"]["total_tasks"] == 1
    assert payload["summary"]["critical_path_duration_days"] == 3.0
    assert payload["critical_path_task_ids"] == [4]
    assert payload["critical_path_task_names"] == ["Packaging"]
    assert payload["near_critical_task_ids"] == []
