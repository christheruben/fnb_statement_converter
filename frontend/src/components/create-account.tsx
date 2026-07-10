import { useState } from 'react'
import { X } from 'lucide-react'
import api from '../api'

type Props = {
  onClose: () => void
  onCreated: (account: { id: number; name: string }) => void
}

export default function CreateAccountModal({ onClose, onCreated }: Props) {
  const [name, setName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      const res = await api.post('/accounts', { name })
      onCreated(res.data)
      onClose()
    } catch {
      setError('Failed to create account. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-sm p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
        >
          <X className="w-4 h-4" />
        </button>
        <h2 className="text-lg font-semibold mb-4">Create Account</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Account Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. My Cheque Account"
              required
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-primary text-primary-foreground rounded px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50"
          >
            {isLoading ? 'Creating...' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  )
}