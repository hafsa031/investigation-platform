interface StatisticProps {
  label: string
  value: number | string
  variant?: 'info' | 'success' | 'warning' | 'danger'
  className?: string
}

const Statistic = ({ label, value, variant = 'info', className = '' }: StatisticProps) => {
  const variantClasses = {
    info: 'bg-blue-50 text-blue-800',
    success: 'bg-green-50 text-green-800',
    warning: 'bg-yellow-50 text-yellow-800',
    danger: 'bg-red-50 text-red-800'
  }

  return (
    <div className={`text-center p-4 rounded-lg border ${variantClasses[variant]} ${className}`}>
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className="text-2xl font-bold mt-2">{value}</p>
    </div>
  )
}

export default Statistic
