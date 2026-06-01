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
    original_tasks = pd.DataFrame(
        [
            {
                "task_id": 1,
                "task_name": "Mobilization",
                "wbs_id": 10,
                "target_cost": 100.0,
                "planned_value": 40.0,
                "earned_value": 30.0,
                "total_float_days": 10.0,
                "constraint_type": "ASAP",
                "last_recalc_date": pd.Timestamp("2026-02-15"),
                "act_end_date": pd.Timestamp("2026-02-10"),
            },
            {
                "task_id": 2,
                "task_name": "Foundations",
                "wbs_id": 10,
                "target_cost": 150.0,
                "planned_value": 60.0,
                "earned_value": 40.0,
                "total_float_days": -2.0,
                "constraint_type": "MSO",
                "last_recalc_date": pd.Timestamp("2026-02-15"),
                "act_end_date": pd.Timestamp("2026-02-12"),
            },
            {
                "task_id": 3,
                "task_name": "Testing",
                "wbs_id": 20,
                "target_cost": 50.0,
                "planned_value": 20.0,
                "earned_value": 20.0,
                "total_float_days": 5.0,
                "constraint_type": "ASAP",
                "last_recalc_date": pd.Timestamp("2026-02-15"),
                "act_end_date": pd.Timestamp("2026-02-15"),
            },
        ]
    )

    updated_tasks = pd.DataFrame(
        [
            {
                "task_id": 1,
                "task_name": "Mobilization",
                "wbs_id": 10,
                "target_cost": 110.0,
                "planned_value": 50.0,
                "earned_value": 35.0,
                "total_float_days": 8.0,
                "constraint_type": "ASAP",
                "last_recalc_date": pd.Timestamp("2026-02-15"),
                "act_end_date": pd.Timestamp("2026-02-10"),
            },
            {
                "task_id": 2,
                "task_name": "Foundations",
                "wbs_id": 10,
                "target_cost": 150.0,
                "planned_value": 70.0,
                "earned_value": 60.0,
                "total_float_days": -2.0,
                "constraint_type": "MSO",
                "last_recalc_date": pd.Timestamp("2026-02-15"),
                "act_end_date": pd.Timestamp("2026-02-12"),
            },
            {
                "task_id": 3,
                "task_name": "Testing",
                "wbs_id": 20,
                "target_cost": 50.0,
                "planned_value": 20.0,
                "earned_value": 20.0,
                "total_float_days": 5.0,
                "constraint_type": "ASAP",
                "last_recalc_date": pd.Timestamp("2026-02-15"),
                "act_end_date": pd.Timestamp("2026-02-15"),
            },
            {
                "task_id": 4,
                "task_name": "Commissioning",
                "wbs_id": 20,
                "target_cost": 70.0,
                "planned_value": 20.0,
                "earned_value": 15.0,
                "total_float_days": 2.0,
                "constraint_type": "ASAP",
                "last_recalc_date": pd.Timestamp("2026-02-15"),
                "act_end_date": pd.Timestamp("2026-02-18"),
            },
        ]
    )

    app.state.project_data = {
        "original": {
            "filename": "baseline.xer",
            "tables": {
                "TASK": original_tasks,
                "PROJWBS": pd.DataFrame(
                    [
                        {"wbs_id": 10, "wbs_name": "Civil"},
                        {"wbs_id": 20, "wbs_name": "Mechanical"},
                    ]
                ),
                "TASKACTV": pd.DataFrame(
                    [
                        {"task_id": 1, "activity_code": "CON"},
                        {"task_id": 2, "activity_code": "CIV"},
                        {"task_id": 3, "activity_code": "CON"},
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
        "updated": {
            "filename": "updated.xer",
            "tables": {
                "TASK": updated_tasks,
                "PROJWBS": pd.DataFrame(
                    [
                        {"wbs_id": 10, "wbs_name": "Civil"},
                        {"wbs_id": 20, "wbs_name": "Mechanical"},
                    ]
                ),
                "TASKACTV": pd.DataFrame(
                    [
                        {"task_id": 1, "activity_code": "CON"},
                        {"task_id": 2, "activity_code": "CIV"},
                        {"task_id": 3, "activity_code": "CON"},
                        {"task_id": 4, "activity_code": "CON"},
                    ]
                ),
                "TASKPRED": pd.DataFrame(
                    [
                        {"task_id": 2, "pred_task_id": 1},
                        {"task_id": 3, "pred_task_id": 2},
                        {"task_id": 4, "pred_task_id": 3},
                    ]
                ),
            },
        },
    }


def test_baseline_compare_returns_400_before_upload():
    reset_state()
    response = client.get("/api/baseline-compare")
    assert response.status_code == 400
    assert response.json()["detail"] == "No project data uploaded yet."


def test_baseline_compare_returns_original_updated_and_delta():
    reset_state()
    seed_project_data()

    response = client.get("/api/baseline-compare?date_window=all&activity_code=all")
    assert response.status_code == 200
    payload = response.json()

    assert payload["source"] == "updated_vs_original"
    assert payload["filters"] == {"date_window": "all", "activity_code": "all"}

    assert payload["original"]["task_count"] == 3
    assert payload["updated"]["task_count"] == 4
    assert payload["original"]["total_budget"] == 300.0
    assert payload["updated"]["total_budget"] == 380.0
    assert payload["delta"]["total_budget"] == 80.0
    assert payload["original"]["planned_value"] == 120.0
    assert payload["updated"]["planned_value"] == 160.0
    assert payload["delta"]["planned_value"] == 40.0
    assert payload["original"]["earned_value"] == 90.0
    assert payload["updated"]["earned_value"] == 130.0
    assert payload["delta"]["earned_value"] == 40.0
    assert payload["original"]["spi"] == 0.75
    assert payload["updated"]["spi"] == 0.8125
    assert payload["delta"]["spi"] == 0.0625

    assert payload["task_changes"]["added"] == [4]
    assert payload["task_changes"]["removed"] == []
    assert payload["task_changes"]["modified"] == [1, 2]


def test_baseline_compare_applies_activity_code_filter():
    reset_state()
    seed_project_data()

    response = client.get("/api/baseline-compare?date_window=all&activity_code=con")
    assert response.status_code == 200
    payload = response.json()

    assert payload["filters"] == {"date_window": "all", "activity_code": "con"}
    assert payload["original"]["task_count"] == 2
    assert payload["updated"]["task_count"] == 3
    assert payload["original"]["total_budget"] == 150.0
    assert payload["updated"]["total_budget"] == 230.0
    assert payload["delta"]["total_budget"] == 80.0
    assert payload["task_changes"]["added"] == [4]
    assert payload["task_changes"]["removed"] == []
    assert payload["task_changes"]["modified"] == [1]
