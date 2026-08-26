from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

db = SQLAlchemy()

class UserRole(enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

class QuestionType(enum.Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_BLANK = "fill_in_blank"
    TRUE_FALSE = "true_false"
    SUBJECTIVE = "subjective"

class DifficultyLevel(enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class ExamType(enum.Enum):
    QUICK = "quick"                # 快速练习
    STANDARD = "standard"          # 标准考试
    COMPREHENSIVE = "comprehensive" # 综合考试
    CUSTOM = "custom"              # 自定义考试

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.STUDENT)
    avatar = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # 关系
    study_records = db.relationship('StudyRecord', backref='user', lazy=True, cascade='all, delete-orphan')
    error_notes = db.relationship('ErrorNote', backref='user', lazy=True, cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='user', lazy=True, cascade='all, delete-orphan')
    exam_records = db.relationship('ExamRecord', backref='user', lazy=True, cascade='all, delete-orphan')

class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    chapters = db.relationship('Chapter', backref='subject', lazy=True, cascade='all, delete-orphan')
    questions = db.relationship('Question', backref='subject', lazy=True)

class Chapter(db.Model):
    __tablename__ = 'chapters'

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    order_num = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    questions = db.relationship('Question', backref='chapter', lazy=True)

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # knowledge_point, difficulty, year, region
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    question_tags = db.relationship('QuestionTag', backref='tag', lazy=True, cascade='all, delete-orphan')

class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=True)
    question_type = db.Column(db.Enum(QuestionType), nullable=False)
    title = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=True)  # 题干详细内容
    options = db.Column(db.JSON, nullable=True)  # 选择题选项
    correct_answer = db.Column(db.JSON, nullable=False)  # 正确答案
    explanation = db.Column(db.Text, nullable=True)  # 解析
    difficulty = db.Column(db.Enum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    score = db.Column(db.Float, default=2.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # 关系
    question_tags = db.relationship('QuestionTag', backref='question', lazy=True, cascade='all, delete-orphan')
    study_records = db.relationship('StudyRecord', backref='question', lazy=True)
    error_notes = db.relationship('ErrorNote', backref='question', lazy=True)
    favorites = db.relationship('Favorite', backref='question', lazy=True)

class QuestionTag(db.Model):
    __tablename__ = 'question_tags'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('question_id', 'tag_id', name='uq_question_tag'),)

class StudyRecord(db.Model):
    __tablename__ = 'study_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    answer = db.Column(db.JSON, nullable=True)  # 用户答案
    used_time = db.Column(db.Float, nullable=True)  # 答题用时（秒）
    practiced_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'question_id', 'practiced_at', name='uq_study_record'),)

class ErrorNote(db.Model):
    __tablename__ = 'error_notes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    note_content = db.Column(db.Text, nullable=True)
    is_corrected = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Favorite(db.Model):
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'question_id', name='uq_favorite'),)

class Exam(db.Model):
    __tablename__ = 'exams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    exam_type = db.Column(db.Enum(ExamType), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)  # 考试时长（分钟）
    passing_score = db.Column(db.Float, default=0.0)          # 及格分数
    total_score = db.Column(db.Float, default=0.0)            # 总分
    total_questions = db.Column(db.Integer, default=0)         # 总题数
    is_published = db.Column(db.Boolean, default=False)        # 是否发布
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    creator = db.relationship('User', backref='created_exams')
    question_rules = db.relationship('ExamQuestionRule', backref='exam', lazy=True, cascade='all, delete-orphan')
    exam_questions = db.relationship('ExamQuestion', backref='exam', lazy=True, cascade='all, delete-orphan')
    records = db.relationship('ExamRecord', backref='exam_template', lazy=True)


class ExamQuestionRule(db.Model):
    __tablename__ = 'exam_question_rules'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=True)  # 可空=整科
    difficulty = db.Column(db.Enum(DifficultyLevel), nullable=True)  # 可空=不限难度
    question_count = db.Column(db.Integer, nullable=False)           # 抽取题数
    order_num = db.Column(db.Integer, default=0)

    # 关系
    subject = db.relationship('Subject')
    chapter = db.relationship('Chapter')
    type_distributions = db.relationship(
        'ExamQuestionTypeDistribution',
        backref='rule',
        lazy=True,
        cascade='all, delete-orphan'
    )


class ExamQuestionTypeDistribution(db.Model):
    __tablename__ = 'exam_question_type_distributions'

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('exam_question_rules.id'), nullable=False)
    question_type = db.Column(db.Enum(QuestionType), nullable=False)
    count = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('rule_id', 'question_type', name='uq_rule_question_type'),
    )


class ExamQuestion(db.Model):
    __tablename__ = 'exam_questions'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    order_num = db.Column(db.Integer, default=0)
    score = db.Column(db.Float, nullable=False, default=2.0)

    # 关系
    question = db.relationship('Question')


class ExamRecord(db.Model):
    __tablename__ = 'exam_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=True)  # 关联试卷模板（可空兼容旧数据）
    total_score = db.Column(db.Float, nullable=False)
    obtained_score = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # 考试时长（秒）
    correct_count = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    exam_type = db.Column(db.String(50), nullable=True)  # 模拟考试类型
    started_at = db.Column(db.DateTime, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True)

    # 关系
    exam_answers = db.relationship('ExamAnswer', backref='exam_record', lazy=True, cascade='all, delete-orphan')

class ExamAnswer(db.Model):
    __tablename__ = 'exam_answers'

    id = db.Column(db.Integer, primary_key=True)
    exam_record_id = db.Column(db.Integer, db.ForeignKey('exam_records.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    user_answer = db.Column(db.JSON, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=False)
    score = db.Column(db.Float, default=0)

class KnowledgePoint(db.Model):
    __tablename__ = 'knowledge_points'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('knowledge_points.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    children = db.relationship('KnowledgePoint', backref=db.backref('parent', remote_side=[id]))
    tags = db.relationship('Tag', secondary='knowledge_point_tags', backref='knowledge_points')

knowledge_point_tags = db.Table('knowledge_point_tags',
    db.Column('knowledge_point_id', db.Integer, db.ForeignKey('knowledge_points.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)