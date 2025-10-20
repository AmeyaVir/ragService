const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class ApiService {
  private baseUrl: string
  private token: string | null

  constructor() {
    this.baseUrl = API_BASE_URL
    this.token = localStorage.getItem('access_token')
  }

  private async request(endpoint: string, options: RequestInit = {}): Promise<any> {
    const url = `${this.baseUrl}${endpoint}`
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (!response.ok) {
      // MODIFIED: Include status in error for better debugging in frontend logic
      const errorDetail = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(`HTTP error! status: ${response.status}. Detail: ${errorDetail.detail}`)
    }

    return response.json()
  }

  // Auth endpoints
  async login(username: string, password: string) {
    const response = await this.request('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })

    this.token = response.access_token
    localStorage.setItem('access_token', this.token!)

    return response
  }

  async logout() {
    await this.request('/api/v1/auth/logout', { method: 'POST' })
    this.token = null
    localStorage.removeItem('access_token')
  }

  async getCurrentUser() {
    return this.request('/api/v1/auth/me')
  }

  // Project endpoints
  async getProjects() {
    return this.request('/api/v1/projects/')
  }

  async getProject(projectId: string) {
    return this.request(`/api/v1/projects/${projectId}`)
  }

  // Chat endpoints
  async sendMessage(message: string, projectContext: any) {
    return this.request('/api/v1/chat/send', {
      method: 'POST',
      body: JSON.stringify({ message, project_context: projectContext }),
    })
  }

  async getChatHistory(sessionId: string) {
    return this.request(`/api/v1/chat/history/${sessionId}`)
  }

  // NEW: Google OAuth endpoints are handled via direct browser redirect (see App.tsx)
}

export const apiService = new ApiService()
export default apiService
