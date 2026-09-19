"""消杀工单状态机与联锁校验。

采收创建（routes/flush_harvests.py）与工单新建/流转（routes/sanitize_orders.py）
共用本模块的校验，保证「同室同时一单」与「消杀期间禁采收」只有一份实现。
"""

from datetime import datetime, timezone
from typing import Iterable, List, Optional

from app.models.climate_log import ClimateLog
from app.models.room import Room
from app.models.sanitize_order import SanitizeOrder

ACTIVE_STATUSES = ("open", "doing")
TERMINAL_STATUSES = ("done", "void")

# 状态机：open→doing、doing→done；非终态（open/doing）可 void；done/void 为终态
ALLOWED_TRANSITIONS = frozenset(
    {
        ("open", "doing"),
        ("doing", "done"),
        ("open", "void"),
        ("doing", "void"),
    }
)


class ConflictError(Exception):
    """业务规则冲突，路由层转为 HTTP 409。"""


def get_active_order(db, room_id: int, exclude_id: Optional[int] = None) -> Optional[SanitizeOrder]:
    q = db.query(SanitizeOrder).filter(
        SanitizeOrder.room_id == room_id,
        SanitizeOrder.status.in_(ACTIVE_STATUSES),
    )
    if exclude_id is not None:
        q = q.filter(SanitizeOrder.id != exclude_id)
    return q.first()


def ensure_no_active_order(db, room_id: int, exclude_id: Optional[int] = None) -> None:
    """同室同时只许一个 open/doing 消杀单。"""
    if get_active_order(db, room_id, exclude_id=exclude_id) is not None:
        raise ConflictError("该出菇室已存在未完成的消杀单（open/doing）")


def ensure_harvest_allowed(db, room_id: int) -> None:
    """同室存在 open/doing 消杀单时禁止新建采收。"""
    if get_active_order(db, room_id) is not None:
        raise ConflictError("该出菇室存在进行中的消杀单，禁止新建采收记录")


def ensure_climate_logged(db, room_id: int, started_at: datetime, until: datetime) -> None:
    """doing→done 前置：startedAt 与当前之间必须至少一条环境记录。"""
    count = (
        db.query(ClimateLog)
        .filter(
            ClimateLog.room_id == room_id,
            ClimateLog.recorded_at >= started_at,
            ClimateLog.recorded_at <= until,
        )
        .count()
    )
    if count == 0:
        raise ConflictError("消杀开始至今缺少环境记录，无法完工（done）")


def apply_transition(db, order: SanitizeOrder, target: str, room: Room) -> None:
    """按状态机推进工单；非法流转或联锁校验失败抛 ConflictError。"""
    if (order.status, target) not in ALLOWED_TRANSITIONS:
        raise ConflictError(f"不允许的状态流转：{order.status} → {target}")
    now = datetime.now(timezone.utc)
    if target == "doing":
        order.started_at = now
        # 开工联锁：Room 非 sanitize 时由服务端改为 sanitize
        if room.status != "sanitize":
            room.status = "sanitize"
    elif target == "done":
        ensure_climate_logged(db, order.room_id, order.started_at, now)
        order.finished_at = now
    else:  # void
        order.finished_at = now
    order.status = target


def annotate_active_orders(db, rooms: Iterable[Room]) -> List[Room]:
    """为出菇室列表挂上开放中消杀单标记（active_sanitize_order_id，可空）。"""
    pairs = (
        db.query(SanitizeOrder.room_id, SanitizeOrder.id)
        .filter(SanitizeOrder.status.in_(ACTIVE_STATUSES))
        .all()
    )
    active_map = {room_id: order_id for room_id, order_id in pairs}
    annotated = list(rooms)
    for room in annotated:
        room.active_sanitize_order_id = active_map.get(room.id)
    return annotated
