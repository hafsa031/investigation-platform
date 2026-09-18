import { useState, useEffect } from 'react'
import axios from 'axios'
import { Card, Statistic, RecentActivity } from '../components'

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalCases: 0,
    totalEvidence: 0,
    totalFindings: 0,
    totalIOCs: 0
  })
  const [recentActivity, setRecentActivity] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        // In a real app, these would be actual API calls
        // For now, we'll simulate with mock data
        setStats({
          totalCases: 12,
          totalEvidence: 45,
          totalFindings: 78,
          totalIOCs: 156
        })
        
        setRecentActivity([
          {
            id: 1,
            type: 'case',
            title: 'Case #CASE-0012 created',
            description: 'New investigation initiated for suspicious network activity',
            timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
            user: 'Analyst Smith'
          },
          {
            id: 2,
            type: 'evidence',
            title: 'Evidence uploaded: network.pcap',
            description: 'Packet capture from DMZ segment analyzed',
            timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
            user: 'Intern 4'
          },
          {
            id: 3,
            type: 'finding',
            title: 'IOC correlation completed',
            description: 'Found 3 malicious IPs associated with known threat actor',
            timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
            user: 'Automated System'
          }
        ])
      } catch (err) {
        setError('Failed to load dashboard data')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    loadDashboardData()
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <Statistic label="Total Cases" value="--" variant="info" />
          <Statistic label="Total Evidence" value="--" variant="success" />
          <Statistic label="Findings" value="--" variant="warning" />
          <Statistic label="IOCs Extracted" value="--" variant="danger" />
        </div>
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Recent Activity</h2>
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="animate-pulse">
                <div className="flex items-start space-x-3">
                  <div className="h-3 w-3 bg-gray-300 rounded-full mt-1"></div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium text-gray-900">Loading activity...</h3>
                      <p className="text-xs text-gray-500">Just now</p>
                    </div>
                    <p className="text-sm text-gray-600">Processing recent activities...</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return <div className="p-4 bg-red-50 border border-red-200 rounded-md text-red-800">{error}</div>
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Statistic label="Total Cases" value={stats.totalCases} variant="info" />
        <Statistic label="Total Evidence" value={stats.totalEvidence} variant="success" />
        <Statistic label="Findings" value={stats.totalFindings} variant="warning" />
        <Statistic label="IOCs Extracted" value={stats.totalIOCs} variant="danger" />
      </div>
      
      <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-2">
        <Card title="Recent Activity">
          {recentActivity.length > 0 ? (
            <div className="space-y-4">
              {recentActivity.map(activity => (
                <div key={activity.id} className="border-b pb-4 last:border-b-0 last:pb-0">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 h-8 w-8 bg-gray-100 rounded-full flex items-center justify-center text-sm font-medium">
                      {activity.type === 'case' ? '📁' : activity.type === 'evidence' ? '📎' : activity.type === 'finding' ? '🔍' : '⚙️'}
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-medium text-gray-900">{activity.title}</h3>
                        <p className="text-xs text-gray-500">{new Date(activity.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</p>
                      </div>
                      <p className="text-sm text-gray-600">{activity.description}</p>
                      <p className="text-xs text-gray-400">By {activity.user}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-8 text-gray-500">No recent activity</p>
          )}
        </Card>
        
        <Card title="System Status">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">API Connection</span>
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded-full">Connected</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Forensic Engine</span>
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded-full">Operational</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">IOC Extractor</span>
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded-full">Active</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Database</span>
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded-full">Healthy</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default Dashboard
