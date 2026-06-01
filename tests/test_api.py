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
    app.state.project_data = {
        "original": None,
        "updated": {
            "filename": "sample.xer",
            "tables": {
                "TASK": pd.DataFrame(
                    [
                        {
                            "task_id": 1,
                            "task_name": "Mobilization",
                            "wbs_id": 10,
                            "target_cost": 100.0,
                            "planned_value": 50.0,
                            "earned_value": 60.0,
                            "total_float_days": 5.0,
                            "constraint_type": "ASAP",
                            "last_recalc_date": pd.Timestamp("2026-02-15"),
                            "act_end_date": pd.Timestamp("2026-02-10"),
                        },
                        {
                            "task_id": 2,
                            "task_name": "Foundations",
                            "wbs_id": 10,
                            "target_cost": 150.0,
                            "planned_value": 80.0,
                            "earned_value": 70.0,
                            "total_float_days": -2.0,
                            "constraint_type": "MSO",
                            "last_recalc_date": pd.Timestamp("2026-02-15"),
                            "act_end_date": pd.Timestamp("2026-02-18"),
                        },
                        {
                            "task_id": 3,
                            "task_name": "Testing",
                            "wbs_id": 20,
                            "target_cost": 120.0,
                            "planned_value": 40.0,
                            "earned_value": 10.0,
                            "total_float_days": 60.0,
                            "constraint_type": "ASAP",
                            "last_recalc_date": pd.Timestamp("2026-02-15"),
                            "act_end_date": pd.Timestamp("2026-02-20"),
                        },
                    ]
                ),
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
                        {"task_id": 3, "activity_code": "CIV"},
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


def test_evm_kpis_returns_400_before_upload():
    reset_state()

    response = client.get("/api/evm-kpis")

    assert response.status_code == 400
    assert response.json()["detail"] == "No project data uploaded yet."


def test_evm_kpis_supports_date_window_and_activity_code_filters():
    reset_state()
    seed_project_data()

    response = client.get("/api/evm-kpis?date_window=all&activity_code=all")
    assert response.status_code == 200
    assert response.json() == {
        "total_budget": 370.0,
        "planned_value": 170.0,
        "earned_value": 140.0,
        "spi": 0.8235,
        "source": "updated_xer",
    }

    filtered_response = client.get("/api/evm-kpis?date_window=all&activity_code=con")
    assert filtered_response.status_code == 200
    assert filtered_response.json() == {
        "total_budget": 250.0,
        "planned_value": 130.0,
        "earned_value": 130.0,
        "spi": 1.0,
        "source": "updated_xer",
    }


def test_s_curve_returns_400_before_upload():
    reset_state()

    response = client.get("/api/s-curve")

    assert response.status_code == 400
    assert response.json()["detail"] == "No project data uploaded yet."


def test_s_curve_returns_filtered_series_and_activity_codes():
    reset_state()
    seed_project_data()

    response = client.get("/api/s-curve")
    assert response.status_code == 200
    assert sorted(response.json()["activity_codes"], key=lambda item: item["value"]) == sorted(
        [
            {"value": "all", "label": "All Activity Codes", "count": 3},
            {"value": "CIV", "label": "CIV", "count": 1},
            {"value": "CON", "label": "CON", "count": 2},
        ],
        key=lambda item: item["value"],
    )

    filtered_response = client.get("/api/s-curve?date_window=all&activity_code=con")
    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert filtered_payload["dates"] == ["2026-02-15", "2026-02-18", "2026-02-20"]
    assert filtered_payload["planned_value"] == [50.0, 80.0, 0.0]
    assert filtered_payload["earned_value"] == [60.0, 70.0, 0.0]
    assert filtered_payload["wbs_weights"] == [
        {"wbs_id": 10, "label": "Civil", "weight": 100.0, "budget": 250.0},
    ]


def test_schedule_health_returns_400_before_upload():
    reset_state()

    response = client.get("/api/schedule-health")

    assert response.status_code == 400
    assert response.json()["detail"] == "No project data uploaded yet."
