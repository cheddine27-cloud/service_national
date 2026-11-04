// أنواع مستمدة من مخطط قاعدة البيانات الحقيقي (لا تغيير في SCHEMA)

export type Service = 'guard' | 'restaurant' | 'kitchen' | 'cleaning' | 'toilet'

export const SERVICE_AR: Record<Service, string> = {
  guard: 'الحراسة',
  restaurant: 'المطعم',
  kitchen: 'المطبخ',
  cleaning: 'التنظيف',
  toilet: 'المرحاض',
}

export const DAY_NAMES_AR = ['السبت', 'الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة']

export interface Group { id: number; code: string; name: string }
export interface Squad { id: number; group_id: number; number: number; name: string; size: number; group_code: string; group_name: string; students?: number }
export interface Student {
  id: number; squad_id: number | null; full_name: string; father_name?: string | null
  national_id?: string | null; birth_date?: string | null; phone?: string | null
  address?: string | null; blood_type?: string | null; rank?: string | null
  enlistment_date?: string | null; notes?: string | null; created_at: string
  squad_name?: string | null
}
export interface Week { id: number; start_date: string; end_date: string; created_at: string; notes?: string | null }
export interface Assignment {
  id: number; week_id: number; day_index: number; date: string
  service: Service; squad_id: number | null; count: number; notes?: string | null
  squad_name?: string | null
}
export interface OptionalService {
  id: number; week_id: number | null; date: string | null; name: string; count: number
  receiver?: string | null; squad_id: number | null; notes?: string | null; created_at: string
  squad_name?: string | null
}
export interface Settings { unit_name?: string; toilet_daily_count?: string; guard_daily_count?: string; week_start?: string }
export interface Health {
  status: string; mode: string; db_path: string; db_exists: boolean; unit_name?: string | null
}
export interface DashboardData {
  counts: { students: number; squads: number; weeks: number }
  latest_week: { week: Week; assignments: Assignment[]; optional_count: number } | null
  students_per_squad: { id: number; squad_name: string; group_code: string; students: number }[]
}
