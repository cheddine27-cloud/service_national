// الشاشة الأساسية: شبكة 7 أيام × 5 خدمات، نافذة توليد، تعديل الخلية، طباعة.

import { useCallback, useEffect, useMemo, useState } from 'react'
import { CalendarPlus, Printer, Trash2, Pencil, FileText, CalendarDays } from 'lucide-react'
import { api } from '../api/client'
import type { Assignment, Service, Squad, Week } from '../types'
import { DAY_NAMES_AR, SERVICE_AR } from '../types'
import { Confirm, Empty, ErrorState, Loading, Modal } from '../components/ui'

const SERVICES: Service[] = ['guard', 'restaurant', 'kitchen', 'cleaning', 'toilet']

function nextSaturday(): string {
  const d = new Date()
  const diff = (6 - d.getDay() + 7) % 7 // السبت = 6
  d.setDate(d.getDate() + diff)
  return d.toISOString().slice(0, 10)
}

export default function Weekly() {
  const [weeks, setWeeks] = useState<Week[]>([])
  const [weekId, setWeekId] = useState<number | null>(null)
  const [week, setWeek] = useState<(Week & { assignments: Assignment[] }) | null>(null)
  const [squads, setSquads] = useState<Squad[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [genOpen, setGenOpen] = useState(false)
  const [dele, setDele] = useState<Week | null>(null)
  const [cell, setCell] = useState<{ day: number; service: Service } | null>(null)

  const load = useCallback(async () => {
    setErr(null); setBusy(true)
    try {
      const [w, sq] = await Promise.all([api.weeks(), api.squads()])
      setWeeks(w); setSquads(sq)
      const target = weekId && w.some(x => x.id === weekId) ? weekId : w[0]?.id ?? null
      setWeekId(target)
      setWeek(target ? await api.week(target) : null)
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }, [weekId])
  useEffect(() => { load() }, [load])

  const refreshWeek = useCallback(async () => {
    if (weekId) setWeek(await api.week(weekId))
  }, [weekId])

  const grid = useMemo(() => {
    const g: Record<number, Partial<Record<Service, Assignment>>> = {}
    for (const a of week?.assignments ?? []) {
      g[a.day_index] = { ...g[a.day_index], [a.service]: a }
    }
    return g
  }, [week])

  if (err) return <ErrorState message={err} onRetry={load} />

  const openReport = async (service: Service | 'optional') => {
    if (!week) return
    try {
      if (service === 'optional') await api.reportOptional(week.id, 'open')
      else await api.reportWeekly(week.id, service, 'open')
    } catch (e: any) { alert(e.message) }
  }

  return (
    <div className="p-6 max-w-7xl">
      {/* شريط التحكم */}
      <div className="flex items-center justify-between gap-3 mb-5 flex-wrap">
        <h1 className="text-xl font-bold">الجدول الأسبوعي</h1>
        <div className="flex gap-2 flex-wrap">
          <select className="input max-w-72 num" value={weekId ?? ''}
                  onChange={e => { setWeekId(e.target.value === '' ? null : +e.target.value) }}
                  disabled={weeks.length === 0}>
            {weeks.length === 0 && <option value="">لا توجد أسابيع</option>}
            {weeks.map(w =>
              <option key={w.id} value={w.id} className="num">
                {w.start_date} ← {w.end_date} (#{w.id})
              </option>)}
          </select>
          <button className="btn-primary btn-sm" onClick={() => setGenOpen(true)}>
            <CalendarPlus size={15} /> توليد أسبوع جديد
          </button>
          {week && <>
            <button className="btn-ghost btn-sm" onClick={() => openReport('guard')}><Printer size={15} /> طباعة حراسة</button>
            <button className="btn-ghost btn-sm" onClick={() => openReport('optional')}><FileText size={15} /> طباعة الاختيارية</button>
            <button className="btn-danger btn-sm" onClick={() => setDele(week)}><Trash2 size={15} /> حذف الأسبوع</button>
          </>}
        </div>
      </div>

      {busy && !week ? <Loading text="جارٍ تحميل الجدول…" /> :
        !week ? <Empty text="لا يوجد أسبوع مولّد" hint="اضغط «توليد أسبوع جديد» للبداية" /> : (
        <div className="card overflow-x-auto">
          <div className="px-5 py-3 border-b border-black/10 flex items-center justify-between bg-khaki/15">
            <div className="flex items-center gap-2">
              <CalendarDays size={16} className="text-olive2" />
              <span className="font-bold num">من {week.start_date} إلى {week.end_date}</span>
            </div>
            <span className="text-xs text-ink/60">انقر أي خلية للتعديل اليدوي (محفوظ مباشرة في قاعدة البيانات)</span>
          </div>
          <table className="w-full">
            <thead>
              <tr>
                <th className="th w-28">اليوم</th><th className="th w-28">التاريخ</th>
                {SERVICES.map(s => <th key={s} className="th">{SERVICE_AR[s]}</th>)}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 7 }).map((_, d) => (
                <tr key={d} className="hover:bg-khaki/5">
                  <td className="td font-bold">{DAY_NAMES_AR[d]}</td>
                  <td className="td num text-ink/40 text-xs">{grid[d]?.guard?.date ?? ''}</td>
                  {SERVICES.map(sn => {
                    const a = grid[d]?.[sn]
                    return (
                      <td key={sn} className="td p-1.5 align-middle"
                          onClick={() => a && setCell({ day: a.day_index, service: sn })}>
                        {a ? (
                          <div className={`rounded-lg border px-2 py-1.5 transition-colors cursor-pointer ${
                            a.squad_name
                              ? 'border-black/10 bg-white hover:border-olive2/60'
                              : 'border-dashed border-black/20 bg-khaki/10 hover:border-olive2/60'}`}>
                            <div className="flex items-center justify-between gap-2">
                              {a.squad_name
                                ? <span className="badge-squad">{a.squad_name}</span>
                                : <span className="text-ink/40 text-xs">— بدون فوج —</span>}
                              <span className="flex items-center gap-1">
                                {a.count > 0 && <span className="badge-count num">{a.count}</span>}
                                {a.notes && <span className="w-2 h-2 rounded-full shrink-0 bg-olive2" title={a.notes} />}
                              </span>
                            </div>
                            {sn === 'toilet' && (
                              <div className="text-[10px] text-dzgreen font-bold mt-1">● خدمة الأسبوع</div>
                            )}
                            <div className="flex items-center gap-1 mt-1 text-[10px] text-ink/40">
                              <Pencil size={9} /> انقر للتعديل
                            </div>
                          </div>
                        ) : <span className="text-ink/30">—</span>}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* نافذة التوليد */}
      {genOpen && (
        <GenerateModal onClose={() => setGenOpen(false)} onDone={(id) => {
          setGenOpen(false); setWeekId(id)
        }} />
      )}

      {/* تعديل خلية */}
      {cell && week && (
        <CellModal week={week} squads={squads} cell={cell}
          onClose={() => setCell(null)} onDone={() => { setCell(null); refreshWeek() }} />
      )}

      {/* حذف أسبوع */}
      {dele && (
        <Confirm title="حذف أسبوع"
          text={`حذف الأسبوع ${dele.start_date} وحذف تعييناته؟ لا يؤثر على الطلاب أو الخدمات الاختيارية المرتبطة.`}
          onCancel={() => setDele(null)} onConfirm={async () => {
            try { await api.deleteWeek(dele.id); setDele(null); setWeekId(null); await load() } catch (e: any) { alert(e.message) }
          }} />
      )}
    </div>
  )
}

function GenerateModal({ onClose, onDone }: { onClose: () => void; onDone: (id: number) => void }) {
  const [start, setStart] = useState(nextSaturday())
  const [toilet, setToilet] = useState<number | ''>('')
  const [guard, setGuard] = useState<number | ''>('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.settings().then(s => {
      if (s.toilet_daily_count) setToilet(+s.toilet_daily_count)
      if (s.guard_daily_count) setGuard(+s.guard_daily_count)
    }).catch(() => {})
  }, [])

  return (
    <Modal title="توليد أسبوع جديد" onClose={onClose}>
      <p className="text-xs text-ink/60 mb-4 leading-5">
        يستخدم التوليد نفس خوارزمية التوزيع العادل في النظام الأصلي — بداية الأسبوع: السبت،
        الخدمات اليومية (حراسة/مطعم/مطبخ/تنظيف) + فوج واحد له خدمة المرحاض طوال الأسبوع.
      </p>
      <div className="space-y-3">
        <div><label className="label">تاريخ السبت (بداية الأسبوع)</label>
          <input type="date" className="input num" value={start} onChange={e => setStart(e.target.value)} /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">عدد المرحاض يوميًا</label>
            <input type="number" className="input num" min={0} max={99} value={toilet}
                   onChange={e => setToilet(e.target.value === '' ? '' : +e.target.value)} /></div>
          <div><label className="label">عدد الحراسة يوميًا</label>
            <input type="number" className="input num" min={0} max={99} value={guard}
                   onChange={e => setGuard(e.target.value === '' ? '' : +e.target.value)} /></div>
        </div>
      </div>
      {error && <p className="text-dzred text-xs mt-3">{error}</p>}
      <div className="flex justify-end gap-2 mt-5">
        <button className="btn-ghost" onClick={onClose}>إلغاء</button>
        <button className="btn-primary" disabled={busy || !start} onClick={async () => {
          setBusy(true); setError(null)
          try {
            const r = await api.generateWeek(start, toilet === '' ? undefined : toilet, guard === '' ? undefined : guard)
            onDone(r.week_id)
          } catch (e: any) { setError(e.message) } finally { setBusy(false) }
        }}>{busy ? 'جارٍ التوليد…' : 'توليد'}</button>
      </div>
    </Modal>
  )
}

function CellModal({ week, squads, cell, onClose, onDone }: {
  week: Week & { assignments: Assignment[] }
  squads: Squad[]
  cell: { day: number; service: Service }
  onClose: () => void; onDone: () => void
}) {
  const a = week.assignments.find(x => x.day_index === cell.day && x.service === cell.service)
  const [squadId, setSquadId] = useState(a?.squad_id ? String(a.squad_id) : '')
  const [count, setCount] = useState(a?.count ?? 0)
  const [notes, setNotes] = useState(a?.notes ?? '')
  const [error, setError] = useState<string | null>(null)

  const save = async () => {
    try {
      if (a) {
        // التعديل اليدوي — نفس سلوك PATCH القديم
        await api.patchAssignment(a.id, {
          squad_id: squadId === '' ? undefined : Number(squadId),
          set_squad_null: squadId === '',
          count,
          notes,
        })
      } else {
        await api.upsertAssignment(week.id, cell.day, cell.service, {
          squad_id: squadId === '' ? null : Number(squadId), count, notes,
        })
      }
      onDone()
    } catch (e: any) { setError(e.message) }
  }

  return (
    <Modal title={`${SERVICE_AR[cell.service]} — ${DAY_NAMES_AR[cell.day]} (${a?.date ?? ''})`} onClose={onClose}>
      <div className="space-y-3">
        <div><label className="label">الفوج</label>
          <select className="input" value={squadId} onChange={e => setSquadId(e.target.value)}>
            <option value="">— بدون فوج —</option>
            {squads.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select></div>
        <div><label className="label">العدد</label>
          <input type="number" className="input num" min={0} max={999} value={count}
                 onChange={e => setCount(+e.target.value)} /></div>
        <div><label className="label">ملاحظات</label>
          <input className="input" value={notes} onChange={e => setNotes(e.target.value)} /></div>
      </div>
      {error && <p className="text-dzred text-xs mt-3">{error}</p>}
      <div className="flex justify-end gap-2 mt-5">
        <button className="btn-ghost" onClick={onClose}>إلغاء</button>
        <button className="btn-primary" onClick={save}>حفظ</button>
      </div>
    </Modal>
  )
}
