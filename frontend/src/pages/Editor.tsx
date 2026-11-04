// محرر الجدول: عرض مسطح لكل التعيينات مع تحرير مباشر (PATCH لكل صف).

import { useCallback, useEffect, useState } from 'react'
import { Save, Table2 } from 'lucide-react'
import { api } from '../api/client'
import type { Assignment, Squad, Week } from '../types'
import { DAY_NAMES_AR, SERVICE_AR } from '../types'
import { Empty, ErrorState, Loading } from '../components/ui'

export default function Editor() {
  const [weeks, setWeeks] = useState<Week[]>([])
  const [weekId, setWeekId] = useState<number | null>(null)
  const [week, setWeek] = useState<(Week & { assignments: Assignment[] }) | null>(null)
  const [squads, setSquads] = useState<Squad[]>([])
  const [drafts, setDrafts] = useState<Record<number, { squad: string; count: number; notes: string }>>({})
  const [savedIds, setSavedIds] = useState<Set<number>>(new Set())
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setErr(null); setBusy(true)
    try {
      const [w, sq] = await Promise.all([api.weeks(), api.squads()])
      setWeeks(w); setSquads(sq)
      const target = weekId && w.some(x => x.id === weekId) ? weekId : w[0]?.id ?? null
      setWeekId(target)
      const wk = target ? await api.week(target) : null
      setWeek(wk)
      const d: typeof drafts = {}
      for (const a of wk?.assignments ?? [])
        d[a.id] = { squad: a.squad_id ? String(a.squad_id) : '', count: a.count, notes: a.notes ?? '' }
      setDrafts(d); setSavedIds(new Set())
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }, [weekId])
  useEffect(() => { load() }, [load])

  if (err) return <ErrorState message={err} onRetry={load} />

  const saveRow = async (id: number) => {
    const d = drafts[id]
    try {
      await api.patchAssignment(id, {
        squad_id: d.squad === '' ? undefined : Number(d.squad),
        set_squad_null: d.squad === '',
        count: d.count,
        notes: d.notes,
      })
      setSavedIds(prev => new Set(prev).add(id))
    } catch (e: any) { alert(e.message) }
  }

  return (
    <div className="p-6 max-w-7xl">
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <h1 className="text-xl font-bold">محرر الجدول</h1>
        <select className="input max-w-72 num" value={weekId ?? ''} disabled={!weeks.length}
                onChange={e => setWeekId(e.target.value === '' ? null : +e.target.value)}>
          {weeks.map(w => <option key={w.id} value={w.id} className="num">{w.start_date} ← {w.end_date}</option>)}
        </select>
      </div>

      {busy ? <Loading /> : !week ? <Empty text="لا توجد أسابيع" /> : (
        <div className="card overflow-x-auto">
          <div className="px-5 py-3 border-b border-black/10 bg-khaki/15 flex items-center gap-2 text-xs text-ink/60">
            <Table2 size={14} /> عدّل القيم ثم اضغط «حفظ» على الصف — تعديل يدوي حقيقي في قاعدة البيانات
          </div>
          <table className="w-full">
            <thead><tr>
              <th className="th">اليوم</th><th className="th">الخدمة</th><th className="th">الفوج</th>
              <th className="th w-20">العدد</th><th className="th">ملاحظات</th><th className="th w-24"></th>
            </tr></thead>
            <tbody>
              {week.assignments.map(a => {
                const d = drafts[a.id] ?? { squad: String(a.squad_id ?? ''), count: a.count, notes: a.notes ?? '' }
                const isSaved = savedIds.has(a.id)
                return (
                  <tr key={a.id} className={isSaved ? 'bg-dzgreen/5' : 'hover:bg-khaki/5'}>
                    <td className="td font-bold">{DAY_NAMES_AR[a.day_index]}<span className="text-[10px] text-ink/40 num block">{a.date}</span></td>
                    <td className="td"><span className="badge-squad">{SERVICE_AR[a.service]}</span></td>
                    <td className="td">
                      <select className="input py-1 text-xs" value={d.squad}
                              onChange={e => setDrafts(ds => ({ ...ds, [a.id]: { ...d, squad: e.target.value } }))}>
                        <option value="">— بدون فوج —</option>
                        {squads.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                      </select>
                    </td>
                    <td className="td">
                      <input type="number" className="input py-1 num" min={0} max={999} value={d.count}
                             onChange={e => setDrafts(ds => ({ ...ds, [a.id]: { ...d, count: +e.target.value } }))} />
                    </td>
                    <td className="td">
                      <input className="input py-1 text-xs" value={d.notes}
                             onChange={e => setDrafts(ds => ({ ...ds, [a.id]: { ...d, notes: e.target.value } }))} />
                    </td>
                    <td className="td">
                      <button className="btn-ghost btn-sm" onClick={() => saveRow(a.id)}>
                        <Save size={13} /> {isSaved ? 'محفوظ ✓' : 'حفظ'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
