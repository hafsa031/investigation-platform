import { useState } from 'react'

interface FileUploadProps {
  onFileUpload: (file: File) => Promise<void>
  uploading?: boolean
  progress?: number
  onError?: (msg: string) => void
  className?: string
}

const FileUpload = ({ 
  onFileUpload, 
  uploading = false, 
  progress = 0, 
  onError, 
  className = '' 
}: FileUploadProps) => {
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(true)
  }

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
  }

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)

    const files = e.dataTransfer?.files
    if (files && files.length > 0) {
      await handleFile(files[0])
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      await handleFile(file)
    }
    e.target.value = '' // Reset input
  }

  const handleFile = async (file: File) => {
    setSelectedFile(file)
    try {
      await onFileUpload(file)
    } catch (err) {
      onError?.('Upload failed. Please try again.')
    }
  }

  return (
    <div className={className}>
      <div 
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center 
          ${dragOver ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 bg-gray-50'}
          hover:border-indigo-400 hover:bg-indigo-50 transition-colors`}
      >
        <input 
          type="file" 
          className="hidden" 
          onChange={handleFileSelect} 
        />
        <div className="space-y-4">
          {(dragOver || selectedFile) ? (
            <>
              <p className="text-sm font-medium text-gray-900">
                {selectedFile ? `Selected: ${selectedFile.name}` : 'Release to upload'}
              </p>
              {selectedFile && (
                <div className="text-xs text-gray-500 mt-1">
                  {selectedFile.name} • {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </div>
              )}
            </>
          ) : (
            <>
              <div className="flex items-center justify-center space-x-3">
                <svg className="h-6 w-6 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 16v-2a2 2 0 012-2h2.586a1 1 0 01.707.293l2.414 2.414a1 1 0 01-.293.707V19a2 2 0 01-2 2h-2zm0 0H5a2 2 0 01-2-2v-3a2 2 0 012-2h2zm0 0l3.293-3.293a1 1 0 011.414 0l1.414 1.414a1 1 0 001.414-1.414V4a1 1 0 00-1-1h-2.586a1 1 0 00-.707.293l-1.172 1.172a3 3 0 00-4.243 0l-1.172-1.172a1 1 0 00-1.414 0l-1.414 1.414z" />
                </svg>
              </div>
              <p className="text-sm text-gray-600">Click to upload or drag and drop</p>
              <p className="text-xs text-gray-500">
                Supported formats: PCAP, images, documents, logs, and more
              </p>
            </>
          )}
        </div>
        
        {uploading && (
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div 
                className={`bg-indigo-600 h-2.5 rounded-full transition-all duration-300`} 
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <p className="mt-2 text-xs text-gray-600">
              Uploading... {progress}%
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default FileUpload
