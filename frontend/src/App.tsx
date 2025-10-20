import React, { useState, useEffect } from 'react'
import ChatInterface from './components/Chat/ChatInterface'
import AuthWrapper from './components/Auth/AuthWrapper'
import ProjectSelector from './components/Dashboard/ProjectSelector'
import { MessageCircle, Database, Settings } from 'lucide-react'

interface User {
  id: string
  name: string
  email: string
}

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    // Check for existing authentication
    const token = localStorage.getItem('access_token')
    if (token) {
      setIsAuthenticated(true)
      // NOTE: In a real app, this should fetch the /api/v1/auth/me endpoint
      setUser({
        id: '1',
        name: 'Demo User',
        email: 'demo@example.com'
      })
    }
  }, [])

  // NEW: Handle OAuth callback redirect (from /api/v1/auth/google/callback)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const authStatus = urlParams.get('google_auth')
    const detail = urlParams.get('detail')

    if (authStatus === 'success') {
      alert('Google Drive linked successfully! You can now sync your projects.')
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname)
    } else if (authStatus === 'error') {
      alert(`Google Drive linking failed: ${detail}`)
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname)
    }
  }, [])

  if (!isAuthenticated) {
    return (
      <AuthWrapper 
        onAuthSuccess={(user) => {
          setUser(user)
          setIsAuthenticated(true)
        }}
      />
    )
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Database className="h-8 w-8 text-blue-600 mr-3" />
              <h1 className="text-xl font-semibold text-gray-900">
                Analytics RAG Platform
              </h1>
            </div>

            <div className="flex items-center space-x-4">
              <ProjectSelector 
                selectedProject={selectedProject}
                onProjectChange={setSelectedProject}
              />

              <div className="text-sm text-gray-700">
                Welcome, {user?.name}
              </div>

              <button
                onClick={() => {
                  localStorage.removeItem('access_token')
                  setIsAuthenticated(false)
                  setUser(null)
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                <Settings className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Chat Interface - Main Area */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-center">
                  <MessageCircle className="h-5 w-5 text-blue-600 mr-2" />
                  <h2 className="text-lg font-medium text-gray-900">
                    Executive Chat Assistant
                  </h2>
                </div>
                <p className="mt-1 text-sm text-gray-600">
                  Ask questions about your projects, KPIs, and generate insights
                </p>
              </div>

              <ChatInterface 
                selectedProject={selectedProject}
                user={user}
              />
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Quick Actions
              </h3>

              <div className="space-y-3">
                <button 
                  onClick={() => window.location.href = 'http://localhost:8000/api/v1/auth/google/login'}
                  className="w-full text-left px-3 py-2 text-sm text-blue-700 bg-blue-50 hover:bg-blue-100 rounded border border-blue-200"
                >
                  Link Google Drive (OAuth)
                </button>
                
                <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded">
                  View Project Summary
                </button>
                <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded">
                  Generate KPI Report
                </button>
                <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded">
                  Create Microsite
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
