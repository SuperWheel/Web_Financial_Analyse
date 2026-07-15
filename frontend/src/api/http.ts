import axios from 'axios'
import { ElMessage } from 'element-plus'

// 全局 axios 实例：baseURL 留空，走 Vite 的 /api 代理
const http = axios.create({
  baseURL: '',
  timeout: 15000,
})

// 响应拦截：统一把后端错误 detail 透出给用户
http.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail =
      error?.response?.data?.detail || error?.message || '请求失败'
    ElMessage.error(typeof detail === 'string' ? detail : '请求失败')
    return Promise.reject(error)
  }
)

export default http
