from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
import xlsxwriter
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.xer_parser import XERParser


app = FastAPI(title="PlanSight Local API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.project_data = None


EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _parse_uploaded_xer(upload: UploadFile) -> dict[str, pd.DataFrame]:
    parser = XERParser(file_path=upload.filename or "<memory>")
    content = upload.file.read()
    if not content:
        raise HTTPException(status_code=400, detail=f"Uploaded file is empty: {upload.filename}")
    return parser.parse_bytes(content)


def _table_snapshot(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    tasks = tables.get("TASK", pd.DataFrame())
    return {
        "tables": sorted(tables.keys()),
        "task_count": int(len(tasks.index)),
    }


def _first_matching_series(df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    normalized = {column.lower(): column for column in df.columns}
    for candidate in candidates:
        if candidate.lower() in normalized:
            column = normalized[candidate.lower()]
            return pd.to_numeric(df[column], errors="coerce").fillna(0)
    return None


def _sum_matching_series(df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    normalized = {column.lower(): column for column in df.columns}
    series_list: list[pd.Series] = []
    for candidate in candidates:
        if candidate.lower() in normalized:
            column = normalized[candidate.lower()]
            series_list.append(pd.to_numeric(df[column], errors="coerce").fillna(0))
    if not series_list:
        return None
    total = series_list[0].copy()
    for series in series_list[1:]:
        total = total.add(series, fill_value=0)
    return total.fillna(0)


def _first_matching_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    normalized = {column.lower(): column for column in df.columns}
    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]
    return None


def _first_matching_datetime_series(df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    column = _first_matching_column(df, candidates)
    if column is None:
        return None
    parsed = pd.to_datetime(df[column], errors="coerce")
    if parsed.notna().any():
        return parsed
    return None


def _calculate_evm_kpis(tasks: pd.DataFrame) -> dict[str, float]:
    if tasks.empty:
        return {
            "total_budget": 0.0,
            "planned_value": 0.0,
            "earned_value": 0.0,
            "actual_cost": 0.0,
            "spi": None,
            "cpi": None,
        }

    budget_series = _first_matching_series(
        tasks,
        ["target_cost", "at_completion_total_cost", "budget_at_completion", "total_cost"],
    )
    if budget_series is None:
        budget_series = pd.Series([0.0] * len(tasks.index), dtype="float64")

    planned_value_series = _first_matching_series(tasks, ["planned_value", "bcws"])
    if planned_value_series is None:
        planned_value_series = pd.Series([0.0] * len(tasks.index), dtype="float64")

    earned_value_series = _first_matching_series(tasks, ["earned_value", "bcwp"])
    if earned_value_series is None:
        progress_series = _first_matching_series(
            tasks,
            ["phys_complete_pct", "task_complete_pct", "complete_pct", "percent_complete"],
        )
        if progress_series is not None:
            earned_value_series = budget_series * (progress_series / 100.0)
        else:
            earned_value_series = pd.Series([0.0] * len(tasks.index), dtype="float64")

    actual_cost_series = _sum_matching_series(
        tasks,
        [
            "actual_cost",
            "act_cost",
            "act_reg_cost",
            "act_labor_cost",
            "act_mat_cost",
            "act_equip_cost",
            "actual_expense",
        ],
    )
    if actual_cost_series is None:
        actual_cost_series = pd.Series([0.0] * len(tasks.index), dtype="float64")

    total_budget = round(float(budget_series.sum()), 2)
    planned_value = round(float(planned_value_series.sum()), 2)
    earned_value = round(float(earned_value_series.sum()), 2)
    actual_cost = round(float(actual_cost_series.sum()), 2)
    spi = round(earned_value / planned_value, 4) if planned_value else None
    cpi = round(earned_value / actual_cost, 4) if actual_cost else None

    return {
        "total_budget": total_budget,
        "planned_value": planned_value,
        "earned_value": earned_value,
        "actual_cost": actual_cost,
        "spi": spi,
        "cpi": cpi,
    }


def _resolve_data_date(tasks: pd.DataFrame, taskactv: pd.DataFrame) -> pd.Timestamp | None:
    for frame in [taskactv, tasks]:
        if frame is None or frame.empty:
            continue
        for candidates in [
            ["data_date", "last_recalc_date", "status_date", "update_date"],
            ["act_end_date", "actual_end_date", "completion_date"],
            ["target_end_date", "planned_end_date", "end_date"],
        ]:
            series = _first_matching_datetime_series(frame, candidates)
            if series is not None:
                valid = series.dropna()
                if not valid.empty:
                    return valid.max().normalize()
    return None


def _normalize_dashboard_filter_value(value: str | None) -> str:
    if value is None:
        return "all"
    normalized = str(value).strip()
    return normalized.lower() if normalized else "all"


def _normalize_text_value(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _preferred_activity_code_column(df: pd.DataFrame) -> str | None:
    preferred = [
        "activity_code",
        "activity_code_value",
        "actv_code_name",
        "code_value",
        "code_name",
        "code",
        "actv_code",
        "actv_code_id",
    ]
    column = _first_matching_column(df, preferred)
    if column is not None:
        return column

    ignore_tokens = ("task", "pred", "succ", "wbs", "date", "cost", "value", "float", "pct", "percent", "budget", "earned", "planned", "actual", "start", "end", "resource")
    for candidate in df.columns:
        lower = candidate.lower()
        if any(token in lower for token in ignore_tokens):
            continue
        non_null = df[candidate].dropna()
        if non_null.empty:
            continue
        if non_null.astype(str).map(lambda value: len(value.strip()) > 0).any():
            return candidate
    return None


def _build_activity_code_catalog(taskactv: pd.DataFrame, actvcode: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = [{"value": "all", "label": "All Activity Codes", "count": 0}]
    frames = [frame for frame in [taskactv, actvcode] if frame is not None and not frame.empty]
    if not frames:
        return options

    counts: dict[str, int] = {}
    labels: dict[str, str] = {}

    for frame in frames:
        code_column = _preferred_activity_code_column(frame)
        if code_column is None:
            continue

        task_id_column = _first_matching_column(frame, ["task_id", "task_code", "task_pk"])
        if task_id_column is not None:
            grouped = (
                frame[[task_id_column, code_column]]
                .dropna(subset=[code_column])
                .assign(code=lambda data: data[code_column].map(_normalize_text_value))
            )
            grouped = grouped[grouped["code"] != ""]
            for code_value, group in grouped.groupby("code"):
                counts[code_value] = counts.get(code_value, 0) + int(group[task_id_column].nunique())
                labels.setdefault(code_value, code_value)
        else:
            series = frame[code_column].dropna().map(_normalize_text_value)
            for code_value, count in series.value_counts().items():
                if not code_value:
                    continue
                counts[code_value] = counts.get(code_value, 0) + int(count)
                labels.setdefault(code_value, code_value)

    for code_value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].lower())):
        options.append({"value": code_value, "label": labels.get(code_value, code_value), "count": int(count)})

    if len(options) == 1:
        return [{"value": "all", "label": "All Activity Codes", "count": 0}]

    options[0]["count"] = int(sum(item["count"] for item in options[1:]))
    return options


def _build_dashboard_date_mask(tasks: pd.DataFrame, data_date: pd.Timestamp, date_window: str) -> pd.Series:
    normalized_window = _normalize_dashboard_filter_value(date_window)
    if normalized_window == "all" or data_date is None or tasks.empty:
        return pd.Series([True] * len(tasks.index), index=tasks.index)

    months_by_window = {"3m": 3, "6m": 6}
    months = months_by_window.get(normalized_window)
    if months is None:
        return pd.Series([True] * len(tasks.index), index=tasks.index)

    cutoff = (data_date - pd.DateOffset(months=months)).normalize()
    mask = pd.Series([False] * len(tasks.index), index=tasks.index)
    found_series = False
    for candidates in [
        ["act_end_date", "actual_end_date", "completion_date"],
        ["target_end_date", "planned_end_date", "end_date"],
        ["last_recalc_date", "data_date", "status_date", "update_date"],
    ]:
        series = _first_matching_datetime_series(tasks, candidates)
        if series is not None:
            found_series = True
            mask = mask | series.between(cutoff, data_date, inclusive="both")
    if not found_series:
        return pd.Series([True] * len(tasks.index), index=tasks.index)
    return mask


def _filter_dashboard_frames(
    tasks: pd.DataFrame,
    taskactv: pd.DataFrame,
    data_date: pd.Timestamp | None,
    date_window: str = "all",
    activity_code: str = "all",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    filtered_tasks = tasks.copy()
    normalized_window = _normalize_dashboard_filter_value(date_window)
    normalized_code = _normalize_text_value(activity_code).lower()

    if data_date is not None and normalized_window != "all":
        mask = _build_dashboard_date_mask(filtered_tasks, data_date, normalized_window)
        filtered_tasks = filtered_tasks.loc[mask].copy()

    if normalized_code and normalized_code != "all" and taskactv is not None and not taskactv.empty:
        task_id_column = _first_matching_column(filtered_tasks, ["task_id", "task_code", "task_pk"])
        taskactv_task_id_column = _first_matching_column(taskactv, ["task_id", "task_code", "task_pk"])
        code_column = _preferred_activity_code_column(taskactv)
        if task_id_column is not None and taskactv_task_id_column is not None and code_column is not None:
            matching_task_ids = (
                taskactv[[taskactv_task_id_column, code_column]]
                .dropna(subset=[code_column])
                .assign(code=lambda data: data[code_column].map(lambda value: _normalize_text_value(value).lower()))
            )
            matching_task_ids = matching_task_ids[matching_task_ids["code"] == normalized_code][taskactv_task_id_column].tolist()
            filtered_tasks = filtered_tasks[filtered_tasks[task_id_column].isin(matching_task_ids)].copy()

    filtered_taskactv = pd.DataFrame()
    if taskactv is not None and not taskactv.empty:
        task_id_column = _first_matching_column(filtered_tasks, ["task_id", "task_code", "task_pk"])
        taskactv_task_id_column = _first_matching_column(taskactv, ["task_id", "task_code", "task_pk"])
        if task_id_column is not None and taskactv_task_id_column is not None:
            filtered_taskactv = taskactv[taskactv[taskactv_task_id_column].isin(filtered_tasks[task_id_column])].copy()
        else:
            filtered_taskactv = taskactv.copy()

    return filtered_tasks, filtered_taskactv


def _build_event_curve(tasks: pd.DataFrame, taskactv: pd.DataFrame) -> dict[str, Any]:
    source_df = tasks if tasks is not None and not tasks.empty else taskactv
    if source_df is None or source_df.empty:
        return {
            "data_date": None,
            "dates": [],
            "planned_value": [],
            "earned_value": [],
        }

    budget_series = _first_matching_series(
        source_df,
        ["target_cost", "planned_cost", "cost", "at_completion_total_cost", "budget_at_completion", "total_cost"],
    )
    if budget_series is None:
        budget_series = pd.Series([0.0] * len(source_df.index), index=source_df.index, dtype="float64")
    else:
        budget_series = budget_series.astype("float64")

    planned_value_series = _first_matching_series(source_df, ["planned_value", "bcws"])
    if planned_value_series is None:
        planned_value_series = budget_series.copy()
    else:
        planned_value_series = planned_value_series.astype("float64")

    earned_value_series = _first_matching_series(source_df, ["earned_value", "bcwp"])
    if earned_value_series is None:
        progress_series = _first_matching_series(
            source_df,
            ["phys_complete_pct", "task_complete_pct", "complete_pct", "percent_complete"],
        )
        if progress_series is not None:
            earned_value_series = budget_series * (progress_series / 100.0)
        else:
            earned_value_series = pd.Series([0.0] * len(source_df.index), index=source_df.index, dtype="float64")
    else:
        earned_value_series = earned_value_series.astype("float64")

    planned_dates = _first_matching_datetime_series(
        source_df,
        ["target_end_date", "planned_end_date", "early_end_date", "late_end_date", "end_date"],
    )
    actual_dates = _first_matching_datetime_series(
        source_df,
        ["act_end_date", "actual_end_date", "completion_date", "status_date", "last_recalc_date"],
    )
    data_date = _resolve_data_date(tasks, taskactv)

    planned_events: list[tuple[pd.Timestamp, float]] = []
    earned_events: list[tuple[pd.Timestamp, float]] = []

    for index in source_df.index:
        planned_date = planned_dates.loc[index].normalize() if planned_dates is not None and pd.notna(planned_dates.loc[index]) else None
        actual_date = actual_dates.loc[index].normalize() if actual_dates is not None and pd.notna(actual_dates.loc[index]) else None
        planned_value = float(planned_value_series.loc[index])
        earned_value = float(earned_value_series.loc[index])

        if planned_date is not None:
            planned_events.append((planned_date, planned_value))

        if earned_value > 0:
            earned_date = actual_date or data_date or planned_date
            if earned_date is not None and data_date is not None and earned_date > data_date:
                earned_date = data_date
            if earned_date is not None:
                earned_events.append((earned_date, earned_value))

    unique_dates = sorted({date for date, _ in planned_events + earned_events} | ({data_date} if data_date is not None else set()))
    if not unique_dates:
        return {
            "data_date": data_date.strftime("%Y-%m-%d") if data_date is not None else None,
            "dates": [],
            "planned_value": [],
            "earned_value": [],
        }

    planned_by_date = pd.Series(0.0, index=unique_dates, dtype="float64")
    earned_by_date = pd.Series(0.0, index=unique_dates, dtype="float64")

    for event_date, value in planned_events:
        planned_by_date.loc[event_date] += value

    for event_date, value in earned_events:
        earned_by_date.loc[event_date] += value

    cumulative_pv = planned_by_date.cumsum().round(2)
    cumulative_ev = earned_by_date.cumsum().round(2)

    return {
        "data_date": data_date.strftime("%Y-%m-%d") if data_date is not None else None,
        "dates": [date.strftime("%Y-%m-%d") for date in unique_dates],
        "planned_value": [round(float(value), 2) for value in cumulative_pv.tolist()],
        "earned_value": [round(float(value), 2) for value in cumulative_ev.tolist()],
    }


def _calculate_wbs_weights(tasks: pd.DataFrame, wbs: pd.DataFrame) -> list[dict[str, Any]]:
    if tasks.empty:
        return []

    budget_series = _first_matching_series(
        tasks,
        ["target_cost", "at_completion_total_cost", "budget_at_completion", "total_cost"],
    )
    wbs_column = _first_matching_column(tasks, ["wbs_id", "projwbs_id", "parent_wbs_id"])
    if budget_series is None or wbs_column is None:
        return []

    grouped = (
        pd.DataFrame({"wbs_id": tasks[wbs_column], "budget": budget_series.astype("float64")})
        .dropna(subset=["wbs_id"])
        .groupby("wbs_id", as_index=False)["budget"]
        .sum()
    )
    if grouped.empty:
        return []

    total_budget = float(grouped["budget"].sum())
    label_lookup: dict[Any, str] = {}
    if wbs is not None and not wbs.empty:
        id_column = _first_matching_column(wbs, ["wbs_id", "projwbs_id"])
        label_column = _first_matching_column(wbs, ["wbs_name", "wbs_short_name", "wbs_code"])
        if id_column is not None and label_column is not None:
            label_lookup = {
                row[id_column]: str(row[label_column])
                for _, row in wbs[[id_column, label_column]].dropna(subset=[id_column]).iterrows()
            }

    grouped = grouped.sort_values("budget", ascending=False)
    weights: list[dict[str, Any]] = []
    for _, row in grouped.iterrows():
        wbs_id = row["wbs_id"]
        budget = round(float(row["budget"]), 2)
        weight = round((budget / total_budget) * 100, 2) if total_budget > 0 else 0.0
        normalized_wbs_id: Any = wbs_id
        if pd.notna(wbs_id):
            try:
                numeric_wbs_id = float(wbs_id)
                normalized_wbs_id = int(numeric_wbs_id) if numeric_wbs_id.is_integer() else numeric_wbs_id
            except (TypeError, ValueError):
                normalized_wbs_id = wbs_id
        weights.append(
            {
                "wbs_id": normalized_wbs_id,
                "label": label_lookup.get(wbs_id, f"WBS {wbs_id}"),
                "weight": weight,
                "budget": budget,
            }
        )

    return weights


def _normalize_activity_ids(series: pd.Series) -> list[Any]:
    activity_ids: list[Any] = []
    for value in series.dropna().tolist():
        try:
            numeric_value = float(value)
            activity_ids.append(int(numeric_value) if numeric_value.is_integer() else numeric_value)
        except (TypeError, ValueError):
            activity_ids.append(value)
    return activity_ids


def _calculate_pass_percentage(total_activities: int, offending_count: int) -> float:
    if total_activities <= 0:
        return 100.0
    return round(((total_activities - offending_count) / total_activities) * 100, 2)


def _task_float_days(tasks: pd.DataFrame) -> pd.Series:
    float_series = _first_matching_series(
        tasks,
        ["total_float_days", "total_float_day_cnt", "total_float_hr_cnt", "total_float"],
    )
    if float_series is None:
        return pd.Series([0.0] * len(tasks.index), index=tasks.index, dtype="float64")

    float_column = _first_matching_column(
        tasks,
        ["total_float_days", "total_float_day_cnt", "total_float_hr_cnt", "total_float"],
    )
    if float_column and float_column.lower() == "total_float_hr_cnt":
        return (float_series / 8.0).astype("float64")
    return float_series.astype("float64")


def _build_schedule_health(tasks: pd.DataFrame, taskpred: pd.DataFrame, data_date: pd.Timestamp | None) -> dict[str, Any]:
    total_activities = int(len(tasks.index))
    if tasks.empty:
        rules = [
            {"rule_key": "missing_logic", "label": "Missing Logic", "pass_percentage": 100.0, "offending_activity_ids": [], "offending_count": 0},
            {"rule_key": "negative_float", "label": "Negative Float", "pass_percentage": 100.0, "offending_activity_ids": [], "offending_count": 0},
            {"rule_key": "high_float", "label": "High Float (>44 days)", "pass_percentage": 100.0, "offending_activity_ids": [], "offending_count": 0},
            {"rule_key": "invalid_dates", "label": "Invalid Dates", "pass_percentage": 100.0, "offending_activity_ids": [], "offending_count": 0},
            {"rule_key": "hard_constraints", "label": "Hard Constraints", "pass_percentage": 100.0, "offending_activity_ids": [], "offending_count": 0},
        ]
        return {
            "data_date": data_date.strftime("%Y-%m-%d") if data_date is not None else None,
            "summary": {
                "total_activities": 0,
                "rule_count": len(rules),
                "average_pass_percentage": 100.0,
            },
            "rules": rules,
        }

    task_id_column = _first_matching_column(tasks, ["task_id", "task_code", "task_pk"])
    if task_id_column is None:
        raise HTTPException(status_code=500, detail="TASK table is missing a task identifier column.")

    task_ids = tasks[task_id_column]
    predecessor_ids: set[Any] = set()
    successor_ids: set[Any] = set()
    if taskpred is not None and not taskpred.empty:
        pred_column = _first_matching_column(taskpred, ["pred_task_id", "pred_task_code", "pred_task_pk"])
        succ_column = _first_matching_column(taskpred, ["task_id", "succ_task_id", "task_code"])
        if pred_column is not None:
            predecessor_ids = set(taskpred[pred_column].dropna().tolist())
        if succ_column is not None:
            successor_ids = set(taskpred[succ_column].dropna().tolist())

    missing_logic_mask = ~task_ids.isin(predecessor_ids) | ~task_ids.isin(successor_ids)
    missing_logic_ids = _normalize_activity_ids(task_ids[missing_logic_mask])

    float_days = _task_float_days(tasks)
    negative_float_ids = _normalize_activity_ids(task_ids[float_days < 0])
    high_float_ids = _normalize_activity_ids(task_ids[float_days > 44])

    invalid_date_mask = pd.Series([False] * len(tasks.index), index=tasks.index)
    if data_date is not None:
        for series in [
            _first_matching_datetime_series(tasks, ["act_start_date", "actual_start_date"]),
            _first_matching_datetime_series(tasks, ["act_end_date", "actual_end_date", "completion_date"]),
        ]:
            if series is not None:
                invalid_date_mask = invalid_date_mask | (series > data_date)
    invalid_date_ids = _normalize_activity_ids(task_ids[invalid_date_mask])

    constraint_column = _first_matching_column(tasks, ["constraint_type", "cstr_type", "primary_constraint_type"])
    hard_constraint_ids: list[Any] = []
    if constraint_column is not None:
        allowed_soft_constraints = {
            "asap",
            "alap",
            "none",
            "start on or after",
            "finish on or before",
            "snet",
            "fnlt",
            "fnet",
            "snlt",
        }
        normalized_constraints = tasks[constraint_column].fillna("").astype(str).str.strip().str.lower()
        hard_constraint_mask = normalized_constraints.ne("") & ~normalized_constraints.isin(allowed_soft_constraints)
        hard_constraint_ids = _normalize_activity_ids(task_ids[hard_constraint_mask])

    rules = [
        {
            "rule_key": "missing_logic",
            "label": "Missing Logic",
            "pass_percentage": _calculate_pass_percentage(total_activities, len(missing_logic_ids)),
            "offending_activity_ids": missing_logic_ids,
            "offending_count": len(missing_logic_ids),
        },
        {
            "rule_key": "negative_float",
            "label": "Negative Float",
            "pass_percentage": _calculate_pass_percentage(total_activities, len(negative_float_ids)),
            "offending_activity_ids": negative_float_ids,
            "offending_count": len(negative_float_ids),
        },
        {
            "rule_key": "high_float",
            "label": "High Float (>44 days)",
            "pass_percentage": _calculate_pass_percentage(total_activities, len(high_float_ids)),
            "offending_activity_ids": high_float_ids,
            "offending_count": len(high_float_ids),
        },
        {
            "rule_key": "invalid_dates",
            "label": "Invalid Dates",
            "pass_percentage": _calculate_pass_percentage(total_activities, len(invalid_date_ids)),
            "offending_activity_ids": invalid_date_ids,
            "offending_count": len(invalid_date_ids),
        },
        {
            "rule_key": "hard_constraints",
            "label": "Hard Constraints",
            "pass_percentage": _calculate_pass_percentage(total_activities, len(hard_constraint_ids)),
            "offending_activity_ids": hard_constraint_ids,
            "offending_count": len(hard_constraint_ids),
        },
    ]

    average_pass_percentage = round(sum(rule["pass_percentage"] for rule in rules) / len(rules), 2)
    return {
        "data_date": data_date.strftime("%Y-%m-%d") if data_date is not None else None,
        "summary": {
            "total_activities": total_activities,
            "rule_count": len(rules),
            "average_pass_percentage": average_pass_percentage,
        },
        "rules": rules,
    }


def _get_selected_project_dataset() -> tuple[str, dict[str, Any]]:
    project_data = app.state.project_data
    if project_data is None:
        raise HTTPException(status_code=400, detail="No project data uploaded yet.")

    source_key = "updated" if project_data.get("updated") is not None else "original"
    selected = project_data[source_key]
    source_label = "updated_xer" if source_key == "updated" else "original_xer"
    return source_label, selected


def _normalize_comparison_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%d")
        except Exception:
            pass
    if isinstance(value, (int, float)):
        numeric = float(value)
        return int(numeric) if numeric.is_integer() else round(numeric, 4)
    text = str(value).strip()
    if not text:
        return None
    try:
        numeric = float(text)
    except Exception:
        return text
    return int(numeric) if numeric.is_integer() else round(numeric, 4)


def _task_id_set(tasks: pd.DataFrame) -> set[Any]:
    task_id_column = _first_matching_column(tasks, ["task_id", "task_code", "task_pk"])
    if task_id_column is None or tasks.empty:
        return set()
    return { _normalize_comparison_value(value) for value in tasks[task_id_column].dropna().tolist() }


def _task_signature(row: pd.Series) -> tuple[Any, ...]:
    columns = [
        ["task_name", "task_short_name", "name"],
        ["wbs_id", "projwbs_id", "parent_wbs_id"],
        ["target_cost", "at_completion_total_cost", "budget_at_completion", "total_cost"],
        ["planned_value", "bcws"],
        ["earned_value", "bcwp"],
        ["total_float_days", "total_float_day_cnt", "total_float_hr_cnt", "total_float"],
        ["constraint_type", "cstr_type", "primary_constraint_type"],
        ["act_end_date", "actual_end_date", "completion_date"],
    ]
    normalized_row = {str(column).lower(): row[column] for column in row.index}
    signature: list[Any] = []
    for candidates in columns:
        value = None
        for candidate in candidates:
            if candidate.lower() in normalized_row:
                value = normalized_row[candidate.lower()]
                break
        signature.append(_normalize_comparison_value(value))
    return tuple(signature)


def _build_performance_snapshot(
    tasks: pd.DataFrame,
    taskactv: pd.DataFrame,
    data_date: pd.Timestamp | None,
    *,
    date_window: str = "all",
    activity_code: str = "all",
    source_label: str,
) -> dict[str, Any]:
    filtered_tasks, _ = _filter_dashboard_frames(
        tasks,
        taskactv,
        data_date,
        date_window=date_window,
        activity_code=activity_code,
    )
    metrics = _calculate_evm_kpis(filtered_tasks)
    task_count = int(len(filtered_tasks.index))
    task_ids = _task_id_set(filtered_tasks)
    return {
        "source": source_label,
        "task_count": task_count,
        **metrics,
        "task_ids": sorted(task_ids, key=lambda value: (str(type(value)), str(value))),
    }


def _build_baseline_comparison(
    original_tasks: pd.DataFrame,
    original_taskactv: pd.DataFrame,
    updated_tasks: pd.DataFrame,
    updated_taskactv: pd.DataFrame,
    original_data_date: pd.Timestamp | None,
    updated_data_date: pd.Timestamp | None,
    *,
    date_window: str = "all",
    activity_code: str = "all",
) -> dict[str, Any]:
    original_snapshot = _build_performance_snapshot(
        original_tasks,
        original_taskactv,
        original_data_date,
        date_window=date_window,
        activity_code=activity_code,
        source_label="original_xer",
    )
    updated_snapshot = _build_performance_snapshot(
        updated_tasks,
        updated_taskactv,
        updated_data_date,
        date_window=date_window,
        activity_code=activity_code,
        source_label="updated_xer",
    )

    original_ids = set(original_snapshot.pop("task_ids", []))
    updated_ids = set(updated_snapshot.pop("task_ids", []))
    original_task_id_column = _first_matching_column(original_tasks, ["task_id", "task_code", "task_pk"])
    updated_task_id_column = _first_matching_column(updated_tasks, ["task_id", "task_code", "task_pk"])

    original_rows = {}
    if original_task_id_column is not None and not original_tasks.empty:
        for _, row in original_tasks.iterrows():
            task_id = _normalize_comparison_value(row[original_task_id_column])
            original_rows[task_id] = _task_signature(row)

    updated_rows = {}
    if updated_task_id_column is not None and not updated_tasks.empty:
        for _, row in updated_tasks.iterrows():
            task_id = _normalize_comparison_value(row[updated_task_id_column])
            updated_rows[task_id] = _task_signature(row)

    added = sorted(updated_ids - original_ids, key=lambda value: (str(type(value)), str(value)))
    removed = sorted(original_ids - updated_ids, key=lambda value: (str(type(value)), str(value)))
    modified = sorted(
        [task_id for task_id in (original_ids & updated_ids) if original_rows.get(task_id) != updated_rows.get(task_id)],
        key=lambda value: (str(type(value)), str(value)),
    )

    def _delta_value(updated_value: Any, original_value: Any) -> Any:
        if updated_value is None or original_value is None:
            return None
        return round(float(updated_value) - float(original_value), 4)

    return {
        "original": original_snapshot,
        "updated": updated_snapshot,
        "delta": {
            "task_count": int(updated_snapshot["task_count"] - original_snapshot["task_count"]),
            "total_budget": _delta_value(updated_snapshot["total_budget"], original_snapshot["total_budget"]),
            "planned_value": _delta_value(updated_snapshot["planned_value"], original_snapshot["planned_value"]),
            "earned_value": _delta_value(updated_snapshot["earned_value"], original_snapshot["earned_value"]),
            "spi": _delta_value(updated_snapshot["spi"], original_snapshot["spi"]),
        },
        "task_changes": {
            "added": added,
            "removed": removed,
            "modified": modified,
        },
    }


def _build_critical_path_summary(
    tasks: pd.DataFrame,
    taskpred: pd.DataFrame,
    taskactv: pd.DataFrame,
    data_date: pd.Timestamp | None,
    *,
    date_window: str = "all",
    activity_code: str = "all",
    source_label: str,
    threshold_days: float = 5.0,
) -> dict[str, Any]:
    filtered_tasks, _ = _filter_dashboard_frames(
        tasks,
        taskactv if taskactv is not None else pd.DataFrame(),
        data_date,
        date_window=date_window,
        activity_code=activity_code,
    )

    if filtered_tasks is None or filtered_tasks.empty:
        return {
            "source": source_label,
            "summary": {
                "total_tasks": 0,
                "critical_path_duration_days": 0.0,
                "critical_path_task_count": 0,
                "near_critical_task_count": 0,
                "threshold_days": threshold_days,
            },
            "critical_path_task_ids": [],
            "critical_path_task_names": [],
            "critical_path_tasks": [],
            "near_critical_task_ids": [],
            "near_critical_task_names": [],
            "near_critical_tasks": [],
        }

    task_id_column = _first_matching_column(filtered_tasks, ["task_id", "task_code", "task_pk"])
    task_name_column = _first_matching_column(filtered_tasks, ["task_name", "task_short_name", "name"])
    duration_series = _first_matching_series(
        filtered_tasks,
        ["target_duration", "remaining_duration", "duration", "orig_duration"],
    )
    if duration_series is None:
        duration_series = pd.Series([1.0] * len(filtered_tasks.index), index=filtered_tasks.index, dtype="float64")
    else:
        duration_series = duration_series.astype("float64").fillna(1.0)

    float_series = _first_matching_series(
        filtered_tasks,
        ["total_float_days", "total_float_day_cnt", "total_float_hr_cnt", "total_float"],
    )
    if float_series is not None:
        float_series = float_series.astype("float64")

    node_order: dict[Any, int] = {}
    node_data: dict[Any, dict[str, Any]] = {}
    for position, (index, row) in enumerate(filtered_tasks.iterrows()):
        task_id_value = _normalize_comparison_value(row[task_id_column]) if task_id_column is not None else _normalize_comparison_value(index)
        if task_id_value is None:
            task_id_value = index
        task_name = str(row[task_name_column]) if task_name_column is not None and pd.notna(row[task_name_column]) else f"Task {task_id_value}"
        duration_days = round(float(duration_series.loc[index]), 2)
        float_days = None
        if float_series is not None and index in float_series.index and pd.notna(float_series.loc[index]):
            float_days = round(float(float_series.loc[index]), 2)
        node_order[task_id_value] = position
        node_data[task_id_value] = {
            "task_id": task_id_value,
            "task_name": task_name,
            "duration_days": duration_days,
            "total_float_days": float_days,
        }

    if not node_data:
        return {
            "source": source_label,
            "summary": {
                "total_tasks": 0,
                "critical_path_duration_days": 0.0,
                "critical_path_task_count": 0,
                "near_critical_task_count": 0,
                "threshold_days": threshold_days,
            },
            "critical_path_task_ids": [],
            "critical_path_task_names": [],
            "critical_path_tasks": [],
            "near_critical_task_ids": [],
            "near_critical_task_names": [],
            "near_critical_tasks": [],
        }

    predecessors: dict[Any, set[Any]] = {task_id: set() for task_id in node_data}
    successors: dict[Any, set[Any]] = {task_id: set() for task_id in node_data}

    if taskpred is not None and not taskpred.empty:
        pred_task_column = _first_matching_column(taskpred, ["task_id", "task_code", "task_pk"])
        pred_pred_column = _first_matching_column(taskpred, ["pred_task_id", "pred_task_code", "pred_task_pk"])
        if pred_task_column is not None and pred_pred_column is not None:
            for _, row in taskpred.iterrows():
                successor_id = _normalize_comparison_value(row[pred_task_column])
                predecessor_id = _normalize_comparison_value(row[pred_pred_column])
                if successor_id in node_data and predecessor_id in node_data:
                    predecessors[successor_id].add(predecessor_id)
                    successors[predecessor_id].add(successor_id)

    indegree = {task_id: len(preds) for task_id, preds in predecessors.items()}
    queue = sorted([task_id for task_id, degree in indegree.items() if degree == 0], key=lambda task_id: node_order[task_id])
    topo_order: list[Any] = []
    queue_index = 0
    while queue_index < len(queue):
        task_id = queue[queue_index]
        queue_index += 1
        topo_order.append(task_id)
        for successor_id in sorted(successors[task_id], key=lambda node: node_order[node]):
            indegree[successor_id] -= 1
            if indegree[successor_id] == 0:
                queue.append(successor_id)
    if len(topo_order) < len(node_data):
        remaining = [task_id for task_id in node_data if task_id not in topo_order]
        topo_order.extend(sorted(remaining, key=lambda task_id: node_order[task_id]))

    best_duration = {task_id: node_data[task_id]["duration_days"] for task_id in node_data}
    best_previous = {task_id: None for task_id in node_data}
    for task_id in topo_order:
        for successor_id in successors.get(task_id, set()):
            candidate_duration = best_duration[task_id] + node_data[successor_id]["duration_days"]
            if candidate_duration > best_duration[successor_id]:
                best_duration[successor_id] = candidate_duration
                best_previous[successor_id] = task_id

    end_task_id = max(node_data, key=lambda task_id: (best_duration[task_id], -node_order[task_id]))
    critical_path: list[Any] = []
    cursor: Any | None = end_task_id
    while cursor is not None:
        critical_path.append(cursor)
        cursor = best_previous[cursor]
    critical_path.reverse()

    critical_set = set(critical_path)
    near_critical = [
        task_id
        for task_id, info in node_data.items()
        if task_id not in critical_set and info["total_float_days"] is not None and info["total_float_days"] <= threshold_days
    ]
    near_critical.sort(key=lambda task_id: (node_data[task_id]["total_float_days"], node_order[task_id]))

    def _path_detail(task_id: Any) -> dict[str, Any]:
        return node_data[task_id]

    return {
        "source": source_label,
        "summary": {
            "total_tasks": int(len(node_data)),
            "critical_path_duration_days": round(float(best_duration[end_task_id]), 2),
            "critical_path_task_count": int(len(critical_path)),
            "near_critical_task_count": int(len(near_critical)),
            "threshold_days": threshold_days,
        },
        "critical_path_task_ids": critical_path,
        "critical_path_task_names": [node_data[task_id]["task_name"] for task_id in critical_path],
        "critical_path_tasks": [_path_detail(task_id) for task_id in critical_path],
        "near_critical_task_ids": near_critical,
        "near_critical_task_names": [node_data[task_id]["task_name"] for task_id in near_critical],
        "near_critical_tasks": [_path_detail(task_id) for task_id in near_critical],
    }


def _build_forecast_summary(
    tasks: pd.DataFrame,
    taskactv: pd.DataFrame,
    data_date: pd.Timestamp | None,
    *,
    date_window: str = "all",
    activity_code: str = "all",
    source_label: str,
) -> dict[str, Any]:
    filtered_tasks, _ = _filter_dashboard_frames(
        tasks,
        taskactv if taskactv is not None else pd.DataFrame(),
        data_date,
        date_window=date_window,
        activity_code=activity_code,
    )

    kpis = _calculate_evm_kpis(filtered_tasks)
    bac = round(float(kpis.get("total_budget") or 0.0), 2)
    pv = round(float(kpis.get("planned_value") or 0.0), 2)
    ev = round(float(kpis.get("earned_value") or 0.0), 2)
    spi_value = kpis.get("spi")
    spi = round(float(spi_value), 4) if spi_value is not None else None
    exact_spi = (ev / pv) if pv else None

    if exact_spi is not None and exact_spi > 0:
        eac = round(bac / exact_spi, 2)
    else:
        eac = bac
    etc = round(eac - ev, 2)
    vac = round(bac - eac, 2)
    completion_percent = round((ev / eac) * 100.0, 2) if eac else 0.0
    forecast_status = "at_risk"
    if spi is not None:
        if spi >= 1.0:
            forecast_status = "on_track"
        elif spi >= 0.9:
            forecast_status = "watch"
        elif spi >= 0.75:
            forecast_status = "at_risk"
        else:
            forecast_status = "critical"

    return {
        "source": source_label,
        "filters": {
            "date_window": date_window,
            "activity_code": activity_code,
        },
        "current": {
            "bac": bac,
            "pv": pv,
            "ev": ev,
            "spi": spi,
        },
        "forecast": {
            "eac": eac,
            "etc": etc,
            "vac": vac,
            "completion_percent": completion_percent,
        },
        "summary": {
            "forecast_status": forecast_status,
            "forecast_completion_percent": completion_percent,
            "forecast_variance": vac,
            "task_count": int(len(filtered_tasks.index)),
        },
    }


def _build_remaining_cost_dataframe(tasks: pd.DataFrame, wbs: pd.DataFrame) -> pd.DataFrame:
    if tasks is None or tasks.empty:
        return pd.DataFrame(
            columns=[
                "task_id",
                "task_name",
                "wbs_id",
                "wbs_name",
                "budget",
                "planned_value",
                "earned_value",
                "variance_to_plan",
                "remaining_cost",
            ]
        )

    task_id_column = _first_matching_column(tasks, ["task_id", "task_code", "task_pk"])
    task_name_column = _first_matching_column(tasks, ["task_name", "task_short_name", "name"])
    wbs_column = _first_matching_column(tasks, ["wbs_id", "projwbs_id", "parent_wbs_id"])

    budget_series = _first_matching_series(
        tasks,
        ["target_cost", "at_completion_total_cost", "budget_at_completion", "total_cost"],
    )
    if budget_series is None:
        budget_series = pd.Series([0.0] * len(tasks.index), index=tasks.index, dtype="float64")

    planned_value_series = _first_matching_series(tasks, ["planned_value", "bcws"])
    if planned_value_series is None:
        planned_value_series = pd.Series([0.0] * len(tasks.index), index=tasks.index, dtype="float64")

    earned_value_series = _first_matching_series(tasks, ["earned_value", "bcwp"])
    if earned_value_series is None:
        progress_series = _first_matching_series(
            tasks,
            ["phys_complete_pct", "task_complete_pct", "complete_pct", "percent_complete"],
        )
        if progress_series is not None:
            earned_value_series = budget_series * (progress_series / 100.0)
        else:
            earned_value_series = pd.Series([0.0] * len(tasks.index), index=tasks.index, dtype="float64")

    task_names = tasks[task_name_column].astype(str) if task_name_column is not None else pd.Series([""] * len(tasks.index), index=tasks.index)
    task_ids = tasks[task_id_column] if task_id_column is not None else pd.Series(range(1, len(tasks.index) + 1), index=tasks.index)
    wbs_ids = tasks[wbs_column] if wbs_column is not None else pd.Series([pd.NA] * len(tasks.index), index=tasks.index)

    label_lookup: dict[Any, str] = {}
    if wbs is not None and not wbs.empty:
        id_column = _first_matching_column(wbs, ["wbs_id", "projwbs_id"])
        label_column = _first_matching_column(wbs, ["wbs_name", "wbs_short_name", "wbs_code"])
        if id_column is not None and label_column is not None:
            label_lookup = {
                row[id_column]: str(row[label_column])
                for _, row in wbs[[id_column, label_column]].dropna(subset=[id_column]).iterrows()
            }

    frame = pd.DataFrame(
        {
            "task_id": task_ids,
            "task_name": task_names,
            "wbs_id": wbs_ids,
            "wbs_name": [label_lookup.get(wbs_id, f"WBS {wbs_id}") if pd.notna(wbs_id) else "Unassigned" for wbs_id in wbs_ids],
            "budget": budget_series.astype("float64"),
            "planned_value": planned_value_series.astype("float64"),
            "earned_value": earned_value_series.astype("float64"),
        }
    )
    frame["variance_to_plan"] = (frame["earned_value"] - frame["planned_value"]).round(2)
    frame["remaining_cost"] = (frame["budget"] - frame["earned_value"]).round(2)
    frame = frame[[
        "task_id",
        "task_name",
        "wbs_id",
        "wbs_name",
        "budget",
        "planned_value",
        "earned_value",
        "variance_to_plan",
        "remaining_cost",
    ]]
    return frame


def _build_wbs_remaining_summary(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame(columns=["wbs_id", "wbs_name", "budget", "planned_value", "earned_value", "remaining_cost"])

    summary = (
        raw_df.groupby(["wbs_id", "wbs_name"], dropna=False, as_index=False)[["budget", "planned_value", "earned_value", "remaining_cost"]]
        .sum()
        .sort_values("budget", ascending=False)
        .reset_index(drop=True)
    )
    return summary


def generate_remaining_cost_export(tasks: pd.DataFrame, wbs: pd.DataFrame, source_label: str = "api") -> bytes:
    raw_df = _build_remaining_cost_dataframe(tasks, wbs)
    wbs_df = _build_wbs_remaining_summary(raw_df)

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})

    title_format = workbook.add_format({"bold": True, "font_size": 16})
    subtitle_format = workbook.add_format({"italic": True, "font_color": "#475569"})
    header_format = workbook.add_format({"bold": True, "bg_color": "#DCE6F1", "border": 1})
    label_format = workbook.add_format({"bold": True, "bg_color": "#F8FAFC", "border": 1})
    currency_format = workbook.add_format({"num_format": "$#,##0.00", "border": 1})
    text_format = workbook.add_format({"border": 1})
    integer_format = workbook.add_format({"num_format": "0", "border": 1})

    raw_sheet = workbook.add_worksheet("Raw Data")
    raw_sheet.freeze_panes(3, 0)
    raw_sheet.set_column("A:A", 10)
    raw_sheet.set_column("B:B", 22)
    raw_sheet.set_column("C:C", 10)
    raw_sheet.set_column("D:D", 18)
    raw_sheet.set_column("E:I", 16)

    raw_sheet.write("A1", "Remaining Cost Export", title_format)
    raw_sheet.write("A2", f"Source: {source_label}", subtitle_format)
    raw_sheet.write("D2", "Visible Budget", label_format)
    raw_sheet.write_formula("E2", "=SUBTOTAL(9,E4:E5)", currency_format)
    raw_sheet.write("F2", "Visible Earned", label_format)
    raw_sheet.write_formula("G2", "=SUBTOTAL(9,G4:G5)", currency_format)
    raw_sheet.write("H2", "Visible Remaining", label_format)
    raw_sheet.write_formula("I2", "=SUBTOTAL(9,I4:I5)", currency_format)

    raw_headers = [
        "Task ID",
        "Task Name",
        "WBS ID",
        "WBS Name",
        "Budget",
        "Planned Value",
        "Earned Value",
        "Variance to Plan",
        "Remaining Cost",
    ]
    for column_index, header in enumerate(raw_headers):
        raw_sheet.write(2, column_index, header, header_format)

    for row_offset, row in enumerate(raw_df.itertuples(index=False), start=3):
        raw_sheet.write_number(row_offset, 0, float(row.task_id), integer_format)
        raw_sheet.write_string(row_offset, 1, str(row.task_name), text_format)
        raw_sheet.write_number(row_offset, 2, float(row.wbs_id), integer_format)
        raw_sheet.write_string(row_offset, 3, str(row.wbs_name), text_format)
        raw_sheet.write_number(row_offset, 4, float(row.budget), currency_format)
        raw_sheet.write_number(row_offset, 5, float(row.planned_value), currency_format)
        raw_sheet.write_number(row_offset, 6, float(row.earned_value), currency_format)
        raw_sheet.write_number(row_offset, 7, float(row.variance_to_plan), currency_format)
        raw_sheet.write_number(row_offset, 8, float(row.remaining_cost), currency_format)

    raw_last_row = max(len(raw_df) + 3, 4)
    raw_sheet.autofilter(f"A3:I{raw_last_row}")
    raw_sheet.conditional_format(
        f"H4:H{raw_last_row}",
        {"type": "cell", "criteria": ">=", "value": 0, "format": workbook.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})},
    )
    raw_sheet.conditional_format(
        f"H4:H{raw_last_row}",
        {"type": "cell", "criteria": "<", "value": 0, "format": workbook.add_format({"bg_color": "#FFC7CE", "font_color": "#9C0006"})},
    )
    raw_sheet.write(f"H{raw_last_row + 1}", "Filtered Total Remaining", label_format)
    raw_sheet.write_formula(f"I{raw_last_row + 1}", f"=SUBTOTAL(9,I4:I{raw_last_row})", currency_format)

    by_wbs_sheet = workbook.add_worksheet("By WBS")
    by_wbs_sheet.freeze_panes(3, 0)
    by_wbs_sheet.set_column("A:B", 18)
    by_wbs_sheet.set_column("C:F", 16)
    by_wbs_sheet.write("A1", "Remaining Cost by WBS", title_format)
    by_wbs_sheet.write("A2", f"Source: {source_label}", subtitle_format)
    by_wbs_sheet.write_formula("C2", "=SUBTOTAL(9,C4:C5)", currency_format)
    by_wbs_sheet.write_formula("D2", "=SUBTOTAL(9,D4:D5)", currency_format)
    by_wbs_sheet.write_formula("E2", "=SUBTOTAL(9,E4:E5)", currency_format)
    by_wbs_sheet.write_formula("F2", "=SUBTOTAL(9,F4:F5)", currency_format)

    by_wbs_headers = ["WBS ID", "WBS Name", "Budget", "Planned Value", "Earned Value", "Remaining Cost"]
    for column_index, header in enumerate(by_wbs_headers):
        by_wbs_sheet.write(2, column_index, header, header_format)

    for row_offset, row in enumerate(wbs_df.itertuples(index=False), start=3):
        by_wbs_sheet.write_number(row_offset, 0, float(row.wbs_id), integer_format)
        by_wbs_sheet.write_string(row_offset, 1, str(row.wbs_name), text_format)
        by_wbs_sheet.write_number(row_offset, 2, float(row.budget), currency_format)
        by_wbs_sheet.write_number(row_offset, 3, float(row.planned_value), currency_format)
        by_wbs_sheet.write_number(row_offset, 4, float(row.earned_value), currency_format)
        by_wbs_sheet.write_number(row_offset, 5, float(row.remaining_cost), currency_format)

    by_wbs_last_row = max(len(wbs_df) + 3, 4)
    by_wbs_sheet.autofilter(f"A3:F{by_wbs_last_row}")
    by_wbs_sheet.conditional_format(
        f"F4:F{by_wbs_last_row}",
        {"type": "3_color_scale"},
    )

    workbook.close()
    output.seek(0)
    return output.getvalue()


@app.post("/upload")
async def upload_xer_files(
    original_xer: UploadFile = File(...),
    updated_xer: UploadFile | None = File(default=None),
) -> dict[str, Any]:
    original_tables = _parse_uploaded_xer(original_xer)
    updated_tables = _parse_uploaded_xer(updated_xer) if updated_xer is not None else None

    app.state.project_data = {
        "original": {
            "filename": original_xer.filename,
            "tables": original_tables,
        },
        "updated": {
            "filename": updated_xer.filename,
            "tables": updated_tables,
        }
        if updated_tables is not None
        else None,
    }

    response: dict[str, Any] = {
        "message": "XER file(s) uploaded and parsed successfully.",
        "original": _table_snapshot(original_tables),
        "updated": _table_snapshot(updated_tables) if updated_tables is not None else None,
    }
    return response


@app.get("/api/evm-kpis")
async def get_evm_kpis(date_window: str = Query("all"), activity_code: str = Query("all")) -> dict[str, Any]:
    _, selected = _get_selected_project_dataset()
    tasks = selected["tables"].get("TASK", pd.DataFrame())
    taskactv = selected["tables"].get("TASKACTV", pd.DataFrame())
    data_date = _resolve_data_date(tasks, taskactv)
    filtered_tasks, _ = _filter_dashboard_frames(tasks, taskactv, data_date, date_window=date_window, activity_code=activity_code)

    kpis = _calculate_evm_kpis(filtered_tasks)
    return {
        **kpis,
        "source": "updated_xer" if app.state.project_data.get("updated") is not None else "original_xer",
    }


@app.get("/api/s-curve")
async def get_s_curve(date_window: str = Query("all"), activity_code: str = Query("all")) -> dict[str, Any]:
    source_label, selected = _get_selected_project_dataset()
    tables = selected["tables"]
    tasks = tables.get("TASK", pd.DataFrame())
    taskactv = tables.get("TASKACTV", pd.DataFrame())
    actvcode = tables.get("ACTVCODE", pd.DataFrame())
    wbs = tables.get("PROJWBS", pd.DataFrame())
    data_date = _resolve_data_date(tasks, taskactv)
    filtered_tasks, filtered_taskactv = _filter_dashboard_frames(tasks, taskactv, data_date, date_window=date_window, activity_code=activity_code)

    curve = _build_event_curve(filtered_tasks, filtered_taskactv)
    return {
        "source": source_label,
        **curve,
        "activity_codes": _build_activity_code_catalog(taskactv, actvcode),
        "wbs_weights": _calculate_wbs_weights(filtered_tasks, wbs),
    }


@app.get("/api/export-excel")
async def export_excel() -> StreamingResponse:
    source_label, selected = _get_selected_project_dataset()
    tables = selected["tables"]
    workbook_bytes = generate_remaining_cost_export(
        tasks=tables.get("TASK", pd.DataFrame()),
        wbs=tables.get("PROJWBS", pd.DataFrame()),
        source_label=source_label,
    )
    return StreamingResponse(
        BytesIO(workbook_bytes),
        media_type=EXCEL_CONTENT_TYPE,
        headers={"Content-Disposition": 'attachment; filename="remaining-cost-export.xlsx"'},
    )


@app.get("/api/schedule-health")
async def get_schedule_health(date_window: str = Query("all"), activity_code: str = Query("all")) -> dict[str, Any]:
    source_label, selected = _get_selected_project_dataset()
    tables = selected["tables"]
    tasks = tables.get("TASK", pd.DataFrame())
    taskpred = tables.get("TASKPRED", pd.DataFrame())
    taskactv = tables.get("TASKACTV", pd.DataFrame())
    data_date = _resolve_data_date(tasks, taskactv)
    filtered_tasks, filtered_taskactv = _filter_dashboard_frames(tasks, taskactv, data_date, date_window=date_window, activity_code=activity_code)
    filtered_task_ids = set()
    task_id_column = _first_matching_column(filtered_tasks, ["task_id", "task_code", "task_pk"])
    pred_taskpred = taskpred
    if task_id_column is not None and not filtered_tasks.empty:
        filtered_task_ids = set(filtered_tasks[task_id_column].dropna().tolist())
    if not taskpred.empty and filtered_task_ids:
        pred_task_column = _first_matching_column(taskpred, ["task_id", "task_code", "task_pk"])
        pred_pred_column = _first_matching_column(taskpred, ["pred_task_id", "pred_task_code", "pred_task_pk"])
        if pred_task_column is not None and pred_pred_column is not None:
            pred_taskpred = taskpred[
                taskpred[pred_task_column].isin(filtered_task_ids) | taskpred[pred_pred_column].isin(filtered_task_ids)
            ].copy()
    assessment = _build_schedule_health(filtered_tasks, pred_taskpred, data_date)
    return {
        "source": source_label,
        **assessment,
    }


@app.get("/api/critical-path")
async def get_critical_path(date_window: str = Query("all"), activity_code: str = Query("all")) -> dict[str, Any]:
    source_label, selected = _get_selected_project_dataset()
    tables = selected["tables"]
    tasks = tables.get("TASK", pd.DataFrame())
    taskpred = tables.get("TASKPRED", pd.DataFrame())
    taskactv = tables.get("TASKACTV", pd.DataFrame())
    data_date = _resolve_data_date(tasks, taskactv)
    filtered_tasks, filtered_taskactv = _filter_dashboard_frames(tasks, taskactv, data_date, date_window=date_window, activity_code=activity_code)
    filtered_taskpred = taskpred
    if not filtered_tasks.empty and not taskpred.empty:
        task_id_column = _first_matching_column(filtered_tasks, ["task_id", "task_code", "task_pk"])
        pred_task_column = _first_matching_column(taskpred, ["task_id", "task_code", "task_pk"])
        pred_pred_column = _first_matching_column(taskpred, ["pred_task_id", "pred_task_code", "pred_task_pk"])
        if task_id_column is not None and pred_task_column is not None and pred_pred_column is not None:
            filtered_task_ids = set(filtered_tasks[task_id_column].dropna().tolist())
            filtered_taskpred = taskpred[
                taskpred[pred_task_column].isin(filtered_task_ids) | taskpred[pred_pred_column].isin(filtered_task_ids)
            ].copy()
    critical_path = _build_critical_path_summary(
        filtered_tasks,
        filtered_taskpred,
        taskactv,
        data_date,
        date_window=date_window,
        activity_code=activity_code,
        source_label=source_label,
    )
    return {
        "source": source_label,
        "filters": {
            "date_window": date_window,
            "activity_code": activity_code,
        },
        **critical_path,
    }


@app.get("/api/forecast")
async def get_forecast(date_window: str = Query("all"), activity_code: str = Query("all")) -> dict[str, Any]:
    source_label, selected = _get_selected_project_dataset()
    tables = selected["tables"]
    tasks = tables.get("TASK", pd.DataFrame())
    taskactv = tables.get("TASKACTV", pd.DataFrame())
    data_date = _resolve_data_date(tasks, taskactv)
    forecast = _build_forecast_summary(
        tasks,
        taskactv,
        data_date,
        date_window=date_window,
        activity_code=activity_code,
        source_label=source_label,
    )
    return forecast


@app.get("/api/baseline-compare")
async def get_baseline_compare(date_window: str = Query("all"), activity_code: str = Query("all")) -> dict[str, Any]:
    project_data = app.state.project_data
    if project_data is None:
        raise HTTPException(status_code=400, detail="No project data uploaded yet.")

    original = project_data.get("original")
    updated = project_data.get("updated")
    if original is None or updated is None:
        raise HTTPException(status_code=400, detail="Baseline comparison requires both original and updated XER files.")

    original_tables = original.get("tables", {})
    updated_tables = updated.get("tables", {})
    original_tasks = original_tables.get("TASK", pd.DataFrame())
    original_taskactv = original_tables.get("TASKACTV", pd.DataFrame())
    updated_tasks = updated_tables.get("TASK", pd.DataFrame())
    updated_taskactv = updated_tables.get("TASKACTV", pd.DataFrame())
    original_data_date = _resolve_data_date(original_tasks, original_taskactv)
    updated_data_date = _resolve_data_date(updated_tasks, updated_taskactv)

    comparison = _build_baseline_comparison(
        original_tasks,
        original_taskactv,
        updated_tasks,
        updated_taskactv,
        original_data_date,
        updated_data_date,
        date_window=date_window,
        activity_code=activity_code,
    )
    return {
        "source": "updated_vs_original",
        "filters": {
            "date_window": date_window,
            "activity_code": activity_code,
        },
        **comparison,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
