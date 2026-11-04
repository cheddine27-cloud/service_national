import { useCallback, useEffect, useState } from 'react'
import { Save, Database, Lock } from 'lucide-react'
import { api } from '../api/client'
import type { Health, Settings } from '../types'
import { ErrorState, Loading } from '../components/ui'

export default function Settings() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const load = useCallback(() => {
    setErr(null)
    Promise.all([api.settings(), api.health()])
      .then(([s, h]) => { setSettings(s); setHealth(h) })
      .catch((e: any) => setErr(e.message))
  }, [])
  useEffect(load, [load])

  if (err) return <ErrorState message={err} onRetry={load} />
  if (!settings) return <Loading />

  const set = (k: keyof Settings, v: string) => setSettings(s => ({ ...s, [k]: v }))

  const save = async () => {
    try {
      await api.saveSettings({
        unit_name: settings.unit_name,
        toilet_daily_count: settings.toilet_daily_count
          ? String(+settings.toilet_daily_count) : undefined,
        guard_daily_count: settings.guard_daily_count
          ? String(+settings.guard_daily_count) : undefined,
      })
      setSaved(true); setTimeout(() => setSaved(false), 2500)
    } catch (e: any) { alert(e.message) }
  }

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <h1 className="text-xl font-bold">الإعدادات</h1>

      <div className="card p-5">
        <h2 className="font-bold mb-4 text-sm">إعدادات الوحدة</h2>
        <div className="space-y-3">
          <div><label className="label">اسم الوحدة (يظهر في رؤوس التقارير)</label>
            <input className="input" value={settings.unit_name ?? ''}
                   onChange={e => set('unit_name', e.target.value)} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">عدد المرحاض يوميًا (افتراضي 3)</label>
              <input type="number" className="input num" min={0} max={99}
                     value={settings.toilet_daily_count ?? ''}
                     onChange={e => set('toilet_daily_count', e.target.value)} /></div>
            <div><label className="label">عدد الحراسة يوميًا (افتراضي 4)</label>
              <input type="number" className="input num" min={0} max={99}
                     value={settings.guard_daily_count ?? ''}
                     onChange={e => set('guard_daily_count', e.target.value)} /></div>
          </div>
          <div><label className="label">بداية الأسبوع (ثابتة — اتفاقية النظام)</label>
            <input className="input bg-khaki/20" value="السبت" disabled /></div>
        </div>
        <div className="flex items-center gap-3 mt-5">
          <button className="btn-primary" onClick={save}><Save size={16} /> حفظ الإعدادات</button>
          {saved && <span className="text-xs font-bold text-dzgreen">تم الحفظ ✓</span>}
        </div>
      </div>

      <div className="card p-5">
        <h2 className="font-bold mb-4 text-sm">قاعدة البيانات</h2>
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <Database size={16} className="text-olive2" />
            <span dir="ltr" className="num text-xs bg-khaki/20 rounded px-2 py-1 break-all">
              {health?.db_path ?? '—'}
            </span>
          </div>
          <div className="text-xs text-ink/60">
            الحالة: {health?.db_exists ? 'متصلة ✓' : 'الملف غير موجود ✗'} ·
            الوضع: {health?.mode} ·
            المسار موصول عبر متغير NS_DB_PATH عند تشغيل الخادم
          </div>
          <div className="flex items-start gap-2 text-[11px] text-ink/50 mt-2 border-r-2 border-khaki pr-3">
            <Lock size={13} className="shrink-0 mt-0.5" />
            <p>لا يقوم الخادم أبدًا بإنشاء أو تعديل قاعدة الإنتاج تلقائيًا. يبقى تطبيق Tkinter القديم يعمل
               على نفس قاعدة البيانات دون أي تغيير.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
