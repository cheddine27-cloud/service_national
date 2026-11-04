import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CalendarPlus, UserRound, Printer, CalendarDays, RefreshCw, Users } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { api } from '../api/client'
import type { DashboardData, Week } from '../types'
import { Empty, ErrorState, Loading } from '../components/ui'

const DAY_AR = ['السبت', 'الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة']

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [weeks, setWeeks] = useState<Week[]>([])
  const [err, setErr] = useState<string | null>(null)
  const nav = useNavigate()

  const load = useCallback(() => {
    setErr(null); setData(null)
    Promise.all([api.dashboard(), api.weeks()])
      .then(([d, w]) => { setData(d); setWeeks(w) })
      .catch(e => setErr(e.message))
  }, [])
  useEffect(load, [load])

  if (err) return <ErrorState message={err} onRetry={load} />
  if (!data) return <Loading />

  const cards = [
    { label: 'إجمالي الطلاب', value: data.counts.students, icon: UserRound, to: '/students' },
    { label: 'الأفواج', value: data.counts.squads, icon: Users, to: '/squads' },
    { label: 'الأسابيع المولّدة', value: data.counts.weeks, icon: CalendarDays, to: '/weekly' },
    { label: 'آخر أسبوع (الاختيارية)', value: data.latest_week ? data.latest_week.optional_count : 0, icon: Printer, to: '/optional' },
  ]

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <h1 className="text-xl font-bold">لوحة التحكم</h1>

      {/* بطاقات عمليات */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map(c => (
          <button key={c.label} onClick={() => nav(c.to)}
            className="card p-5 text-right hover:border-olive2/50 transition-colors">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold num">{c.value}</div>
                <div className="text-xs text-ink/60 mt-1">{c.label}</div>
              </div>
              <c.icon size={26} className="text-olive2" />
            </div>
          </button>
        ))}
      </div>

      {/* إجراءات سريعة */}
      <div className="card p-5">
        <h2 className="font-bold mb-4">إجراءات سريعة</h2>
        <div className="flex flex-wrap gap-3">
          <button className="btn-primary" onClick={() => nav('/weekly')}>
            <CalendarPlus size={16} /> توليد أسبوع جديد
          </button>
          <button className="btn-ghost" onClick={() => nav('/students')}>
            <UserRound size={16} /> إدارة الطلاب
          </button>
          <button className="btn-ghost" onClick={() => api.downloadReport('students').catch(e => alert(e.message))}>
            <Printer size={16} /> طباعة قائمة الطلاب
          </button>
          <button className="btn-ghost" onClick={load}><RefreshCw size={16} /> تحديث</button>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* أعداد الطلاب لكل فوج */}
        <div className="card p-5">
          <h2 className="font-bold mb-4">أعداد الطلاب حسب الفوج</h2>
          {data.students_per_squad.every(s => !s.students) ? (
            <Empty text="لا يوجد طلاب بعد" hint="أضف الطلاب من شاشة إدارة الطلاب" />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.students_per_squad}>
                <CartesianGrid strokeDasharray="3 3" stroke="#00000011" />
                <XAxis dataKey="squad_name" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="students" name="عدد الطلاب" fill="#556B2F" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* آخر أسبوع */}
        <div className="card p-5">
          <h2 className="font-bold mb-4">آخر أسبوع مولّد</h2>
          {data.latest_week ? (
            <>
              <div className="text-sm text-ink/70 mb-3 num">
                من {data.latest_week.week.start_date} إلى {data.latest_week.week.end_date}
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr><th className="th">اليوم</th><th className="th">حراسة</th><th className="th">مطبخ</th><th className="th">تنظيف</th></tr>
                </thead>
                <tbody>
                  {Array.from({ length: 7 }).map((_, d) => {
                    const row = data.latest_week!.assignments.filter(a => a.day_index === d)
                    const s = (t: string) => row.find(x => x.service === t)?.squad_name ?? '—'
                    return (
                      <tr key={d} className="hover:bg-khaki/10">
                        <td className="td">{DAY_AR[d]}</td>
                        <td className="td">{s('guard')}</td>
                        <td className="td">{s('kitchen')}</td>
                        <td className="td">{s('cleaning')}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <button className="btn-ghost mt-4" onClick={() => nav('/weekly')}>عرض الجدول كاملاً</button>
            </>
          ) : (
            <Empty text="لا توجد أسابيع مولّدة بعد" hint="ابدأ بتوليد أسبوع من الجدول الأسبوعي" />
          )}
        </div>
      </div>
    </div>
  )
}
