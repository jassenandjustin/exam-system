"""模拟考试模块。

提供：
- 教师端：试卷 CRUD、选题规则管理、题目生成、发布/取消发布
- 学生端：获取可用试卷、从试卷开始考试、暂存/提交、历史/进行中
- 辅助：学科章节题目统计
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc, func, case
from functools import wraps

from models import (
    db, Question, QuestionType, DifficultyLevel, ExamType,
    Exam, ExamQuestionRule, ExamQuestion, ExamQuestionTypeDistribution,
    ExamRecord, ExamAnswer, StudyRecord, ErrorNote,
    User, UserRole, Subject, Chapter, Section,
)
from datetime import datetime, timedelta, timezone

from access import allowed_subject_ids

exam_bp = Blueprint('exam', __name__)


# ============ 权限装饰器 ============

def _current_user():
    return User.query.get(int(get_jwt_identity()))


def teacher_required(f):
    """管理员或教师才能访问。"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _current_user()
        if not user or user.role not in (UserRole.ADMIN, UserRole.TEACHER):
            return jsonify({'error': 'Teacher or admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


# ============ 工具：考试时间窗 ============

def _parse_iso_utc(value):
    """ISO 字符串 → naive UTC datetime；空值返回 None。

    前端统一用 toISOString() 提交（带 Z 或偏移）；库内统一 naive UTC。
    """
    if not value:
        return None
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _parse_paper_window(data):
    """从请求体解析 {start_time, end_time}。两者要么都空要么都填且 start < end。

    返回 (start_time, end_time, err)。
    """
    start_time = _parse_iso_utc(data.get('start_time'))
    end_time = _parse_iso_utc(data.get('end_time'))
    if start_time and not end_time:
        return None, None, '结束时间不能为空'
    if end_time and not start_time:
        return None, None, '开始时间不能为空'
    if start_time and end_time and start_time >= end_time:
        return None, None, '开始时间必须早于结束时间'
    return start_time, end_time, None


def _paper_status(paper, now=None):
    """试卷当前状态：not_started / available / ended。"""
    now = now or datetime.utcnow()
    if paper.start_time and now < paper.start_time:
        return 'not_started'
    if paper.end_time and now > paper.end_time:
        return 'ended'
    return 'available'


def _record_deadline(record):
    """进行中考试的截止时间：开始+时长 与 试卷结束时间 取早者。

    exam_id 为空的旧记录没有试卷概念，退回旧逻辑。
    """
    deadline = record.started_at + timedelta(seconds=record.duration)
    if record.exam_id:
        paper = Exam.query.get(record.exam_id)
        if paper and paper.end_time:
            deadline = min(deadline, paper.end_time)
    return deadline


# ============ 工具：批改 ============

def _is_answer_correct(question, user_answer):
    """对比用户答案与正确答案。主观题永远返回 None（不自动判分）。"""
    qtype = question.question_type
    correct = question.correct_answer

    if qtype == QuestionType.SINGLE_CHOICE:
        return user_answer == correct
    if qtype == QuestionType.MULTIPLE_CHOICE:
        if not isinstance(user_answer, list):
            return False
        a = sorted(user_answer)
        b = sorted(correct) if isinstance(correct, list) else []
        return a == b
    if qtype == QuestionType.TRUE_FALSE:
        truth = correct is True or correct == 'true'
        return bool(user_answer) is truth
    if qtype == QuestionType.FILL_IN_BLANK:
        def norm(v): return str(v or '').strip().lower()
        if isinstance(correct, list):
            return any(norm(c) == norm(user_answer) for c in correct)
        return norm(correct) == norm(user_answer)
    # 主观题
    return None


def _serialize_question_for_exam(q, with_answer=False):
    base = {
        'id': q.id,
        'subject_id': q.subject_id,
        'chapter_id': q.chapter_id,
        'title': q.title,
        'content': q.content,
        'question_type': q.question_type.value,
        'options': q.options,
        'difficulty': q.difficulty.value,
        'score': q.score,
    }
    if with_answer:
        base['correct_answer'] = q.correct_answer
        base['explanation'] = q.explanation
    return base


QUESTION_TYPE_LABELS = {
    QuestionType.SINGLE_CHOICE: '单选题',
    QuestionType.MULTIPLE_CHOICE: '多选题',
    QuestionType.FILL_IN_BLANK: '填空题',
    QuestionType.TRUE_FALSE: '判断题',
    QuestionType.SUBJECTIVE: '主观题',
}


def _question_type_label(question_type):
    return QUESTION_TYPE_LABELS.get(question_type, question_type.value)


def _base_rule_question_query(subject_id, chapter_id=None, difficulty=None, section_id=None):
    q = Question.query.filter_by(subject_id=subject_id)
    if chapter_id:
        q = q.filter_by(chapter_id=chapter_id)
    if section_id:
        q = q.filter_by(section_id=section_id)
    if difficulty:
        q = q.filter(Question.difficulty == difficulty)
    return q


def _parse_difficulty(difficulty):
    if not difficulty:
        return None, None
    try:
        return DifficultyLevel(difficulty), None
    except ValueError:
        return None, f'无效的难度: {difficulty}'


def _parse_type_distribution(data):
    raw = data.get('type_distribution')
    if raw in (None, ''):
        return {}, None
    if not isinstance(raw, dict):
        return None, '题型分配格式不正确'

    result = {}
    for key, value in raw.items():
        try:
            question_type = QuestionType(key)
        except ValueError:
            return None, f'无效的题型: {key}'
        try:
            count = int(value or 0)
        except (TypeError, ValueError):
            return None, f'{_question_type_label(question_type)}数量必须是整数'
        if count < 0:
            return None, f'{_question_type_label(question_type)}数量不能小于0'
        if count > 0:
            result[question_type] = count
    return result, None


def _count_available_by_type(subject_id, chapter_id=None, difficulty=None, section_id=None):
    base_q = _base_rule_question_query(subject_id, chapter_id, difficulty, section_id)
    return {
        question_type.value: base_q.filter(Question.question_type == question_type).count()
        for question_type in QuestionType
    }


def _type_distribution_dict(rule):
    return {
        item.question_type.value: item.count
        for item in rule.type_distributions
        if item.count > 0
    }


def _serialize_rule(rule):
    available_by_type = _count_available_by_type(
        rule.subject_id,
        rule.chapter_id,
        rule.difficulty,
        rule.section_id,
    )
    return {
        'id': rule.id,
        'subject_id': rule.subject_id,
        'subject_name': rule.subject.name if rule.subject else '',
        'chapter_id': rule.chapter_id,
        'chapter_name': rule.chapter.name if rule.chapter else '全部章',
        'section_id': rule.section_id,
        'section_name': rule.section.name if rule.section else None,
        'difficulty': rule.difficulty.value if rule.difficulty else None,
        'question_count': rule.question_count,
        'order_num': rule.order_num,
        'type_distribution': _type_distribution_dict(rule),
        'available_count': sum(available_by_type.values()),
        'available_by_type': available_by_type,
    }


def _validate_rule_payload(data):
    subject_id = data.get('subject_id')
    if not subject_id:
        return None, '请选择学科'

    subject = Subject.query.get(subject_id)
    if not subject:
        return None, '学科不存在'

    chapter_id = data.get('chapter_id')
    if chapter_id:
        chapter = Chapter.query.get(chapter_id)
        if not chapter or chapter.subject_id != subject.id:
            return None, '章不存在或不属于所选学科'

    section_id = data.get('section_id')
    if section_id:
        section = Section.query.get(section_id)
        if not section:
            return None, '节不存在'
        # 未显式选章时从节推导，保持两列一致
        if not chapter_id:
            chapter_id = section.chapter_id
        elif section.chapter_id != chapter_id:
            return None, '节不存在或不属于所选章'

    difficulty, error = _parse_difficulty(data.get('difficulty'))
    if error:
        return None, error

    try:
        question_count = int(data.get('question_count', 0))
    except (TypeError, ValueError):
        return None, '抽取题数必须是整数'
    if question_count <= 0:
        return None, '抽取题数必须大于0'

    type_distribution, error = _parse_type_distribution(data)
    if error:
        return None, error

    available_by_type = _count_available_by_type(subject_id, chapter_id, difficulty, section_id)
    available = sum(available_by_type.values())

    if type_distribution:
        distribution_total = sum(type_distribution.values())
        if distribution_total != question_count:
            return None, '各题型数量之和必须等于抽取题数'
        for question_type, count in type_distribution.items():
            type_available = available_by_type.get(question_type.value, 0)
            if type_available < count:
                return None, f'{_question_type_label(question_type)}可用题目不足，当前仅有 {type_available} 题'
    elif available < question_count:
        return None, f'可用题目不足，当前仅有 {available} 题'

    return {
        'subject_id': subject_id,
        'chapter_id': chapter_id,
        'section_id': section_id,
        'difficulty': difficulty,
        'question_count': question_count,
        'type_distribution': type_distribution,
        'available': available,
    }, None


def _replace_type_distributions(rule, type_distribution):
    rule.type_distributions.clear()
    for question_type, count in type_distribution.items():
        rule.type_distributions.append(ExamQuestionTypeDistribution(
            question_type=question_type,
            count=count,
        ))


# ============ 教师端：试卷 CRUD ============

@exam_bp.route('/papers', methods=['GET'])
@jwt_required()
@teacher_required
def list_papers():
    """获取试卷列表：教师只看自己创建的，管理员看全部（可回顾他人试卷）。"""
    user = _current_user()
    if user.role == UserRole.ADMIN:
        papers = Exam.query.order_by(desc(Exam.created_at)).all()
    else:
        papers = Exam.query.filter_by(created_by=user.id).order_by(desc(Exam.created_at)).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'exam_type': p.exam_type.value,
        'duration_minutes': p.duration_minutes,
        'passing_score': p.passing_score,
        'total_score': p.total_score,
        'total_questions': p.total_questions,
        'is_published': p.is_published,
        'start_time': p.start_time.isoformat() + 'Z' if p.start_time else None,
        'end_time': p.end_time.isoformat() + 'Z' if p.end_time else None,
        'creator': p.creator.username if p.creator else '',
        'is_owner': p.created_by == user.id,
        'rule_count': len(p.question_rules),
        'question_count': len(p.exam_questions),
        'created_at': p.created_at.isoformat() + 'Z',
        'updated_at': p.updated_at.isoformat() + 'Z',
    } for p in papers])


