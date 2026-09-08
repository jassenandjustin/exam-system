from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import (
    db, Question, QuestionType, DifficultyLevel,
    Subject, Chapter, Section, Tag, QuestionTag,
    StudyRecord, ErrorNote, Favorite, ExamAnswer,
    User, UserRole,
)
from datetime import datetime
import json

question_bp = Blueprint('questions', __name__)

QUESTION_SOURCES = ('real', 'mock')  # real=真题 / mock=模拟题


def _validated_question_source(value):
    """校验题目来源，返回 (value, err)；缺省 mock。"""
    source = value or 'mock'
    if source not in QUESTION_SOURCES:
        return None, '题目来源无效（real=真题 / mock=模拟题）'
    return source, None


def _resolve_chapter_section(data):
    """解析题目的章/节归属，返回 (chapter_id, section_id, err)。

    规则：选了节 → 章从节推导（两列同写）；只给章 → 章下已建节时必须选到节。
    """
    section_id = data.get('section_id')
    if section_id:
        section = Section.query.get(section_id)
        if not section:
            return None, None, '节不存在'
        return section.chapter_id, section.id, None

    chapter_id = data.get('chapter_id')
    if chapter_id:
        chapter = Chapter.query.get(chapter_id)
        if not chapter:
            return None, None, '章不存在'
        if Section.query.filter_by(chapter_id=chapter_id).count() > 0:
            return None, None, '该章已划分节，请选择具体节'
        return chapter_id, None, None

    return None, None, None

#
@question_bp.route('', methods=['GET'])
@jwt_required(optional=True)
def get_questions():
    #
    subject_id = request.args.get('subject_id', type=int)
    chapter_id = request.args.get('chapter_id', type=int)
    section_id = request.args.get('section_id', type=int)
    question_type = request.args.get('question_type')
    difficulty = request.args.get('difficulty')
    question_source = request.args.get('question_source')
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
    if section_id:
        query = query.filter_by(section_id=section_id)
    if question_type:
        query = query.filter_by(question_type=QuestionType(question_type))
    if difficulty:
        query = query.filter_by(difficulty=DifficultyLevel(difficulty))
    if question_source in QUESTION_SOURCES:
        query = query.filter_by(question_source=question_source)
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
            'section_id': q.section_id,
            'section_name': q.section.name if q.section else None,
            'question_type': q.question_type.value,
            'title': q.title,
            'content': q.content,
            'options': q.options,
            'difficulty': q.difficulty.value,
            'question_source': q.question_source or 'mock',
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
        'section_id': question.section_id,
        'section_name': question.section.name if question.section else None,
        'question_type': question.question_type.value,
        'title': question.title,
        'content': question.content,
        'options': question.options,
        'correct_answer': question.correct_answer,
        'difficulty': question.difficulty.value,
        'question_source': question.question_source or 'mock',
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

    # correct_answer 可能为布尔 False（判断题「错误」），不能用 truthy 判断
    for field in ('subject_id', 'question_type', 'title'):
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    if data.get('correct_answer') is None:
        return jsonify({'error': 'correct_answer is required'}), 400

    source, source_err = _validated_question_source(data.get('question_source'))
    if source_err:
        return jsonify({'error': source_err}), 400

    chapter_id, section_id, cs_err = _resolve_chapter_section(data)
    if cs_err:
        return jsonify({'error': cs_err}), 400

    #
    try:
        question = Question(
            subject_id=data['subject_id'],
            chapter_id=chapter_id,
            section_id=section_id,
            question_type=QuestionType(data['question_type']),
            title=data['title'],
            content=data.get('content'),
            options=data.get('options'),
            correct_answer=data['correct_answer'],
            explanation=data.get('explanation'),
            difficulty=DifficultyLevel(data.get('difficulty', 'medium')),
            question_source=source,
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
        # 章/节归属：选了节 → 从节推导章（两列同写）；只挂章 → 章下已建节时必须选节
        if 'section_id' in data and data['section_id'] is not None:
            section = Section.query.get(data['section_id'])
            if not section:
                return jsonify({'error': '节不存在'}), 400
            question.chapter_id = section.chapter_id
            question.section_id = section.id
        elif 'chapter_id' in data:
            if data['chapter_id'] is None:
                question.chapter_id = None
                question.section_id = None
            else:
                chapter = Chapter.query.get(data['chapter_id'])
                if not chapter:
                    return jsonify({'error': '章不存在'}), 400
                if Section.query.filter_by(chapter_id=data['chapter_id']).count() > 0:
                    return jsonify({'error': '该章已划分节，请选择具体节'}), 400
                question.chapter_id = data['chapter_id']
                question.section_id = None
        elif 'section_id' in data:
            # 只把节置空、章保持：章下已建节时不允许脱离节
            if question.chapter_id and Section.query.filter_by(chapter_id=question.chapter_id).count() > 0:
                return jsonify({'error': '该章已划分节，请选择具体节'}), 400
            question.section_id = None
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
        if data.get('question_source'):
            source, source_err = _validated_question_source(data['question_source'])
            if source_err:
                return jsonify({'error': source_err}), 400
            question.question_source = source
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

            source, source_err = _validated_question_source(
                q_data.get('question_source', q_data.get('source')))
            if source_err:
                raise ValueError(source_err)

            chapter_id, section_id, cs_err = _resolve_chapter_section(q_data)
            if cs_err:
                raise ValueError(cs_err)

            # 用 savepoint 让单行失败不影响整个批次
            with db.session.begin_nested():
                question = Question(
                    subject_id=q_data['subject_id'],
                    chapter_id=chapter_id,
                    section_id=section_id,
                    question_type=QuestionType(q_data['question_type']),
                    title=q_data['title'],
                    content=q_data.get('content'),
                    options=q_data.get('options'),
                    correct_answer=q_data['correct_answer'],
                    explanation=q_data.get('explanation'),
                    difficulty=DifficultyLevel(q_data.get('difficulty', 'medium')),
                    question_source=source,
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