import React from 'react'
import { BarChart3, TrendingUp, TrendingDown, Building2, Calendar, CheckCircle } from 'lucide-react'

interface DashboardProps {
  data: {
    title: string
    client: {
      name: string
      sector: string
      summary: string
    }
    projects: Array<{
      id: string
      title: string
      description: string
      status: string
      completion?: number
    }>
    kpis: Array<{
      name: string
      value: string
      change: string
      trend: string
      icon: any
    }>
    valueOutcomes: Array<{
      type: string
      description: string
      amount: string
      timeframe: string
    }>
  }
}

export default function Dashboard({ data }: DashboardProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{data.title}</h1>
              <div className="flex items-center mt-2 text-sm text-gray-600">
                <Building2 className="h-4 w-4 mr-2" />
                <span>{data.client.name}</span>
                <span className="mx-2">•</span>
                <span>{data.client.sector}</span>
              </div>
            </div>
            <div className="flex items-center text-sm text-gray-500">
              <Calendar className="h-4 w-4 mr-2" />
              <span>Generated: {new Date().toLocaleDateString()}</span>
            </div>
          </div>
          <p className="mt-2 text-gray-700">{data.client.summary}</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* KPIs Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {data.kpis.map((kpi, index) => {
            const IconComponent = kpi.icon
            const isPositive = kpi.trend === 'up'

            return (
              <div key={index} className="bg-white p-6 rounded-lg shadow">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className={`p-2 rounded-lg ${
                      isPositive ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                    }`}>
                      <IconComponent className="h-5 w-5" />
                    </div>
                  </div>
                  <div className={`flex items-center text-sm font-medium ${
                    isPositive ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {isPositive ? (
                      <TrendingUp className="h-4 w-4 mr-1" />
                    ) : (
                      <TrendingDown className="h-4 w-4 mr-1" />
                    )}
                    {kpi.change}
                  </div>
                </div>
                <div className="mt-4">
                  <h3 className="text-sm font-medium text-gray-700">{kpi.name}</h3>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{kpi.value}</p>
                </div>
              </div>
            )
          })}
        </div>

        {/* Projects and Value Outcomes */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Active Projects */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <BarChart3 className="h-5 w-5 mr-2 text-blue-600" />
              Active Projects
            </h2>
            <div className="space-y-4">
              {data.projects.map((project, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900">{project.title}</h3>
                      <p className="text-sm text-gray-600 mt-1">{project.description}</p>
                      <div className="flex items-center mt-2">
                        <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                        <span className="text-sm text-gray-700">Status: {project.status}</span>
                      </div>
                    </div>
                  </div>
                  {project.completion && (
                    <div className="mt-3">
                      <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>Progress</span>
                        <span>{project.completion}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full" 
                          style={{ width: `${project.completion}%` }}
                        ></div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Value Outcomes */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <TrendingUp className="h-5 w-5 mr-2 text-green-600" />
              Value Delivered
            </h2>
            <div className="space-y-4">
              {data.valueOutcomes.map((outcome, index) => (
                <div key={index} className="border-l-4 border-green-500 pl-4 py-2">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium text-gray-900">{outcome.type}</h3>
                    <div className="text-right">
                      <div className="text-lg font-bold text-green-600">{outcome.amount}</div>
                      <div className="text-xs text-gray-500">{outcome.timeframe}</div>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{outcome.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="mt-8 bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Executive Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{data.projects.length}</div>
              <div className="text-sm text-gray-600">Active Projects</div>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">$2.3M+</div>
              <div className="text-sm text-gray-600">Value Delivered</div>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">94.2%</div>
              <div className="text-sm text-gray-600">Avg Efficiency</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
