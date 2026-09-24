import { useState } from 'react'
import { Card, FileUpload, Button } from '../components'
import axios from 'axios'

const EvidenceUpload = () => {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadResult, setUploadResult] = useState(null)
  const [error, setError] = useState<string | null>(null)

  const handleFileUpload = async (file: File) => {
    setUploading(true)
    setError(null)
    setUploadResult(null)
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90))
      }, 200)
      
      // In a real app, this would be:
      // const response = await axios.post('/api/evidence/upload', formData, {
      //   onUploadProgress: (progressEvent) => {
      //     const percentCompleted = Math.round(
      //       (progressEvent.loaded * 100) / progressEvent.total
      //     )
      //     setUploadProgress(percentCompleted)
      //   }
      // })
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 3000))
      
      clearInterval(progressInterval)
      setUploadProgress(100)
      
      // Simulate successful response
      const mockResult = {
        evidence_id: `EV-${Date.now()}`,
        filename: file.name,
        size: file.size,
        type: file.type,
        upload_time: new Date().toISOString(),
        status: 'uploaded'
      }
      
      setUploadResult(mockResult)
    } catch (err) {
      setError('Upload failed. Please try again.')
      console.error(err)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Upload Evidence</h1>
        <p className="text-gray-600 mb-6">
          Upload files for forensic analysis. Supported formats: PCAP, images, documents, logs, and more.
        </p>
        
        <Card>
          <FileUpload 
            onFileUpload={handleFileUpload}
            uploading={uploading}
            progress={uploadProgress}
            onError={(msg) => setError(msg)}
          />
          
          {uploadResult && (
            <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-md">
              <h3 className="text-lg font-semibold text-green-800 mb-2">Upload Successful!</h3>
              <p className="text-sm text-gray-600">
                Evidence ID: <span className="font-mono">{uploadResult.evidence_id}</span><br />
                Filename: {uploadResult.filename}<br />
                Size: {(uploadResult.size / 1024 / 1024).toFixed(2)} MB<br />
                Type: {uploadResult.type}
              </p>
              <Button 
                onClick={() => {
                  // In a real app, this would navigate to the investigation view
                  window.location.href = `/investigation/${uploadResult.evidence_id}`
                }}
                variant="primary"
              >
                Analyze Evidence
              </Button>
            </div>
          )}
          
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-800">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default EvidenceUpload
