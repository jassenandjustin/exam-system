from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import (
    db, Question, QuestionType, DifficultyLevel,
    Subject, Chapter, Tag, QuestionTag,
    StudyRecord, ErrorNote, Favorite, ExamAnswer,
    User, UserRole,
)
from datetime import datetime
import json

question_bp = Blueprint('questions', __name__)

#
@question_bp.route('', methods=['GET'])
@jwt_required(optional=True)
def get_questions():
    #
    subject_id = request.args.get('subject_id', type=int)
    chapter_id = request.args.get('chapter_id', type=int)
    question_type = request.args.get('question_type')
    difficulty = request.args.get('difficulty')
    tag_ids = request.args.getlist('tag_ids', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '')

    #
    query = Question.query

    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    if chapter_id:
        query = query.filter_by(chapter_id=chapter_id)
    if question_type:
        query = query.filter_by(question_type=QuestionType(question_type))
    if difficulty:
        query = query.filter_by(difficulty=DifficultyLevel(difficulty))
    if search:
        query = query.filter(Question.title.contains(search) | Question.content.contains(search))

    #
    if tag_ids:
        query = query.join(QuestionTag).filter(QuestionTag.tag_id.in_(tag_ids))

    #
    pagination = query.order_by(Question.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    questions = []
    for q in pagination.items:
        #
        tags = Tag.query.join(QuestionTag).filter(QuestionTag.question_id == q.id).all()

        questions.append({
            'id': q.id,
            'subject_id': q.subject_id,
            'chapter_id': q.chapter_id,
            'question_type': q.question_type.value,
            'title': q.title,
            'content': q.content,
            'options': q.options,
            'difficulty': q.difficulty.value,
            'score': q.score,
            'explanation': q.explanation,
            'tags': [{'id': t.id, 'name': t.name, 'category': t.category} for t in tags],
            'created_at': q.created_at,
            'updated_at': q.updated_at
        })

    return jsonify({
        'questions': questions,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

#
@question_bp.route('/<int:question_id>', methods=['GET'])
@jwt_required(optional=True)
def get_question(question_id):
    question = Question.query.get(question_id)
    if not question:
        return jsonify({'error': 'Question not found'}), 404

    #
    tags = Tag.query.join(QuestionTag).filter(QuestionTag.question_id == question.id).all()

    return jsonify({
        'id': question.id,
        'subject_id': question.subject_id,
        'chapter_id': question.chapter_id,
        'question_type': question.question_type.value,
        'title': question.title,
        'content': question.content,
        'options': question.options,
        'correct_answer': question.correct_answer,
        'difficulty': question.difficulty.value,
        'score': question.score,
        'explanation': question.explanation,
        'tags': [{'id': t.id, 'name': t.name, 'category': t.category} for t in tags],
        'created_at': question.created_at,
        'updated_at': question.updated_at
    })

#
@question_bp.route('', methods=['POST'])
@jwt_required()
def create_question():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    #
    if user.role not in [UserRole.TEACHER, UserRole.ADMIN]:
        return jsonify({'error': 'Permission denied'}), 403

    data = request.get_json()

    #
    required_fields = ['subject_id', 'question_type', 'title', 'correct_answer']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    #
    try:
        question = Question(
            subject_id=data['subject_id'],
            chapter_id=data.get('chapter_id'),
            question_type=QuestionType(data['question_type']),
            title=data['title'],
            content=data.get('content'),
            options=data.get('options'),
            correct_answer=data['correct_answer'],
            explanation=data.get('explanation'),
            difficulty=DifficultyLevel(data.get('difficulty', 'medium')),
            score=data.get('score', 2.0),
            created_by=user_id
        )

        db.session.add(question)
        db.session.flush()

        #
        if data.get('tag_ids'):
            for tag_id in data['tag_ids']:
                question_tag = QuestionTag(question_id=question.id, tag_id=tag_id)
                db.session.add(question_tag)

        db.session.commit()

        return jsonify({
            'message': 'Question created successfully',
            'question_id': question.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create question'}), 500

#
@question_bp.route('/<int:question_id>', methods=['PUT'])
@jwt_required()
def update_question(question_id):
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    question = Question.query.get(question_id)

    if not question:
        return jsonify({'error': 'Question not found'}), 404

    #
    if user.role not in [UserRole.TEACHER, UserRole.ADMIN] and question.created_by != user_id:
        return jsonify({'error': 'Permission denied'}), 403

    data = request.get_json()

    try:
        #
        if data.get('subject_id'):
            question.subject_id = data['subject_id']
        if data.get('chapter_id') is not None:
            question.chapter_id = data['chapter_id']
        if data.get('question_type'):
            question.question_type = QuestionType(data['question_type'])
        if data.get('title'):
            question.title = data['title']
        if data.get('content') is not None:
            question.content = data['content']
        if data.get('options') is not None:
            question.options = data['options']
        if data.get('correct_answer') is not None:
            question.correct_answer = data['correct_answer']
        if data.get('explanation') is not None:
            question.explanation = data['explanation']
        if data.get('difficulty'):
            question.difficulty = DifficultyLevel(data['difficulty'])
        if data.get('score'):
            question.score = data['score']

        question.updated_at = datetime.utcnow()

        #
        if 'tag_ids' in data:
            #
            QuestionTag.query.filter_by(question_id=question_id).delete()
            #
            for tag_id in data['tag_ids']:
                question_tag = QuestionTag(question_id=question_id, tag_id=tag_id)
                db.session.add(question_tag)

        db.session.commit()

        return jsonify({'message': 'Question updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update question'}), 500

#
@question_bp.route('/<int:question_id>', methods=['DELETE'])
@jwt_required()
def delete_question(question_id):
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    question = Question.query.get(question_id)

    if not question:
        return jsonify({'error': 'Question not found'}), 404

    #
    if user.role not in [UserRole.TEACHER, UserRole.ADMIN] and question.created_by != user_id:
        return jsonify({'error': 'Permission denied'}), 403

    try:
        # Question 的 study_records / error_notes / favorites / exam_answers 关系
        # 都没有配置级联删除，外键约束会把 db.session.delete(question) 撞掉。
        # 这里手动把所有引用清掉再删题。
        StudyRecord.query.filter_by(question_id=question_id).delete(synchronize_session=False)
        ErrorNote.query.filter_by(question_id=question_id).delete(synchronize_session=False)
        Favorite.query.filter_by(question_id=question_id).delete(synchronize_session=False)
        ExamAnswer.query.filter_by(question_id=question_id).delete(synchronize_session=False)
        # question_tags 已经配了 cascade='all, delete-orphan'，会随 question 一起走

        db.session.delete(question)
        db.session.commit()
        return jsonify({'message': 'Question deleted successfully'})
    except Exception as e:
        db.session.rollback()
        # 把真实错误吐出来，方便排查；管理员能看到具体冲突
        return jsonify({'error': f'Failed to delete question: {str(e)}'}), 500

#
@question_bp.route('/batch-import', methods=['POST'])
@jwt_required()
def batch_import_questions():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    #
    if user.role not in [UserRole.TEACHER, UserRole.ADMIN]:
        return jsonify({'error': 'Permission denied'}), 403

    data = request.get_json()
    questions_data = data.get('questions', [])

    if not questions_data:
        return jsonify({'error': 'No questions provided'}), 400

    imported_count = 0
    failed_count = 0
    errors = []

    for idx, q_data in enumerate(questions_data):
        try:
            # 必需字段：注意判断题 correct_answer 可能为 False，不能用 truthy 判断
            for field in ['subject_id', 'question_type', 'title']:
                if not q_data.get(field):
                    raise ValueError(f'Field {field} is required')
            if q_data.get('correct_answer') is None:
                raise ValueError('Field correct_answer is required')

            # 用 savepoint 让单行失败不影响整个批次
            with db.session.begin_nested():
                question = Question(
                    subject_id=q_data['subject_id'],
                    chapter_id=q_data.get('chapter_id'),
                    question_type=QuestionType(q_data['question_type']),
                    title=q_data['title'],
                    content=q_data.get('content'),
                    options=q_data.get('options'),
                    correct_answer=q_data['correct_answer'],
                    explanation=q_data.get('explanation'),
                    difficulty=DifficultyLevel(q_data.get('difficulty', 'medium')),
                    score=q_data.get('score', 2.0),
                    created_by=user_id
                )

                db.session.add(question)
                db.session.flush()

                #
                if q_data.get('tag_ids'):
                    for tag_id in q_data['tag_ids']:
                        question_tag = QuestionTag(question_id=question.id, tag_id=tag_id)
                        db.session.add(question_tag)

            imported_count += 1

        except Exception as e:
            failed_count += 1
            errors.append({'index': idx, 'error': str(e)})

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to commit changes'}), 500

    return jsonify({
        'message': f'Successfully imported {imported_count} questions, {failed_count} failed',
        'imported_count': imported_count,
        'failed_count': failed_count,
        'errors': errors
    })

#
@question_bp.route('/types', methods=['GET'])
def get_question_types():
    return jsonify({
        'types': [
            {'value': 'single_choice', 'name': 'msg'},
            {'value': 'multiple_choice', 'name': 'msg'},
            {'value': 'fill_in_blank', 'name': 'msg'},
            {'value': 'true_false', 'name': 'msg'},
            {'value': 'subjective', 'name': 'msg'}
        ]
    })

#
@question_bp.route('/difficulties', methods=['GET'])
def get_difficulties():
    return jsonify({
        'difficulties': [
            {'value': 'easy', 'name': 'msg'},
            {'value': 'medium', 'name': 'msg'},
            {'value': 'hard', 'name': 'msg'}
        ]
    })