@exam_bp.route('/papers', methods=['POST'])
@jwt_required()
@teacher_required
def create_paper():
    """创建试卷。"""
    user = _current_user()
    data = request.get_json() or {}

    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': '试卷名称不能为空'}), 400

    exam_type_str = data.get('exam_type', 'custom')
    try:
        exam_type = ExamType(exam_type_str)
    except ValueError:
        return jsonify({'error': f'无效的考试类型: {exam_type_str}'}), 400

    duration_minutes = int(data.get('duration_minutes', 45))
    passing_score = float(data.get('passing_score', 0))

    paper = Exam(
        name=name,
        description=data.get('description', ''),
        exam_type=exam_type,
        duration_minutes=duration_minutes,
        passing_score=passing_score,
        created_by=user.id,
    )
    db.session.add(paper)
    db.session.commit()
    return jsonify({'id': paper.id, 'name': paper.name}), 201


@exam_bp.route('/papers/<int:paper_id>', methods=['GET'])
@jwt_required()
@teacher_required
def get_paper(paper_id):
    """获取试卷详情（含规则和题目）。"""
    user = _current_user()
    paper = Exam.query.get(paper_id)
    if not paper or paper.created_by != user.id:
        return jsonify({'error': '试卷不存在'}), 404

    rules = []
    for r in paper.question_rules:
        rules.append(_serialize_rule(r))

    questions = []
    for eq in paper.exam_questions:
        q = eq.question
        questions.append({
            'order_num': eq.order_num,
            'score': eq.score,
            **_serialize_question_for_exam(q, with_answer=True),
        })

    return jsonify({
        'id': paper.id,
        'name': paper.name,
        'description': paper.description,
        'exam_type': paper.exam_type.value,
        'duration_minutes': paper.duration_minutes,
        'passing_score': paper.passing_score,
        'total_score': paper.total_score,
        'total_questions': paper.total_questions,
        'is_published': paper.is_published,
        'start_time': paper.start_time.isoformat() + 'Z' if paper.start_time else None,
        'end_time': paper.end_time.isoformat() + 'Z' if paper.end_time else None,
        'rules': rules,
        'questions': questions,
        'created_at': paper.created_at.isoformat() + 'Z',
        'updated_at': paper.updated_at.isoformat() + 'Z',
    })


