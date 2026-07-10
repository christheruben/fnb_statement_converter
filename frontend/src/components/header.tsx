import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronDown } from 'lucide-react'
import { useAuth } from '../AuthContext'
import api from '../api'

type FinancialAccount = {
  id: number
  name: string
}

export default function Header() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [accounts, setAccounts] = useState<FinancialAccount[]>([])
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (user) {
      api.get('/accounts')
        .then(res => setAccounts(res.data))
        .catch(() => {})
    }
  }, [user])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center justify-between px-6 md:px-8">
        {/* Logo */}
        <Link to="/dashboard" className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary" />
          <h1 className="text-xl font-semibold text-foreground">Statement Converter</h1>
        </Link>

        {/* Nav */}
        <nav className="flex items-center gap-4">
          {user && (
            <>
              {/* Accounts dropdown */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setDropdownOpen(prev => !prev)}
                  className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  Accounts
                  <ChevronDown className={`w-4 h-4 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
                </button>
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-48 rounded-lg border border-border bg-white shadow-lg py-1 z-50">
                    {accounts.length === 0 ? (
                      <p className="px-3 py-2 text-xs text-muted-foreground">No accounts yet.</p>
                    ) : (
                      accounts.map(account => (
                        <Link
                          key={account.id}
                          to={`/accounts/${account.id}`}
                          onClick={() => setDropdownOpen(false)}
                          className="block px-3 py-2 text-sm hover:bg-muted transition-colors"
                        >
                          {account.name}
                        </Link>
                      ))
                    )}
                    <div className="border-t border-border mt-1 pt-1">
                      <Link
                        to="/dashboard"
                        onClick={() => setDropdownOpen(false)}
                        className="block px-3 py-2 text-xs text-primary hover:bg-muted transition-colors"
                      >
                        + New Account
                      </Link>
                    </div>
                  </div>
                )}
              </div>

              {/* Logout */}
              <button
                onClick={handleLogout}
                className="px-4 py-2 text-sm font-medium rounded-lg border border-border hover:bg-muted transition-colors"
              >
                Log out
              </button>
            </>
          )}

          {!user && (
            <Link
              to="/login"
              className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  )
}