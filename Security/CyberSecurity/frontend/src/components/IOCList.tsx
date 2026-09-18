import { ReactNode } from 'react'

interface IOCRecord {
  id: string
  value: string
  type: 'ip' | 'domain' | 'hash' | 'url' | 'email'
  confidence: number
  sources: string[]
  first_seen: string
  last_seen: string
  hash_type?: string
}

interface IOCListProps {
  iocs: IOCRecord[]
  className?: string
}

const IOCList = ({ iocs, className = '' }: IOCListProps) => {
  if (iocs.length === 0) {
    return (
      <div className={`text-center py-8 text-gray-500 ${className}`}>
        No IOCs found
      </div>
    )
  }

  const typeIcons = {
    ip: '🌐',
    domain: '🔗',
    hash: '🔏',
    url: '🔗',
    email: '📧'
  }

  const typeColors = {
    ip: 'border-blue-500 bg-blue-50',
    domain: 'border-green-500 bg-green-50',
    hash: 'border-purple-500 bg-purple-50',
    url: 'border-indigo-500 bg-indigo-50',
    email: 'border-pink-500 bg-pink-50'
  }

  return (
    <div className={className}>
      <div className="space-y-4">
        {iocs.map(ioc => (
          <div key={ioc.id} className="border-l-4 p-4">
            <div className="flex items-start space-x-3">
              <div className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center text-sm font-medium ${typeColors[ioc.type]}`}>
                {typeIcons[ioc.type]}
              </div>
              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-900 truncate max-w-xs">
                    {ioc.value}
                  </h3>
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 text-xs font-medium 
                      {ioc.confidence >= 90 ? 'bg-green-100 text-green-800' :
                       ioc.confidence >= 75 ? 'bg-yellow-100 text-yellow-800' :
                       'bg-red-100 text-red-800'}
                      rounded-full">
                      {ioc.confidence}%
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(ioc.last_seen).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <p className="text-sm text-gray-600">
                  Type: {ioc.type.toUpperCase()}{ioc.hash_type ? ` (${ioc.hash_type})` : ''} • 
                  Sources: {ioc.sources.join(', ')}
                </p>
                <p className="text-xs text-gray-400">
                  First seen: {new Date(ioc.first_seen).toLocaleString()} • 
                  Last seen: {new Date(ioc.last_seen).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default IOCList