@exam_bp.route('/papers/<int:paper_id>', methods=['PUT'])
@jwt_required()
@teacher_required
def update_paper(paper_id):
    """更新试卷基本信息。"""
    user = _current_user()
    paper = Exam.query.get(paper_id)
    if not paper or paper.created_by != user.id:
        return jsonify({'error': '试卷不存在'}), 404

    data = request.get_json() or {}
    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name:
            return jsonify({'error': '试卷名称不能为空'}), 400
        paper.name = name
    if 'description' in data:
        paper.description = data['description']
    if 'exam_type' in data:
        try:
            paper.exam_type = ExamType(data['exam_type'])
        except ValueError:
            return jsonify({'error': f'无效的考试类型: {data["exam_type"]}'}), 400
    if 'duration_minutes' in data:
        paper.duration_minutes = int(data['duration_minutes'])
    if 'passing_score' in data:
        paper.passing_score = float(data['passing_score'])
    if 'start_time' in data or 'end_time' in data:
        # 考试时间窗：发布后也允许修改（教师纠错场景）；选题规则仍锁死。
        # 必须成对提供（都为 null 表示清空，回到长期开放），避免误清窗口。
        if 'start_time' not in data or 'end_time' not in data:
            return jsonify({'error': '开始与结束时间需成对设置（都为空表示不限时）'}), 400
        start_time, end_time, window_err = _parse_paper_window(data)
        if window_err:
            return jsonify({'error': window_err}), 400
        paper.start_time = start_time
        paper.end_time = end_time

    db.session.commit()
    return jsonify({'message': '更新成功'})


@exam_bp.route('/papers/<int:paper_id>', methods=['DELETE'])
@jwt_required()
@teacher_required
def delete_paper(paper_id):
    """删除试卷（仅未发布的可删）。"""
    user = _current_user()
    paper = Exam.query.get(paper_id)
    if not paper or paper.created_by != user.id:
        return jsonify({'error': '试卷不存在'}), 404
    if paper.is_published:
        return jsonify({'error': '已发布的试卷不能删除，请先取消发布'}), 400
    # 检查是否有人已参加过此试卷的考试
    if ExamRecord.query.filter_by(exam_id=paper_id).count() > 0:
        return jsonify({'error': '已有学生参加过此考试，无法删除'}), 400

    db.session.delete(paper)
    db.session.commit()
    return jsonify({'message': '删除成功'})


# ============ 教师端：选题规则管理 ============

@exam_bp.route('/papers/<int:paper_id>/rules', methods=['POST'])
@jwt_required()
@teacher_required
def add_rule(paper_id):
    """添加选题规则。"""
    user = _current_user()
    paper = Exam.query.get(paper_id)
    if not paper or paper.created_by != user.id:
        return jsonify({'error': '试卷不存在'}), 404
    if paper.is_published:
        return jsonify({'error': '已发布的试卷不能修改规则'}), 400

    data = request.get_json() or {}
    payload, error = _validate_rule_payload(data)
    if error:
        return jsonify({'error': error}), 400

    rule = ExamQuestionRule(
        exam_id=paper_id,
        subject_id=payload['subject_id'],
        chapter_id=payload['chapter_id'],
        section_id=payload['section_id'],
        difficulty=payload['difficulty'],
        question_count=payload['question_count'],
        order_num=data.get('order_num', 0),
    )
    db.session.add(rule)
    db.session.flush()
    _replace_type_distributions(rule, payload['type_distribution'])
    db.session.commit()
    return jsonify({'id': rule.id, 'available_count': payload['available']}), 201


