import { useCallback, useEffect, useState } from 'react'
import { Printer, Download, FileText } from 'lucide-react'
import { api } from '../api/client'
import type { Week } from '../types'
import { Empty, ErrorState, Loading } from '../components/ui'

const REPORTS = [
  { key: 'guard', label: 'قائمة الحراسة (أسبوعية)', needWeek: true },
  { key: 'restaurant', label: 'قائمة خدمة المطعم', needWeek: true },
  { key: 'kitchen', label: 'قائمة خدمة المطبخ', needWeek: true },
  { key: 'cleaning', label: 'قائمة خدمة التنظيف', needWeek: true },
  { key: 'toilet', label: 'قائمة تنظيف المرحاض', needWeek: true },
  { key: 'optional', label: 'الخدمات الاختيارية', needWeek: true },
  { key: 'students', label: 'قائمة الطلاب', needWeek: false },
] as const

export default function Reports() {
  const [weeks, setWeeks] = useState<Week[]>([])
  const [weekId, setWeekId] = useState<number | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(() => {
    setErr(null)
    api.weeks().then(w => {
      setWeeks(w); setWeekId(w[0]?.id ?? null)
    }).catch((e: any) => setErr(e.message))
  }, [])
  useEffect(load, [load])

  if (err) return <ErrorState message={err} onRetry={load} />
  if (!weeks.length) return (
    <div className="p-6 max-w-4xl">
      <Empty text="لا توجد أسابيع مولّدة بعد" hint="التقارير الأسبوعية تتطلب أسبوعًا (قائمة الطلاب لا تتطلب)" />
    </div>
  )

  const openReport = async (key: string) => {
    setBusy(key)
    try {
      if (key === 'students') await api.reportStudents('open')
      else if (key === 'optional') await api.reportOptional(weekId, 'open')
      else await api.reportWeekly(weekId!, key, 'open')
      alert('تم توليد التقرير وفتح ملف PDF على جهازك (يفتح تلقائيًا). للحصول على نسخة في المتصفح استخدم زر «تحميل».')
    } catch (e: any) { alert(e.message) } finally { setBusy(null) }
  }

  const downloadReport = async (key: string) => {
    setBusy(key + '_d')
    try {
      if (key === 'students') await api.downloadReport('students')
      else if (key === 'optional') await api.downloadReport('optional', weekId ?? undefined)
      else await api.downloadReport('weekly', weekId ?? undefined, key)
    } catch (e: any) { alert(e.message) } finally { setBusy(null) }
  }

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-xl font-bold mb-1">التقارير والطباعة (PDF)</h1>
      <p className="text-sm text-ink/60 mb-5">التقارير السبعة بنفس منطق الطباعة الأصلي مع خانات التوقيع.</p>

      <div className="card p-3 mb-5 flex items-center gap-3">
        <span className="text-sm font-medium">الأسبوع:</span>
        <select className="input max-w-64 num" value={weekId ?? ''} onChange={e => setWeekId(+e.target.value)}>
          {weeks.map(w => <option key={w.id} value={w.id} className="num">{w.start_date} ← {w.end_date}</option>)}
        </select>
      </div>

      <div className="space-y-3">
        {REPORTS.map(r => {
          const disabled = busy !== null || (r.needWeek && weekId === null)
          return (
            <div key={r.key} className="card p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText size={18} className="text-olive2" />
                <div>
                  <div className="font-bold text-sm">{r.label}</div>
                  {r.needWeek && weekId === null && <div className="text-xs text-dzred">يتطلب اختيار أسبوع</div>}
                </div>
              </div>
              <div className="flex gap-2">
                <button className="btn-ghost btn-sm" disabled={disabled}
                  onClick={() => openReport(r.key)}>
                  <Printer size={14} /> {busy === r.key ? 'جارٍ التوليد…' : 'فتح نسخة PDF'}
                </button>
                <button className="btn-primary btn-sm" disabled={disabled}
                  onClick={() => downloadReport(r.key)}>
                  <Download size={14} /> {busy === r.key + '_d' ? '…' : 'تحميل'}
                </button>
              </div>
            </div>
          )
        })}
      </div>
      {busy && <Loading text="جارٍ توليد PDF…" />}
    </div>
  )
}
