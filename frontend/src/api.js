// 独立的 axios 实例：不放在 Pinia store 里，避免 setup store 对返回值做响应式包装
// 导致 api.get / api.post 等方法被吞掉的坑。
import axios from 'axios'

const api = axios.create({
  // 相对路径：同源部署时走 nginx 反代到后端；本地开发由 vite proxy 转发
  baseURL: '/api',
  timeout: 10000
})

// 直接读 localStorage 的 token；store 里登入/登出时同步写 localStorage 即可。
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 401 触发的登出会在 store 里通过事件桥接（避免循环依赖）
let onUnauthorized = null
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof onUnauthorized === 'function') {
      onUnauthorized()
    }
    return Promise.reject(error)
  }
)

export default api
