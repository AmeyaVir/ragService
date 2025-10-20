import React, { useState } from 'react'
import { ExternalLink, Maximize2, Minimize2 } from 'lucide-react'
import { MicrositeData } from '../../types'

interface MicrositePreviewProps {
  micrositeData: MicrositeData
}

export default function MicrositePreview({ micrositeData }: MicrositePreviewProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const micrositeUrl = micrositeData.url || 'http://localhost:5173'

  return (
    <div className={`mt-4 border border-gray-200 rounded-lg overflow-hidden ${
      isExpanded ? 'fixed inset-4 z-50 bg-white' : ''
    }`}>
      <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <ExternalLink className="h-4 w-4 text-gray-600" />
          <span className="text-sm font-medium text-gray-900">
            Generated Dashboard
          </span>
          <span className="text-xs text-gray-500">
            {micrositeData.title}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-gray-600 hover:text-gray-900 p-1"
          >
            {isExpanded ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </button>

          <a
            href={micrositeUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 text-xs font-medium"
          >
            Open Full View
          </a>
        </div>
      </div>

      <div className={isExpanded ? 'h-full' : 'h-96'}>
        <iframe
          src={micrositeUrl}
          className="w-full h-full border-0"
          title="Generated Microsite"
          sandbox="allow-scripts allow-same-origin"
        />
      </div>

      {isExpanded && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 -z-10"
          onClick={() => setIsExpanded(false)}
        />
      )}
    </div>
  )
}
