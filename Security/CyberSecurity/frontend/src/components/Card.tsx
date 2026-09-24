import { ReactNode } from 'react'

interface CardProps {
  title?: string
  children: ReactNode
  className?: string
}

const Card = ({ title, children, className = '' }: CardProps) => {
  return (
    <div className={`bg-white rounded-lg shadow-md border border-gray-200 ${className}`}>
      {title && (
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">{title}</h3>
        </div>
      )}
      <div className="px-6 py-5">{children}</div>
    </div>
  )
}

export default Card
