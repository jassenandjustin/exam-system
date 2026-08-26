"""学习分析模块。

为前端「学习分析」页面提供：
- 总览统计（总练习量、正确率、用时、连续打卡）
- 每日趋势（练习量 / 正确率 / 用时折线）
- 学科维度统计（用时、正确率，雷达图/条形图）
- 薄弱知识点（按 tag 聚合错题，标记掌握度）
- 学习报告（周/月，含建议）
- 推荐题目（依据当前正确率挑难度）

这些接口都需要登录，且只能查询自己的数据。
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import case, func, desc

from models import (
    db, StudyRecord, Question, Subject, Tag, QuestionTag,
    ErrorNote, ExamRecord, Favorite, DifficultyLevel,
)
from datetime import datetime, timedelta

import numpy as np

analysis_bp = Blueprint('analysis', __name__)


def _check_self(user_id):
    """只允许查询自己的数据。返回 (current_id, error_response_or_None)。"""
    cur = int(get_jwt_identity())
    if cur != user_id:
        return cur, (jsonify({'error': 'Permission denied'}), 403)
    return cur, None


def _correct_sum():
    """跨方言通用的 SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)。"""
    return func.sum(case((StudyRecord.is_correct, 1), else_=0))


def _streak_days(user_id):
    """从今天往前数连续打卡天数（有任何一条 StudyRecord 即算）。"""
    rows = db.session.query(
        func.date(StudyRecord.practiced_at)
    ).filter(StudyRecord.user_id == user_id).distinct().all()
    days = {r[0] for r in rows}
    if not days:
        return 0
    streak = 0
    today = datetime.utcnow().date()
    while today in days:
        streak += 1
        today -= timedelta(days=1)
    return streak


# ============ 概览 ============

@analysis_bp.route('/stats/<int:user_id>', methods=['GET'])
@jwt_required()
def get_learning_stats(user_id):
    _, err = _check_self(user_id)
    if err:
        return err

    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)

    total = StudyRecord.query.filter_by(user_id=user_id).count()
    correct = StudyRecord.query.filter_by(user_id=user_id, is_correct=True).count()
    overall_acc = (correct / total * 100) if total else 0

    period_total = StudyRecord.query.filter(
        StudyRecord.user_id == user_id,
        StudyRecord.practiced_at >= start_date
    ).count()
    period_correct = StudyRecord.query.filter(
        StudyRecord.user_id == user_id,
        StudyRecord.is_correct.is_(True),
        StudyRecord.practiced_at >= start_date
    ).count()
    period_acc = (period_correct / period_total * 100) if period_total else 0

    avg_time = db.session.query(func.avg(StudyRecord.used_time)).filter_by(user_id=user_id).scalar()
    total_time = db.session.query(func.sum(StudyRecord.used_time)).filter_by(user_id=user_id).scalar()

    error_count = ErrorNote.query.filter_by(user_id=user_id).count()
    favorite_count = Favorite.query.filter_by(user_id=user_id).count()

    # 已练独立题目数 / 系统题库总数
    practiced_q = db.session.query(StudyRecord.question_id).filter_by(
        user_id=user_id
    ).distinct().count()
    total_q = Question.query.count()

    return jsonify({
        'overall': {
            'total_practice': total,
            'correct_count': correct,
            'accuracy': round(overall_acc, 2),
            'total_time_minutes': round((total_time or 0) / 60, 1),
            'avg_time_seconds': round(avg_time or 0, 1),
            'error_count': error_count,
            'favorite_count': favorite_count,
            'practiced_questions': practiced_q,
            'total_questions': total_q,
            'coverage': round((practiced_q / total_q * 100), 2) if total_q else 0,
            'streak_days': _streak_days(user_id),
        },
        'period': {
            'days': days,
            'total_practice': period_total,
            'correct_count': period_correct,
            'accuracy': round(period_acc, 2),
        }
    })


# ============ 趋势（每日练习量 / 正确率 / 用时） ============

@analysis_bp.route('/trend/<int:user_id>', methods=['GET'])
@jwt_required()
def analyze_trend(user_id):
    _, err = _check_self(user_id)
    if err:
        return err

    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days - 1)
    start_date = datetime(start_date.year, start_date.month, start_date.day)

    daily = db.session.query(
        func.date(StudyRecord.practiced_at).label('date'),
        func.count(StudyRecord.id).label('total'),
        _correct_sum().label('correct'),
        func.avg(StudyRecord.used_time).label('avg_time')
    ).filter(
        StudyRecord.user_id == user_id,
        StudyRecord.practiced_at >= start_date
    ).group_by(func.date(StudyRecord.practiced_at)).order_by('date').all()

    by_date = {row.date: row for row in daily}

    dates, accuracies, avg_times, practice_counts = [], [], [], []
    cur = start_date.date()
    end = datetime.utcnow().date()
    while cur <= end:
        dates.append(cur.strftime('%Y-%m-%d'))
        row = by_date.get(cur)
        if row and row.total:
            practice_counts.append(int(row.total))
            accuracies.append(round((row.correct or 0) / row.total * 100, 1))
            avg_times.append(round(row.avg_time or 0, 1))
        else:
            practice_counts.append(0)
            accuracies.append(0)
            avg_times.append(0)
        cur += timedelta(days=1)

    # 趋势方向：对有效（>0）正确率做线性拟合
    valid = [(i, a) for i, a in enumerate(accuracies) if practice_counts[i] > 0]
    if len(valid) >= 2:
        xs = np.array([v[0] for v in valid], dtype=float)
        ys = np.array([v[1] for v in valid], dtype=float)
        slope = np.polyfit(xs, ys, 1)[0]
        direction = 'up' if slope > 0.1 else 'down' if slope < -0.1 else 'stable'
    else:
        direction = 'stable'

    return jsonify({
        'trend': {
            'direction': direction,
            'dates': dates,
            'accuracies': accuracies,
            'avg_times': avg_times,
            'practice_counts': practice_counts,
        }
    })


# ============ 学科维度 ============

@analysis_bp.route('/subject-analysis/<int:user_id>', methods=['GET'])
@jwt_required()
def subject_analysis(user_id):
    _, err = _check_self(user_id)
    if err:
        return err

    rows = db.session.query(
        Subject.id,
        Subject.name,
        func.count(StudyRecord.id).label('total'),
        _correct_sum().label('correct'),
        func.avg(StudyRecord.used_time).label('avg_time'),
    ).join(Question, StudyRecord.question_id == Question.id) \
     .join(Subject, Question.subject_id == Subject.id) \
     .filter(StudyRecord.user_id == user_id) \
     .group_by(Subject.id).all()

    data = []
    for r in rows:
        acc = (r.correct / r.total * 100) if r.total else 0
        data.append({
            'subject_id': r.id,
            'subject_name': r.name,
            'total_practice': int(r.total or 0),
            'correct_count': int(r.correct or 0),
            'accuracy': round(acc, 1),
            'avg_time': round(r.avg_time or 0, 1),
        })
    data.sort(key=lambda x: -x['total_practice'])
    return jsonify({'subjects': data})


# ============ 薄弱知识点（按标签） ============

@analysis_bp.route('/weak-points/<int:user_id>', methods=['GET'])
@jwt_required()
def weak_points(user_id):
    _, err = _check_self(user_id)
    if err:
        return err

    subject_id = request.args.get('subject_id', type=int)
    limit = request.args.get('limit', 10, type=int)

    err_q = db.session.query(StudyRecord.question_id).filter_by(
        user_id=user_id, is_correct=False
    ).distinct()
    if subject_id:
        err_q = err_q.join(Question, StudyRecord.question_id == Question.id) \
                     .filter(Question.subject_id == subject_id)
    err_qids = [q[0] for q in err_q.all()]

    if not err_qids:
        return jsonify({'weak_points': []})

    # 错得最多的标签 top N
    rows = db.session.query(
        Tag.id, Tag.name, Tag.category,
        func.count(QuestionTag.id).label('error_count'),
    ).join(QuestionTag, QuestionTag.tag_id == Tag.id) \
     .filter(QuestionTag.question_id.in_(err_qids)) \
     .group_by(Tag.id, Tag.name, Tag.category) \
     .order_by(desc('error_count')).limit(limit).all()

    result = []
    for tag in rows:
        # 该标签下所有题目，用户练过多少道、对多少道
        agg = db.session.query(
            func.count(StudyRecord.id).label('total'),
            _correct_sum().label('correct'),
        ).join(QuestionTag, QuestionTag.question_id == StudyRecord.question_id) \
         .filter(StudyRecord.user_id == user_id, QuestionTag.tag_id == tag.id).first()
        total = int(agg.total or 0)
        correct = int(agg.correct or 0)
        mastery = (correct / total * 100) if total else 0
        result.append({
            'tag_id': tag.id,
            'tag_name': tag.name,
            'tag_category': tag.category,
            'error_count': int(tag.error_count),
            'total_practice': total,
            'correct_count': correct,
            'mastery_level': round(mastery, 2),
            'recommend_practice': max(10 - total, 5),
        })
    return jsonify({'weak_points': result})


# ============ 题型分布 ============

@analysis_bp.route('/type-distribution/<int:user_id>', methods=['GET'])
@jwt_required()
def type_distribution(user_id):
    _, err = _check_self(user_id)
    if err:
        return err

    rows = db.session.query(
        Question.question_type,
        func.count(StudyRecord.id).label('total'),
        _correct_sum().label('correct'),
    ).join(StudyRecord, StudyRecord.question_id == Question.id) \
     .filter(StudyRecord.user_id == user_id) \
     .group_by(Question.question_type).all()

    data = []
    for r in rows:
        total = int(r.total or 0)
        correct = int(r.correct or 0)
        data.append({
            'question_type': r.question_type.value,
            'total': total,
            'correct': correct,
            'accuracy': round((correct / total * 100), 1) if total else 0,
        })
    return jsonify({'distribution': data})


# ============ 学习报告（周/月） ============

@analysis_bp.route('/report/<int:user_id>', methods=['GET'])
@jwt_required()
def generate_report(user_id):
    _, err = _check_self(user_id)
    if err:
        return err

    rtype = request.args.get('type', 'week')
    days = 7 if rtype == 'week' else 30 if rtype == 'month' else 7
    start = datetime.utcnow() - timedelta(days=days)

    total = StudyRecord.query.filter(
        StudyRecord.user_id == user_id,
        StudyRecord.practiced_at >= start,
    ).count()
    correct = StudyRecord.query.filter(
        StudyRecord.user_id == user_id,
        StudyRecord.is_correct.is_(True),
        StudyRecord.practiced_at >= start,
    ).count()
    accuracy = (correct / total * 100) if total else 0

    error_count = ErrorNote.query.filter_by(user_id=user_id, is_corrected=False).count()

    sub_rows = db.session.query(
        Subject.name,
        func.count(StudyRecord.id).label('count'),
        _correct_sum().label('correct'),
    ).join(Question, StudyRecord.question_id == Question.id) \
     .join(Subject, Question.subject_id == Subject.id) \
     .filter(StudyRecord.user_id == user_id, StudyRecord.practiced_at >= start) \
     .group_by(Subject.id, Subject.name).all()

    subjects_perf = [{
        'subject': r.name,
        'practice_count': int(r.count or 0),
        'accuracy': round((r.correct or 0) / r.count * 100, 1) if r.count else 0,
    } for r in sub_rows]

    active_days = db.session.query(
        func.date(StudyRecord.practiced_at)
    ).filter(
        StudyRecord.user_id == user_id,
        StudyRecord.practiced_at >= start,
    ).distinct().count()
    consistency = (active_days / days * 100) if days else 0

    suggestions = []
    if total == 0:
        suggestions.append('本周期还没有练习记录，先去刷上几题打个基础吧。')
    else:
        if accuracy < 60:
            suggestions.append(f'整体正确率 {round(accuracy,1)}%，建议先回顾错题、慢下来打牢基础。')
        elif accuracy < 80:
            suggestions.append(f'整体正确率 {round(accuracy,1)}%，可以适当增加中等难度题目以提升稳定性。')
        else:
            suggestions.append(f'整体正确率 {round(accuracy,1)}% 表现不错，可以挑战更高难度。')

    if error_count > 10:
        suggestions.append(f'当前有 {error_count} 道未消化的错题，建议优先去「错题回顾」专项练习。')
    elif error_count > 0:
        suggestions.append(f'有 {error_count} 道错题未消化，抽空在「错题回顾」里清一清。')

    if consistency < 50:
        suggestions.append(f'打卡天数 {active_days}/{days}，坚持每天少量练习比一次性刷大量更有效。')
    elif consistency < 80:
        suggestions.append(f'打卡天数 {active_days}/{days}，规律性不错，再保持几天就能形成习惯。')
    else:
        suggestions.append(f'打卡天数 {active_days}/{days}，学习节奏稳定，继续保持！')

    return jsonify({
        'report': {
            'type': rtype,
            'start_date': start.strftime('%Y-%m-%d'),
            'end_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'total_practice': total,
            'correct_count': correct,
            'accuracy': round(accuracy, 1),
            'error_count': error_count,
            'active_days': active_days,
            'consistency_score': round(consistency, 1),
            'subjects_performance': subjects_perf,
            'suggestions': suggestions,
        }
    })


# ============ 推荐题目（基于正确率挑难度） ============

@analysis_bp.route('/recommend/<int:user_id>', methods=['GET'])
@jwt_required()
def recommend_questions(user_id):
    _, err = _check_self(user_id)
    if err:
        return err

    subject_id = request.args.get('subject_id', type=int)
    count = min(request.args.get('count', 10, type=int), 20)

    user_acc = db.session.query(
        func.avg(case((StudyRecord.is_correct, 1.0), else_=0.0))
    ).filter_by(user_id=user_id).scalar() or 0

    if user_acc < 0.6:
        target = DifficultyLevel.EASY
        reason = '当前正确率偏低，先用简单题打底'
    elif user_acc < 0.8:
        target = DifficultyLevel.MEDIUM
        reason = '正确率稳定，挑战中等难度提升空间'
    else:
        target = DifficultyLevel.HARD
        reason = '掌握度高，推荐困难题继续突破'

    practiced_ids = [r[0] for r in db.session.query(StudyRecord.question_id)
                     .filter_by(user_id=user_id).distinct().all()]

    q = Question.query.filter(Question.difficulty == target)
    if subject_id:
        q = q.filter(Question.subject_id == subject_id)
    if practiced_ids:
        q = q.filter(~Question.id.in_(practiced_ids))

    recommended = q.limit(count).all()

    # 没题就放宽到所有难度
    if not recommended:
        q2 = Question.query
        if subject_id:
            q2 = q2.filter(Question.subject_id == subject_id)
        recommended = q2.limit(count).all()

    return jsonify({'questions': [{
        'id': q.id,
        'title': q.title,
        'subject_id': q.subject_id,
        'difficulty': q.difficulty.value,
        'recommend_reason': reason,
    } for q in recommended]})
