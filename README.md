# 智能刷题系统

## 项目简介
基于Vue+Flask+MySQL开发的智能刷题系统，支持多种题型、智能推荐、学习分析等功能。

## 技术栈
- 前端：Vue 3 + Vite + Pinia
- 后端：Flask + SQLAlchemy + JWT
- 数据库：MySQL
- 部署：Docker + Nginx

## 核心功能
- 题库管理（多题型、标签系统）
- 刷题模式（顺序、随机、错题、模拟考试）
- 学习分析（数据统计、薄弱点分析）
- 用户系统（多端同步）

## 快速开始
### 后端启动
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 前端启动
```bash
cd frontend
npm install
npm run dev
```

### 数据库初始化
```bash
cd database
mysql -u root -p < init.sql
```

## API文档
详见 `docs/api.md`