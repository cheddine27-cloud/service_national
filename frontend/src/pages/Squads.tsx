import { useCallback, useEffect, useState } from 'react'
import { Plus, Pencil, Trash2, FolderPlus } from 'lucide-react'
import { api } from '../api/client'
import type { Group, Squad } from '../types'
import { Confirm, Empty, ErrorState, Loading, Modal } from '../components/ui'

export default function Squads() {
  const [groups, setGroups] = useState<Group[]>([])
  const [squads, setSquads] = useState<Squad[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [edit, setEdit] = useState<Squad | null>(null)
  const [del, setDel] = useState<Squad | null>(null)

  const load = useCallback(() => {
    setErr(null); setBusy(true)
    Promise.all([api.groups(), api.squads()])
      .then(([g, s]) => { setGroups(g); setSquads(s) })
      .catch((e: any) => setErr(e.message))
      .finally(() => setBusy(false))
  }, [])
  useEffect(load, [load])

  if (err) return <ErrorState message={err} onRetry={load} />
  if (busy && squads.length === 0) return <Loading />

  return (
    <div className="p-6 max-w-6xl">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-bold">الأفواج والمجموعات</h1>
        <div className="flex gap-2">
          <button className="btn-ghost btn-sm" onClick={async () => {
            try {
              const r = await api.ensureDefaults()
              alert(r.created ? `تم إنشاء ${r.created} أفقاج` : 'الأفواج الافتراضية موجودة من قبل')
              load()
            } catch (e: any) { alert(e.message) }
          }}><FolderPlus size={15} /> إنشاء الأفواج الافتراضية (A1-B5)</button>
          <button className="btn-primary btn-sm" onClick={() => setAddOpen(true)}><Plus size={15} /> إضافة فوج</button>
        </div>
      </div>

      {groups.map(g => {
        const list = squads.filter(s => s.group_code === g.code)
        return (
          <div key={g.id} className="card p-5 mb-5">
            <h2 className="font-bold mb-3 text-olive">{g.name} ({g.code})</h2>
            {list.length === 0 ? <Empty text="لا توجد أفواج في هذه المجموعة" /> : (
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="th w-20">الرقم</th><th className="th">الاسم</th>
                    <th className="th w-28">الحجم</th><th className="th w-28">الطلاب</th>
                    <th className="th w-44">إجراءات</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map(s => (
                    <tr key={s.id} className="hover:bg-khaki/10">
                      <td className="td num">{s.number}</td>
                      <td className="td font-bold"><span className="badge-squad">{s.name}</span></td>
                      <td className="td num">{s.size}</td>
                      <td className="td num">{s.students ?? 0}</td>
                      <td className="td">
                        <div className="flex gap-1">
                          <button className="btn-ghost btn-sm" onClick={() => setEdit(s)}><Pencil size={13} /> تعديل</button>
                          <button className="btn-danger btn-sm" onClick={() => setDel(s)}><Trash2 size={13} /> حذف</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )
      })}

      {addOpen && <AddModal onClose={() => setAddOpen(false)} onDone={() => { setAddOpen(false); load() }} />}
      {edit && <EditModal squad={edit} onClose={() => setEdit(null)} onDone={() => { setEdit(null); load() }} />}
      {del && (
        <Confirm title="حذف الفوج"
          text={`سيتم حذف الفوج "${del.name}". سيبقى الطلاب الموجودون فيه بدون فوج (سلوك النظام الحالي). هل تريد المتابعة؟`}
          onCancel={() => setDel(null)} onConfirm={async () => {
            try { await api.deleteSquad(del.id); setDel(null); load() } catch (e: any) { alert(e.message) }
          }} />
      )}
    </div>
  )
}

function AddModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [group, setGroup] = useState<'A' | 'B'>('A')
  const [number, setNumber] = useState(6)
  const [name, setName] = useState('')
  const [size, setSize] = useState(0)
  const [error, setError] = useState<string | null>(null)
  return (
    <Modal title="إضافة فوج جديد" onClose={onClose}>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">المجموعة</label>
          <select className="input" value={group} onChange={e => setGroup(e.target.value as 'A' | 'B')}>
            <option value="A">فوج أ (A)</option><option value="B">فوج ب (B)</option>
          </select>
        </div>
        <div>
          <label className="label">الرقم</label>
          <input type="number" className="input num" min={1} max={99} value={number}
                 onChange={e => setNumber(+e.target.value)} />
        </div>
        <div className="col-span-2">
          <label className="label">الاسم (اختياري — الافتراضي {group}{number})</label>
          <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder={`${group}${number}`} />
        </div>
        <div className="col-span-2">
          <label className="label">الحجم</label>
          <input type="number" className="input num" min={0} value={size} onChange={e => setSize(+e.target.value)} />
        </div>
      </div>
      {error && <p className="text-dzred text-xs mt-3">{error}</p>}
      <div className="flex justify-end gap-2 mt-5">
        <button className="btn-ghost" onClick={onClose}>إلغاء</button>
        <button className="btn-primary" onClick={async () => {
          try { await api.createSquad(group, number, size, name || undefined); onDone() }
          catch (e: any) { setError(e.message) }
        }}>حفظ</button>
      </div>
    </Modal>
  )
}

function EditModal({ squad, onClose, onDone }: { squad: Squad; onClose: () => void; onDone: () => void }) {
  const [name, setName] = useState(squad.name)
  const [size, setSize] = useState(squad.size)
  return (
    <Modal title={`تعديل الفوج ${squad.name}`} onClose={onClose}>
      <div className="space-y-3">
        <div><label className="label">الاسم</label>
          <input className="input" value={name} onChange={e => setName(e.target.value)} /></div>
        <div><label className="label">الحجم</label>
          <input type="number" className="input num" value={size} onChange={e => setSize(+e.target.value)} /></div>
      </div>
      <div className="flex justify-end gap-2 mt-5">
        <button className="btn-ghost" onClick={onClose}>إلغاء</button>
        <button className="btn-primary" onClick={async () => {
          try { await api.updateSquad(squad.id, { name, size }); onDone() }
          catch (e: any) { alert(e.message) }
        }}>حفظ</button>
      </div>
    </Modal>
  )
}
