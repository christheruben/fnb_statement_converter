'use client'

import { useState } from 'react'
import Home from './page'

type Row = Record<string, string | number | null>

export default function App() {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFileSelect(file: File) {
    setUploadedFile(file)
    setError(null)
    setRows([])
    setLoading(true)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('http://localhost:8000/extract?format=json', {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        // Try to read FastAPI error body
        let message = 'Upload failed'
        try {
          const data = await res.json()
          if (data.detail) message = data.detail
        } catch {
          // ignore parse error
        }
        throw new Error(message)
      }

      const data = await res.json()
      setRows(data.rows || [])
    } catch (err: any) {
      setError(err.message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  async function handleDownloadCsv() {
    if (!uploadedFile) return

    const formData = new FormData()
    formData.append('file', uploadedFile)

    const res = await fetch('http://localhost:8000/extract?format=csv', {
      method: 'POST',
      body: formData,
    })

    if (!res.ok) {
      let message = 'CSV download failed'
      try {
        const data = await res.json()
        if (data.detail) message = data.detail
      } catch {
        // ignore
      }
      setError(message)
      return
    }

    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'statement.csv'
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  }

  const hasRows = rows && rows.length > 0

  return (
    <main className="min-h-screen bg-background">
      <Home />
    </main>
  )
}
