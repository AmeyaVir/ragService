import React from 'react'
import { User, Bot, ExternalLink, Download, FileText, FileSpreadsheet, Presentation } from 'lucide-react'
import { Message } from '../../types'

interface MessageBubbleProps {
  message: Message
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.type === 'user'
  const isArtifact = message.type === 'artifact_generated'
  
  const getFileIcon = (mimeType: string) => {
    if (mimeType.includes('spreadsheet')) return <FileSpreadsheet className="h-4 w-4 text-green-600" />
    if (mimeType.includes('wordprocessing')) return <FileText className="h-4 w-4 text-blue-600" />
    if (mimeType.includes('presentation')) return <Presentation className="h-4 w-4 text-orange-600" />
    return <Download className="h-4 w-4" />
  }

  return (
    <div className={`chat-message ${isUser ? 'user-message' : isArtifact ? 'assistant-message' : 'assistant-message'}`}>
      <div className="flex items-start space-x-3">
        {/* FIX: Removed the explicit \n which caused the Unicode error in JSX/Babel parsing */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-blue-600 text-white' : 'bg-gray-600 text-white'
        }`}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </div>

        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-1">
            <span className="text-sm font-medium text-gray-900">
              {isUser ? 'You' : 'Assistant'}
            </span>
            <span className="text-xs text-gray-500">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          </div>

          {/* Render content text for standard messages */}
          {message.content && (
            <div className="text-gray-800 whitespace-pre-wrap">
              {message.content}
            </div>
          )}

          {/* NEW: Render Artifact Download Link */}
          {isArtifact && message.artifact && (
            <a 
              // The download URL is a relative API path which the browser will resolve correctly
              href={message.artifact.download_url} 
              target="_blank" 
              download 
              className="mt-3 inline-flex items-center space-x-2 text-sm font-medium text-purple-600 hover:text-purple-800 transition-colors bg-purple-50 p-3 rounded-lg border border-purple-200 shadow-sm"
              rel="noopener noreferrer"
            >
              {getFileIcon(message.artifact.mime_type)}
              <span>Download: {message.artifact.filename}</span>
            </a>
          )}

          {/* Render Sources */}
          {message.sources && message.sources.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="text-xs font-medium text-gray-700 mb-2">Sources:</div>
              <div className="space-y-1">
                {message.sources.map((source, index) => (
                  <div
                    key={index}
                    className="flex items-center space-x-2 text-xs text-gray-600"
                  >
                    <ExternalLink className="h-3 w-3" />
                    <span className="font-medium">{source.file}</span>
                    <span className="text-gray-400">•</span>
                    <span>{source.project}</span>
                    {source.score && (
                      <>
                        <span className="text-gray-400">•</span>
                        <span>Score: {(source.score * 100).toFixed(0)}%</span>
                      </>
                    )}
                  </div>
                ))}\n              </div>
            </div>
          )}\n        </div>
      </div>
    </div>
  )
}