@exam_bp.route('/papers/<int:paper_id>/rules/<int:rule_id>', methods=['PUT'])
@jwt_required()
@teacher_required
def update_rule(paper_id, rule_id):
    """修改选题规则。"""
    user = _current_user()
    paper = Exam.query.get(paper_id)
    if not paper or paper.created_by != user.id:
        return jsonify({'error': '试卷不存在'}), 404
    if paper.is_published:
        return jsonify({'error': '已发布的试卷不能修改规则'}), 400

    rule = ExamQuestionRule.query.get(rule_id)
    if not rule or rule.exam_id != paper_id:
        return jsonify({'error': '规则不存在'}), 404

    data = request.get_json() or {}
    # 章变了但没给新节 → 清掉旧节；显式给节 → 覆盖（校验器会自动补齐所属章）
    if 'section_id' in data:
        merged_section_id = data['section_id']
    elif 'chapter_id' in data and data['chapter_id'] != rule.chapter_id:
        merged_section_id = None
    else:
        merged_section_id = rule.section_id
    merged = {
        'subject_id': data.get('subject_id', rule.subject_id),
        'chapter_id': data.get('chapter_id', rule.chapter_id),
        'section_id': merged_section_id,
        'difficulty': data.get('difficulty', rule.difficulty.value if rule.difficulty else ''),
        'question_count': data.get('question_count', rule.question_count),
    }
    if 'type_distribution' in data:
        merged['type_distribution'] = data.get('type_distribution')
    else:
        merged['type_distribution'] = _type_distribution_dict(rule)

    payload, error = _validate_rule_payload(merged)
    if error:
        return jsonify({'error': error}), 400

    rule.subject_id = payload['subject_id']
    rule.chapter_id = payload['chapter_id']
    rule.section_id = payload['section_id']
    rule.difficulty = payload['difficulty']
    rule.question_count = payload['question_count']
    if 'order_num' in data:
        rule.order_num = data['order_num']
    if 'type_distribution' in data:
        _replace_type_distributions(rule, payload['type_distribution'])

    db.session.commit()
    return jsonify({'message': '更新成功'})


@exam_bp.route('/papers/<int:paper_id>/rules/<int:rule_id>', methods=['DELETE'])
@jwt_required()
@teacher_required
def delete_rule(paper_id, rule_id):
    """删除选题规则。"""
    user = _current_user()
    paper = Exam.query.get(paper_id)
    if not paper or paper.created_by != user.id:
        return jsonify({'error': '试卷不存在'}), 404
    if paper.is_published:
        return jsonify({'error': '已发布的试卷不能修改规则'}), 400

    rule = ExamQuestionRule.query.get(rule_id)
    if not rule or rule.exam_id != paper_id:
        return jsonify({'error': '规则不存在'}), 404

    db.session.delete(rule)
    db.session.commit()
    return jsonify({'message': '删除成功'})


# ============ 教师端：题目生成与发布 ============

@exam_bp.route('/papers/<int:paper_id>/generate', methods=['POST'])
@jwt_required()
@teacher_required
def generate_questions(paper_id):
    """根据规则随机生成试卷题目（清除旧题目，重新抽取）。"""
    user = _current_user()
    paper = Exam.query.get(paper_id)
    if not paper or paper.created_by != user.id:
        return jsonify({'error': '试卷不存在'}), 404
    if paper.is_published:
        return jsonify({'error': '已发布的试卷不能重新生成'}), 400

    rules = paper.question_rules
    if not rules:
        return jsonify({'error': '请先添加选题规则'}), 400

    # 清除旧题目
    ExamQuestion.query.filter_by(exam_id=paper_id).delete()

    selected_ids = set()  # 避免重复
    order = 0
    for rule in sorted(rules, key=lambda r: r.order_num):
        distributions = list(rule.type_distributions)
        if distributions:
            selection_groups = [
                (item.question_type, item.count)
                for item in distributions
                if item.count > 0
            ]
        else:
            selection_groups = [(None, rule.question_count)]

        for question_type, count in selection_groups:
            q = _base_rule_question_query(rule.subject_id, rule.chapter_id, rule.difficulty, rule.section_id)
            if question_type:
                q = q.filter(Question.question_type == question_type)
            # 排除已选的题目，避免跨规则重复
            if selected_ids:
                q = q.filter(~Question.id.in_(selected_ids))
            questions = q.order_by(db.func.random()).limit(count).all()
            if len(questions) < count:
                db.session.rollback()
                label = _question_type_label(question_type) if question_type else '题目'
                return jsonify({'error': f'规则 {rule.order_num} 的{label}可用题目不足，无法生成试卷'}), 400
            for qq in questions:
                order += 1
                db.session.add(ExamQuestion(
                    exam_id=paper_id,
                    question_id=qq.id,
                    order_num=order,
                    score=qq.score or 2.0,
                ))
                selected_ids.add(qq.id)

    # 更新试卷统计
    eqs = ExamQuestion.query.filter_by(exam_id=paper_id).all()
    paper.total_questions = len(eqs)
    paper.total_score = sum(eq.score for eq in eqs)

    db.session.commit()
    return jsonify({
        'message': '生成成功',
        'total_questions': paper.total_questions,
        'total_score': paper.total_score,
    })


@exam_bp.route('/papers/<int:paper_id>/publish', methods=['POST'])
@jwt_required()
@teacher_required
def publish_paper(paper_id):
    """发布试卷（可同时设置开始/结束考试时间；都不填则长期开放）。"""
    user = _current_user()
    paper = Exam.query.get(paper_id)
    if not paper or paper.created_by != user.id:
        return jsonify({'error': '试卷不存在'}), 404
    if paper.is_published:
        return jsonify({'error': '试卷已发布'}), 400
    if not paper.exam_questions:
        return jsonify({'error': '请先生成题目再发布'}), 400

    data = request.get_json() or {}
    start_time, end_time, window_err = _parse_paper_window(data)
    if window_err:
        return jsonify({'error': window_err}), 400

    paper.start_time = start_time
    paper.end_time = end_time
    paper.is_published = True
    db.session.commit()
    return jsonify({'message': '发布成功'})


@exam_bp.route('/papers/<int:paper_id>/unpublish', methods=['POST'])
@jwt_required()
@teacher_required
def unpublish_paper(paper_id):
    """取消发布。"""
    user = _current_user()
    paper = Exam.query.get(paper_id)
    if not paper or paper.created_by != user.id:
        return jsonify({'error': '试卷不存在'}), 404
    if not paper.is_published:
        return jsonify({'error': '试卷未发布'}), 400

    paper.is_published = False
    db.session.commit()
    return jsonify({'message': '取消发布成功'})


