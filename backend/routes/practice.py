from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Question, QuestionType, StudyRecord, ErrorNote, Favorite, Subject, Chapter
from datetime import datetime, timedelta
import random

from access import current_user, allowed_subject_ids, gate_subject, gate_question

practice_bp = Blueprint('practice', __name__)


def _serialize_question(q, favorite_ids=None):
    """刷题模式下返回的题目字段：包含答案与解析，便于前端判题、展示讲解。

    favorite_ids 可选传入用户的收藏 question_id 集合，减少 N+1 查询。
    """
    return {
        'id': q.id,
        'subject_id': q.subject_id,
        'chapter_id': q.chapter_id,
        'title': q.title,
        'content': q.content,
        'question_type': q.question_type.value,
        'options': q.options,
        'correct_answer': q.correct_answer,
        'explanation': q.explanation,
        'difficulty': q.difficulty.value,
        'score': q.score,
        'is_favorite': (q.id in favorite_ids) if favorite_ids is not None else False,
    }


def _favorite_id_set(user_id, question_ids):
    """批量查询当前用户在指定题目里的收藏集合。"""
    if not question_ids:
        return set()
    rows = db.session.query(Favorite.question_id).filter(
        Favorite.user_id == user_id,
        Favorite.question_id.in_(question_ids)
    ).all()
    return {r[0] for r in rows}

