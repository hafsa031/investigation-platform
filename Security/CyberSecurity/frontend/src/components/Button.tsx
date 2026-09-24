import { ReactNode } from 'react'

interface ButtonProps {
  onClick: () => void
  variant?: 'primary' | 'secondary' | 'outline' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  className?: string
  disabled?: boolean
  children: ReactNode
}

const Button = ({ 
  onClick, 
  variant = 'primary', 
  size = 'md', 
  className = '', 
  disabled = false,
  children 
}: ButtonProps) => {
  const baseClasses = 'font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus-ring-offset-2 disabled:opacity-50 disabled:pointer-events-none'
  
  const variantClasses = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-700 focus:ring-indigo-500',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-500',
    outline: 'border border-indigo-600 text-indigo-600 hover:bg-indigo-50 focus:ring-indigo-500',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
  }
  
  const sizeClasses = {
    sm: 'px-3 py-1 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg'
  }

  return (
    <button
      onClick={disabled ? undefined : onClick}
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      disabled={disabled}
    >
      {children}
    </button>
  )
}

export default Button