# ============ 教师端：试卷回顾 ============

@exam_bp.route('/papers/<int:paper_id>/review', methods=['GET'])
@jwt_required()
@teacher_required
def review_paper(paper_id):
    """试卷回顾：总体及格/优秀统计、章节正确率（薄弱章节）、逐题正确率。

    教师只能回顾自己创建的试卷；管理员可回顾全部。
    及格线 = 总分的 60%，优秀线 = 总分的 85%。
    """
    user = _current_user()
    paper = Exam.query.get(paper_id)
    if not paper or (user.role != UserRole.ADMIN and paper.created_by != user.id):
        return jsonify({'error': '试卷不存在'}), 404

    records = ExamRecord.query.filter_by(exam_id=paper_id) \
        .filter(ExamRecord.submitted_at.isnot(None)).all()
    rec_ids = [r.id for r in records]
    participants = len(records)
    in_progress = ExamRecord.query.filter_by(exam_id=paper_id, submitted_at=None).count()

    pass_line = (paper.total_score or 0) * 0.6
    excellent_line = (paper.total_score or 0) * 0.85
    pass_count = sum(1 for r in records if r.obtained_score >= pass_line)
    excellent_count = sum(1 for r in records if r.obtained_score >= excellent_line)
    avg_obtained = round(
        sum(r.obtained_score for r in records) / participants, 1
    ) if participants else 0

    overview = {
        'participants': participants,
        'in_progress': in_progress,
        'avg_obtained': avg_obtained,
        'pass_count': pass_count,
        'pass_rate': round(pass_count / participants * 100, 1) if participants else 0,
        'excellent_count': excellent_count,
        'excellent_rate': round(excellent_count / participants * 100, 1) if participants else 0,
        'total_score': paper.total_score,
        'total_questions': paper.total_questions,
    }

    chapters = []
    questions = []

    # 卷内题目（含每题卷面分值与章节归属）
    eqs = ExamQuestion.query.filter_by(exam_id=paper_id) \
        .order_by(ExamQuestion.order_num.asc()).all()
    qids = [eq.question_id for eq in eqs]
    qmap = {q.id: q for q in Question.query.filter(Question.id.in_(qids)).all()} if qids else {}

    if rec_ids:
        # 逐题统计：每人每题一行占位（未作答 is_correct=False），答对数即正确人数
        q_rows = db.session.query(
            ExamAnswer.question_id,
            func.count(ExamAnswer.id),
            func.sum(case((ExamAnswer.is_correct, 1), else_=0)),
        ).filter(ExamAnswer.exam_record_id.in_(rec_ids)) \
         .group_by(ExamAnswer.question_id).all()
        q_stats = {row[0]: (row[1], row[2] or 0) for row in q_rows}

        for eq in eqs:
            q = qmap.get(eq.question_id)
            if not q:
                continue
            _answered, correct = q_stats.get(eq.question_id, (0, 0))
            questions.append({
                'question_id': eq.question_id,
                'order_num': eq.order_num,
                'title': q.title,
                'question_type': q.question_type.value,
                'score': eq.score,
                'correct_count': correct,
                'wrong_count': participants - correct,
                'accuracy': round(correct / participants * 100, 1) if participants else 0,
            })
        # 正确率最差的题在前
        questions.sort(key=lambda x: x['accuracy'])

        # 章节统计：按 (学生, 题) 粒度聚合，正确率 = 正确作答数 / 总作答记录数
        ch_rows = db.session.query(
            Question.chapter_id,
            func.count(ExamAnswer.id),
            func.sum(case((ExamAnswer.is_correct, 1), else_=0)),
        ).join(ExamAnswer, ExamAnswer.question_id == Question.id) \
         .filter(ExamAnswer.exam_record_id.in_(rec_ids)) \
         .group_by(Question.chapter_id).all()
        ch_stats = {row[0]: (row[1], row[2] or 0) for row in ch_rows}
        real_ids = [cid for cid in ch_stats if cid]
        ch_names = {c.id: c.name for c in Chapter.query.filter(Chapter.id.in_(real_ids)).all()}

        # 卷中每章的题数（按生成时冻结的题目列表统计）
        ch_question_count = {}
        for eq in eqs:
            q = qmap.get(eq.question_id)
            if q:
                ch_question_count[q.chapter_id] = ch_question_count.get(q.chapter_id, 0) + 1

        for chapter_id, qcount in ch_question_count.items():
            answered, correct = ch_stats.get(chapter_id, (0, 0))
            accuracy = round(correct / answered * 100, 1) if answered else 0
            chapters.append({
                'chapter_id': chapter_id,
                'chapter_name': ch_names.get(chapter_id, '未分章') if chapter_id else '未分章',
                'question_count': qcount,
                'answered': answered,
                'correct_people': correct,
                'accuracy': accuracy,
                'is_weak': accuracy < 60,
            })
        # 正确率最低的章节在前（薄弱章节）
        chapters.sort(key=lambda c: c['accuracy'])

    return jsonify({
        'paper': {
            'id': paper.id,
            'name': paper.name,
            'exam_type': paper.exam_type.value,
            'duration_minutes': paper.duration_minutes,
            'passing_score': paper.passing_score,
            'total_score': paper.total_score,
            'total_questions': paper.total_questions,
            'is_published': paper.is_published,
            'start_time': paper.start_time.isoformat() + 'Z' if paper.start_time else None,
            'end_time': paper.end_time.isoformat() + 'Z' if paper.end_time else None,
            'status': _paper_status(paper),
            'creator': paper.creator.username if paper.creator else '',
        },
        'overview': overview,
        'chapters': chapters,
        'questions': questions,
    })


