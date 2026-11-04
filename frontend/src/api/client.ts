// طبقة الاتصال المركزية، تمتد عليها محاولة مستقبلية (Tauri).
// - الافتراضي: /api (proxy لـ Vite → 127.0.0.1:8765، بلا CORS).
// - VITE_API_BASE: لإliği auto direct "http://127.0.0.1:8765/api" apporter حسب
//   الحاجة (مثلاً في Tauri حيث لا يوجد proxy).
// - Mock: VITE_USE_MOCK=1 إظهار شارة على العميل. MOCK غير مصرح به حيال بيانات الإنتاج.

import type {
  Assignment, DashboardData, Group, Health, OptionalService,
  Squad, Settings, Student, Week,
} from '../types'

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'
const MOCK = import.meta.env.VITE_USE_MOCK === '1'

class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (MOCK) throw new ApiError(501, 'وضع MOCK غير مُفعّل في هذه المرحلة - يستخدم بيانات حقيقية فقط')
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(0, 'لا يمكن الوصول إلى الخادم المحلي. تأكد من تشغيل server.py')
  }
  if (res.status === 204) return undefined as T
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json())?.detail ?? detail } catch { /* ignore */ }
    throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json() as Promise<T>
}

const get = <T,>(p: string) => request<T>(p)
const post = <T,>(p: string, body?: unknown) =>
  request<T>(p, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined })
const put = <T,>(p: string, body: unknown) => request<T>(p, { method: 'PUT', body: JSON.stringify(body) })
const patch = <T,>(p: string, body: unknown) => request<T>(p, { method: 'PATCH', body: JSON.stringify(body) })
const del = <T,>(p: string) => request<T>(p, { method: 'DELETE' })

export const api = {
  mock: MOCK,

  health: () => get<Health>('/health'),
  dashboard: () => get<DashboardData>('/dashboard'),

  settings: () => get<Settings>('/settings'),
  saveSettings: (s: Partial<Settings>) => put<{ updated: string[] }>('/settings', s),

  groups: () => get<Group[]>('/groups'),
  squads: () => get<Squad[]>('/squads'),
  createSquad: (group_code: 'A' | 'B', number: number, size = 0, name?: string) =>
    post<Squad>('/squads', { group_code, number, size, name }),
  updateSquad: (id: number, data: Partial<Pick<Squad, 'name' | 'size' | 'number'>>) =>
    patch<Squad>(`/squads/${id}`, data),
  deleteSquad: (id: number) => del<{ deleted: number }>(`/squads/${id}`),
  ensureDefaults: () => post<{ created: number }>('/squads/defaults'),

  students: (squad_id?: number, search?: string) => {
    const q = new URLSearchParams()
    if (squad_id) q.set('squad_id', String(squad_id))
    if (search) q.set('search', search)
    const qs = q.toString()
    return get<Student[]>(`/students${qs ? `?${qs}` : ''}`)
  },
  createStudent: (s: Partial<Student> & { full_name: string }) =>
    post<{ student: Student }>('/students', s),
  updateStudent: (id: number, s: Partial<Student>) =>
    patch<Student>(`/students/${id}`, s),
  deleteStudent: (id: number) => del<{ deleted: number }>(`/students/${id}`),

  weeks: () => get<Week[]>('/weeks'),
  generateWeek: (start_date: string, toilet_count?: number, guard_count?: number) =>
    post<{ week_id: number; assignments: Assignment[] }>('/weeks/generate',
      { start_date, toilet_count, guard_count }),
  week: (id: number) => get<Week & { assignments: Assignment[] }>(`/weeks/${id}`),
  deleteWeek: (id: number) => del<{ deleted: number }>(`/weeks/${id}`),
  patchAssignment: (id: number, data: Partial<Pick<Assignment, 'squad_id' | 'count' | 'notes'>> & { set_squad_null?: boolean }) =>
    patch<Assignment>(`/assignments/${id}`, data),
  upsertAssignment: (weekId: number, dayIndex: number, service: string, data: { squad_id?: number | null; count?: number; notes?: string | null }) =>
    put<Assignment[]>(`/weeks/${weekId}/assignments/${dayIndex}/${service}`, data),

  optional: (week_id?: number) =>
    get<OptionalService[]>(`/optional${week_id ? `?week_id=${week_id}` : ''}`),
  createOptional: (o: Omit<OptionalService, 'id' | 'created_at' | 'squad_name'>) =>
    post<OptionalService>('/optional', o),
  deleteOptional: (id: number) => del<{ deleted: number }>(`/optional/${id}`),

  // PDF: mode=time "open" يفتح النافذة عبر الخادم، "download" يجلب الملف في المتصفح
  reportWeekly: (week_id: number, service: string, mode: 'open' | 'download' | 'print' | 'path' = 'open') =>
    post<{ path: string } | Blob>('/reports/weekly', { week_id, service, mode }),
  reportOptional: (week_id: number | null, mode: 'open' | 'download' | 'print' | 'path' | 'x' = 'open') =>
    post<{ path: string } | Blob>(`/reports/optional?week_id=${week_id ?? ''}&mode=${mode}`, {}),
  reportStudents: (mode: 'open' | 'download' | 'print' | 'path' = 'open') =>
    post<{ path: string } | Blob>(`/reports/students?mode=${mode}`, {}),

  async downloadReport(kind: 'weekly' | 'optional' | 'students', weekId?: number, service?: string) {
    let res: Response
    const base = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'
    if (kind === 'weekly') {
      res = await fetch(`${base}/reports/weekly`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ week_id: weekId, service, mode: 'download' }),
      })
    } else if (kind === 'optional') {
      res = await fetch(`${base}/reports/optional?week_id=${weekId ?? ''}&mode=download`, { method: 'POST' })
    } else {
      res = await fetch(`${base}/reports/students?mode=download`, { method: 'POST' })
    }
    if (!res.ok) throw new ApiError(res.status, 'فشل توليد التقرير')
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `report_${kind}${service ? `_${service}` : ''}.pdf`
    a.click()
    URL.revokeObjectURL(a.href)
  },
}
