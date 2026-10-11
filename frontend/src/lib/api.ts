import axios from 'axios'

export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api', timeout: 12000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(undefined, (error) => {
  if (error.response?.status === 401) {
    localStorage.removeItem('token')
    if (location.pathname !== '/login') location.assign('/login')
  }
  return Promise.reject(error)
})

export const messageFrom = (error: any) => error.response?.data?.detail || error.message || 'Something went wrong'
