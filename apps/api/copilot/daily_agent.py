"""
Minimal LangGraph daily planning agent for Task 23.
"""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Callable, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from alerts.stockout import StockoutAlert, detect_stockout_risk
from alerts.waste import WasteAlert, detect_waste_risk
from copilot.prompts import DAILY_ACTIONS_BRIEF_PROMPT, DAILY_ACTIONS_RANKING_PROMPT
from db.models import ForecastRun, Ingredient, Outlet, PrepPlan, ReplenishmentPlan, SKU
from forecasting.engine import run_forecast_for_date
from planning.prep import generate_prep_plan
from planning.replenishment import recommend_replenishment

ActionDict = dict[str, Any]
LLMFn = Callable[[str, str], str]

MAX_TOP_ACTIONS = 5
DAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_LABELS_BY_LANGUAGE = {
    "en": DAY_LABELS,
    "ms": ["Isnin", "Selasa", "Rabu", "Khamis", "Jumaat", "Sabtu", "Ahad"],
    "zh-CN": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"],
}
URGENCY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SOURCE_RANK = {
    "stockout": 0,
    "waste": 1,
    "rebalance": 2,
    "reorder": 3,
    "risk": 4,
}


def _local_daypart(language: str, daypart: str) -> str:
    if language == "ms":
        return {"morning": "pagi", "midday": "tengah hari", "evening": "petang"}.get(daypart, daypart)
    if language == "zh-CN":
        return {"morning": "早上", "midday": "中午", "evening": "傍晚"}.get(daypart, daypart)
    return daypart


