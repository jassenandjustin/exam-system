from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, UserRole, StudyRecord, ErrorNote, Favorite, SchoolClass, ClassMember
from datetime import datetime
import bcrypt

user_bp = Blueprint('users', __name__)


def _classes_of(user_id):
    """用户的班级列表 [{id, name}]。"""
    rows = (db.session.query(SchoolClass.id, SchoolClass.name)
            .join(ClassMember, ClassMember.class_id == SchoolClass.id)
            .filter(ClassMember.user_id == user_id)
            .order_by(SchoolClass.id.asc()).all())
    return [{'id': r[0], 'name': r[1]} for r in rows]


def _classes_for_users(user_ids):
    """批量查询多个用户的班级，返回 {user_id: [{id, name}]}，避免 N+1。"""
    result = {uid: [] for uid in user_ids}
    if not user_ids:
        return result
    rows = (db.session.query(ClassMember.user_id, SchoolClass.id, SchoolClass.name)
            .join(SchoolClass, SchoolClass.id == ClassMember.class_id)
            .filter(ClassMember.user_id.in_(user_ids))
            .order_by(SchoolClass.id.asc()).all())
    for uid, cid, cname in rows:
        result[uid].append({'id': cid, 'name': cname})
    return result


def _require_admin():
    """Return (user, None) if caller is admin, else (None, (resp, code))."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return None, (jsonify({'error': 'User not found'}), 404)
    if user.role != UserRole.ADMIN:
        return None, (jsonify({'error': 'Admin permission required'}), 403)
    return user, None


#
@user_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    #
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    if len(data['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    # 角色与班级：仅允许注册学生/教师，admin 只能由管理员后台设置
    role_str = data.get('role', 'student')
    if role_str not in ('student', 'teacher'):
        return jsonify({'error': 'Invalid role for registration'}), 400

    class_ids = data.get('class_ids')
    if class_ids is None:
        class_ids = []
    if not isinstance(class_ids, list):
        return jsonify({'error': 'class_ids must be a list'}), 400
    class_ids = list(set(class_ids))
    valid_classes = (SchoolClass.query.filter(SchoolClass.id.in_(class_ids)).all()
                     if class_ids else [])
    if len(valid_classes) != len(class_ids):
        return jsonify({'error': 'Invalid class id'}), 400
    if role_str == 'student' and len(class_ids) != 1:
        return jsonify({'error': 'Student registration requires exactly one class'}), 400

    #
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409

    #
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    new_user = User(
        username=data['username'],
        email=data['email'],
        password_hash=hashed_password.decode('utf-8'),
        phone=data.get('phone'),
        role=UserRole(role_str),
        status='pending',  # 注册后需管理员审核通过才可登录
    )
    db.session.add(new_user)
    db.session.flush()
    for cls in valid_classes:
        db.session.add(ClassMember(class_id=cls.id, user_id=new_user.id))

    try:
        db.session.commit()
        return jsonify({'message': '注册成功，请等待管理员审核', 'user_id': new_user.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to register user'}), 500

#
@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required'}), 400

    user = User.query.filter_by(username=data['username']).first()

    if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Invalid username or password'}), 401

    # 注册审核：未通过的用户不发 token（用 403，避免触发前端 401 全局登出）
    if user.status == 'pending':
        return jsonify({'error': '账号正在审核中，请等待管理员审核通过后登录'}), 403
    if user.status == 'rejected':
        return jsonify({'error': '账号审核未通过，请联系管理员'}), 403

    #
    user.last_login = datetime.utcnow()
    db.session.commit()

    #
    from flask_jwt_extended import create_access_token
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        'message': 'Login successful',
        'token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'status': user.status,
            'avatar': user.avatar,
            'classes': _classes_of(user.id)
        }
    })

#
@user_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone': user.phone,
        'role': user.role.value,
        'status': user.status,
        'avatar': user.avatar,
        'classes': _classes_of(user.id),
        'created_at': user.created_at,
        'last_login': user.last_login
    })


#
# 注意：密码校验失败用 400 而非 401——前端 axios 拦截器会把 401 当作
# 登录态失效自动登出，输错原密码不应把用户踢下线。
#
@user_bp.route('/change-password', methods=['PUT'])
@jwt_required()
def change_password():
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not old_password or not new_password:
        return jsonify({'error': 'Original and new passwords are required'}), 400
    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400
    if new_password != confirm_password:
        return jsonify({'error': 'New passwords do not match'}), 400

    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if not bcrypt.checkpw(old_password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Original password is incorrect'}), 400

    user.password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.session.commit()
    return jsonify({'message': 'Password changed successfully'})


#
@user_bp.route('/me', methods=['DELETE'])
@jwt_required()
def delete_account():
    data = request.get_json()
    password = data.get('password', '')

    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # 密码错误同样用 400，理由同上
    if not password or not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Password is incorrect'}), 400

    # 学习记录/错题/收藏/考试记录由 ORM 级联删除；创建的试卷保留（created_by 置空）
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Account deleted successfully'})

#
@user_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_user():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if data.get('email') and data['email'] != user.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409
        user.email = data['email']

    if data.get('phone'):
        user.phone = data['phone']

    if data.get('avatar'):
        user.avatar = data['avatar']

    try:
        db.session.commit()
        return jsonify({'message': 'User updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update user'}), 500

#
@user_bp.route('/<int:user_id>/stats', methods=['GET'])
@jwt_required()
def get_user_stats(user_id):
    current_user_id = int(get_jwt_identity())
    if current_user_id != user_id:
        return jsonify({'error': 'Permission denied'}), 403

    #
    total_practice = StudyRecord.query.filter_by(user_id=user_id).count()

    #
    correct_practice = StudyRecord.query.filter_by(user_id=user_id, is_correct=True).count()
    accuracy = (correct_practice / total_practice * 100) if total_practice > 0 else 0

    #
    error_count = ErrorNote.query.filter_by(user_id=user_id, is_corrected=False).count()

    #
    favorite_count = Favorite.query.filter_by(user_id=user_id).count()

    #
    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_practice = StudyRecord.query.filter(
        StudyRecord.user_id == user_id,
        StudyRecord.practiced_at >= week_ago
    ).count()

    return jsonify({
        'total_practice': total_practice,
        'accuracy': round(accuracy, 2),
        'error_count': error_count,
        'favorite_count': favorite_count,
        'weekly_practice': weekly_practice
    })

#
@user_bp.route('/<int:user_id>/progress', methods=['GET'])
@jwt_required()
def get_user_progress(user_id):
    current_user_id = int(get_jwt_identity())
    if current_user_id != user_id:
        return jsonify({'error': 'Permission denied'}), 403

    #
    from models import Subject, Question
    subjects = Subject.query.all()

    progress_data = []
    for subject in subjects:
        total_questions = Question.query.filter_by(subject_id=subject.id).count()
        practiced_questions = db.session.query(StudyRecord.question_id).distinct().filter(
            StudyRecord.user_id == user_id,
            StudyRecord.question_id.in_(
                db.session.query(Question.id).filter_by(subject_id=subject.id)
            )
        ).count()

        progress_data.append({
            'subject_id': subject.id,
            'subject_name': subject.name,
            'total_questions': total_questions,
            'practiced_questions': practiced_questions,
            'progress_rate': (practiced_questions / total_questions * 100) if total_questions > 0 else 0
        })

    return jsonify(progress_data)

#
@user_bp.route('/sync', methods=['POST'])
@jwt_required()
def sync_data():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    #
    if 'study_records' in data:
        for record in data['study_records']:
            existing = StudyRecord.query.filter_by(
                user_id=user_id,
                question_id=record['question_id'],
                practiced_at=record['practiced_at']
            ).first()

            if not existing:
                new_record = StudyRecord(
                    user_id=user_id,
                    question_id=record['question_id'],
                    is_correct=record['is_correct'],
                    answer=record.get('answer'),
                    used_time=record.get('used_time'),
                    practiced_at=record['practiced_at']
                )
                db.session.add(new_record)

    #
    if 'error_notes' in data:
        for note in data['error_notes']:
            existing = ErrorNote.query.filter_by(
                user_id=user_id,
                question_id=note['question_id']
            ).first()

            if not existing:
                new_note = ErrorNote(
                    user_id=user_id,
                    question_id=note['question_id'],
                    note_content=note.get('note_content'),
                    is_corrected=note.get('is_corrected', False)
                )
                db.session.add(new_note)

    #
    if 'favorites' in data:
        for favorite in data['favorites']:
            existing = Favorite.query.filter_by(
                user_id=user_id,
                question_id=favorite['question_id']
            ).first()

            if not existing:
                new_favorite = Favorite(
                    user_id=user_id,
                    question_id=favorite['question_id'],
                    created_at=favorite['created_at']
                )
                db.session.add(new_favorite)

    try:
        db.session.commit()
        return jsonify({'message': 'Data synced successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to sync data'}), 500


# ====== 管理员专用接口 ======

# 列出所有用户（分页 + 搜索）
@user_bp.route('/admin/users', methods=['GET'])
@jwt_required()
def admin_list_users():
    _admin, err = _require_admin()
    if err:
        return err

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = (request.args.get('search') or '').strip()
    role = request.args.get('role')
    status = request.args.get('status')

    query = User.query
    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(User.username.like(like), User.email.like(like))
        )
    if role:
        try:
            query = query.filter(User.role == UserRole(role))
        except ValueError:
            return jsonify({'error': f'Unknown role: {role}'}), 400
    if status:
        if status not in ('pending', 'approved', 'rejected'):
            return jsonify({'error': f'Unknown status: {status}'}), 400
        query = query.filter(User.status == status)

    pagination = query.order_by(User.id.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    classes_by_user = _classes_for_users([u.id for u in pagination.items])
    items = [{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'phone': u.phone,
        'role': u.role.value,
        'status': u.status,
        'classes': classes_by_user.get(u.id, []),
        'created_at': u.created_at,
        'last_login': u.last_login,
    } for u in pagination.items]
    return jsonify({
        'users': items,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


# 修改用户角色
@user_bp.route('/admin/users/<int:user_id>/role', methods=['PUT'])
@jwt_required()
def admin_set_user_role(user_id):
    admin, err = _require_admin()
    if err:
        return err

    if admin.id == user_id:
        return jsonify({'error': "You can't change your own role"}), 400

    target = User.query.get(user_id)
    if not target:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}
    role_str = data.get('role')
    try:
        target.role = UserRole(role_str)
    except (ValueError, TypeError):
        return jsonify({'error': f'Invalid role: {role_str}'}), 400

    # 改为学生时若残留多个班级成员关系，截断为最早加入的一个
    if target.role == UserRole.STUDENT and len(target.class_memberships) > 1:
        keep = sorted(target.class_memberships, key=lambda m: m.id)[0]
        for membership in list(target.class_memberships):
            if membership.id != keep.id:
                db.session.delete(membership)

    db.session.commit()
    return jsonify({
        'message': 'Role updated',
        'user': {'id': target.id, 'username': target.username, 'role': target.role.value}
    })


# 审核用户（通过/拒绝/重置为待审核）
@user_bp.route('/admin/users/<int:user_id>/status', methods=['PUT'])
@jwt_required()
def admin_set_user_status(user_id):
    admin, err = _require_admin()
    if err:
        return err

    if admin.id == user_id:
        return jsonify({'error': "You can't change your own status"}), 400

    target = User.query.get(user_id)
    if not target:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}
    status = data.get('status')
    if status not in ('pending', 'approved', 'rejected'):
        return jsonify({'error': 'Invalid status, must be pending/approved/rejected'}), 400

    target.status = status
    db.session.commit()
    return jsonify({
        'message': 'Status updated',
        'user': {'id': target.id, 'username': target.username, 'status': target.status}
    })


# 重置用户密码（管理员指定新密码）
@user_bp.route('/admin/users/<int:user_id>/reset-password', methods=['PUT'])
@jwt_required()
def admin_reset_password(user_id):
    admin, err = _require_admin()
    if err:
        return err

    if admin.id == user_id:
        return jsonify({'error': "You can't reset your own password here, use change-password instead"}), 400

    target = User.query.get(user_id)
    if not target:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}
    new_password = data.get('new_password') or ''
    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400

    target.password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.session.commit()
    return jsonify({'message': '密码已重置'})


# 分配班级（学生单班 / 教师多班，class_ids 全量替换；空数组 = 移出所有班级）
@user_bp.route('/admin/users/<int:user_id>/class', methods=['PUT'])
@jwt_required()
def admin_set_user_class(user_id):
    admin, err = _require_admin()
    if err:
        return err

    target = User.query.get(user_id)
    if not target:
        return jsonify({'error': 'User not found'}), 404

    if target.role == UserRole.ADMIN:
        return jsonify({'error': '管理员不属于任何班级'}), 400

    data = request.get_json() or {}
    class_ids = data.get('class_ids')
    if class_ids is None:
        class_ids = []
    if not isinstance(class_ids, list):
        return jsonify({'error': 'class_ids must be a list'}), 400
    class_ids = list(set(class_ids))
    if target.role == UserRole.STUDENT and len(class_ids) > 1:
        return jsonify({'error': '学生只能属于一个班级'}), 400

    valid_classes = (SchoolClass.query.filter(SchoolClass.id.in_(class_ids)).all()
                     if class_ids else [])
    if len(valid_classes) != len(class_ids):
        return jsonify({'error': 'Invalid class id'}), 400

    ClassMember.query.filter_by(user_id=user_id).delete()
    for cls in valid_classes:
        db.session.add(ClassMember(class_id=cls.id, user_id=user_id))
    db.session.commit()
    return jsonify({
        'message': '班级已更新',
        'user': {'id': target.id, 'username': target.username, 'classes': _classes_of(user_id)}
    })


# 删除用户
@user_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_user(user_id):
    admin, err = _require_admin()
    if err:
        return err
    if admin.id == user_id:
        return jsonify({'error': "You can't delete yourself"}), 400

    target = User.query.get(user_id)
    if not target:
        return jsonify({'error': 'User not found'}), 404

    db.session.delete(target)
    db.session.commit()
    return jsonify({'message': 'User deleted'})


# 系统总览
@user_bp.route('/admin/overview', methods=['GET'])
@jwt_required()
def admin_overview():
    _admin, err = _require_admin()
    if err:
        return err

    from models import Question, Subject, ExamRecord
    total_users = User.query.count()
    by_role = {r.value: User.query.filter_by(role=r).count() for r in UserRole}
    total_questions = Question.query.count()
    total_subjects = Subject.query.count()
    total_practice = StudyRecord.query.count()
    total_exams = ExamRecord.query.count()

    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = User.query.filter(User.created_at >= week_ago).count()
    practice_week = StudyRecord.query.filter(StudyRecord.practiced_at >= week_ago).count()

    return jsonify({
        'users': {
            'total': total_users,
            'by_role': by_role,
            'new_this_week': new_users_week,
        },
        'questions': {
            'total': total_questions,
            'subjects': total_subjects,
        },
        'activity': {
            'total_practice': total_practice,
            'total_exams': total_exams,
            'practice_this_week': practice_week,
        }
    })
