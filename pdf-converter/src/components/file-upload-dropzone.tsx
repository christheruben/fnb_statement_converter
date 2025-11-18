'use client'

import { useState, useRef } from 'react'
import { Upload, CheckCircle, AlertCircle } from 'lucide-react'

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error'

type StatementRow = {
  Date: string
  Description: string
  Amount: number
  Balance: string
  'Accrued Bank Charges': string
}

type ExtractResponse = {
  rows: StatementRow[]
}

// ---- API helper ----

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function uploadStatement(file: File): Promise<ExtractResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/extract?format=json`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    let message = `Upload failed with status ${response.status}`

    try {
      const errorData = await response.json()
      if (errorData && typeof errorData === 'object' && 'detail' in errorData) {
        message = (errorData as any).detail
      }
    } catch {
      // ignore JSON parse errors, keep default message
    }

    throw new Error(message)
  }

  return response.json()
}

// ---- Component ----

export function FileUploadDropZone() {
  const [isDragActive, setIsDragActive] = useState(false)
  const [status, setStatus] = useState<UploadStatus>('idle')
  const [fileName, setFileName] = useState<string>('')
  const [previewRows, setPreviewRows] = useState<StatementRow[]>([])
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
    const validTypes = ['.csv', '.xls', '.xlsx', '.pdf']
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()

    if (!validTypes.includes(fileExt)) {
      setFileName(file.name)
      setStatus('error')
      setPreviewRows([])
      return
    }

    setFileName(file.name)
    setStatus('uploading')
    setPreviewRows([])

    try {
      const data = await uploadStatement(file)
      console.log('File processed successfully:', data)

      // data is guaranteed to be { rows: [...] }
      setPreviewRows(data.rows || [])
      setStatus('success')
    } catch (error) {
      console.error('Error uploading file:', error)
      setStatus('error')
      setPreviewRows([])
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
            <p className="text-xs text-muted-foreground">Successfully processed</p>
            <button
              onClick={() => {
                setStatus('idle')
                setPreviewRows([])
                setFileName('')
              }}
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
            <p className="text-sm font-medium text-foreground">Upload failed</p>
            <p className="text-xs text-muted-foreground">
              Check that your file is a CSV, XLS, XLSX, or PDF and try again.
            </p>
            <button
              onClick={() => {
                setStatus('idle')
                setPreviewRows([])
              }}
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

  const renderPreviewTable = () => {
    if (!previewRows.length) return null

    const maxRows = 15
    const visibleRows = previewRows.slice(0, maxRows)

    return (
      <div className="mt-6 border rounded-lg bg-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold">Preview</h2>
          <span className="text-xs text-muted-foreground">
            Showing {visibleRows.length} of {previewRows.length} rows
          </span>
        </div>
        <div className="max-h-64 overflow-auto rounded border">
          <table className="min-w-full text-xs">
            <thead className="bg-muted">
              <tr>
                <th className="px-2 py-1 text-left font-medium border-b">Date</th>
                <th className="px-2 py-1 text-left font-medium border-b">
                  Description
                </th>
                <th className="px-2 py-1 text-right font-medium border-b">Amount</th>
                <th className="px-2 py-1 text-right font-medium border-b">Balance</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row, idx) => (
                <tr key={idx} className="border-b last:border-b-0">
                  <td className="px-2 py-1 whitespace-nowrap">{row.Date}</td>
                  <td className="px-2 py-1">{row.Description}</td>
                  <td className="px-2 py-1 text-right">
                    {row.Amount?.toLocaleString?.('en-ZA', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    }) ?? row.Amount}
                  </td>
                  <td className="px-2 py-1 text-right">{row.Balance}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
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

      {renderPreviewTable()}
    </div>
  )
}