def _msg(language: str, key: str, **kwargs) -> str:
    if language == "ms":
        templates = {
            "brief_intro": (
                "Tindakan harian untuk {target_date} ({weekday}). Jumlah jualan diramal ialah "
                "{total_predicted_sales} unit, dengan {high_waste_count} amaran pembaziran tinggi, "
                "{high_stockout_count} amaran kehabisan stok tinggi, dan {critical_reorder_count} item pesanan kritikal."
            ),
            "brief_risks": "Risiko utama tertumpu di {outlets}.",
            "brief_none": "Tiada tindakan persediaan, pesanan semula atau penyeimbangan semula yang mendesak pada masa ini.",
            "brief_top": "Tindakan utama: {actions}",
            "brief_monitor": "Tindakan utama: Teruskan pemantauan pelan langsung dan muat semula ringkasan harian apabila data baharu tiba.",
            "risk_waste_watch": "Pantau risiko pembaziran {sku_name} di {outlet_name} pada sesi {daypart}",
            "risk_waste_impact": "Boleh menyebabkan pembaziran hujung hari jika prep tidak dilaras.",
            "prep_reduce": "Kurangkan prep {sku_name} di {outlet_name} sebanyak {pct}%",
            "prep_reduce_impact": "Kurangkan tekanan pembaziran; kadar pembaziran 3 hari terkini ialah {waste_rate}.",
            "affected_dayparts": "Sesi terjejas: {dayparts}",
            "risk_stockout_watch": "Pantau risiko kehabisan stok {sku_name} di {outlet_name} pada sesi {daypart}",
            "risk_stockout_impact": "Boleh menjejaskan ketersediaan jualan jika permintaan pagi meningkat.",
            "prep_increase": "Tingkatkan liputan {sku_name} untuk sesi {daypart} di {outlet_name} sebanyak {pct}%",
            "prep_increase_impact": "Kurangkan kira-kira {shortage} unit risiko kekurangan dan tingkatkan liputan {coverage}.",
            "coverage": "Liputan {coverage}",
            "shortage": "Kekurangan {shortage} unit",
            "reorder": "Buat pesanan semula {ingredient_name} sekarang ({urgency} keutamaan)",
            "reorder_impact": "Lindungi pengeluaran terancang untuk {count} SKU dan elakkan risiko kehabisan stok bahan.",
            "need": "Perlu {value} {unit}",
            "stock_on_hand": "Stok sedia ada {value} {unit}",
            "driving_skus": "SKU pemacu: {value}",
            "rebalance": "Semak alokasi antara cawangan untuk {sku_name} antara {waste_outlet} dan {stockout_outlet}",
            "rebalance_impact": "Boleh mengurangkan pembaziran di satu cawangan sambil melindungi ketersediaan di cawangan lain.",
            "waste_risk_at": "Risiko pembaziran di {outlet_name}",
            "stockout_risk_at": "Risiko kehabisan stok di {outlet_name}",
        }
    elif language == "zh-CN":
        templates = {
            "brief_intro": (
                "{target_date}（{weekday}）每日行动。预测总销量为 {total_predicted_sales} 单位，"
                "当前有 {high_waste_count} 条高浪费预警、{high_stockout_count} 条高缺货预警，以及 "
                "{critical_reorder_count} 个关键补货事项。"
            ),
            "brief_risks": "主要风险集中在 {outlets}。",
            "brief_none": "目前没有紧急的备货、补货或再平衡行动。",
            "brief_top": "重点行动：{actions}",
            "brief_monitor": "重点行动：继续监控实时计划，并在新数据到达后刷新每日简报。",
            "risk_waste_watch": "关注 {outlet_name} 在{daypart}的 {sku_name} 浪费风险",
            "risk_waste_impact": "如果不调整备货，可能导致当日结束时的可避免浪费。",
            "prep_reduce": "将 {outlet_name} 的 {sku_name} 备货减少 {pct}%",
            "prep_reduce_impact": "降低浪费压力；最近 3 天浪费率为 {waste_rate}。",
            "affected_dayparts": "受影响时段：{dayparts}",
            "risk_stockout_watch": "关注 {outlet_name} 在{daypart}的 {sku_name} 缺货风险",
            "risk_stockout_impact": "若早间需求上升，可能影响可售性。",
            "prep_increase": "将 {outlet_name} 在{daypart}的 {sku_name} 供应提高 {pct}%",
            "prep_increase_impact": "可减少约 {shortage} 单位短缺风险，并把覆盖率提高到 {coverage}。",
            "coverage": "覆盖率 {coverage}",
            "shortage": "短缺 {shortage} 单位",
            "reorder": "立即补货 {ingredient_name}（{urgency}）",
            "reorder_impact": "保护 {count} 个 SKU 的计划生产，并降低原料导致的缺货风险。",
            "need": "需求 {value} {unit}",
            "stock_on_hand": "现有库存 {value} {unit}",
            "driving_skus": "驱动 SKU：{value}",
            "rebalance": "检查 {waste_outlet} 与 {stockout_outlet} 之间 {sku_name} 的跨门店分配",
            "rebalance_impact": "可减少一个门店的浪费，同时保障另一个门店的供应。",
            "waste_risk_at": "{outlet_name} 存在浪费风险",
            "stockout_risk_at": "{outlet_name} 存在缺货风险",
        }
    else:
        templates = {
            "brief_intro": (
                "Daily actions for {target_date} ({weekday}). Total predicted sales are "
                "{total_predicted_sales} units, with {high_waste_count} high waste alerts, "
                "{high_stockout_count} high stockout alerts, and {critical_reorder_count} critical reorder items."
            ),
            "brief_risks": "Key risks are concentrated in {outlets}.",
            "brief_none": "No urgent prep, reorder, or rebalance actions are currently required.",
            "brief_top": "Top actions: {actions}",
            "brief_monitor": "Top actions: Keep monitoring the live plan and refresh the daily brief after new data arrives.",
            "risk_waste_watch": "Watch {sku_name} at {outlet_name} for {daypart} waste risk",
            "risk_waste_impact": "Could lead to avoidable end-of-day waste if prep is not adjusted.",
            "prep_reduce": "Reduce {sku_name} prep at {outlet_name} by {pct}%",
            "prep_reduce_impact": "Reduce waste pressure; recent 3-day waste rate is {waste_rate}.",
            "affected_dayparts": "Affected dayparts: {dayparts}",
            "risk_stockout_watch": "Watch {sku_name} at {outlet_name} for {daypart} stockout risk",
            "risk_stockout_impact": "Could reduce service availability if morning demand spikes.",
            "prep_increase": "Increase {sku_name} {daypart} coverage at {outlet_name} by {pct}%",
            "prep_increase_impact": "Recover about {shortage} units of shortage risk and improve {coverage} coverage.",
            "coverage": "Coverage {coverage}",
            "shortage": "Shortage {shortage} units",
            "reorder": "Reorder {ingredient_name} now ({urgency} urgency)",
            "reorder_impact": "Protect planned production for {count} SKU(s) and prevent ingredient-driven stockout risk.",
            "need": "Need {value} {unit}",
            "stock_on_hand": "Stock on hand {value} {unit}",
            "driving_skus": "Driving SKUs: {value}",
            "rebalance": "Review cross-outlet allocation for {sku_name} between {waste_outlet} and {stockout_outlet}",
            "rebalance_impact": "May reduce waste at one outlet while protecting availability at another.",
            "waste_risk_at": "Waste risk at {outlet_name}",
            "stockout_risk_at": "Stockout risk at {outlet_name}",
        }

    return templates[key].format(**kwargs)


