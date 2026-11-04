import { useCallback, useEffect, useState } from 'react'
import { Plus, Pencil, Trash2, Printer, Search } from 'lucide-react'
import { api } from '../api/client'
import type { Squad, Student } from '../types'
import { Confirm, Empty, ErrorState, Loading, Modal } from '../components/ui'

const FIELDS: { key: string; label: string; type?: string; wide?: boolean }[] = [
  { key: 'full_name', label: 'الاسم الكامل *' },
  { key: 'father_name', label: 'اسم الأب' },
  { key: 'national_id', label: 'رقم التعريف الوطني' },
  { key: 'birth_date', label: 'تاريخ الميلاد', type: 'date' },
  { key: 'phone', label: 'الهاتف' },
  { key: 'address', label: 'العنوان', wide: true },
  { key: 'blood_type', label: 'فصيلة الدم' },
  { key: 'rank', label: 'الرتبة' },
  { key: 'enlistment_date', label: 'تاريخ الالتحاق', type: 'date' },
  { key: 'notes', label: 'ملاحظات', wide: true },
]

export default function Students() {
  const [students, setStudents] = useState<Student[]>([])
  const [squads, setSquads] = useState<Squad[]>([])
  const [search, setSearch] = useState('')
  const [squadId, setSquadId] = useState<number | ''>('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [modal, setModal] = useState<{ open: boolean; student: Student | null }>({ open: false, student: null })
  const [dele, setDele] = useState<Student | null>(null)

  const load = useCallback(() => {
    setErr(null); setBusy(true)
    Promise.all([
      api.students(squadId === '' ? undefined : squadId, search || undefined),
      api.squads(),
    ]).then(([st, sq]) => { setStudents(st); setSquads(sq) })
      .catch((e: any) => setErr(e.message))
      .finally(() => setBusy(false))
  }, [squadId, search])
  useEffect(load, [load])

  if (err) return <ErrorState message={err} onRetry={load} />

  return (
    <div className="p-6 max-w-7xl">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold">إدارة الطلاب <span className="text-sm text-ink/50 num">({students.length})</span></h1>
        <div className="flex gap-2">
          <button className="btn-ghost btn-sm" onClick={async () => {
            try { await api.downloadReport('students') } catch (e: any) { alert(e.message) }
          }}><Printer size={15} /> طباعة القائمة (PDF)</button>
          <button className="btn-primary btn-sm" onClick={() => setModal({ open: true, student: null })}>
            <Plus size={15} /> إضافة طالب
          </button>
        </div>
      </div>

      <div className="card p-3 mb-4 flex flex-wrap gap-2 items-center">
        <div className="relative flex-1 min-w-60">
          <Search size={15} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink/40" />
          <input className="input pr-9" placeholder="بحث بالاسم أو رقم التعريف…"
                 value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="input w-48" value={squadId}
                onChange={e => setSquadId(e.target.value === '' ? '' : Number(e.target.value))}>
          <option value="">كل الأفواج</option>
          {squads.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </div>

      <div className="card overflow-x-auto">
        {busy ? <Loading /> : students.length === 0 ? (
          <Empty text="لا يوجد طلاب" hint="أضف أول طالب أو عدّل الفلتر/البحث" />
        ) : (
          <table className="w-full">
            <thead>
              <tr>
                <th className="th">الاسم الكامل</th><th className="th">الفوج</th>
                <th className="th">الرتبة</th><th className="th">رقم التعريف</th>
                <th className="th">فصيلة الدم</th><th className="th">الهاتف</th>
                <th className="th w-36">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {students.map(st => (
                <tr key={st.id} className="hover:bg-khaki/10">
                  <td className="td font-bold">{st.full_name}</td>
                  <td className="td">{st.squad_name ?? '—'}</td>
                  <td className="td">{st.rank ?? '—'}</td>
                  <td className="td num">{st.national_id ?? '—'}</td>
                  <td className="td">{st.blood_type ?? '—'}</td>
                  <td className="td num text-left">{st.phone ?? '—'}</td>
                  <td className="td">
                    <div className="flex gap-1">
                      <button className="btn-ghost btn-sm" onClick={() => setModal({ open: true, student: st })}><Pencil size={13} /> تعديل</button>
                      <button className="btn-danger btn-sm" onClick={() => setDele(st)}><Trash2 size={13} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modal.open && (
        <StudentModal student={modal.student} squads={squads}
          onClose={() => setModal({ open: false, student: null })}
          onDone={() => { setModal({ open: false, student: null }); load() }} />
      )}
      {dele && (
        <Confirm title="حذف طالب" text={`حذف الطالب "${dele.full_name}" نهائيًا؟`}
          onCancel={() => setDele(null)} onConfirm={async () => {
            try { await api.deleteStudent(dele.id); setDele(null); load() } catch (e: any) { alert(e.message) }
          }} />
      )}
    </div>
  )
}

function StudentModal({ student, squads, onClose, onDone }: {
  student: Student | null; squads: Squad[]; onClose: () => void; onDone: () => void
}) {
  const [form, setForm] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {}
    for (const f of FIELDS) init[f.key] = (student?.[f.key as keyof Student] as string | null) ?? ''
    return init
  })
  const [squadId, setSquadId] = useState<string>(student?.squad_id ? String(student.squad_id) : '')
  const [error, setError] = useState<string | null>(null)

  const save = async () => {
    if (!form.full_name?.trim()) { setError('الاسم الكامل مطلوب'); return }
    const data: Record<string, unknown> = {}
    for (const f of FIELDS) data[f.key] = form[f.key] === '' ? null : form[f.key]
    data.squad_id = squadId === '' ? null : Number(squadId)
    try {
      if (student) await api.updateStudent(student.id, data)
      else await api.createStudent({ full_name: data.full_name as string, ...data } as any)
      onDone()
    } catch (e: any) { setError(e.message) }
  }

  return (
    <Modal title={student ? `تعديل الطالب: ${student.full_name}` : 'إضافة طالب جديد'} onClose={onClose} wide>
      {/* حوار طويل مع تمرير عمودي كما في المتطلبات */}
      <div className="grid grid-cols-2 gap-3">
        {FIELDS.map(f => (
          <div key={f.key} className={f.wide ? 'col-span-2' : ''}>
            <label className="label">{f.label}</label>
            <input className="input" type={f.type ?? 'text'}
                   value={form[f.key]}
                   onChange={e => setForm(v => ({ ...v, [f.key]: e.target.value }))} />
          </div>
        ))}
        <div>
          <label className="label">الفوج</label>
          <select className="input" value={squadId} onChange={e => setSquadId(e.target.value)}>
            <option value="">بدون فوج</option>
            {squads.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
      </div>
      {error && <p className="text-dzred text-xs mt-3">{error}</p>}
      <div className="flex justify-end gap-2 mt-5">
        <button className="btn-ghost" onClick={onClose}>إلغاء</button>
        <button className="btn-primary" onClick={save}>حفظ</button>
      </div>
    </Modal>
  )
}
