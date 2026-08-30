from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os
from dotenv import load_dotenv

from models import db, User, UserRole
import bcrypt
from routes.users import user_bp
from routes.questions import question_bp
from routes.practice import practice_bp
from routes.analysis import analysis_bp
from routes.taxonomy import taxonomy_bp
from routes.exam import exam_bp

load_dotenv()

app = Flask(__name__)

# 配置
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'sqlite:///exam_system.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# 初始化扩展（绑定 models.py 中定义的 db）
db.init_app(app)
jwt = JWTManager(app)
CORS(app, resources={r"/*": {"origins": "*"}})

# 注册蓝图
app.register_blueprint(user_bp, url_prefix='/api/users')
app.register_blueprint(question_bp, url_prefix='/api/questions')
app.register_blueprint(practice_bp, url_prefix='/api/practice')
app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
app.register_blueprint(taxonomy_bp, url_prefix='/api/taxonomy')
app.register_blueprint(exam_bp, url_prefix='/api/exam')

def _seed_default_admin():
    """首次部署时若不存在管理员则自动创建，保证管理后台可登录。

    播种失败不应导致应用无法启动（例如遗留库中存在与 ORM 枚举不兼容的
    脏数据时），记录警告后继续运行。
    """
    try:
        if User.query.filter_by(role=UserRole.ADMIN).first():
            return
        admin = User(
            username='admin',
            email='admin@exam.com',
            password_hash=bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode('utf-8'),
            role=UserRole.ADMIN,
        )
        db.session.add(admin)
        db.session.commit()
        print('Seeded default admin account: admin / admin123')
    except Exception as e:
        db.session.rollback()
        print(f'WARNING: default admin seeding failed (app continues to start): {e}')


# 创建数据库表
with app.app_context():
    db.create_all()
    _seed_default_admin()

# 健康检查
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Server is running'})

# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # 必须绑定 0.0.0.0：默认的 127.0.0.1 在容器里只对容器自身可见，
    # nginx 反代与端口发布都无法连进来
    app.run(debug=True, host='0.0.0.0', port=15000)