class DailyAgentState(TypedDict, total=False):
    target_date: date
    top_n: int
    forecast_run: ForecastRun
    prep_plan: PrepPlan
    replenishment_plan: ReplenishmentPlan
    waste_alerts: list[WasteAlert]
    stockout_alerts: list[StockoutAlert]
    prep_actions: list[ActionDict]
    reorder_actions: list[ActionDict]
    risk_warnings: list[ActionDict]
    rebalance_suggestions: list[ActionDict]
    candidate_actions: list[ActionDict]
    ranked_actions: list[ActionDict]
    brief: str
    fallback_mode: bool
    total_predicted_sales: int
    high_waste_count: int
    high_stockout_count: int
    critical_reorder_count: int
    errors: list[str]


def _clamp_top_n(top_n: int) -> int:
    return max(1, min(MAX_TOP_ACTIONS, top_n))


def _get_latest_forecast_run(target_date: date, db: Session):
    return (
        db.query(ForecastRun)
        .filter(ForecastRun.forecast_date == target_date)
        .order_by(ForecastRun.created_at.desc())
        .first()
    )


def _get_latest_prep_plan(target_date: date, db: Session):
    return (
        db.query(PrepPlan)
        .filter(PrepPlan.plan_date == target_date)
        .order_by(PrepPlan.created_at.desc())
        .first()
    )


def _get_latest_replenishment_plan(target_date: date, db: Session):
    return (
        db.query(ReplenishmentPlan)
        .filter(ReplenishmentPlan.plan_date == target_date)
        .order_by(ReplenishmentPlan.created_at.desc())
        .first()
    )


def _format_pct(value: float) -> str:
    return f"{value:.1f}%"


def _target(
    *,
    outlet_id: int | None = None,
    outlet_name: str | None = None,
    sku_id: int | None = None,
    sku_name: str | None = None,
    ingredient_id: int | None = None,
    ingredient_name: str | None = None,
) -> dict[str, Any]:
    return {
        "outlet_id": outlet_id,
        "outlet_name": outlet_name,
        "sku_id": sku_id,
        "sku_name": sku_name,
        "ingredient_id": ingredient_id,
        "ingredient_name": ingredient_name,
    }


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        clean = item.strip()
        if clean and clean not in seen:
            deduped.append(clean)
            seen.add(clean)
    return deduped


def _make_action(
    *,
    action_id: str,
    action_type: str,
    action_text: str,
    urgency: str,
    estimated_impact: str,
    target_data: dict[str, Any],
    evidence: list[str],
    priority: int,
    source_family: str,
) -> ActionDict:
    return {
        "action_id": action_id,
        "action_type": action_type,
        "action_text": action_text,
        "urgency": urgency,
        "estimated_impact": estimated_impact,
        "target": target_data,
        "evidence": _dedupe_strings(evidence),
        "source_type": "deterministic",
        "_priority": priority,
        "_source_family": source_family,
    }


def _priority_sort_key(action: ActionDict) -> tuple[int, int, int, int, str]:
    evidence_text = " ".join(action.get("evidence", []))
    explicit_metric = 1 if re.search(r"\d", evidence_text) else 0
    urgency_rank = URGENCY_RANK.get(action["urgency"], 99)
    source_rank = SOURCE_RANK.get(action.get("_source_family", "risk"), 99)
    return (
        -int(action.get("_priority", 0)),
        source_rank,
        urgency_rank,
        -explicit_metric,
        action["action_text"],
    )


