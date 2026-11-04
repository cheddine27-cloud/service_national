import { useCallback, useEffect, useState } from 'react'
import { Plus, Trash2, Printer } from 'lucide-react'
import { api } from '../api/client'
import type { OptionalService, Squad, Week } from '../types'
import { Confirm, Empty, ErrorState, Loading } from '../components/ui'

interface Form {
  name: string; date: string; count: number; receiver: string
  week_id: string; squad_id: string; notes: string
}

export default function Optional() {
  const [items, setItems] = useState<OptionalService[]>([])
  const [weeks, setWeeks] = useState<Week[]>([])
  const [squads, setSquads] = useState<Squad[]>([])
  const [weekId, setWeekId] = useState<string>('')
  const [form, setForm] = useState<Form>({
    name: '', date: '', count: 1, receiver: '', week_id: '', squad_id: '', notes: '' })
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [dele, setDele] = useState<OptionalService | null>(null)

  const load = useCallback(() => {
    setErr(null); setBusy(true)
    Promise.all([
      api.optional(weekId === '' ? undefined : Number(weekId)),
      api.weeks(), api.squads(),
    ]).then(([o, w, s]) => { setItems(o); setWeeks(w); setSquads(s) })
      .catch((e: any) => setErr(e.message))
      .finally(() => setBusy(false))
  }, [weekId])
  useEffect(load, [load])

  if (err) return <ErrorState message={err} onRetry={load} />

  const add = async () => {
    if (!form.name.trim()) { alert('اسم الخدمة مطلوب'); return }
    setBusy(true)
    try {
      await api.createOptional({
        name: form.name.trim(),
        date: form.date || null,
        count: form.count,
        receiver: form.receiver || null,
        week_id: form.week_id === '' ? null : Number(form.week_id),
        squad_id: form.squad_id === '' ? null : Number(form.squad_id),
        notes: form.notes || null,
      })
      setForm(f => ({ ...f, name: '', receiver: '', notes: '' }))
      await load()
    } catch (e: any) { alert(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="p-6 max-w-7xl">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold">الخدمات الاختيارية <span className="text-sm text-ink/50 num">({items.length})</span></h1>
        <button className="btn-ghost btn-sm" onClick={async () => {
          const wid = weekId === '' ? null : Number(weekId)
          try { await api.reportOptional(wid, 'open') } catch (e: any) { alert(e.message) }
        }}><Printer size={15} /> طباعة PDF</button>
      </div>

      {/* نموذج الإضافة */}
      <div className="card p-5 mb-4">
        <h2 className="font-bold mb-3 text-sm">إضافة خدمة اختيارية</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div><label className="label">اسم الخدمة *</label>
            <input className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
          <div><label className="label">التاريخ</label>
            <input type="date" className="input num" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} /></div>
          <div><label className="label">العدد</label>
            <input type="number" className="input num" min={0} value={form.count} onChange={e => setForm({ ...form, count: +e.target.value })} /></div>
          <div><label className="label">المستلم</label>
            <input className="input" value={form.receiver} onChange={e => setForm({ ...form, receiver: e.target.value })} /></div>
          <div><label className="label">الأسبوع (اختياري)</label>
            <select className="input" value={form.week_id} onChange={e => setForm({ ...form, week_id: e.target.value })}>
              <option value="">بدون أسبوع</option>
              {weeks.map(w => <option key={w.id} value={w.id} className="num">أسبوع {w.start_date}</option>)}
            </select></div>
          <div><label className="label">الفوج</label>
            <select className="input" value={form.squad_id} onChange={e => setForm({ ...form, squad_id: e.target.value })}>
              <option value="">بدون فوج</option>
              {squads.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select></div>
          <div className="col-span-2"><label className="label">ملاحظات</label>
            <input className="input" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
        </div>
        <div className="mt-3 flex justify-end">
          <button className="btn-primary btn-sm" disabled={busy} onClick={add}><Plus size={15} /> إضافة</button>
        </div>
      </div>

      {/* فلترة */}
      <div className="card p-3 mb-4">
        <select className="input max-w-xs" value={weekId} onChange={e => setWeekId(e.target.value)}>
          <option value="">كل الأسابيع</option>
          {weeks.map(w => <option key={w.id} value={w.id} className="num">أسبوع {w.start_date} ({w.end_date})</option>)}
        </select>
      </div>

      <div className="card">
        {busy ? <Loading /> : items.length === 0 ? (
          <Empty text="لا توجد خدمات اختيارية" hint="أضف خدمة من النموذج أعلاه" />
        ) : (
          <table className="w-full">
            <thead><tr>
              <th className="th">اسم الخدمة</th><th className="th">التاريخ</th><th className="th">العدد</th>
              <th className="th">المستلم</th><th className="th">الفوج</th><th className="th">ملاحظات</th><th className="th w-20"></th>
            </tr></thead>
            <tbody>
              {items.map(o => (
                <tr key={o.id} className="hover:bg-khaki/10">
                  <td className="td font-bold">{o.name}</td>
                  <td className="td num">{o.date ?? '—'}</td>
                  <td className="td num"><span className="badge-count">{o.count}</span></td>
                  <td className="td">{o.receiver ?? '—'}</td>
                  <td className="td">{o.squad_name ? <span className="badge-squad">{o.squad_name}</span> : '—'}</td>
                  <td className="td text-ink/60">{o.notes ?? '—'}</td>
                  <td className="td">
                    <button className="btn-danger btn-sm" onClick={() => setDele(o)}><Trash2 size={13} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {dele && (
        <Confirm title="حذف خدمة اختيارية" text={`حذف "${dele.name}"؟`}
          onCancel={() => setDele(null)} onConfirm={async () => {
            try { await api.deleteOptional(dele.id); setDele(null); await load() } catch (e: any) { alert(e.message) }
          }} />
      )}
    </div>
  )
}