# ============ 辅助 API ============

@exam_bp.route('/subjects/<int:subject_id>/chapter-stats', methods=['GET'])
@jwt_required()
def chapter_stats(subject_id):
    """获取学科下各章/节的题目数量统计（含按难度和题型分组）。

    每章附带 sections 细分：题目两列同写（chapter_id + section_id），直接按
    section_id 聚合即可得到各节数；章级 total 仍含全部节的题（按 chapter_id 聚合）。
    """
    def build_type_counts(base_q):
        return {
            question_type.value: base_q.filter(Question.question_type == question_type).count()
            for question_type in QuestionType
        }

    def build_difficulty_type_counts(subject_id, chapter_id=None, section_id=None):
        data = {}
        for difficulty in DifficultyLevel:
            q = Question.query.filter_by(subject_id=subject_id, difficulty=difficulty)
            if section_id:
                q = q.filter_by(section_id=section_id)
            elif chapter_id:
                q = q.filter_by(chapter_id=chapter_id)
            data[difficulty.value] = build_type_counts(q)
        return data

    def build_section_breakdown(chapter):
        """该章下各节的题目统计（按 section_id 聚合）。"""
        sections = Section.query.filter_by(chapter_id=chapter.id).order_by(
            Section.order_num.asc(), Section.id.asc()
        ).all()
        out = []
        for s in sections:
            sec_q = Question.query.filter_by(subject_id=subject_id, section_id=s.id)
            out.append({
                'id': s.id,
                'name': s.name,
                'order_num': s.order_num,
                'total': sec_q.count(),
                'easy': Question.query.filter_by(
                    subject_id=subject_id, section_id=s.id, difficulty=DifficultyLevel.EASY
                ).count(),
                'medium': Question.query.filter_by(
                    subject_id=subject_id, section_id=s.id, difficulty=DifficultyLevel.MEDIUM
                ).count(),
                'hard': Question.query.filter_by(
                    subject_id=subject_id, section_id=s.id, difficulty=DifficultyLevel.HARD
                ).count(),
                'by_type': build_type_counts(sec_q),
                'by_difficulty_type': build_difficulty_type_counts(subject_id, section_id=s.id),
            })
        return out

    chapters = Chapter.query.filter_by(subject_id=subject_id).order_by(Chapter.order_num.asc()).all()
    result = []
    for c in chapters:
        base_q = Question.query.filter_by(subject_id=subject_id, chapter_id=c.id)
        total = base_q.count()
        easy = Question.query.filter_by(subject_id=subject_id, chapter_id=c.id, difficulty=DifficultyLevel.EASY).count()
        medium = Question.query.filter_by(subject_id=subject_id, chapter_id=c.id, difficulty=DifficultyLevel.MEDIUM).count()
        hard = Question.query.filter_by(subject_id=subject_id, chapter_id=c.id, difficulty=DifficultyLevel.HARD).count()
        result.append({
            'id': c.id,
            'name': c.name,
            'order_num': c.order_num,
            'total': total,
            'easy': easy,
            'medium': medium,
            'hard': hard,
            'by_type': build_type_counts(base_q),
            'by_difficulty_type': build_difficulty_type_counts(subject_id, c.id),
            'sections': build_section_breakdown(c),
        })
    # 整科统计
    subject_q = Question.query.filter_by(subject_id=subject_id)
    total_all = subject_q.count()
    return jsonify({
        'chapters': result,
        'subject_total': total_all,
        'subject_by_type': build_type_counts(subject_q),
        'subject_by_difficulty_type': build_difficulty_type_counts(subject_id),
    })


# ============ 学生端：获取可用试卷 ============

def _paper_subject_ids(paper):
    """试卷涉及的学科集合：优先用抽题规则的 subject_id，无规则回退到
    已固定题目（ExamQuestion → Question.subject_id）。用于班级学科范围判定。"""
    rule_subjects = {r.subject_id for r in paper.question_rules}
    if rule_subjects:
        return rule_subjects
    eqs = ExamQuestion.query.filter_by(exam_id=paper.id).all()
    qids = [eq.question_id for eq in eqs]
    if not qids:
        return set()
    return {q.subject_id for q in Question.query.filter(Question.id.in_(qids)).all()}


def _exam_subject_gate_err(user, paper):
    """学生班级学科范围 ⊇ 试卷学科 才能考试；教师/管理员豁免。"""
    allowed = allowed_subject_ids(user)
    if allowed is None:
        return None
    if not allowed:
        return (jsonify({'error': '请先加入班级后再使用该功能'}), 403)
    paper_subjects = _paper_subject_ids(paper)
    if not paper_subjects or paper_subjects <= allowed:
        return None
    return (jsonify({'error': '该试卷包含你班级学科范围以外的内容'}), 403)


@exam_bp.route('/available', methods=['GET'])
@jwt_required()
def list_available_exams():
    """学生获取已发布的试卷列表（含考试时间窗状态）。"""
    user = _current_user()
    papers = Exam.query.filter_by(is_published=True).order_by(desc(Exam.created_at)).all()
    user_id = user.id
    now = datetime.utcnow()
    items = []
    for p in papers:
        gate_err = _exam_subject_gate_err(user, p)
        if gate_err:
            continue  # 范围外试卷直接不可见
        # 查看学生是否已参加过此试卷
        existing = ExamRecord.query.filter_by(user_id=user_id, exam_id=p.id).first()
        items.append({
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'exam_type': p.exam_type.value,
            'duration_minutes': p.duration_minutes,
            'passing_score': p.passing_score,
            'total_score': p.total_score,
            'total_questions': p.total_questions,
            'is_published': p.is_published,
            'start_time': p.start_time.isoformat() + 'Z' if p.start_time else None,
            'end_time': p.end_time.isoformat() + 'Z' if p.end_time else None,
            'status': _paper_status(p, now),
            'creator': p.creator.username if p.creator else '',
            'created_at': p.created_at.isoformat() + 'Z',
            'has_taken': existing is not None,
        })
    return jsonify({'items': items})