#
@practice_bp.route('/sequential', methods=['GET'])
@jwt_required()
def sequential_practice():
    user = current_user()
    subject_id = request.args.get('subject_id', type=int)
    chapter_id = request.args.get('chapter_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    if not subject_id:
        return jsonify({'error': 'subject_id is required'}), 400

    gate_err = gate_subject(user, subject_id)
    if gate_err:
        return gate_err

    user_id = user.id
    #
    practiced_question_ids = db.session.query(StudyRecord.question_id).filter_by(
        user_id=user_id
    ).distinct().all()
    practiced_question_ids = [q[0] for q in practiced_question_ids]

    #
    query = Question.query.filter_by(subject_id=subject_id)
    if chapter_id:
        query = query.filter_by(chapter_id=chapter_id)
    if practiced_question_ids:
        query = query.filter(~Question.id.in_(practiced_question_ids))

    pagination = query.order_by(Question.id).paginate(
        page=page, per_page=per_page, error_out=False
    )

    fav_set = _favorite_id_set(user_id, [q.id for q in pagination.items])
    questions = [_serialize_question(q, fav_set) for q in pagination.items]

    return jsonify({
        'questions': questions,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

#
@practice_bp.route('/random', methods=['GET'])
@jwt_required()
def random_practice():
    user = current_user()
    subject_id = request.args.get('subject_id', type=int)
    count = request.args.get('count', 10, type=int)

    if not subject_id:
        return jsonify({'error': 'subject_id is required'}), 400

    gate_err = gate_subject(user, subject_id)
    if gate_err:
        return gate_err

    user_id = user.id

    if count > 50:
        count = 50

    #
    practiced_question_ids = db.session.query(StudyRecord.question_id).filter_by(
        user_id=user_id
    ).distinct().all()
    practiced_question_ids = [q[0] for q in practiced_question_ids]

    #
    query = Question.query.filter_by(subject_id=subject_id)
    if practiced_question_ids:
        query = query.filter(~Question.id.in_(practiced_question_ids))

    total_questions = query.count()
    if total_questions == 0:
        #
        query = Question.query.filter_by(subject_id=subject_id)

    questions = query.order_by(db.func.random()).limit(count).all()

    fav_set = _favorite_id_set(user_id, [q.id for q in questions])
    result = [_serialize_question(q, fav_set) for q in questions]

    return jsonify({'questions': result})

#
@practice_bp.route('/error-review', methods=['GET'])
@jwt_required()
def error_review():
    user = current_user()
    subject_id = request.args.get('subject_id', type=int)
    limit = request.args.get('limit', 20, type=int)

    user_id = user.id
    allowed = allowed_subject_ids(user)
    if allowed is not None and not allowed:
        return jsonify({'error': '请先加入班级后再使用该功能'}), 403

    #
    error_query = db.session.query(StudyRecord.question_id).filter_by(
        user_id=user_id, is_correct=False
    ).distinct()

    if subject_id:
        if allowed is not None and subject_id not in allowed:
            return jsonify({'error': '该学科不在你的班级学科范围内'}), 403
        error_query = error_query.join(Question).filter(Question.subject_id == subject_id)
    elif allowed is not None:
        # 不传 subject 时也不能看到班级学科范围外的错题
        error_query = error_query.join(Question).filter(Question.subject_id.in_(allowed))

    error_question_ids = [q[0] for q in error_query.limit(limit).all()]

    if not error_question_ids:
        return jsonify({'questions': [], 'message': 'No error questions found'})

    questions = Question.query.filter(Question.id.in_(error_question_ids)).all()

    fav_set = _favorite_id_set(user_id, [q.id for q in questions])
    result = [_serialize_question(q, fav_set) for q in questions]

    return jsonify({'questions': result})

#
@practice_bp.route('/favorites', methods=['GET'])
@jwt_required()
def favorite_practice():
    user = current_user()
    subject_id = request.args.get('subject_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    user_id = user.id
    allowed = allowed_subject_ids(user)
    if allowed is not None and not allowed:
        return jsonify({'error': '请先加入班级后再使用该功能'}), 403

    #
    favorite_query = db.session.query(Favorite.question_id).filter_by(user_id=user_id)

    if subject_id:
        if allowed is not None and subject_id not in allowed:
            return jsonify({'error': '该学科不在你的班级学科范围内'}), 403
        favorite_query = favorite_query.join(Question).filter(Question.subject_id == subject_id)
    elif allowed is not None:
        # 不传 subject 时也不能看到班级学科范围外的收藏
        favorite_query = favorite_query.join(Question).filter(Question.subject_id.in_(allowed))

    pagination = favorite_query.paginate(page=page, per_page=per_page, error_out=False)

    question_ids = [q[0] for q in pagination.items]
    questions = Question.query.filter(Question.id.in_(question_ids)).all()

    # 收藏夹页面显然全部都已收藏
    fav_set = set(question_ids)
    result = [_serialize_question(q, fav_set) for q in questions]

    return jsonify({
        'questions': result,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

#
@practice_bp.route('/submit-answer', methods=['POST'])
@jwt_required()
def submit_answer():
    user = current_user()
    data = request.get_json()

    required_fields = ['question_id', 'answer', 'is_correct']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400

    question = Question.query.get(data['question_id'])
    if not question:
        return jsonify({'error': 'Question not found'}), 404

    gate_err = gate_question(user, question)
    if gate_err:
        return gate_err

    user_id = user.id

    try:
        #
        study_record = StudyRecord(
            user_id=user_id,
            question_id=data['question_id'],
            is_correct=data['is_correct'],
            answer=data['answer'],
            used_time=data.get('used_time'),
            practiced_at=datetime.utcnow()
        )

        db.session.add(study_record)

        #
        if not data['is_correct']:
            existing_error = ErrorNote.query.filter_by(
                user_id=user_id,
                question_id=data['question_id']
            ).first()

            if not existing_error:
                error_note = ErrorNote(
                    user_id=user_id,
                    question_id=data['question_id'],
                    note_content=data.get('note_content', '')
                )
                db.session.add(error_note)

        db.session.commit()

        return jsonify({
            'message': 'Answer submitted successfully',
            'record_id': study_record.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to submit answer'}), 500

#
@practice_bp.route('/favorites', methods=['POST'])
@jwt_required()
def add_favorite():
    """收藏一道题。幂等：已收藏则直接返回 ok。"""
    user = current_user()
    data = request.get_json() or {}
    question_id = data.get('question_id')
    if not question_id:
        return jsonify({'error': 'question_id is required'}), 400

    question = Question.query.get(question_id)
    if not question:
        return jsonify({'error': 'Question not found'}), 404

    gate_err = gate_question(user, question)
    if gate_err:
        return gate_err

    user_id = user.id

    existing = Favorite.query.filter_by(user_id=user_id, question_id=question_id).first()
    if existing:
        return jsonify({'message': 'already favorited', 'is_favorite': True})

    try:
        fav = Favorite(user_id=user_id, question_id=question_id)
        db.session.add(fav)
        db.session.commit()
        return jsonify({'message': 'favorited', 'is_favorite': True}), 201
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to add favorite'}), 500


@practice_bp.route('/favorites/<int:question_id>', methods=['DELETE'])
@jwt_required()
def remove_favorite(question_id):
    """取消收藏。幂等。"""
    user_id = int(get_jwt_identity())
    fav = Favorite.query.filter_by(user_id=user_id, question_id=question_id).first()
    if not fav:
        return jsonify({'message': 'not favorited', 'is_favorite': False})
    try:
        db.session.delete(fav)
        db.session.commit()
        return jsonify({'message': 'removed', 'is_favorite': False})
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to remove favorite'}), 500

#
@practice_bp.route('/chapter-practice', methods=['GET'])
@jwt_required()
def chapter_practice():
    user = current_user()
    chapter_id = request.args.get('chapter_id', type=int)
    limit = request.args.get('limit', 20, type=int)

    if not chapter_id:
        return jsonify({'error': 'chapter_id is required'}), 400

    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        return jsonify({'error': 'Chapter not found'}), 404

    gate_err = gate_subject(user, chapter.subject_id)
    if gate_err:
        return gate_err

    user_id = user.id

    #
    questions = Question.query.filter_by(chapter_id=chapter_id).limit(limit).all()

    fav_set = _favorite_id_set(user_id, [q.id for q in questions])
    result = [_serialize_question(q, fav_set) for q in questions]

    return jsonify({'questions': result})

#
@practice_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_practice_stats():
    user_id = int(get_jwt_identity())
    days = request.args.get('days', 7, type=int)

    start_date = datetime.utcnow() - timedelta(days=days)

    #
    daily_stats = db.session.query(
        db.func.date(StudyRecord.practiced_at).label('date'),
        db.func.count(StudyRecord.id).label('total'),
        db.func.sum(db.case((StudyRecord.is_correct, 1), else_=0)).label('correct')
    ).filter(
        StudyRecord.user_id == user_id,
        StudyRecord.practiced_at >= start_date
    ).group_by(db.func.date(StudyRecord.practiced_at)).order_by('date').all()

    stats = []
    for row in daily_stats:
        stats.append({
            'date': row.date.strftime('%Y-%m-%d'),
            'total': row.total or 0,
            'correct': row.correct or 0,
            'accuracy': (row.correct / row.total * 100) if row.total > 0 else 0
        })

    return jsonify({'stats': stats})

#
@practice_bp.route('/smart-recommend', methods=['GET'])
@jwt_required()
def smart_recommend():
    user = current_user()
    subject_id = request.args.get('subject_id', type=int)
    limit = request.args.get('limit', 10, type=int)

    if not subject_id:
        return jsonify({'error': 'subject_id is required'}), 400

    gate_err = gate_subject(user, subject_id)
    if gate_err:
        return gate_err

    user_id = user.id

    #
    from models import Tag, QuestionTag
    error_question_ids = db.session.query(StudyRecord.question_id).filter_by(
        user_id=user_id, is_correct=False
    ).distinct().all()
    error_question_ids = [q[0] for q in error_question_ids]

    if not error_question_ids:
        #
        questions = Question.query.filter_by(subject_id=subject_id).order_by(
            db.func.random()
        ).limit(limit).all()

        result = []
        for q in questions:
            result.append({
                'id': q.id,
                'title': q.title,
                'content': q.content,
                'question_type': q.question_type.value,
                'options': q.options,
                'difficulty': q.difficulty.value,
                'score': q.score,
                'recommend_reason': 'msg'
            })

        return jsonify({'questions': result})

    #
    weak_tags = db.session.query(
        Tag.id,
        Tag.name,
        db.func.count(Tag.id).label('error_count')
    ).join(QuestionTag).filter(
        QuestionTag.question_id.in_(error_question_ids)
    ).group_by(Tag.id).order_by(db.desc('error_count')).limit(5).all()

    if not weak_tags:
        #
        questions = Question.query.filter_by(subject_id=subject_id).order_by(
            db.func.random()
        ).limit(limit).all()

        result = []
        for q in questions:
            result.append({
                'id': q.id,
                'title': q.title,
                'content': q.content,
                'question_type': q.question_type.value,
                'options': q.options,
                'difficulty': q.difficulty.value,
                'score': q.score,
                'recommend_reason': 'msg'
            })

        return jsonify({'questions': result})

    #
    recommended_questions = []
    for tag in weak_tags:
        tag_questions = Question.query.join(QuestionTag).filter(
            QuestionTag.tag_id == tag.id,
            Question.subject_id == subject_id
        ).order_by(db.func.random()).limit(limit // len(weak_tags)).all()

        for q in tag_questions:
            #
            correct_record = StudyRecord.query.filter_by(
                user_id=user_id,
                question_id=q.id,
                is_correct=True
            ).first()

            if not correct_record:
                recommended_questions.append({
                    'id': q.id,
                    'title': q.title,
                    'content': q.content,
                    'question_type': q.question_type.value,
                    'options': q.options,
                    'difficulty': q.difficulty.value,
                    'score': q.score,
                    'recommend_reason': f'msg'
                })

                if len(recommended_questions) >= limit:
                    break

        if len(recommended_questions) >= limit:
            break

    return jsonify({'questions': recommended_questions[:limit]})