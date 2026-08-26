"""学科 / 章节 / 标签管理接口（题库元数据）。

读接口对所有登录用户开放（前端做筛选要用），写接口需要管理员或教师权限。
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Subject, Chapter, Tag, Question, QuestionTag, User, UserRole

taxonomy_bp = Blueprint('taxonomy', __name__)


def _current_user():
    return User.query.get(int(get_jwt_identity()))


def _require_editor():
    """管理员或教师才能写。"""
    user = _current_user()
    if not user:
        return None, (jsonify({'error': 'User not found'}), 404)
    if user.role not in (UserRole.ADMIN, UserRole.TEACHER):
        return None, (jsonify({'error': 'Permission denied'}), 403)
    return user, None


# ============ Subject 学科 ============

@taxonomy_bp.route('/subjects', methods=['GET'])
@jwt_required(optional=True)
def list_subjects():
    items = Subject.query.order_by(Subject.id.asc()).all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'description': s.description,
        'icon': s.icon,
        'chapter_count': len(s.chapters),
        'question_count': Question.query.filter_by(subject_id=s.id).count(),
        'created_at': s.created_at,
    } for s in items])


@taxonomy_bp.route('/subjects', methods=['POST'])
@jwt_required()
def create_subject():
    _u, err = _require_editor()
    if err:
        return err
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    if Subject.query.filter_by(name=name).first():
        return jsonify({'error': 'Subject already exists'}), 409
    s = Subject(name=name, description=data.get('description'), icon=data.get('icon'))
    db.session.add(s)
    db.session.commit()
    return jsonify({'id': s.id, 'name': s.name}), 201


@taxonomy_bp.route('/subjects/<int:subject_id>', methods=['PUT'])
@jwt_required()
def update_subject(subject_id):
    _u, err = _require_editor()
    if err:
        return err
    s = Subject.query.get(subject_id)
    if not s:
        return jsonify({'error': 'Subject not found'}), 404
    data = request.get_json() or {}
    if 'name' in data:
        new_name = (data['name'] or '').strip()
        if not new_name:
            return jsonify({'error': 'name cannot be empty'}), 400
        if new_name != s.name and Subject.query.filter_by(name=new_name).first():
            return jsonify({'error': 'Subject name conflicts'}), 409
        s.name = new_name
    if 'description' in data:
        s.description = data['description']
    if 'icon' in data:
        s.icon = data['icon']
    db.session.commit()
    return jsonify({'message': 'updated'})


@taxonomy_bp.route('/subjects/<int:subject_id>', methods=['DELETE'])
@jwt_required()
def delete_subject(subject_id):
    _u, err = _require_editor()
    if err:
        return err
    s = Subject.query.get(subject_id)
    if not s:
        return jsonify({'error': 'Subject not found'}), 404
    if Question.query.filter_by(subject_id=subject_id).count() > 0:
        return jsonify({'error': 'Subject has questions, please remove them first'}), 400
    db.session.delete(s)
    db.session.commit()
    return jsonify({'message': 'deleted'})


# ============ Chapter 章节 ============

@taxonomy_bp.route('/chapters', methods=['GET'])
@jwt_required(optional=True)
def list_chapters():
    subject_id = request.args.get('subject_id', type=int)
    q = Chapter.query
    if subject_id:
        q = q.filter_by(subject_id=subject_id)
    items = q.order_by(Chapter.subject_id.asc(), Chapter.order_num.asc(), Chapter.id.asc()).all()
    return jsonify([{
        'id': c.id,
        'subject_id': c.subject_id,
        'name': c.name,
        'description': c.description,
        'order_num': c.order_num,
        'question_count': Question.query.filter_by(chapter_id=c.id).count(),
    } for c in items])


@taxonomy_bp.route('/chapters', methods=['POST'])
@jwt_required()
def create_chapter():
    _u, err = _require_editor()
    if err:
        return err
    data = request.get_json() or {}
    subject_id = data.get('subject_id')
    name = (data.get('name') or '').strip()
    if not subject_id or not name:
        return jsonify({'error': 'subject_id and name are required'}), 400
    if not Subject.query.get(subject_id):
        return jsonify({'error': 'Subject not found'}), 404
    c = Chapter(
        subject_id=subject_id,
        name=name,
        description=data.get('description'),
        order_num=data.get('order_num', 0),
    )
    db.session.add(c)
    db.session.commit()
    return jsonify({'id': c.id}), 201


@taxonomy_bp.route('/chapters/<int:chapter_id>', methods=['PUT'])
@jwt_required()
def update_chapter(chapter_id):
    _u, err = _require_editor()
    if err:
        return err
    c = Chapter.query.get(chapter_id)
    if not c:
        return jsonify({'error': 'Chapter not found'}), 404
    data = request.get_json() or {}
    if 'name' in data:
        c.name = data['name']
    if 'description' in data:
        c.description = data['description']
    if 'order_num' in data:
        c.order_num = data['order_num']
    db.session.commit()
    return jsonify({'message': 'updated'})


@taxonomy_bp.route('/chapters/<int:chapter_id>', methods=['DELETE'])
@jwt_required()
def delete_chapter(chapter_id):
    _u, err = _require_editor()
    if err:
        return err
    c = Chapter.query.get(chapter_id)
    if not c:
        return jsonify({'error': 'Chapter not found'}), 404
    if Question.query.filter_by(chapter_id=chapter_id).count() > 0:
        return jsonify({'error': 'Chapter has questions, please remove them first'}), 400
    db.session.delete(c)
    db.session.commit()
    return jsonify({'message': 'deleted'})


# ============ Tag 标签 ============

@taxonomy_bp.route('/tags', methods=['GET'])
@jwt_required(optional=True)
def list_tags():
    category = request.args.get('category')
    q = Tag.query
    if category:
        q = q.filter_by(category=category)
    items = q.order_by(Tag.category.asc(), Tag.name.asc()).all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'category': t.category,
        'usage_count': QuestionTag.query.filter_by(tag_id=t.id).count(),
    } for t in items])


@taxonomy_bp.route('/tags', methods=['POST'])
@jwt_required()
def create_tag():
    _u, err = _require_editor()
    if err:
        return err
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    category = (data.get('category') or '').strip() or 'knowledge_point'
    if not name:
        return jsonify({'error': 'name is required'}), 400
    if Tag.query.filter_by(name=name).first():
        return jsonify({'error': 'Tag already exists'}), 409
    t = Tag(name=name, category=category)
    db.session.add(t)
    db.session.commit()
    return jsonify({'id': t.id}), 201


@taxonomy_bp.route('/tags/<int:tag_id>', methods=['PUT'])
@jwt_required()
def update_tag(tag_id):
    _u, err = _require_editor()
    if err:
        return err
    t = Tag.query.get(tag_id)
    if not t:
        return jsonify({'error': 'Tag not found'}), 404
    data = request.get_json() or {}
    if 'name' in data:
        new_name = (data['name'] or '').strip()
        if not new_name:
            return jsonify({'error': 'name cannot be empty'}), 400
        if new_name != t.name and Tag.query.filter_by(name=new_name).first():
            return jsonify({'error': 'Tag name conflicts'}), 409
        t.name = new_name
    if 'category' in data:
        t.category = data['category']
    db.session.commit()
    return jsonify({'message': 'updated'})


@taxonomy_bp.route('/tags/<int:tag_id>', methods=['DELETE'])
@jwt_required()
def delete_tag(tag_id):
    _u, err = _require_editor()
    if err:
        return err
    t = Tag.query.get(tag_id)
    if not t:
        return jsonify({'error': 'Tag not found'}), 404
    # 删除标签会级联删除 question_tag 关联
    db.session.delete(t)
    db.session.commit()
    return jsonify({'message': 'deleted'})
