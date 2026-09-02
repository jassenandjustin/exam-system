"""班级学科范围的访问控制工具。

被 routes/practice.py、routes/exam.py、routes/taxonomy.py 共用；
只依赖 models，不依赖任何 routes 模块，无循环导入。

约定：业务拒绝一律返回 403（不是 401）——前端 axios 拦截器会把
401 当作登录态失效自动登出。
"""
from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from models import db, User, UserRole, ClassMember, class_subjects


def current_user():
    """JWT identity → User 行；用户不存在时返回 None。"""
    return User.query.get(int(get_jwt_identity()))


def allowed_subject_ids(user):
    """用户可访问的学科集合。

    teacher/admin → None 表示不限（豁免，便于预览试做与排查）；
    学生 → 其所有班级学科范围的并集（未入班 = 空 set）。
    """
    if user is None or user.role in (UserRole.TEACHER, UserRole.ADMIN):
        return None
    rows = (db.session.query(class_subjects.c.subject_id)
            .join(ClassMember, ClassMember.class_id == class_subjects.c.class_id)
            .filter(ClassMember.user_id == user.id)
            .all())
    return {r[0] for r in rows}


def gate_subject(user, subject_id):
    """单学科门禁。通过返回 None；否则返回 (resp, 403) 供路由直接 return。"""
    allowed = allowed_subject_ids(user)
    if allowed is None:
        return None
    if not allowed:
        return (jsonify({'error': '请先加入班级后再使用该功能'}), 403)
    if subject_id not in allowed:
        return (jsonify({'error': '该学科不在你的班级学科范围内'}), 403)
    return None


def gate_question(user, question):
    """写路径（提交答案/收藏）按题目所属学科做门禁。"""
    return gate_subject(user, question.subject_id)