# ============ 学生端：从试卷开始考试 ============

@exam_bp.route('/start/<int:paper_id>', methods=['POST'])
@jwt_required()
def start_exam_from_paper(paper_id):
    """从指定试卷开始考试。"""
    user = _current_user()
    paper = Exam.query.get(paper_id)
    if not paper or not paper.is_published:
        return jsonify({'error': '试卷不存在或未发布'}), 404

    gate_err = _exam_subject_gate_err(user, paper)
    if gate_err:
        return gate_err

    # 考试时间窗（严格窗口：未开始不能考、结束后不能开考）
    now = datetime.utcnow()
    if paper.start_time and now < paper.start_time:
        return jsonify({'error': '考试尚未开始'}), 400
    if paper.end_time and now > paper.end_time:
        return jsonify({'error': '考试已结束，无法开始'}), 400

    user_id = user.id

    # 阻止用户同时开多场进行中的考试
    in_progress = ExamRecord.query.filter_by(
        user_id=user_id, submitted_at=None
    ).first()
    if in_progress:
        return jsonify({
            'error': 'You already have an exam in progress',
            'exam_id': in_progress.id
        }), 409

    # 获取试卷题目
    eqs = ExamQuestion.query.filter_by(exam_id=paper_id).order_by(ExamQuestion.order_num.asc()).all()
    if not eqs:
        return jsonify({'error': '试卷中没有题目'}), 400

    qids = [eq.question_id for eq in eqs]
    questions = {q.id: q for q in Question.query.filter(Question.id.in_(qids)).all()}

    total_score = sum(eq.score for eq in eqs)
    duration_sec = paper.duration_minutes * 60

    record = ExamRecord(
        user_id=user_id,
        exam_id=paper_id,
        total_score=total_score,
        obtained_score=0,
        duration=duration_sec,
        correct_count=0,
        total_questions=len(eqs),
        exam_type=paper.exam_type.value,
        started_at=datetime.utcnow(),
        submitted_at=None,
    )
    db.session.add(record)
    db.session.flush()

    # 占位 ExamAnswer
    for eq in eqs:
        db.session.add(ExamAnswer(
            exam_record_id=record.id,
            question_id=eq.question_id,
            user_answer=None,
            is_correct=False,
            score=0,
        ))
    db.session.commit()

    # 截止时间 = 开始 + 时长 与 试卷结束时间 取早者
    deadline = record.started_at + timedelta(seconds=duration_sec)
    if paper.end_time:
        deadline = min(deadline, paper.end_time)
    question_list = []
    for eq in eqs:
        q = questions.get(eq.question_id)
        if q:
            item = _serialize_question_for_exam(q, with_answer=False)
            item['score'] = eq.score
            item['order_num'] = eq.order_num
            question_list.append(item)

    return jsonify({
        'exam_id': record.id,
        'exam_name': paper.name,
        'exam_type': record.exam_type,
        'started_at': record.started_at.isoformat() + 'Z',
        'deadline': deadline.isoformat() + 'Z',
        'duration_sec': duration_sec,
        'total_score': record.total_score,
        'total_questions': record.total_questions,
        'questions': question_list,
    }), 201


# ============ 进行中：拉考试状态 ============

@exam_bp.route('/<int:exam_id>', methods=['GET'])
@jwt_required()
def get_exam(exam_id):
    user_id = int(get_jwt_identity())
    record = ExamRecord.query.get(exam_id)
    if not record or record.user_id != user_id:
        return jsonify({'error': 'Exam not found'}), 404

    answers = ExamAnswer.query.filter_by(exam_record_id=exam_id).all()
    qmap = {q.id: q for q in Question.query.filter(
        Question.id.in_([a.question_id for a in answers])
    ).all()}

    submitted = record.submitted_at is not None
    deadline = _record_deadline(record)

    # 获取试卷名称
    exam_name = ''
    if record.exam_id:
        paper = Exam.query.get(record.exam_id)
        if paper:
            exam_name = paper.name

    items = []
    for a in answers:
        q = qmap.get(a.question_id)
        if not q:
            continue
        items.append({
            **_serialize_question_for_exam(q, with_answer=submitted),
            'user_answer': a.user_answer,
            'is_correct': a.is_correct if submitted else None,
            'score_obtained': a.score if submitted else None,
        })

    return jsonify({
        'exam_id': record.id,
        'exam_name': exam_name,
        'exam_type': record.exam_type,
        'started_at': record.started_at.isoformat() + 'Z',
        'submitted_at': record.submitted_at.isoformat() + 'Z' if submitted else None,
        'deadline': deadline.isoformat() + 'Z',
        'duration_sec': record.duration,
        'total_score': record.total_score,
        'obtained_score': record.obtained_score,
        'total_questions': record.total_questions,
        'correct_count': record.correct_count,
        'submitted': submitted,
        'questions': items,
    })


# ============ 暂存答案 ============

