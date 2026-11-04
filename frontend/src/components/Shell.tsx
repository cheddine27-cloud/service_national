// الهيكل العام RTL: عمود جانبي يمين + شريط علوي. جاهز للتكامل المستقبلي في Tauri.

import { ReactNode, useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Users, UserRound, Star, CalendarDays, Table2,
  FileText, Settings as SettingsIcon, Database, CircleDot,
} from 'lucide-react'
import { api } from '../api/client'
import type { Health } from '../types'
import { MockBanner } from './ui'

const NAV = [
  { to: '/dashboard', label: 'لوحة التحكم', icon: LayoutDashboard },
  { to: '/squads', label: 'الأفواج والمجموعات', icon: Users },
  { to: '/students', label: 'إدارة الطلاب', icon: UserRound },
  { to: '/optional', label: 'الخدمات الاختيارية', icon: Star },
  { to: '/weekly', label: 'الجدول الأسبوعي', icon: CalendarDays },
  { to: '/editor', label: 'محرر الجدول', icon: Table2 },
  { to: '/reports', label: 'التقارير والطباعة', icon: FileText },
  { to: '/settings', label: 'الإعدادات', icon: SettingsIcon },
] as const

export default function Shell({ children }: { children: ReactNode }) {
  const [health, setHealth] = useState<Health | null>(null)
  const loc = useLocation()

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null))
  }, [loc.pathname])

  const active = NAV.find(n => loc.pathname.startsWith(n.to))?.label

  return (
    <div className="h-full flex flex-col">
      <MockBanner />
      {/* شريط علوي */}
      <header className="bg-olive text-white px-5 py-3 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-dzgreen flex items-center justify-center font-bold text-lg">★</div>
          <div>
            <div className="font-bold leading-5">نظام إدارة الخدمة الوطنية</div>
            <div className="text-[11px] text-white/70">{health?.unit_name || 'تنظيم - متابعة - إنضباط'}</div>
          </div>
        </div>
        <div className="text-sm text-white/85 flex items-center gap-4">
          <span className="hidden md:block">{active}</span>
          <span className={`flex items-center gap-1.5 text-xs rounded-full px-2.5 py-1 ${
            health ? 'bg-white/10 text-emerald-200' : 'bg-dzred/80 text-white'}`}>
            <Database size={13} />
            {health
              ? (health.db_exists ? `DB متصلة (${health.mode})` : 'DB غير موجودة!')
              : 'الخادم غير متاح'}
          </span>
        </div>
      </header>

      <div className="flex-1 flex min-h-0">
        {/* عمود جانبي يمين (RTL) */}
        <aside className="w-64 bg-forest text-white/85 shrink-0 flex flex-col">
          <nav className="flex-1 py-3">
            {NAV.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-5 py-3 text-sm border-r-2 transition-colors ${
                    isActive
                      ? 'bg-khaki/15 text-white border-dzgreen font-bold'
                      : 'border-transparent hover:bg-white/5'}`}>
                <Icon size={18} />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="p-4 text-[10px] text-white/40 border-t border-white/10 leading-5">
            <div className="flex items-center gap-1.5"><CircleDot size={11} /> إصدار 1.0 (معاينة متصفح)</div>
            <span dir="ltr" className="block text-left">{api.mock ? 'MOCK' : ''} localhost:5173 → 127.0.0.1:8765</span>
          </div>
        </aside>

        {/* المحتوى */}
        <main className="flex-1 overflow-y-auto bg-ivory min-w-0">{children}</main>
      </div>
    </div>
  )
}
