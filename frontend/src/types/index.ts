export interface User {
  id: string // MODIFIED: In the demo, this now maps to the DB ID (e.g., '1')
  username: string
  name: string
  email: string
  tenant_id: string
}

export interface Project {
  id: string
  name: string
  description: string
  status: string
  folder_id: string
  created_at: string
  updated_at: string
}

// NEW: Artifact Metadata Interface
export interface ArtifactData {
  id: string
  filename: string
  mime_type: string
  download_url: string
}

export interface Message {
  id: string
  // Added new types for conversational response and artifact message
  type: 'user' | 'assistant' | 'artifact_generated' | 'error' 
  content: string // Used for 'user' and 'assistant' text responses
  timestamp: string
  sources?: Source[]
  microsite?: MicrositeData
  artifact?: ArtifactData // NEW: Field for structured artifact files
}

export interface Source {
  file: string
  project: string
  type: string
  score?: number
}

export interface MicrositeData {
  title: string
  url: string
  data: any
}
