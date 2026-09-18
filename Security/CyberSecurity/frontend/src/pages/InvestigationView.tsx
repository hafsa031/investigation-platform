import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Card, IOCList, FindingsList, Timeline, Button } from '../components'
import axios from 'axios'

const InvestigationView = () => {
  const { caseId } = useParams<{ caseId: string }>()
  const [caseData, setCaseData] = useState(null)
  const [findings, setFindings] = useState([])
  const [iocs, setIOCs] = useState([])
  const [timeline, setTimeline] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadCaseData = async () => {
      if (!caseId) return
      
      try {
        setLoading(true)
        // In a real app, these would be actual API calls
        // For demo, we'll use mock data
        
        // Simulate API calls
        await Promise.all([
          // Mock case data
          new Promise(resolve => setTimeout(() => {
            setCaseData({
              id: caseId,
              title: `Investigation ${caseId}`,
              description: 'Suspicious network activity detected in DMZ segment',
              status: 'active',
              created_at: '2026-09-15T10:30:00Z',
              updated_at: '2026-09-18T08:15:00Z',
              analyst: 'Intern 4',
              priority: 'high'
            })
            resolve(true)
          }, 500)),
          
          // Mock findings
          new Promise(resolve => setTimeout(() => {
            setFindings([
              {
                id: 'F-001',
                title: 'Malicious DNS Query Detected',
                description: 'DNS query to known C2 domain example-malicious.com',
                severity: 'high',
                category: 'network',
                timestamp: '2026-09-17T14:22:00Z',
                evidence_id: 'EV-001'
              },
              {
                id: 'F-002',
                title: 'Suspicious File Hash Found',
                description: 'File with hash matching known malware sample',
                severity: 'medium',
                category: 'file',
                timestamp: '2026-09-17T09:15:00Z',
                evidence_id: 'EV-001'
              }
            ])
            resolve(true)
          }, 800)),
          
          // Mock IOCs
          new Promise(resolve => setTimeout(() => {
            setIOCs([
              {
                id: 'IOC-001',
                value: '192.168.1.100',
                type: 'ip',
                confidence: 95,
                sources: ['network_analysis'],
                first_seen: '2026-09-17T14:22:00Z',
                last_seen: '2026-09-17T14:22:00Z'
              },
              {
                id: 'IOC-002',
                value: 'example-malicious.com',
                type: 'domain',
                confidence: 90,
                sources: ['dns_analysis'],
                first_seen: '2026-09-17T14:21:00Z',
                last_seen: '2026-09-17T14:21:00Z'
              },
              {
                id: 'IOC-003',
                value: 'a1b2c3d4e5f6789012345678901234567890abcd',
                type: 'hash',
                hash_type: 'sha256',
                confidence: 85,
                sources: ['file_analysis'],
                first_seen: '2026-09-17T09:15:00Z',
                last_seen: '2026-09-17T09:15:00Z'
              }
            ])
            resolve(true)
          }, 600)),
          
          // Mock timeline
          new Promise(resolve => setTimeout(() => {
            setTimeline([
              {
                id: 'T-001',
                timestamp: '2026-09-15T10:30:00Z',
                event: 'Case created',
                description: 'Investigation initiated based on alert from SIEM',
                type: 'case'
              },
              {
                id: 'T-002',
                timestamp: '2026-09-16T14:22:00Z',
                event: 'Evidence uploaded',
                description: 'Network packet capture (network.pcap) uploaded for analysis',
                type: 'evidence'
              },
              {
                id: 'T-003',
                timestamp: '2026-09-16T09:15:00Z',
                event: 'File analysis completed',
                description: 'Suspicious executable extracted and analyzed',
                type: 'analysis'
              },
              {
                id: 'T-004',
                timestamp: '2026-09-17T14:21:00Z',
                event: 'DNS analysis completed',
                description: 'Malicious domain contact detected',
                type: 'analysis'
              },
              {
                id: 'T-005',
                timestamp: '2026-09-17T14:22:00Z',
                event: 'High confidence IOC identified',
                description: 'Malicious IP address correlated with threat intelligence',
                type: 'ioc'
              }
            ])
            resolve(true)
          }, 700))
        ])
      } catch (err) {
        setError('Failed to load investigation data')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    loadCaseData()
  }, [caseId])

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
        <p className="mt-4 text-gray-500">Loading investigation data...</p>
      </div>
    )
  }

  if (error) {
    return <div className="p-4 bg-red-50 border border-red-200 rounded-md text-red-800">{error}</div>
  }

  if (!caseData) {
    return <div className="p-6 text-center">Case not found</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{caseData.title}</h1>
          <p className="text-gray-600 mb-2">{caseData.description}</p>
          <div className="flex items-center space-x-4">
            <span className="px-3 py-1 text-xs font-medium 
              {caseData.priority === 'high' ? 'bg-red-100 text-red-800' :
               caseData.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
               'bg-green-100 text-green-800'}
              rounded-full">
              {caseData.priority.toUpperCase()} PRIORITY
            </span>
            <span className="px-3 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
              {caseData.status.toUpperCase()}
            </span>
            <span className="text-sm text-gray-500">
              Assigned to: {caseData.analyst}
            </span>
          </div>
        </div>
        <div className="text-right">
          <Button 
            onClick={() => window.location.href = '/'}
            variant="outline"
          >
            Back to Dashboard
          </Button>
        </div>
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card title="Investigation Timeline">
          <Timeline events={timeline} />
        </Card>
        
        <Card title="Findings">
          <FindingsList findings={findings} />
        </Card>
        
        <Card title="Indicators of Compromise (IOCs)">
          <IOCList iocs={iocs} />
        </Card>
      </div>
    </div>
  )
}

export default InvestigationView
