'use client'

import { useState, useRef } from 'react'
import { Upload, CheckCircle, AlertCircle, Download } from 'lucide-react'

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

type AnalyticsResponse = {
  total_income: number
  total_spend: number
  net_savings: number
  savings_rate: number
  category_breakdown: {
    category: string
    amount: number
    percentage: number
  }[]
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

function downloadCSV(data: ExtractResponse, fileName: string) {
  const headers = ['date', 'description', 'amount', 'balance', 'type', 'category']
  const metaRows = [
    `Account,${data.account_number}`,
    `Period,${data.statement_period.start_date} to ${data.statement_period.end_date}`,
    `Opening Balance,${data.opening_balance.toFixed(2)}`,
    `Closing Balance,${data.closing_balance.toFixed(2)}`,
    '',
    headers.join(',')
  ]
  const rows = data.transactions.map(txn => 
  [
    txn.date,
    `"${txn.description.replace(/"/g, '""')}"`,
    txn.category,
    txn.amount ??'',
    txn.balance ??'',
    txn.type,
  ].join(',')
  )
  const csvContent = [...metaRows, ...rows].join('\n')
  const blob = new Blob([csvContent], {type: 'text/csv'})
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName.replace('.pdf','.csv')
  link.click()
  URL.revokeObjectURL(url)
}

async function analyzeTransactions(transactions: Transaction[]): Promise<AnalyticsResponse> {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transactions }),
  })

  if (!response.ok) {
    throw new Error(`Analysis failed with status ${response.status}`)
  }

  return response.json()
}

export function FileUploadDropZone() {
  const [isDragActive, setIsDragActive] = useState(false)
  const [status, setStatus] = useState<UploadStatus>('idle')
  const [fileName, setFileName] = useState<string>('')
  const [data, setData] = useState<ExtractResponse | null>(null)
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null)
  const [analyticsError, setAnalyticsError] = useState<string | null>(null)
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
    setAnalytics(null)
    setAnalyticsError(null)

    let result: ExtractResponse | null = null

    try {
      result = await uploadStatement(file)
      setData(result)
      setStatus('success')
    } catch (error) {
      console.error('Error uploading file:', error)
      setStatus('error')
      setData(null)
      return
    }

    try {
      const analyticsResult = await analyzeTransactions(result.transactions)
      setAnalytics(analyticsResult)
    } catch (error) {
      console.error('Error analyzing transactions:', error)
      setAnalyticsError('Analysis failed, but your transactions loaded successfully.')
    }
  }

  const reset = () => {
    setStatus('idle')
    setData(null)
    setAnalytics(null)
    setAnalyticsError(null)
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

  const renderAnalytics = () => {
    if (analyticsError) {
      return (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3">
          <p className="text-xs text-red-600">{analyticsError}</p>
        </div>
      )
    }

    if (!analytics) return null

    return (
      <div className="mt-4 border rounded-lg bg-card p-4">
        <h2 className="text-sm font-semibold mb-3">Analytics</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-lg border bg-card p-3">
            <p className="text-xs text-muted-foreground">Total Income</p>
            <p className="text-sm font-semibold text-green-600">R {analytics.total_income.toFixed(2)}</p>
          </div>
          <div className="rounded-lg border bg-card p-3">
            <p className="text-xs text-muted-foreground">Total Spend</p>
            <p className="text-sm font-semibold text-red-500">R {analytics.total_spend.toFixed(2)}</p>
          </div>
          <div className="rounded-lg border bg-card p-3">
            <p className="text-xs text-muted-foreground">Net Savings</p>
            <p className={`text-sm font-semibold ${analytics.net_savings >= 0 ? 'text-green-600' : 'text-red-500'}`}>
              R {analytics.net_savings.toFixed(2)}
            </p>
          </div>
          <div className="rounded-lg border bg-card p-3">
            <p className="text-xs text-muted-foreground">Savings Rate</p>
            <p className={`text-sm font-semibold ${analytics.savings_rate >= 0 ? 'text-green-600' : 'text-red-500'}`}>
              {analytics.savings_rate.toFixed(1)}%
            </p>
          </div>
        </div>

        <div className="mt-3">
          <h3 className="text-xs font-semibold text-muted-foreground mb-2">Spending by Category</h3>
          <div className="space-y-2">
            {analytics.category_breakdown.map((item) => (
              <div key={item.category} className="flex items-center gap-2">
                <div className="w-28 text-xs truncate text-muted-foreground">{item.category}</div>
                <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
                <div className="text-xs text-muted-foreground w-10 text-right">{item.percentage}%</div>
                <div className="text-xs font-medium w-24 text-right">R {item.amount.toFixed(2)}</div>
              </div>
            ))}
          </div>
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
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground">
              Showing {visibleRows.length} of {data.transactions.length}
            </span>
            <button
              onClick={(e) => { e.stopPropagation(); downloadCSV(data, fileName) }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:cursor-pointer hover:underline"
            >
              <Download className="w-3 h-3" />
              Download CSV
            </button>
          </div>
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
      {renderAnalytics()}
      {renderTransactionTable()}
    </div>
  )
}