import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"
import type { Account } from "../types/auth"
import { restoreSession, signIn, signOut, signUp } from "../services/auth"
import { setAccessToken } from "../services/api"
type AuthContextValue = { account: Account | null; loading: boolean; login: (email: string, password: string) => Promise<void>; register: (role: "student" | "tutor", payload: Record<string, unknown>) => Promise<void>; logout: () => Promise<void> }
const AuthContext = createContext<AuthContextValue | null>(null)
export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<Account | null>(null), [loading, setLoading] = useState(true)
  const clear = useCallback(() => { setAccessToken(null); setAccount(null) }, [])
  useEffect(() => {
    let active = true
    const invalid = () => clear()
    window.addEventListener("tutorinn-auth-invalid", invalid)
    void restoreSession().then(result => { if (active) setAccount(result.account) }).catch(() => { if (active) clear() }).finally(() => { if (active) setLoading(false) })
    return () => { active = false; window.removeEventListener("tutorinn-auth-invalid", invalid) }
  }, [clear])
  const login = useCallback(async (email: string, password: string) => { const result = await signIn(email, password); setAccount(result.account) }, [])
  const register = useCallback(async (role: "student" | "tutor", payload: Record<string, unknown>) => { const result = await signUp(role, payload); setAccount(result.account) }, [])
  const logout = useCallback(async () => { try { await signOut() } finally { clear() } }, [clear])
  const value = useMemo(() => ({ account, loading, login, register, logout }), [account, loading, login, register, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
export function useAuth(): AuthContextValue { const value = useContext(AuthContext); if (!value) throw new Error("useAuth must be used inside AuthProvider."); return value }
