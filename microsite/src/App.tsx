import React, { useState, useEffect } from 'react'
import Dashboard from './components/Dashboard'
import { BarChart3, TrendingUp, DollarSign, Activity } from 'lucide-react'

// Sample data - would be fetched from API in production
const sampleData = {
  title: "Analytics Dashboard - Demo Client",
  client: {
    name: "Demo Oil & Gas Company",
    sector: "Oil & Gas",
    summary: "Comprehensive analytics across 3 active projects"
  },
  projects: [
    {
      id: "mars_project",
      title: "MARS Analytics Platform",
      description: "AI-driven production optimization and predictive maintenance system",
      status: "Active",
      completion: 85
    },
    {
      id: "shell_optimization", 
      title: "Production Optimization Initiative",
      description: "Advanced analytics for production efficiency improvements",
      status: "Active", 
      completion: 72
    }
  ],
  kpis: [
    {
      name: "Production Efficiency",
      value: "94.2%",
      change: "+2.8%",
      trend: "up",
      icon: TrendingUp
    },
    {
      name: "Cost Reduction",
      value: "$2.3M",
      change: "+15%", 
      trend: "up",
      icon: DollarSign
    },
    {
      name: "Downtime Reduction",
      value: "18%",
      change: "-5.2%",
      trend: "down",
      icon: Activity
    },
    {
      name: "Data Quality Score",
      value: "96.7%",
      change: "+1.1%",
      trend: "up", 
      icon: BarChart3
    }
  ],
  valueOutcomes: [
    {
      type: "Cost Savings",
      description: "Reduced operational costs through predictive maintenance and optimization",
      amount: "$2.3M",
      timeframe: "Annual"
    },
    {
      type: "Efficiency Gain",
      description: "Improved production efficiency across all monitored facilities",
      amount: "2.8%",
      timeframe: "YTD"
    },
    {
      type: "Risk Reduction", 
      description: "Decreased unplanned downtime through predictive analytics",
      amount: "18%",
      timeframe: "Quarterly"
    }
  ]
}

function App() {
  const [dashboardData, setDashboardData] = useState(sampleData)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    // In production, this would fetch data from the main API
    // based on URL parameters or API calls
    const urlParams = new URLSearchParams(window.location.search)
    const dataParam = urlParams.get('data')

    if (dataParam) {
      try {
        const parsedData = JSON.parse(decodeURIComponent(dataParam))
        setDashboardData(parsedData)
      } catch (error) {
        console.error('Failed to parse dashboard data:', error)
      }
    }
  }, [])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return <Dashboard data={dashboardData} />
}

export default App