def _top_action_key(action: ActionDict) -> tuple[Any, ...]:
    target_data = action["target"]
    if target_data.get("ingredient_id") is not None:
        return ("ingredient", target_data["ingredient_id"])
    if target_data.get("outlet_id") is not None and target_data.get("sku_id") is not None:
        return ("sku", target_data["outlet_id"], target_data["sku_id"])
    if target_data.get("sku_id") is not None:
        return ("sku_any", target_data["sku_id"])
    return ("action", action["action_id"])


def _select_top_actions(actions: list[ActionDict], top_n: int) -> list[ActionDict]:
    chosen: list[ActionDict] = []
    seen_keys: set[tuple[Any, ...]] = set()
    for action in sorted(actions, key=_priority_sort_key):
        key = _top_action_key(action)
        if key in seen_keys:
            continue
        chosen.append(action)
        seen_keys.add(key)
        if len(chosen) >= top_n:
            break
    return chosen


def _serialize_action(action: ActionDict) -> ActionDict:
    return {
        "action_type": action["action_type"],
        "action_text": action["action_text"],
        "urgency": action["urgency"],
        "estimated_impact": action["estimated_impact"],
        "target": dict(action["target"]),
        "evidence": list(action["evidence"]),
        "source_type": action["source_type"],
    }


def _extract_json_array(raw: str) -> list[dict[str, Any]] | None:
    if not raw:
        return None

    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.replace("json", "", 1).strip()

    payload: Any
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", stripped)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    if isinstance(payload, dict):
        payload = payload.get("top_actions")
    if not isinstance(payload, list):
        return None
    return [item for item in payload if isinstance(item, dict)]


def _deterministic_brief(
    state: DailyAgentState, top_actions: list[ActionDict], language: str
) -> str:
    target_date = state["target_date"]
    weekday = DAY_LABELS_BY_LANGUAGE.get(language, DAY_LABELS)[target_date.weekday()]
    intro = _msg(
        language,
        "brief_intro",
        target_date=target_date,
        weekday=weekday,
        total_predicted_sales=state["total_predicted_sales"],
        high_waste_count=state["high_waste_count"],
        high_stockout_count=state["high_stockout_count"],
        critical_reorder_count=state["critical_reorder_count"],
    )
    if top_actions:
        outlets = ", ".join(
            _dedupe_strings(
                [
                    action["target"].get("outlet_name")
                    for action in top_actions
                    if action["target"].get("outlet_name")
                ]
            )[:3]
        )
        main_risks = _msg(language, "brief_risks", outlets=outlets)
        action_summary = _msg(
            language,
            "brief_top",
            actions="; ".join(action["action_text"] for action in top_actions[:3]),
        )
    else:
        main_risks = _msg(language, "brief_none")
        action_summary = _msg(language, "brief_monitor")
    return f"{intro}\n\n{main_risks}\n\n{action_summary}"


