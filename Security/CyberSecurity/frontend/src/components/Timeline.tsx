import { ReactNode } from 'react'

interface TimelineEvent {
  id: string
  timestamp: string
  event: string
  description: string
  type: 'case' | 'evidence' | 'analysis' | 'ioc' | 'finding'
}

interface TimelineProps {
  events: TimelineEvent[]
  className?: string
}

const Timeline = ({ events, className = '' }: TimelineProps) => {
  if (events.length === 0) {
    return (
      <div className={`text-center py-8 text-gray-500 ${className}`}>
        No timeline events
      </div>
    )
  }

  // Sort events by timestamp (newest first)
  const sortedEvents = [...events].sort((a, b) => 
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  )

  const typeIcons = {
    case: '📁',
    evidence: '📎',
    analysis: '🔬',
    ioc: '🎯',
    finding: '🔍'
  }

  const typeColors = {
    case: 'border-blue-500 bg-blue-50',
    evidence: 'border-green-500 bg-green-50',
    analysis: 'border-purple-500 bg-purple-50',
    ioc: 'border-red-500 bg-red-50',
    finding: 'border-orange-500 bg-orange-50'
  }

  return (
    <div className={className}>
      <div className="relative pl-4">
        {/* Timeline line */}
        <div className="absolute left-0 top-0 h-full w-0.5 bg-gray-300"></div>
        
        {/* Events */}
        <div className="space-y-6">
          {sortedEvents.map((event, index) => (
            <div key={event.id} className="flex items-start">
              {/* Timeline dot */}
              <div className="relative">
                <div className={`w-3 h-3 rounded-full bg-gray-300 border-2 border-white 
                  ${typeColors[event.type]} z-10 mt-1 flex-shrink-0`}></div>
                {/* Connection line */}
                {!event.id && (
                  <div className="absolute left-0 -top-2 h-2 w-2.5 bg-gray-300"></div>
                )}
              </div>
              
              {/* Event content */}
              <div className="ml-4 flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-900">
                    {event.event}
                  </h3>
                  <p className="text-xs text-gray-500">
                    {new Date(event.timestamp).toLocaleString()}
                  </p>
                </div>
                <p className="text-sm text-gray-600">{event.description}</p>
                <p className="text-xs text-gray-400">
                  Type: {event.type.toUpperCase()}
                </p>
              </div>
            </div>
          ))}
        </div>
        
        {/* Bottom line */}
        <div className="absolute left-0 bottom-0 h-0.5 w-0.5 bg-gray-300"></div>
      </div>
    </div>
  )
}

export default Timeline
