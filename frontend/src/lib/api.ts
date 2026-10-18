import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export const api = axios.create({ baseURL, timeout: 12000 })

let refreshPromise: Promise<string> | null = null

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as any
    const url = String(originalRequest?.url || '')
    const isAuthRequest = url.includes('/auth/login') || url.includes('/auth/refresh')

    if (error.response?.status !== 401 || !originalRequest || isAuthRequest || originalRequest._retry) {
      return Promise.reject(error)
    }

    const refreshToken = localStorage.getItem('refresh_token')

    if (!refreshToken) {
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      if (!location.hash.startsWith('#/login')) location.hash = '#/login'
      return Promise.reject(error)
    }

    originalRequest._retry = true

    try {
      if (!refreshPromise) {
        refreshPromise = axios.post(
          `${baseURL}/auth/refresh`,
          null,
          { params: { refresh_token: refreshToken }, timeout: 12000 }
        ).then((response) => {
          const accessToken = response.data.access_token
          const newRefreshToken = response.data.refresh_token

          if (!accessToken || !newRefreshToken) {
            throw new Error('The server did not return valid session tokens.')
          }

          localStorage.setItem('token', accessToken)
          localStorage.setItem('refresh_token', newRefreshToken)
          return accessToken
        }).finally(() => {
          refreshPromise = null
        })
      }

      const newAccessToken = await refreshPromise
      originalRequest.headers = originalRequest.headers || {}
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
      return api(originalRequest)
    } catch (refreshError) {
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      if (!location.hash.startsWith('#/login')) location.hash = '#/login'
      return Promise.reject(refreshError)
    }
  }
)


export const messageFrom = (err: unknown): string => {
    if (typeof err === 'string') return err
    if (err && typeof err === 'object' && 'response' in err) {
        const response = (err as { response?: { data?: { detail?: unknown; message?: unknown } } }).response
        const detail = response?.data?.detail
        const message = response?.data?.message
        if (typeof detail === 'string') return detail
        if (Array.isArray(detail)) {
            return detail.map((item: unknown) => {
                if (typeof item === 'string') return item
                if (item && typeof item === 'object' && 'msg' in item) {
                    const msg = (item as { msg?: unknown }).msg
                    const loc = 'loc' in item ? (item as { loc?: unknown }).loc : undefined
                    const location = Array.isArray(loc) ? loc.filter((part) => part !== 'body').join(' → ') : ''
                    return `${location ? `${location}: ` : ''}${String(msg ?? 'Invalid input')}`
                }
                return 'Invalid input'
            }).join('; ')
        }
        if (typeof message === 'string') return message
    }
    if (err instanceof Error) return err.message
    return 'Something went wrong. Please try again.'
}
