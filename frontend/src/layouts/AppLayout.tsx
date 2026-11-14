import type { ReactNode } from "react"
import { SiteFooter } from "../components/SiteFooter"
import { SiteHeader } from "../components/SiteHeader"

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <SiteHeader />
      <main className="page">{children}</main>
      <SiteFooter />
    </>
  )
}
