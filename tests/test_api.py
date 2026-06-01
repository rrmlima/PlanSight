from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_project_data():
    main.app.state.project_data = None
    yield
    main.app.state.project_data = None


SAMPLE_XER_WITH_COSTS = """%T\tTASK
%F\ttask_id\ttask_name\twbs_id\ttarget_cost\tplanned_value\tearned_value\tactual_cost\ttotal_float_days\tconstraint_type\ttarget_duration\tlast_recalc_date\tact_end_date
%R\t1\tDesign\t10\t100\t40\t40\t30\t0\tASAP\t5\t2026-02-15\t2026-02-10
%R\t2\tBuild\t10\t150\t60\t50\t55\t0\tMSO\t10\t2026-02-15\t2026-02-12
%R\t3\tTest\t10\t80\t20\t10\t15\t0\tASAP\t4\t2026-02-15\t2026-02-15
%R\t4\tPackaging\t20\t60\t10\t5\t7\t3\tASAP\t3\t2026-02-15\t2026-02-18
%T\tPROJWBS
%F\twbs_id\twbs_name
%R\t10\tCivil
%R\t20\tMechanical
%T\tTASKACTV
%F\ttask_id\tactivity_code
%R\t1\tCON
%R\t2\tCON
%R\t3\tCON
%R\t4\tCIV
%T\tTASKPRED
%F\ttask_id\tpred_task_id
%R\t2\t1
%R\t3\t2
"""


@pytest.fixture()
def uploaded_project_with_costs():
    files = {
        "original_xer": ("baseline.xer", SAMPLE_XER_WITH_COSTS.encode("utf-8"), "text/plain"),
        "updated_xer": ("updated.xer", SAMPLE_XER_WITH_COSTS.encode("utf-8"), "text/plain"),
    }
    response = client.post("/upload", files=files)
    assert response.status_code == 200, response.text
    return response.json()


def test_evm_kpis_requires_upload():
    response = client.get("/api/evm-kpis")
    assert response.status_code == 400
    assert "No project data" in response.json()["detail"]


def test_evm_kpis_exposes_actual_cost_and_cpi(uploaded_project_with_costs):
    response = client.get("/api/evm-kpis?date_window=all&activity_code=all")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["source"] == "updated_xer"
    assert body["total_budget"] == pytest.approx(390.0)
    assert body["planned_value"] == pytest.approx(130.0)
    assert body["earned_value"] == pytest.approx(105.0)
    assert body["actual_cost"] == pytest.approx(107.0)
    assert body["spi"] == pytest.approx(0.8077, rel=1e-4)
    assert body["cpi"] == pytest.approx(0.9813, rel=1e-4)
