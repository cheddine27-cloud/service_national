import { Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import Dashboard from './pages/Dashboard'
import Squads from './pages/Squads'
import Students from './pages/Students'
import Optional from './pages/Optional'
import Weekly from './pages/Weekly'
import Editor from './pages/Editor'
import Reports from './pages/Reports'
import Settings from './pages/Settings'

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/squads" element={<Squads />} />
        <Route path="/students" element={<Students />} />
        <Route path="/optional" element={<Optional />} />
        <Route path="/weekly" element={<Weekly />} />
        <Route path="/editor" element={<Editor />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Shell>
  )
}
