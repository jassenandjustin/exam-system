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

### 数据库说明
表结构由后端 SQLAlchemy 在应用启动时自动创建（`db.create_all()`），
无需手动执行 SQL。默认管理员账号也在启动时自动播种：

- 用户名：`admin`
- 密码：`admin123`（生产环境请立即修改）

### Docker 部署
```bash
docker compose up -d --build
```

访问入口为前端容器 `http://<服务器IP>:15010`（静态页面 + `/api` 反向代理同源转发，
浏览器无需直连后端）。首次部署如曾用旧版 compose 启动过，需先删除旧的数据库卷以
重建与 ORM 一致的表结构：

```bash
docker compose down -v
docker compose up -d --build
```

## API文档
详见 `docs/api.md`