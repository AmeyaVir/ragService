import React, { useState, useEffect, useRef } from 'react'
import { Send, Loader2 } from 'lucide-react'
import MessageBubble from './MessageBubble'
import MicrositePreview from './MicrositePreview'
import { Message, User } from '../../types'

interface ChatInterfaceProps {
  selectedProject: string // CRITICAL: This MUST be the numeric ID (e.g., "6"), not the name ("Diatomite")
  user: User | null
}

export default function ChatInterface({ selectedProject, user }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [websocket, setWebsocket] = useState<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Initialize WebSocket connection
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
    const sessionId = `session_${Date.now()}`
    const ws = new WebSocket(`${wsUrl}/ws/${sessionId}`)

    ws.onopen = () => {
      console.log('WebSocket connected')
      setWebsocket(ws)
      // Send initial welcome/system message to user
      const initialMessage: Message = {
        id: `sys_msg_${Date.now()}`,
        type: 'assistant',
        content: `Hello ${user?.name || 'User'}! I'm your PMO Assistant. Ask me about your projects or request an artifact (e.g., "Generate an Excel risk log").`,
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, initialMessage])
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'response') {
        // Standard chat response (could be the result of a normal query or a function call confirmation)
        const assistantMessage: Message = {
          id: `msg_${Date.now()}_resp`,
          type: 'assistant',
          content: data.response,
          timestamp: new Date().toISOString(),
          sources: data.sources,
          microsite: data.microsite
        }

        setMessages(prev => [...prev, assistantMessage])
        setIsLoading(false)
      } else if (data.type === 'artifact_generated') {
        // NEW: Artifact message sent directly from the artifacts endpoint (via manager.send_message)
        const artifactMessage: Message = {
          id: `msg_${Date.now()}_art`,
          type: 'artifact_generated',
          content: `Your requested artifact, "${data.artifact.filename}", is ready! Click the link below to download.`,
          timestamp: new Date().toISOString(),
          artifact: data.artifact
        }
        
        setMessages(prev => [...prev, artifactMessage])

      } else if (data.type === 'error') {
        const errorMessage: Message = {
          id: `msg_${Date.now()}_err`,
          type: 'assistant',
          content: data.error,
          timestamp: new Date().toISOString()
        }

        setMessages(prev => [...prev, errorMessage])
        setIsLoading(false)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setIsLoading(false)
    }

    return () => {
      ws.close()
    }
  }, [user]) // Re-run effect if user changes (auth state)

  const sendMessage = async () => {
    if (!inputMessage.trim() || !websocket || isLoading) return

    const userMessage: Message = {
      id: `msg_${Date.now()}_user`,
      type: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    
    // CRITICAL FIX: Ensure the project ID is passed as a string and ONLY if it exists.
    const projectIds = selectedProject ? [String(selectedProject)] : [];

    // Send message via WebSocket
    websocket.send(JSON.stringify({
      message: inputMessage,
      project_context: {
        tenant_id: user?.tenant_id || 'demo',
        project_ids: projectIds, // Using the ensured array of string IDs
        selected_project: selectedProject
      },
      type: 'chat'
    }))

    setInputMessage('')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-[600px]">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-lg font-medium">Welcome to Analytics RAG Platform</p>
            <p className="text-sm mt-2">
              Ask questions about your projects, KPIs, or request dashboard generation
            </p>
            <div className="mt-4 text-sm text-gray-400">
              Example queries:
              <ul className="mt-2 space-y-1">
                <li>• "Generate an Excel risk log for the Stone Hill project"</li>
                <li>• "Draft a Word status report based on the latest documents"</li>
                <li>• "What is the predicted spud success rate?"</li>
              </ul>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id}>
            <MessageBubble message={message} />
            {/* Microsite is rendered below the bubble if present */}
            {message.microsite && (
              <MicrositePreview micrositeData={message.microsite} />
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center space-x-2 text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Processing your request...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex space-x-2">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={selectedProject 
              ? `Ask about ${selectedProject} or request insights (e.g., 'Generate risk log')...`
              : "Ask about your projects or request insights..."
            }
            className="flex-1 resize-none border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={2}
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>

        {selectedProject && (
          <div className="mt-2 text-xs text-gray-500">
            Active project: <span className="font-medium">{selectedProject}</span>
          </div>
        )}
      </div>
    </div>
  )
}
