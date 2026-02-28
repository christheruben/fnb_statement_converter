'use client'

import { useState, useRef } from 'react'
import { Upload, CheckCircle, AlertCircle } from 'lucide-react'

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error'

type Transaction = {
  date: string
  description: string
  amount: number | null
  balance: number | null
  type: 'credit' | 'debit'
  category: string
}

type ExtractResponse = {
  account_number: string
  statement_period: {
    start_date: string
    end_date: string
  }
  opening_balance: number
  closing_balance: number
  transactions: Transaction[]
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function uploadStatement(file: File): Promise<ExtractResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/extract-and-categorize`, {
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

export function FileUploadDropZone() {
  const [isDragActive, setIsDragActive] = useState(false)
  const [status, setStatus] = useState<UploadStatus>('idle')
  const [fileName, setFileName] = useState<string>('')
  const [data, setData] = useState<ExtractResponse | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') setIsDragActive(true)
    else if (e.type === 'dragleave') setIsDragActive(false)
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0])
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) handleFile(e.target.files[0])
  }

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setFileName(file.name)
      setStatus('error')
      setData(null)
      return
    }

    setFileName(file.name)
    setStatus('uploading')
    setData(null)

    try {
      const result = await uploadStatement(file)
      setData(result)
      setStatus('success')
    } catch (error) {
      console.error('Error uploading file:', error)
      setStatus('error')
      setData(null)
    }
  }

  const reset = () => {
    setStatus('idle')
    setData(null)
    setFileName('')
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
            <p className="text-xs text-muted-foreground">Extracting and categorizing transactions...</p>
          </div>
        )
      case 'success':
        return (
          <div className="flex flex-col items-center gap-3">
            <CheckCircle className="w-8 h-8 text-green-600" />
            <p className="text-sm font-medium text-foreground">{fileName}</p>
            <p className="text-xs text-muted-foreground">Successfully processed</p>
            <button
              onClick={(e) => { e.stopPropagation(); reset() }}
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
              Check that your file is a PDF and try again.
            </p>
            <button
              onClick={(e) => { e.stopPropagation(); reset() }}
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
              <p className="text-lg font-semibold text-foreground">Drop your PDF here</p>
              <p className="text-sm text-muted-foreground mt-1">or click to browse</p>
            </div>
            <p className="text-xs text-muted-foreground mt-2">FNB bank statements only</p>
          </div>
        )
    }
  }

  const renderSummary = () => {
    if (!data) return null
    return (
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border bg-card p-3">
          <p className="text-xs text-muted-foreground">Account</p>
          <p className="text-sm font-semibold truncate">{data.account_number}</p>
        </div>
        <div className="rounded-lg border bg-card p-3">
          <p className="text-xs text-muted-foreground">Period</p>
          <p className="text-sm font-semibold">{data.statement_period.start_date} → {data.statement_period.end_date}</p>
        </div>
        <div className="rounded-lg border bg-card p-3">
          <p className="text-xs text-muted-foreground">Opening Balance</p>
          <p className="text-sm font-semibold">R {data.opening_balance?.toFixed(2)}</p>
        </div>
        <div className="rounded-lg border bg-card p-3">
          <p className="text-xs text-muted-foreground">Closing Balance</p>
          <p className="text-sm font-semibold">R {data.closing_balance?.toFixed(2)}</p>
        </div>
      </div>
    )
  }

  const renderTransactionTable = () => {
    if (!data?.transactions.length) return null

    const maxRows = 15
    const visibleRows = data.transactions.slice(0, maxRows)

    return (
      <div className="mt-4 border rounded-lg bg-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold">Transactions</h2>
          <span className="text-xs text-muted-foreground">
            Showing {visibleRows.length} of {data.transactions.length}
          </span>
        </div>
        <div className="max-h-72 overflow-auto rounded border">
          <table className="min-w-full text-xs">
            <thead className="bg-muted sticky top-0">
              <tr>
                <th className="px-2 py-1 text-left font-medium border-b">Date</th>
                <th className="px-2 py-1 text-left font-medium border-b">Description</th>
                <th className="px-2 py-1 text-left font-medium border-b">Category</th>
                <th className="px-2 py-1 text-right font-medium border-b">Amount</th>
                <th className="px-2 py-1 text-right font-medium border-b">Balance</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row, idx) => (
                <tr key={idx} className="border-b last:border-b-0 hover:bg-muted/50">
                  <td className="px-2 py-1 whitespace-nowrap">{row.date}</td>
                  <td className="px-2 py-1 max-w-[200px] truncate">{row.description}</td>
                  <td className="px-2 py-1">
                    <span className="px-1.5 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-medium">
                      {row.category}
                    </span>
                  </td>
                  <td className={`px-2 py-1 text-right font-medium ${row.type === 'credit' ? 'text-green-600' : 'text-red-500'}`}>
                    {row.type === 'credit' ? '+' : ''}
                    {row.amount?.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '-'}
                  </td>
                  <td className="px-2 py-1 text-right text-muted-foreground">
                    {row.balance?.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full max-w-4xl mx-auto">
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
          accept=".pdf"
        />
      </div>

      {renderSummary()}
      {renderTransactionTable()}
    </div>
  )
}