@exam_bp.route('/<int:exam_id>/save', methods=['POST'])
@jwt_required()
def save_answers(exam_id):
    """考试期间用来同步当前已作答的内容；提交时再批改。"""
    user_id = int(get_jwt_identity())
    record = ExamRecord.query.get(exam_id)
    if not record or record.user_id != user_id:
        return jsonify({'error': 'Exam not found'}), 404
    if record.submitted_at:
        return jsonify({'error': 'Exam already submitted'}), 400

    data = request.get_json() or {}
    answers = data.get('answers') or []
    by_qid = {int(a['question_id']): a.get('user_answer') for a in answers if 'question_id' in a}

    rows = ExamAnswer.query.filter_by(exam_record_id=exam_id).all()
    for r in rows:
        if r.question_id in by_qid:
            r.user_answer = by_qid[r.question_id]
    db.session.commit()
    return jsonify({'message': 'saved'})


# ============ 提交考试 ============

@exam_bp.route('/<int:exam_id>/submit', methods=['POST'])
@jwt_required()
def submit_exam(exam_id):
    user_id = int(get_jwt_identity())
    record = ExamRecord.query.get(exam_id)
    if not record or record.user_id != user_id:
        return jsonify({'error': 'Exam not found'}), 404
    if record.submitted_at:
        return jsonify({'error': 'Exam already submitted'}), 400

    data = request.get_json() or {}
    answers = data.get('answers') or []
    by_qid = {int(a['question_id']): a.get('user_answer') for a in answers if 'question_id' in a}

    rows = ExamAnswer.query.filter_by(exam_record_id=exam_id).all()
    qmap = {q.id: q for q in Question.query.filter(
        Question.id.in_([r.question_id for r in rows])
    ).all()}

    # 试卷中每题的分值（生成时冻结在 ExamQuestion 上）；
    # 旧记录 exam_id 为空或题目已被换掉时回退 Question.score
    eq_scores = {}
    if record.exam_id:
        eq_scores = {eq.question_id: eq.score
                     for eq in ExamQuestion.query.filter_by(exam_id=record.exam_id).all()}

    obtained = 0.0
    correct_count = 0
    for r in rows:
        q = qmap.get(r.question_id)
        if not q:
            continue
        if r.question_id in by_qid:
            r.user_answer = by_qid[r.question_id]

        if r.user_answer is None:
            r.is_correct = False
            r.score = 0
            continue
        verdict = _is_answer_correct(q, r.user_answer)
        if verdict is True:
            r.is_correct = True
            r.score = eq_scores.get(r.question_id, q.score or 0)
            obtained += r.score
            correct_count += 1
        elif verdict is False:
            r.is_correct = False
            r.score = 0
        else:
            r.is_correct = False
            r.score = 0

    record.obtained_score = obtained
    record.correct_count = correct_count
    record.submitted_at = datetime.utcnow()

    # 同步写入学习记录与错题本
    for r in rows:
        if r.user_answer is None:
            continue
        db.session.add(StudyRecord(
            user_id=user_id,
            question_id=r.question_id,
            is_correct=bool(r.is_correct),
            answer=r.user_answer,
            practiced_at=datetime.utcnow(),
        ))
        if not r.is_correct:
            existing = ErrorNote.query.filter_by(
                user_id=user_id, question_id=r.question_id
            ).first()
            if not existing:
                db.session.add(ErrorNote(
                    user_id=user_id,
                    question_id=r.question_id,
                ))

    db.session.commit()

    used_seconds = int((record.submitted_at - record.started_at).total_seconds())
    return jsonify({
        'exam_id': record.id,
        'total_score': record.total_score,
        'obtained_score': record.obtained_score,
        'total_questions': record.total_questions,
        'correct_count': record.correct_count,
        'accuracy': round(correct_count / len(rows) * 100, 1) if rows else 0,
        'used_seconds': used_seconds,
        'submitted_at': record.submitted_at.isoformat() + 'Z',
    })


# ============ 历史 ============

@exam_bp.route('/history', methods=['GET'])
@jwt_required()
def list_history():
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    pagination = ExamRecord.query.filter_by(user_id=user_id) \
        .order_by(desc(ExamRecord.started_at)) \
        .paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for r in pagination.items:
        used = None
        if r.submitted_at:
            used = int((r.submitted_at - r.started_at).total_seconds())
        # 获取试卷名称
        exam_name = ''
        if r.exam_id:
            paper = Exam.query.get(r.exam_id)
            if paper:
                exam_name = paper.name
        items.append({
            'exam_id': r.id,
            'exam_name': exam_name,
            'exam_type': r.exam_type,
            'total_score': r.total_score,
            'obtained_score': r.obtained_score,
            'total_questions': r.total_questions,
            'correct_count': r.correct_count,
            'accuracy': round(r.correct_count / r.total_questions * 100, 1)
                       if r.total_questions and r.submitted_at else None,
            'duration_sec': r.duration,
            'used_seconds': used,
            'started_at': r.started_at.isoformat() + 'Z',
            'submitted_at': r.submitted_at.isoformat() + 'Z' if r.submitted_at else None,
            'submitted': r.submitted_at is not None,
        })

    return jsonify({
        'items': items,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


@exam_bp.route('/in-progress', methods=['GET'])
@jwt_required()
def in_progress_exam():
    """前端进入考试页前调一下：是否有未交卷的考试需要继续。"""
    user_id = int(get_jwt_identity())
    record = ExamRecord.query.filter_by(user_id=user_id, submitted_at=None) \
        .order_by(desc(ExamRecord.started_at)).first()
    if not record:
        return jsonify({'in_progress': False})
    deadline = _record_deadline(record)
    # 获取试卷名称
    exam_name = ''
    if record.exam_id:
        paper = Exam.query.get(record.exam_id)
        if paper:
            exam_name = paper.name
    return jsonify({
        'in_progress': True,
        'exam_id': record.id,
        'exam_name': exam_name,
        'exam_type': record.exam_type,
        'started_at': record.started_at.isoformat() + 'Z',
        'deadline': deadline.isoformat() + 'Z',
    })
