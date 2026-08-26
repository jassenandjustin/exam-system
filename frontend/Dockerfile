# 前端Dockerfile
FROM node:22-alpine AS build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 生产环境
FROM nginx:alpine AS production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
# 注意：nginx.conf将在docker-compose中通过volume挂载
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]