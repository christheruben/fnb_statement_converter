import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Download } from 'lucide-react'
import Header from '../components/header'
import api from '../api'

type Transaction = {
  date: string
  description: string
  amount: number | null
  balance: number | null
  type: 'credit' | 'debit'
  category: string
}

type Statement = {
  id: number
  account_number: string
  start_date: string
  end_date: string
  opening_balance: number
  closing_balance: number
  uploaded_at: string
}

function downloadCSV(statement: Statement, transactions: Transaction[]) {
  const headers = ['date', 'description', 'category', 'amount', 'balance', 'type']
  const metaRows = [
    `Account,${statement.account_number}`,
    `Period,${statement.start_date} to ${statement.end_date}`,
    `Opening Balance,${statement.opening_balance?.toFixed(2)}`,
    `Closing Balance,${statement.closing_balance?.toFixed(2)}`,
    '',
    headers.join(','),
  ]
  const rows = transactions.map(txn =>
    [
      txn.date,
      `"${(txn.description ?? '').replace(/"/g, '""')}"`,
      txn.category,
      txn.amount ?? '',
      txn.balance ?? '',
      txn.type,
    ].join(',')
  )
  const csvContent = [...metaRows, ...rows].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `statement-${statement.start_date}-to-${statement.end_date}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

export default function StatementPage() {
  const { id } = useParams<{ id: string }>()
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [statement, setStatement] = useState<Statement | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    api.get(`/statements/${id}/transactions`)
      .then(res => setTransactions(res.data))
      .catch(() => setError('Failed to load transactions.'))
      .finally(() => setLoading(false))
  }, [id])

  // Get statement metadata from the transactions list breadcrumb
  // We'll fetch it from the accounts list via the header — for now derive from transactions
  useEffect(() => {
    if (!id) return
    // Fetch statement metadata — we don't have a direct /statements/:id endpoint yet
    // so we derive what we can from the transactions response header
    // For now we'll use a placeholder and rely on the transactions data
  }, [id])

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex items-center justify-center h-64">
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex items-center justify-center h-64">
          <p className="text-sm text-red-500">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="max-w-5xl mx-auto px-4 py-10">

        {/* Header row */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-xs text-muted-foreground mb-1">
              <Link to="/dashboard" className="hover:underline">Dashboard</Link>
              {' / '}
              <span>Statement {id}</span>
            </p>
            <h1 className="text-xl font-semibold">Statement Detail</h1>
          </div>
          {transactions.length > 0 && statement && (
            <button
              onClick={() => downloadCSV(statement, transactions)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:opacity-90"
            >
              <Download className="w-3 h-3" />
              Download CSV
            </button>
          )}
        </div>

        {/* Transactions table */}
        <div className="rounded-lg border bg-card">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <h2 className="text-sm font-semibold">Transactions</h2>
            <span className="text-xs text-muted-foreground">{transactions.length} total</span>
          </div>
          {transactions.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-muted-foreground">No transactions found.</p>
            </div>
          ) : (
            <div className="overflow-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Date</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Description</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Category</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">Amount</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((txn, idx) => (
                    <tr key={idx} className="border-t hover:bg-muted/50">
                      <td className="px-4 py-2 whitespace-nowrap text-xs">{txn.date}</td>
                      <td className="px-4 py-2 max-w-[260px] truncate text-xs">{txn.description}</td>
                      <td className="px-4 py-2 text-xs">
                        <span className="px-1.5 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-medium">
                          {txn.category}
                        </span>
                      </td>
                      <td className={`px-4 py-2 text-right text-xs font-medium ${txn.type === 'credit' ? 'text-green-600' : 'text-red-500'}`}>
                        {txn.type === 'credit' ? '+' : ''}
                        {txn.amount?.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '-'}
                      </td>
                      <td className="px-4 py-2 text-right text-xs text-muted-foreground">
                        {txn.balance?.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}