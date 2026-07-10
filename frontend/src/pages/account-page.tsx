import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import Header from '../components/header'
import api from '../api'

type Statement = {
  id: number
  account_number: string
  start_date: string
  end_date: string
  opening_balance: number
  closing_balance: number
  uploaded_at: string
}

type TrendsData = {
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

export default function AccountPage() {
  const { id } = useParams<{ id: string }>()
  const [statements, setStatements] = useState<Statement[]>([])
  const [trends, setTrends] = useState<TrendsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    Promise.all([
      api.get(`/accounts/${id}/statements`),
      api.get(`/accounts/${id}/trends`),
    ])
      .then(([statementsRes, trendsRes]) => {
        setStatements(statementsRes.data)
        setTrends(trendsRes.data.message ? null : trendsRes.data)
      })
      .catch(() => setError('Failed to load account data.'))
      .finally(() => setLoading(false))
  }, [id])

  // Build month-by-month chart data from statements
  const monthlyData = statements.map(s => ({
    month: s.start_date.slice(0, 7), // "2025-12"
    closing_balance: s.closing_balance,
  })).reverse()

  const categoryChartData = trends?.category_breakdown.map(item => ({
    category: item.category,
    amount: item.amount,
  })) ?? []

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

        {/* Summary cards */}
        {trends && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-8">
            <div className="rounded-lg border bg-card p-4">
              <p className="text-xs text-muted-foreground">Total Income</p>
              <p className="text-lg font-semibold text-green-600">R {trends.total_income.toFixed(2)}</p>
            </div>
            <div className="rounded-lg border bg-card p-4">
              <p className="text-xs text-muted-foreground">Total Spend</p>
              <p className="text-lg font-semibold text-red-500">R {trends.total_spend.toFixed(2)}</p>
            </div>
            <div className="rounded-lg border bg-card p-4">
              <p className="text-xs text-muted-foreground">Net Savings</p>
              <p className={`text-lg font-semibold ${trends.net_savings >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                R {trends.net_savings.toFixed(2)}
              </p>
            </div>
            <div className="rounded-lg border bg-card p-4">
              <p className="text-xs text-muted-foreground">Savings Rate</p>
              <p className={`text-lg font-semibold ${trends.savings_rate >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                {trends.savings_rate.toFixed(1)}%
              </p>
            </div>
          </div>
        )}

        {/* Charts */}
        {trends && (
          <div className="grid grid-cols-1 gap-6 mb-8 md:grid-cols-2">
            {/* Balance over time */}
            {monthlyData.length > 1 && (
              <div className="rounded-lg border bg-card p-4">
                <h2 className="text-sm font-semibold mb-4">Balance Over Time</h2>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={monthlyData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="closing_balance" stroke="#6366f1" strokeWidth={2} dot={false} name="Balance" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Spending by category */}
            {categoryChartData.length > 0 && (
              <div className="rounded-lg border bg-card p-4">
                <h2 className="text-sm font-semibold mb-4">Spending by Category</h2>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={categoryChartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" tick={{ fontSize: 11 }} />
                    <YAxis dataKey="category" type="category" tick={{ fontSize: 11 }} width={80} />
                    <Tooltip />
                    <Bar dataKey="amount" fill="#6366f1" name="Amount (R)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {/* Statements list */}
        <div className="rounded-lg border bg-card">
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <h2 className="text-sm font-semibold">Statements</h2>
            <Link
              to="/dashboard"
              className="text-xs text-primary hover:underline"
            >
              + Upload Statement
            </Link>
          </div>
          {statements.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-muted-foreground">No statements uploaded yet.</p>
              <Link to="/dashboard" className="text-sm text-primary hover:underline mt-2 inline-block">
                Upload your first statement
              </Link>
            </div>
          ) : (
            <table className="min-w-full text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Period</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Account Number</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">Opening</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">Closing</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">Uploaded</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {statements.map(s => (
                  <tr key={s.id} className="border-t hover:bg-muted/50">
                    <td className="px-4 py-2 whitespace-nowrap">
                      {s.start_date} → {s.end_date}
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">{s.account_number}</td>
                    <td className="px-4 py-2 text-right">R {s.opening_balance?.toFixed(2)}</td>
                    <td className="px-4 py-2 text-right">R {s.closing_balance?.toFixed(2)}</td>
                    <td className="px-4 py-2 text-right text-muted-foreground text-xs">
                      {new Date(s.uploaded_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Link
                        to={`/statements/${s.id}`}
                        className="text-xs text-primary hover:underline"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  )
}