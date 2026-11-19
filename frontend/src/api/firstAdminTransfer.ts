import { api } from "./api"

export type FirstAdminTransferRow = {
  id: number
  status: "pending" | "accepted" | "declined" | "cancelled" | "expired"
  created_at: string
  expires_at: string
  responded_at: string | null
  initiator_email: string | null
  recipient_email: string | null
}

export type FirstAdminTransferState = { pending: FirstAdminTransferRow | null; can_start: boolean }

export const getFirstAdminTransfer = () => api<FirstAdminTransferState>("/api/admin/first-admin-transfer")

export const startFirstAdminTransfer = (recipient_email: string, confirm_recipient_email: string, password: string) =>
  api<FirstAdminTransferRow>("/api/admin/first-admin-transfer", {
    method: "POST",
    body: JSON.stringify({ recipient_email, confirm_recipient_email, password }),
  })

export const cancelFirstAdminTransfer = () => api<{ status: string }>("/api/admin/first-admin-transfer", { method: "DELETE" })

export const acceptFirstAdminTransfer = () => api<{ status: string }>("/api/admin/first-admin-transfer/accept", { method: "POST" })

export const declineFirstAdminTransfer = () => api<{ status: string }>("/api/admin/first-admin-transfer/decline", { method: "POST" })
