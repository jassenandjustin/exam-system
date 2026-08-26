r"""Create the exam rule question-type distribution table.

Run with:
    .\.venv\Scripts\python.exe migrate_add_exam_rule_type_distribution.py
"""
from app import app
from models import db


TABLE_NAME = 'exam_question_type_distributions'


if __name__ == '__main__':
    with app.app_context():
        inspector = db.inspect(db.engine)
        existed = TABLE_NAME in inspector.get_table_names()
        db.create_all()
        if existed:
            print(f'{TABLE_NAME} already exists')
        else:
            print(f'{TABLE_NAME} created')
