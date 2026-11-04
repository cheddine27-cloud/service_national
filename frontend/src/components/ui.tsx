// Shared UI primitives: Banner, Loading, ErrorState, Empty, Modal, ConfirmDialog

import { ReactNode } from 'react'
import { AlertTriangle, Loader2, X, XCircle, Inbox } from 'lucide-react'
import { api } from '../api/client'

export function MockBanner() {
  if (!api.mock) return null
  return (
    <div className="bg-dzred text-white text-center text-sm py-1.5 font-bold">
      ⚠ وضع بيانات وهمية (MOCK) — ليست بيانات حقيقية
    </div>
  )
}

export function Loading({ text = 'جارٍ التحميل…' }: { text?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-20 text-ink/60">
      <Loader2 className="animate-spin" size={22} />
      <span>{text}</span>
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card p-8 m-6 text-center">
      <XCircle className="mx-auto text-dzred mb-3" size={36} />
      <p className="font-bold mb-1">حدث خطأ</p>
      <p className="text-sm text-ink/60 mb-4">{message}</p>
      {onRetry && <button className="btn-ghost" onClick={onRetry}>إعادة المحاولة</button>}
    </div>
  )
}

export function Empty({ text, hint }: { text: string; hint?: string }) {
  return (
    <div className="text-center py-16 text-ink/50">
      <Inbox size={36} className="mx-auto mb-3" />
      <p className="font-medium">{text}</p>
      {hint && <p className="text-xs mt-1">{hint}</p>}
    </div>
  )
}

export function Modal({ title, onClose, children, wide }: {
  title: string; onClose: () => void; children: ReactNode; wide?: boolean
}) {
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
         onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className={`card max-h-[85vh] overflow-y-auto ${wide ? 'w-[720px] max-w-full' : 'w-[440px] max-w-full'}`}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-black/10 sticky top-0 bg-white">
          <h3 className="font-bold">{title}</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-black/5"><X size={18} /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

export function Confirm({ title, text, onCancel, onConfirm, danger = true }: {
  title: string; text: string; onCancel: () => void; onConfirm: () => void; danger?: boolean
}) {
  return (
    <Modal title={title} onClose={onCancel}>
      <div className="flex items-start gap-3 mb-5">
        {danger && <AlertTriangle className="text-dzred shrink-0 mt-0.5" size={20} />}
        <p className="text-sm leading-6">{text}</p>
      </div>
      <div className="flex gap-2 justify-end">
        <button className="btn-ghost" onClick={onCancel}>إلغاء</button>
        <button className={danger ? 'btn-danger' : 'btn-primary'} onClick={onConfirm}>تأكيد</button>
      </div>
    </Modal>
  )
}
