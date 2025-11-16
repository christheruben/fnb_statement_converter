'use client'

import { useState, useRef } from 'react'
import { Upload, CheckCircle, AlertCircle } from 'lucide-react'

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error'

export function FileUploadDropZone() {
  const [isDragActive, setIsDragActive] = useState(false)
  const [status, setStatus] = useState<UploadStatus>('idle')
  const [fileName, setFileName] = useState<string>('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true)
    } else if (e.type === 'dragleave') {
      setIsDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleFile = async (file: File) => {
    // Validate file type
    const validTypes = ['.csv', '.xls', '.xlsx', '.pdf']
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()

    if (!validTypes.includes(fileExt)) {
      setStatus('error')
      setFileName(file.name)
      return
    }

    // Call PDF parser API
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('http://localhost:8000/extract?format=json', {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) {
        //throw error if backend returns bad response
        throw new Error('Upload failed with status ' + response.status)
      }

      // adjust to backend reponse
      const data = await response.json()
      console.log('File processed successfully:', data)

      setStatus('success')
  
    } catch (error) {
      console.error('Error uploading file:', error)
      setStatus('error')
    }
  }

  const getStatusContent = () => {
    switch (status) {
      case 'uploading':
        return (
          <div className="flex flex-col items-center gap-3">
            <div className="animate-spin">
              <Upload className="w-8 h-8 text-primary" />
            </div>
            <p className="text-sm text-muted-foreground">Processing {fileName}...</p>
          </div>
        )
      case 'success':
        return (
          <div className="flex flex-col items-center gap-3">
            <CheckCircle className="w-8 h-8 text-green-600" />
            <p className="text-sm font-medium text-foreground">{fileName}</p>
            <p className="text-xs text-muted-foreground">Successfully uploaded</p>
            <button
              onClick={() => setStatus('idle')}
              className="mt-2 px-4 py-2 text-sm font-medium text-primary hover:text-primary/80 transition-colors"
            >
              Upload Another File
            </button>
          </div>
        )
      case 'error':
        return (
          <div className="flex flex-col items-center gap-3">
            <AlertCircle className="w-8 h-8 text-red-600" />
            <p className="text-sm font-medium text-foreground">Invalid file type</p>
            <p className="text-xs text-muted-foreground">Please upload CSV, XLS, XLSX, or PDF</p>
            <button
              onClick={() => setStatus('idle')}
              className="mt-2 px-4 py-2 text-sm font-medium text-primary hover:text-primary/80 transition-colors"
            >
              Try Again
            </button>
          </div>
        )
      default:
        return (
          <div className="flex flex-col items-center gap-3">
            <Upload className="w-10 h-10 text-primary" />
            <div className="text-center">
              <p className="text-lg font-semibold text-foreground">Drop your file here</p>
              <p className="text-sm text-muted-foreground mt-1">or click to browse</p>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Supported: CSV, XLS, XLSX, PDF
            </p>
          </div>
        )
    }
  }

  return (
    <div className="w-full max-w-md">
      <div
        className={`relative rounded-lg border-2 border-dashed px-6 py-16 text-center transition-colors cursor-pointer ${
          isDragActive
            ? 'border-primary bg-primary/5'
            : 'border-border hover:border-primary/50 bg-card'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        {getStatusContent()}
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={handleChange}
          accept=".csv,.xls,.xlsx,.pdf"
        />
      </div>
    </div>
  )
}
