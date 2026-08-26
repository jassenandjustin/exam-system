-- 智能刷题系统数据库初始化脚本

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS exam_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE exam_system;

-- 创建表结构
SET foreign_key_checks = 0;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'teacher', 'admin') DEFAULT 'student',
    avatar VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 学科表
CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    icon VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 章节表
CREATE TABLE IF NOT EXISTS chapters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    order_num INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    INDEX idx_subject_id (subject_id),
    INDEX idx_order_num (order_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 标签表
CREATE TABLE IF NOT EXISTS tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 知识点表
CREATE TABLE IF NOT EXISTS knowledge_points (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    subject_id INT NOT NULL,
    parent_id INT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES knowledge_points(id) ON DELETE SET NULL,
    INDEX idx_subject_id (subject_id),
    INDEX idx_parent_id (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 知识点标签关联表
CREATE TABLE IF NOT EXISTS knowledge_point_tags (
    knowledge_point_id INT,
    tag_id INT,
    PRIMARY KEY (knowledge_point_id, tag_id),
    FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 题目表
CREATE TABLE IF NOT EXISTS questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject_id INT NOT NULL,
    chapter_id INT,
    question_type ENUM('single_choice', 'multiple_choice', 'fill_in_blank', 'true_false', 'subjective') NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    options JSON,
    correct_answer JSON NOT NULL,
    explanation TEXT,
    difficulty ENUM('easy', 'medium', 'hard') DEFAULT 'medium',
    score FLOAT DEFAULT 2.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_subject_id (subject_id),
    INDEX idx_chapter_id (chapter_id),
    INDEX idx_question_type (question_type),
    INDEX idx_difficulty (difficulty)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 题目标签关联表
CREATE TABLE IF NOT EXISTS question_tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    tag_id INT NOT NULL,
    UNIQUE KEY uq_question_tag (question_id, tag_id),
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 学习记录表
CREATE TABLE IF NOT EXISTS study_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    question_id INT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    answer JSON,
    used_time FLOAT,
    practiced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_study_record (user_id, question_id, practiced_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_question_id (question_id),
    INDEX idx_practiced_at (practiced_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 错题本表
CREATE TABLE IF NOT EXISTS error_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    question_id INT NOT NULL,
    note_content TEXT,
    is_corrected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_question_id (question_id),
    INDEX idx_is_corrected (is_corrected)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 收藏表
CREATE TABLE IF NOT EXISTS favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    question_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_favorite (user_id, question_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_question_id (question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 考试记录表
CREATE TABLE IF NOT EXISTS exam_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_score FLOAT NOT NULL,
    obtained_score FLOAT NOT NULL,
    duration INT NOT NULL,
    correct_count INT DEFAULT 0,
    total_questions INT DEFAULT 0,
    exam_type VARCHAR(50),
    started_at TIMESTAMP NOT NULL,
    submitted_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 考试答案表
CREATE TABLE IF NOT EXISTS exam_answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_record_id INT NOT NULL,
    question_id INT NOT NULL,
    user_answer JSON,
    is_correct BOOLEAN NOT NULL,
    score FLOAT DEFAULT 0,
    FOREIGN KEY (exam_record_id) REFERENCES exam_records(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    INDEX idx_exam_record_id (exam_record_id),
    INDEX idx_question_id (question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 启用外键检查
SET foreign_key_checks = 1;

-- 插入基础数据

-- 创建默认管理员用户（密码: admin123）
INSERT IGNORE INTO users (username, email, password_hash, role) VALUES
('admin', 'admin@exam.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.S6GqPqPqPqPqPq', 'admin');

-- 插入示例学科
INSERT IGNORE INTO subjects (name, description, icon) VALUES
('数学', '数学学科题库', '📐'),
('英语', '英语学科题库', '🇬🇧'),
('物理', '物理学科题库', '⚡'),
('化学', '化学学科题库', '🧪');

-- 插入示例标签
INSERT IGNORE INTO tags (name, category) VALUES
('基础知识', 'knowledge_point'),
('重点难点', 'knowledge_point'),
('高频考点', 'knowledge_point'),
('简单', 'difficulty'),
('中等', 'difficulty'),
('困难', 'difficulty'),
('2024年', 'year'),
('高考', 'exam_type'),
('中考', 'exam_type'),
('易错题', 'characteristic');

-- 插入示例题目（数学）
INSERT IGNORE INTO questions (subject_id, question_type, title, options, correct_answer, explanation, difficulty, score) VALUES
(1, 'single_choice', '下列哪个数是质数？',
 '["15", "21", "29", "35"]',
 '["29"]',
 '质数是指大于1且只能被1和自身整除的数。29是质数，其他都是合数。',
 'easy', 2.0),

(1, 'multiple_choice', '下列哪些是二次函数的性质？（多选）',
 '["图像是抛物线", "最高次数为2", "导数是常数", "有对称轴"]',
 '["图像是抛物线", "最高次数为2", "有对称轴"]',
 '二次函数的图像是抛物线，最高次数为2，有对称轴。导数不是常数而是线性函数。',
 'medium', 3.0),

(1, 'fill_in_blank', '一元二次方程 ax² + bx + c = 0 的求根公式是：x = ________',
 NULL,
 '["(-b ± √(b²-4ac)) / 2a"]',
 '一元二次方程的标准求根公式',
 'easy', 2.0);

-- 插入示例用户学习记录
INSERT IGNORE INTO study_records (user_id, question_id, is_correct, answer, used_time) VALUES
(1, 1, 1, '["29"]', 45.6),
(1, 2, 0, '["图像是抛物线", "最高次数为2"]', 120.3);

-- 插入示例错题记录
INSERT IGNORE INTO error_notes (user_id, question_id, note_content) VALUES
(1, 2, '需要记住二次函数的完整性质，特别是导数部分。');

-- 插入示例收藏
INSERT IGNORE INTO favorites (user_id, question_id) VALUES
(1, 1),
(1, 3);

-- 显示创建完成信息
SELECT '数据库初始化完成！' as message;
SELECT CONCAT('创建了 ', ROW_COUNT(), ' 个表') as table_count;