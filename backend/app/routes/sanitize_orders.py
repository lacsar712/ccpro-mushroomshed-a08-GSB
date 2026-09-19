from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError

from app.database import SessionLocal
from app.models.room import Room
from app.models.sanitize_order import SanitizeOrder
from app.sanitize import SanitizeConflict, apply_transition, assert_no_active_order
from app.schemas.sanitize_order import (
    SanitizeOrderCreateSchema,
    SanitizeOrderOutSchema,
    SanitizeOrderTransitionSchema,
)
from app.utils import validation_error_response

bp = Blueprint("sanitize_orders", __name__, url_prefix="/api/sanitize-orders")

create_schema = SanitizeOrderCreateSchema()
transition_schema = SanitizeOrderTransitionSchema()
out_schema = SanitizeOrderOutSchema()
out_many = SanitizeOrderOutSchema(many=True)


@bp.get("")
@jwt_required()
def list_sanitize_orders():
    db = SessionLocal()
    try:
        room_id = request.args.get("roomId", type=int)
        status = request.args.get("status")
        q = db.query(SanitizeOrder)
        if room_id is not None:
            q = q.filter(SanitizeOrder.room_id == room_id)
        if status:
            q = q.filter(SanitizeOrder.status == status)
        rows = q.order_by(SanitizeOrder.id.desc()).all()
        return jsonify(out_many.dump(rows))
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_sanitize_order():
    db = SessionLocal()
    try:
        try:
            data = create_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        room = db.query(Room).filter(Room.id == data["room_id"]).first()
        if not room:
            return jsonify({"detail": "出菇室不存在"}), 400
        try:
            assert_no_active_order(db, room.id)
        except SanitizeConflict as err:
            return jsonify({"detail": err.detail}), 409
        item = SanitizeOrder(
            room_id=data["room_id"],
            method=data["method"],
            status="open",
            operator_name=data["operator_name"],
            planned_at=data["planned_at"],
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return jsonify(out_schema.dump(item)), 201
    finally:
        db.close()


@bp.post("/<int:order_id>/transition")
@jwt_required()
def transition_sanitize_order(order_id: int):
    db = SessionLocal()
    try:
        try:
            data = transition_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        item = db.query(SanitizeOrder).filter(SanitizeOrder.id == order_id).first()
        if not item:
            return jsonify({"detail": "消杀工单不存在"}), 404
        try:
            apply_transition(db, item, data["to_status"])
        except SanitizeConflict as err:
            db.rollback()
            return jsonify({"detail": err.detail}), 409
        db.commit()
        db.refresh(item)
        return jsonify(out_schema.dump(item))
    finally:
        db.close()
