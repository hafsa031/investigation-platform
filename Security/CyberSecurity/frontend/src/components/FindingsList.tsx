import { ReactNode } from 'react'

interface Finding {
  id: string
  title: string
  description: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  category: string
  timestamp: string
  evidence_id?: string
}

interface FindingsListProps {
  findings: Finding[]
  className?: string
}

const FindingsList = ({ findings, className = '' }: FindingsListProps) => {
  if (findings.length === 0) {
    return (
      <div className={`text-center py-8 text-gray-500 ${className}`}>
        No findings found
      </div>
    )
  }

  const severityClasses = {
    low: 'border-green-500 bg-green-50',
    medium: 'border-yellow-500 bg-yellow-50',
    high: 'border-orange-500 bg-orange-50',
    critical: 'border-red-500 bg-red-50'
  }

  return (
    <div className={className}>
      <div className="space-y-4">
        {findings.map(finding => (
          <div key={finding.id} className="border-l-4 p-4">
            <div className="flex items-start space-x-3">
              <div className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center text-sm font-medium ${severityClasses[finding.severity]}`}>
                {finding.severity === 'critical' ? '🚨' : 
                 finding.severity === 'high' ? '⚠️' : 
                 finding.severity === 'medium' ? '🔶' : 'ℹ️'}
              </div>
              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-900 truncate max-w-xs">
                    {finding.title}
                  </h3>
                  <span className="px-2 py-0.5 text-xs font-medium 
                    {finding.severity === 'critical' ? 'bg-red-100 text-red-800' :
                     finding.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                     finding.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                     'bg-green-100 text-green-800'}
                    rounded-full">
                    {finding.severity.toUpperCase()}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{finding.description}</p>
                <p className="text-xs text-gray-400 flex items-center space-x-2">
                  <span>Category: {finding.category}</span>
                  <span>• Evidence: {finding.evidence_id || 'N/A'}</span>
                  <span>• {new Date(finding.timestamp).toLocaleString()}</span>
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default FindingsList
