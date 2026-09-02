from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from models import (
    db, User, UserRole, Subject, SchoolClass, ClassMember, class_subjects
)

class_bp = Blueprint('classes', __name__)


def _require_admin():
    """与 routes/users.py 相同模式；本地实现避免 routes 模块间互相 import。"""
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return None, (jsonify({'error': 'User not found'}), 404)
    if user.role != UserRole.ADMIN:
        return None, (jsonify({'error': 'Admin permission required'}), 403)
    return user, None


def _validate_subject_ids(subject_ids):
    """校验学科 id 列表：非空、去重后全部存在。返回错误信息或 None。"""
    if not isinstance(subject_ids, list) or not subject_ids:
        return 'subject_ids 必须为非空数组'
    unique_ids = set(subject_ids)
    found = Subject.query.filter(Subject.id.in_(unique_ids)).count()
    if found != len(unique_ids):
        return '存在无效的学科'
    return None


@class_bp.route('', methods=['GET'])
@jwt_required(optional=True)
def list_classes():
    """班级列表。

    公开接口（注册页需要班级名）；普通用户只看到 {id, name, description}，
    admin 附加学科配置、师生数等管理字段。
    """
    is_admin = False
    identity = get_jwt_identity()
    if identity is not None:
        user = User.query.get(int(identity))
        is_admin = user is not None and user.role == UserRole.ADMIN

    classes = SchoolClass.query.order_by(SchoolClass.id.asc()).all()
    if not is_admin:
        return jsonify([
            {'id': c.id, 'name': c.name, 'description': c.description}
            for c in classes
        ])

    # 批量统计各班学生/教师数与学科配置，避免逐班查询
    role_rows = (db.session.query(ClassMember.class_id, User.role, func.count(ClassMember.id))
                 .join(User, User.id == ClassMember.user_id)
                 .group_by(ClassMember.class_id, User.role).all())
    student_counts, teacher_counts = {}, {}
    for class_id, role, cnt in role_rows:
        if role == UserRole.STUDENT:
            student_counts[class_id] = cnt
        elif role == UserRole.TEACHER:
            teacher_counts[class_id] = cnt

    subject_rows = (db.session.query(class_subjects.c.class_id, Subject.id, Subject.name)
                    .join(Subject, Subject.id == class_subjects.c.subject_id)
                    .order_by(Subject.id.asc()).all())
    subjects_by_class = {}
    for class_id, subject_id, subject_name in subject_rows:
        subjects_by_class.setdefault(class_id, []).append(
            {'id': subject_id, 'name': subject_name})

    return jsonify([{
        'id': c.id,
        'name': c.name,
        'description': c.description,
        'subject_ids': [s['id'] for s in subjects_by_class.get(c.id, [])],
        'subject_names': [s['name'] for s in subjects_by_class.get(c.id, [])],
        'student_count': student_counts.get(c.id, 0),
        'teacher_count': teacher_counts.get(c.id, 0),
        'created_at': c.created_at,
    } for c in classes])


@class_bp.route('', methods=['POST'])
@jwt_required()
def create_class():
    admin, err = _require_admin()
    if err:
        return err

    data = request.get_json()
    name = (data.get('name') or '').strip()
    subject_ids = data.get('subject_ids') or []

    if not name:
        return jsonify({'error': '班级名称不能为空'}), 400
    if SchoolClass.query.filter_by(name=name).first():
        return jsonify({'error': '班级名称已存在'}), 409
    subject_err = _validate_subject_ids(subject_ids)
    if subject_err:
        return jsonify({'error': subject_err}), 400

    school_class = SchoolClass(name=name, description=data.get('description'))
    db.session.add(school_class)
    db.session.flush()
    for subject_id in set(subject_ids):
        db.session.execute(class_subjects.insert().values(
            class_id=school_class.id, subject_id=subject_id))
    db.session.commit()
    return jsonify({'id': school_class.id, 'name': school_class.name}), 201


@class_bp.route('/<int:class_id>', methods=['PUT'])
@jwt_required()
def update_class(class_id):
    admin, err = _require_admin()
    if err:
        return err

    school_class = SchoolClass.query.get(class_id)
    if not school_class:
        return jsonify({'error': '班级不存在'}), 404

    data = request.get_json()
    name = (data.get('name') or '').strip()
    if name and name != school_class.name:
        if SchoolClass.query.filter_by(name=name).first():
            return jsonify({'error': '班级名称已存在'}), 409
        school_class.name = name
    if 'description' in data:
        school_class.description = data.get('description')

    if 'subject_ids' in data:
        subject_ids = data.get('subject_ids') or []
        subject_err = _validate_subject_ids(subject_ids)
        if subject_err:
            return jsonify({'error': subject_err}), 400
        # 学科范围全量替换（缩小范围会即时收缩该班学生的可见学科，属预期行为）
        db.session.execute(
            class_subjects.delete().where(class_subjects.c.class_id == class_id))
        for subject_id in set(subject_ids):
            db.session.execute(class_subjects.insert().values(
                class_id=class_id, subject_id=subject_id))

    db.session.commit()
    return jsonify({'message': '班级已更新'})


@class_bp.route('/<int:class_id>', methods=['DELETE'])
@jwt_required()
def delete_class(class_id):
    admin, err = _require_admin()
    if err:
        return err

    school_class = SchoolClass.query.get(class_id)
    if not school_class:
        return jsonify({'error': '班级不存在'}), 404

    # 显式先删学科关联行（双保险）；成员关系由 ORM cascade 清理
    db.session.execute(
        class_subjects.delete().where(class_subjects.c.class_id == class_id))
    db.session.delete(school_class)
    db.session.commit()
    return jsonify({'message': '班级已删除'})