def generate_daily_actions(
    target_date: date, top_n: int, db: Session, llm_fn: LLMFn, language: str = "en"
) -> dict[str, Any]:
    top_n = _clamp_top_n(top_n)

    def load_context(state: DailyAgentState) -> DailyAgentState:
        forecast_run = _get_latest_forecast_run(target_date, db)
        if not forecast_run:
            forecast_run = run_forecast_for_date(target_date, db)

        prep_plan = _get_latest_prep_plan(target_date, db)
        if not prep_plan:
            prep_plan = generate_prep_plan(target_date, db)

        replenishment_plan = _get_latest_replenishment_plan(target_date, db)
        if not replenishment_plan:
            replenishment_plan = recommend_replenishment(target_date, db)

        waste_alerts = detect_waste_risk(target_date, db)
        stockout_alerts = detect_stockout_risk(target_date, db)

        return {
            "forecast_run": forecast_run,
            "prep_plan": prep_plan,
            "replenishment_plan": replenishment_plan,
            "waste_alerts": waste_alerts,
            "stockout_alerts": stockout_alerts,
            "total_predicted_sales": round(sum(line.total for line in forecast_run.lines), 0),
            "high_waste_count": sum(1 for alert in waste_alerts if alert.risk_level == "high"),
            "high_stockout_count": sum(1 for alert in stockout_alerts if alert.risk_level == "high"),
            "critical_reorder_count": sum(
                1 for line in replenishment_plan.lines if line.urgency == "critical"
            ),
            "fallback_mode": False,
            "errors": [],
        }

    def derive_candidate_actions(state: DailyAgentState) -> DailyAgentState:
        prep_actions: list[ActionDict] = []
        reorder_actions: list[ActionDict] = []
        risk_warnings: list[ActionDict] = []
        rebalance_suggestions: list[ActionDict] = []

        waste_groups: dict[tuple[int, int], dict[str, Any]] = {}
        for alert in state["waste_alerts"]:
            if alert.risk_level not in {"high", "medium"}:
                continue
            key = (alert.outlet_id, alert.sku_id)
            group = waste_groups.setdefault(
                key,
                {
                    "outlet_id": alert.outlet_id,
                    "outlet_name": alert.outlet_name,
                    "sku_id": alert.sku_id,
                    "sku_name": alert.sku_name,
                    "risk_level": alert.risk_level,
                    "waste_rate": alert.waste_rate,
                    "dayparts": [],
                    "evidence": [],
                },
            )
            if URGENCY_RANK.get(alert.risk_level, 99) < URGENCY_RANK.get(group["risk_level"], 99):
                group["risk_level"] = alert.risk_level
            group["waste_rate"] = max(group["waste_rate"], alert.waste_rate)
            group["dayparts"].append(alert.daypart)
            group["evidence"].extend(alert.triggers[:2])

            risk_warnings.append(
                _make_action(
                    action_id=f"risk-waste-{alert.outlet_id}-{alert.sku_id}-{alert.daypart}",
                    action_type="risk",
                    action_text=_msg(
                        language,
                        "risk_waste_watch",
                        sku_name=alert.sku_name,
                        outlet_name=alert.outlet_name,
                        daypart=_local_daypart(language, alert.daypart),
                    ),
                    urgency=alert.risk_level,
                    estimated_impact=_msg(language, "risk_waste_impact"),
                    target_data=_target(
                        outlet_id=alert.outlet_id,
                        outlet_name=alert.outlet_name,
                        sku_id=alert.sku_id,
                        sku_name=alert.sku_name,
                    ),
                    evidence=[
                        f"3-day waste rate {_format_pct(alert.waste_rate * 100)}",
                        alert.reason,
                    ],
                    priority=80 if alert.risk_level == "high" else 50,
                    source_family="waste",
                )
            )

        for group in waste_groups.values():
            reduction_pct = 10 if group["risk_level"] == "high" else 5
            prep_actions.append(
                _make_action(
                    action_id=f"prep-waste-{group['outlet_id']}-{group['sku_id']}",
                    action_type="prep",
                    action_text=(
                        _msg(
                            language,
                            "prep_reduce",
                            sku_name=group["sku_name"],
                            outlet_name=group["outlet_name"],
                            pct=reduction_pct,
                        )
                    ),
                    urgency=group["risk_level"],
                    estimated_impact=_msg(
                        language,
                        "prep_reduce_impact",
                        waste_rate=_format_pct(group["waste_rate"] * 100),
                    ),
                    target_data=_target(
                        outlet_id=group["outlet_id"],
                        outlet_name=group["outlet_name"],
                        sku_id=group["sku_id"],
                        sku_name=group["sku_name"],
                    ),
                    evidence=[
                        f"3-day waste rate {_format_pct(group['waste_rate'] * 100)}",
                        _msg(
                            language,
                            "affected_dayparts",
                            dayparts=", ".join(_local_daypart(language, value) for value in sorted(set(group["dayparts"]))),
                        ),
                    ]
                    + group["evidence"][:2],
                    priority=80 if group["risk_level"] == "high" else 50,
                    source_family="waste",
                )
            )

        stockout_groups: dict[tuple[int, int], dict[str, Any]] = {}
        for alert in state["stockout_alerts"]:
            if alert.risk_level not in {"high", "medium"}:
                continue
            key = (alert.outlet_id, alert.sku_id)
            group = stockout_groups.setdefault(
                key,
                {
                    "outlet_id": alert.outlet_id,
                    "outlet_name": alert.outlet_name,
                    "sku_id": alert.sku_id,
                    "sku_name": alert.sku_name,
                    "risk_level": alert.risk_level,
                    "coverage_pct": alert.coverage_pct,
                    "shortage_qty": alert.shortage_qty,
                    "dayparts": [],
                    "evidence": [],
                },
            )
            if URGENCY_RANK.get(alert.risk_level, 99) < URGENCY_RANK.get(group["risk_level"], 99):
                group["risk_level"] = alert.risk_level
            group["coverage_pct"] = min(group["coverage_pct"], alert.coverage_pct)
            group["shortage_qty"] = max(group["shortage_qty"], alert.shortage_qty)
            group["dayparts"].append(alert.affected_daypart)
            group["evidence"].append(alert.reason)

            risk_warnings.append(
                _make_action(
                    action_id=f"risk-stockout-{alert.outlet_id}-{alert.sku_id}-{alert.affected_daypart}",
                    action_type="risk",
                    action_text=(
                        _msg(
                            language,
                            "risk_stockout_watch",
                            sku_name=alert.sku_name,
                            outlet_name=alert.outlet_name,
                            daypart=_local_daypart(language, alert.affected_daypart),
                        )
                    ),
                    urgency=alert.risk_level,
                    estimated_impact=_msg(language, "risk_stockout_impact"),
                    target_data=_target(
                        outlet_id=alert.outlet_id,
                        outlet_name=alert.outlet_name,
                        sku_id=alert.sku_id,
                        sku_name=alert.sku_name,
                    ),
                    evidence=[
                        _msg(language, "coverage", coverage=_format_pct(alert.coverage_pct)),
                        _msg(language, "shortage", shortage=f"{alert.shortage_qty:.1f}"),
                        alert.reason,
                    ],
                    priority=90 if alert.risk_level == "high" else 60,
                    source_family="stockout",
                )
            )

        for group in stockout_groups.values():
            increase_pct = 10 if group["risk_level"] == "high" else 5
            primary_daypart = sorted(set(group["dayparts"]))[0]
            prep_actions.append(
                _make_action(
                    action_id=f"prep-stockout-{group['outlet_id']}-{group['sku_id']}",
                    action_type="prep",
                    action_text=(
                        _msg(
                            language,
                            "prep_increase",
                            sku_name=group["sku_name"],
                            daypart=_local_daypart(language, primary_daypart),
                            outlet_name=group["outlet_name"],
                            pct=increase_pct,
                        )
                    ),
                    urgency=group["risk_level"],
                    estimated_impact=_msg(
                        language,
                        "prep_increase_impact",
                        shortage=f"{group['shortage_qty']:.1f}",
                        coverage=_format_pct(group["coverage_pct"]),
                    ),
                    target_data=_target(
                        outlet_id=group["outlet_id"],
                        outlet_name=group["outlet_name"],
                        sku_id=group["sku_id"],
                        sku_name=group["sku_name"],
                    ),
                    evidence=[
                        _msg(language, "coverage", coverage=_format_pct(group["coverage_pct"])),
                        _msg(language, "shortage", shortage=f"{group['shortage_qty']:.1f}"),
                        _msg(
                            language,
                            "affected_dayparts",
                            dayparts=", ".join(
                                _local_daypart(language, value) for value in sorted(set(group["dayparts"]))
                            ),
                        ),
                    ]
                    + group["evidence"][:2],
                    priority=90 if group["risk_level"] == "high" else 60,
                    source_family="stockout",
                )
            )

        for line in state["replenishment_plan"].lines:
            if line.urgency not in {"critical", "high"}:
                continue
            ingredient = line.ingredient
            unit = ingredient.unit if ingredient else "units"
            driving_skus = line.driving_skus or []
            reorder_actions.append(
                _make_action(
                    action_id=f"reorder-{line.ingredient_id}",
                    action_type="reorder",
                    action_text=(
                        _msg(
                            language,
                            "reorder",
                            ingredient_name=ingredient.name if ingredient else "ingredient",
                            urgency=line.urgency,
                        )
                    ),
                    urgency=line.urgency,
                    estimated_impact=_msg(
                        language,
                        "reorder_impact",
                        count=len(driving_skus),
                    ),
                    target_data=_target(
                        ingredient_id=line.ingredient_id,
                        ingredient_name=ingredient.name if ingredient else None,
                    ),
                    evidence=[
                        _msg(language, "need", value=f"{line.need_qty:.1f}", unit=unit),
                        _msg(language, "stock_on_hand", value=f"{line.stock_on_hand:.1f}", unit=unit),
                        _msg(
                            language,
                            "driving_skus",
                            value=", ".join(driving_skus[:3]) if driving_skus else "none",
                        ),
                    ],
                    priority=100 if line.urgency == "critical" else 40,
                    source_family="reorder",
                )
            )

        waste_by_sku: dict[int, WasteAlert] = {}
        stockout_by_sku: dict[int, StockoutAlert] = {}
        for alert in state["waste_alerts"]:
            if alert.risk_level in {"high", "medium"} and alert.sku_id not in waste_by_sku:
                waste_by_sku[alert.sku_id] = alert
        for alert in state["stockout_alerts"]:
            if alert.risk_level in {"high", "medium"} and alert.sku_id not in stockout_by_sku:
                stockout_by_sku[alert.sku_id] = alert

        for sku_id, waste_alert in waste_by_sku.items():
            stockout_alert = stockout_by_sku.get(sku_id)
            if not stockout_alert or stockout_alert.outlet_id == waste_alert.outlet_id:
                continue
            urgency = (
                "high"
                if "high" in {waste_alert.risk_level, stockout_alert.risk_level}
                else "medium"
            )
            rebalance_suggestions.append(
                _make_action(
                    action_id=f"rebalance-{sku_id}",
                    action_type="rebalance",
                    action_text=(
                        _msg(
                            language,
                            "rebalance",
                            sku_name=waste_alert.sku_name,
                            waste_outlet=waste_alert.outlet_name,
                            stockout_outlet=stockout_alert.outlet_name,
                        )
                    ),
                    urgency=urgency,
                    estimated_impact=_msg(language, "rebalance_impact"),
                    target_data=_target(
                        sku_id=sku_id,
                        sku_name=waste_alert.sku_name,
                    ),
                    evidence=[
                        _msg(language, "waste_risk_at", outlet_name=waste_alert.outlet_name),
                        _msg(language, "stockout_risk_at", outlet_name=stockout_alert.outlet_name),
                    ],
                    priority=70,
                    source_family="rebalance",
                )
            )

        risk_warnings = sorted(risk_warnings, key=_priority_sort_key)[:5]
        candidate_actions = prep_actions + reorder_actions + risk_warnings + rebalance_suggestions

        return {
            "prep_actions": prep_actions,
            "reorder_actions": reorder_actions,
            "risk_warnings": risk_warnings,
            "rebalance_suggestions": rebalance_suggestions,
            "candidate_actions": candidate_actions,
        }

    def rank_and_phrase_actions(state: DailyAgentState) -> DailyAgentState:
        top_actions = _select_top_actions(state.get("candidate_actions", []), state["top_n"])
        fallback_mode = bool(state.get("fallback_mode", False))

        candidate_payload = [
            {
                "action_id": action["action_id"],
                "action_type": action["action_type"],
                "urgency": action["urgency"],
                "action_text": action["action_text"],
                "estimated_impact": action["estimated_impact"],
                "target": action["target"],
                "evidence": action["evidence"],
            }
            for action in top_actions
        ]

        if candidate_payload:
            prompt = DAILY_ACTIONS_RANKING_PROMPT.format(
                date=str(state["target_date"]),
                top_n=state["top_n"],
                candidate_actions_json=json.dumps(candidate_payload, indent=2),
            )
            raw = llm_fn(prompt, "")
            parsed = _extract_json_array(raw)
            if parsed:
                actions_by_id = {action["action_id"]: action for action in top_actions}
                ranked: list[ActionDict] = []
                seen_ids: set[str] = set()
                for item in parsed:
                    action_id = item.get("action_id")
                    if not isinstance(action_id, str) or action_id not in actions_by_id or action_id in seen_ids:
                        continue
                    action = actions_by_id[action_id]
                    action_text = item.get("action_text")
                    estimated_impact = item.get("estimated_impact")
                    if isinstance(action_text, str) and action_text.strip():
                        action["action_text"] = action_text.strip()
                    if isinstance(estimated_impact, str) and estimated_impact.strip():
                        action["estimated_impact"] = estimated_impact.strip()
                    action["source_type"] = "llm_rephrased"
                    ranked.append(action)
                    seen_ids.add(action_id)
                    if len(ranked) >= state["top_n"]:
                        break

                if ranked:
                    for action in top_actions:
                        if action["action_id"] not in seen_ids and len(ranked) < state["top_n"]:
                            ranked.append(action)
                    top_actions = ranked[: state["top_n"]]
                else:
                    fallback_mode = True
            else:
                fallback_mode = True

        brief_fallback = _deterministic_brief(state, top_actions, language)
        brief_prompt = DAILY_ACTIONS_BRIEF_PROMPT.format(
            date=str(state["target_date"]),
            weekday=DAY_LABELS_BY_LANGUAGE.get(language, DAY_LABELS)[state["target_date"].weekday()],
            total_predicted_sales=state["total_predicted_sales"],
            high_waste_count=state["high_waste_count"],
            high_stockout_count=state["high_stockout_count"],
            critical_reorder_count=state["critical_reorder_count"],
            fallback_mode=str(fallback_mode).lower(),
            top_actions_json=json.dumps(
                [
                    {
                        "action_type": action["action_type"],
                        "urgency": action["urgency"],
                        "action_text": action["action_text"],
                        "estimated_impact": action["estimated_impact"],
                    }
                    for action in top_actions
                ],
                indent=2,
            ),
        )
        brief = llm_fn(brief_prompt, brief_fallback).strip() or brief_fallback
        if brief == brief_fallback:
            fallback_mode = True

        return {
            "ranked_actions": top_actions,
            "brief": brief,
            "fallback_mode": fallback_mode,
        }

    def validate_and_finalize(state: DailyAgentState) -> DailyAgentState:
        outlet_ids = {outlet.id for outlet in db.query(Outlet).all()}
        sku_ids = {sku.id for sku in db.query(SKU).all()}
        ingredient_ids = {ingredient.id for ingredient in db.query(Ingredient).all()}

        def is_valid(action: ActionDict) -> bool:
            target_data = action["target"]
            if target_data["outlet_id"] is not None and target_data["outlet_id"] not in outlet_ids:
                return False
            if target_data["sku_id"] is not None and target_data["sku_id"] not in sku_ids:
                return False
            if target_data["ingredient_id"] is not None and target_data["ingredient_id"] not in ingredient_ids:
                return False
            return True

        prep_actions = [action for action in state["prep_actions"] if is_valid(action)]
        reorder_actions = [action for action in state["reorder_actions"] if is_valid(action)]
        risk_warnings = [action for action in state["risk_warnings"] if is_valid(action)]
        rebalance_suggestions = [
            action for action in state["rebalance_suggestions"] if is_valid(action)
        ]
        ranked_actions = [
            action for action in state.get("ranked_actions", []) if is_valid(action)
        ][: state["top_n"]]

        return {
            "prep_actions": [_serialize_action(action) for action in prep_actions],
            "reorder_actions": [_serialize_action(action) for action in reorder_actions],
            "risk_warnings": [_serialize_action(action) for action in risk_warnings],
            "rebalance_suggestions": [
                _serialize_action(action) for action in rebalance_suggestions
            ],
            "ranked_actions": [_serialize_action(action) for action in ranked_actions],
        }

    graph = StateGraph(DailyAgentState)
    graph.add_node("load_context", load_context)
    graph.add_node("derive_candidate_actions", derive_candidate_actions)
    graph.add_node("rank_and_phrase_actions", rank_and_phrase_actions)
    graph.add_node("validate_and_finalize", validate_and_finalize)
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "derive_candidate_actions")
    graph.add_edge("derive_candidate_actions", "rank_and_phrase_actions")
    graph.add_edge("rank_and_phrase_actions", "validate_and_finalize")
    graph.add_edge("validate_and_finalize", END)

    final_state = graph.compile().invoke({"target_date": target_date, "top_n": top_n})
    return {
        "date": str(target_date),
        "brief": final_state["brief"],
        "fallback_mode": final_state["fallback_mode"],
        "top_actions": final_state["ranked_actions"],
        "prep_actions": final_state["prep_actions"],
        "reorder_actions": final_state["reorder_actions"],
        "risk_warnings": final_state["risk_warnings"],
        "rebalance_suggestions": final_state["rebalance_suggestions"],
    }
