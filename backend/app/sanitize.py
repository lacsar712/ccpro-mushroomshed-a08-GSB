"""消杀工单状态机与联锁校验。

工单创建 / 流转、采收创建、出菇室列表标记都走本模块，
保证「同室同时仅一个 open/doing 工单」「完工需环境记录」等规则只有一份实现。
"""
from datetime import datetime, timezone

from app.models.climate_log import ClimateLog
from app.models.sanitize_order import SanitizeOrder

ACTIVE_STATUSES = ("open", "doing")
TERMINAL_STATUSES = ("done", "void")
# 允许的推进流转；void 单独处理（任意非终态可作废）
ALLOWED_TRANSITIONS = {("open", "doing"), ("doing", "done")}


class SanitizeConflict(Exception):
    """工单状态冲突，路由层转为 HTTP 409。"""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


def get_active_order(db, room_id: int):
    """该室当前进行中（open/doing）的工单，无则 None。"""
    return (
        db.query(SanitizeOrder)
        .filter(
            SanitizeOrder.room_id == room_id,
            SanitizeOrder.status.in_(ACTIVE_STATUSES),
        )
        .order_by(SanitizeOrder.id.desc())
        .first()
    )


def get_active_order_map(db, room_ids):
    """room_id -> 进行中工单 id，供出菇室列表打标记。"""
    if not room_ids:
        return {}
    rows = (
        db.query(SanitizeOrder.room_id, SanitizeOrder.id)
        .filter(
            SanitizeOrder.room_id.in_(room_ids),
            SanitizeOrder.status.in_(ACTIVE_STATUSES),
        )
        .all()
    )
    return {room_id: order_id for room_id, order_id in rows}


def assert_no_active_order(db, room_id: int) -> None:
    order = get_active_order(db, room_id)
    if order:
        raise SanitizeConflict(f"该出菇室已存在进行中的消杀工单 #{order.id}（{order.status}）")


def has_climate_log_between(db, room_id: int, start: datetime, end: datetime) -> bool:
    """该室在 [start, end] 内是否至少有一条环境记录。"""
    return (
        db.query(ClimateLog)
        .filter(
            ClimateLog.room_id == room_id,
            ClimateLog.recorded_at >= start,
            ClimateLog.recorded_at <= end,
        )
        .count()
        > 0
    )


def apply_transition(db, order: SanitizeOrder, to_status: str) -> SanitizeOrder:
    """按状态机推进工单；非法流转抛 SanitizeConflict。

    open → doing：记录 startedAt；若 Room 非 sanitize 则服务端改为 sanitize（见 README）。
    doing → done：该室 startedAt 至当前须至少一条 ClimateLog，否则抛冲突（409）。
    非终态 → void：作废；done/void 为终态，不可再流转。
    """
    now = datetime.now(timezone.utc)
    if order.status in TERMINAL_STATUSES:
        raise SanitizeConflict(f"工单 #{order.id} 已终态（{order.status}），不可再流转")
    if to_status == "void":
        order.status = "void"
        return order
    if (order.status, to_status) not in ALLOWED_TRANSITIONS:
        raise SanitizeConflict(f"非法状态流转：{order.status} → {to_status}")
    if to_status == "doing":
        order.started_at = now
        order.status = "doing"
        room = order.room
        if room.status != "sanitize":
            room.status = "sanitize"
    elif to_status == "done":
        if not order.started_at:
            raise SanitizeConflict("工单缺少 startedAt，无法完工")
        if not has_climate_log_between(db, order.room_id, order.started_at, now):
            raise SanitizeConflict("完工前需该室在 startedAt 与当前之间至少一条环境记录")
        order.finished_at = now
        order.status = "done"
    return order
