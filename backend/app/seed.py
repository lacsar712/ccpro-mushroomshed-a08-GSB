from datetime import datetime, timedelta, timezone

from app.auth import hash_password
from app.database import SessionLocal
from app.models.climate_log import ClimateLog
from app.models.flush_harvest import FlushHarvest
from app.models.room import Room
from app.models.sanitize_order import SanitizeOrder
from app.models.shed import Shed
from app.models.user import User


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add_all(
                [
                    User(
                        username="admin",
                        hashed_password=hash_password("123456"),
                        role="admin",
                        display_name="场长",
                    ),
                    User(
                        username="fruiter",
                        hashed_password=hash_password("123456"),
                        role="fruiter",
                        display_name="出菇员",
                    ),
                ]
            )
            db.commit()

        if db.query(Shed).count() == 0:
            s1 = Shed(
                name="松木岭一号菇房",
                location="闽北高海拔林区 A 区",
                notes="主产香菇与平菇",
            )
            s2 = Shed(
                name="溪谷恒温菇房",
                location="山谷侧翼 B 区",
                notes="杏鲍菇与秀珍菇轮作",
            )
            db.add_all([s1, s2])
            db.flush()

            r1 = Room(
                shed_id=s1.id,
                room_code="R-01",
                species="香菇",
                capacity_bags=1200,
                status="fruiting",
            )
            r2 = Room(
                shed_id=s1.id,
                room_code="R-02",
                species="平菇",
                capacity_bags=800,
                status="idle",
            )
            r3 = Room(
                shed_id=s2.id,
                room_code="V-01",
                species="杏鲍菇",
                capacity_bags=600,
                status="fruiting",
            )
            r4 = Room(
                shed_id=s2.id,
                room_code="V-02",
                species="秀珍菇",
                capacity_bags=500,
                status="sanitize",
            )
            db.add_all([r1, r2, r3, r4])
            db.flush()

            now = datetime.now(timezone.utc)
            db.add_all(
                [
                    ClimateLog(
                        room_id=r1.id,
                        recorded_at=now - timedelta(hours=2),
                        temp_c=18.5,
                        humidity_pct=88,
                        co2_ppm=950.0,
                        notes="晨检正常",
                    ),
                    ClimateLog(
                        room_id=r1.id,
                        recorded_at=now - timedelta(hours=8),
                        temp_c=17.8,
                        humidity_pct=90,
                        co2_ppm=880.0,
                        notes=None,
                    ),
                    ClimateLog(
                        room_id=r3.id,
                        recorded_at=now - timedelta(hours=4),
                        temp_c=16.2,
                        humidity_pct=85,
                        co2_ppm=720.0,
                        notes="CO2 略偏高",
                    ),
                    ClimateLog(
                        room_id=r3.id,
                        recorded_at=now - timedelta(hours=12),
                        temp_c=15.9,
                        humidity_pct=87,
                        co2_ppm=690.0,
                        notes=None,
                    ),
                    FlushHarvest(
                        room_id=r1.id,
                        harvested_at=now - timedelta(hours=6),
                        flush_no=2,
                        weight_kg=42.5,
                        grade="A",
                        operator_name="出菇员",
                    ),
                    FlushHarvest(
                        room_id=r1.id,
                        harvested_at=now - timedelta(days=1),
                        flush_no=1,
                        weight_kg=38.0,
                        grade="B",
                        operator_name="场长",
                    ),
                    FlushHarvest(
                        room_id=r3.id,
                        harvested_at=now - timedelta(days=3),
                        flush_no=1,
                        weight_kg=55.2,
                        grade="A",
                        operator_name="出菇员",
                    ),
                ]
            )
            db.commit()
            print("Seed data inserted.")
        else:
            print("Seed skipped (data exists).")

        _seed_sanitize_orders(db)
    finally:
        db.close()


def _seed_sanitize_orders(db) -> None:
    """消杀工单演示数据（独立于主 seed，老库也会补齐）。

    - R-02：doing 且窗口内有环境记录 → 可 done。
    - V-02：doing 但 startedAt 之后无环境记录 → done 必 409。
    两室状态置为 sanitize，与 open→doing 联锁一致。
    """
    if db.query(SanitizeOrder).count() > 0:
        return
    ready_room = db.query(Room).filter(Room.room_code == "R-02").first()
    blocked_room = db.query(Room).filter(Room.room_code == "V-02").first()
    if not ready_room or not blocked_room:
        return
    now = datetime.now(timezone.utc)

    ready_room.status = "sanitize"
    db.add(
        ClimateLog(
            room_id=ready_room.id,
            recorded_at=now - timedelta(hours=1),
            temp_c=19.4,
            humidity_pct=92,
            co2_ppm=810.0,
            notes="消杀期间环境监测",
        )
    )
    db.add(
        SanitizeOrder(
            room_id=ready_room.id,
            method="uv",
            status="doing",
            operator_name="场长",
            planned_at=now - timedelta(hours=4),
            started_at=now - timedelta(hours=3),
        )
    )

    blocked_room.status = "sanitize"
    db.add(
        SanitizeOrder(
            room_id=blocked_room.id,
            method="chemical",
            status="doing",
            operator_name="出菇员",
            planned_at=now - timedelta(hours=5),
            started_at=now - timedelta(hours=3),
        )
    )
    db.commit()
    print("Sanitize order seed inserted.")


if __name__ == "__main__":
    seed()
