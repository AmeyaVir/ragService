import React, { useState, useEffect } from 'react'
import { ChevronDown, Folder } from 'lucide-react'
import apiService from '../../services/api'
import { Project } from '../../types' // Assuming Project type is imported

interface ProjectSelectorProps {
  selectedProject: string
  onProjectChange: (projectId: string) => void
}

export default function ProjectSelector({ selectedProject, onProjectChange }: ProjectSelectorProps) {
  const [projects, setProjects] = useState<Project[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      const projectsData = await apiService.getProjects()
      setProjects(projectsData)

      // CRITICAL FIX: Only set the default if a project hasn't been selected YET.
      // This prevents the initial load from firing repeated state updates 
      // if selectedProject starts as an empty string.
      if (projectsData.length > 0 && selectedProject === '') {
        // Ensure we pass the ID as a string, matching Qdrant indexing
        onProjectChange(String(projectsData[0].id))
      }
    } catch (error) {
      console.error('Failed to load projects:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Helper to find the project data for display
  const selectedProjectData = projects.find(p => String(p.id) === selectedProject)

  if (isLoading) {
    return (
      <div className="flex items-center space-x-2 text-gray-500">
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-500"></div>
        <span className="text-sm">Loading projects...</span>
      </div>
    )
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 bg-white border border-gray-300 rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
      >
        <Folder className="h-4 w-4" />
        <span>
          {selectedProjectData ? selectedProjectData.name : 'Select Project'}
        </span>
        <ChevronDown className="h-4 w-4" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-1 w-64 bg-white border border-gray-200 rounded-md shadow-lg z-10">
          <div className="py-1">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => {
                  // Ensure ID is passed as a string
                  onProjectChange(String(project.id)) 
                  setIsOpen(false)
                }}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 ${
                  selectedProject === String(project.id) ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                }`}
              >
                <div className="font-medium">{project.name}</div>
                <div className="text-xs text-gray-500 truncate">
                  {project.description}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
