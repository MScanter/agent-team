import { Routes, Route } from 'react-router-dom'
import Layout from './components/Common/Layout'
import HomePage from './pages/HomePage'
import AgentsPage from './pages/AgentsPage'
import TeamsPage from './pages/TeamsPage'
import ExecutionPage from './pages/ExecutionPage'
import ModelConfigManager from './components/ModelConfig/ModelConfigManager'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="agents" element={<AgentsPage />} />
        <Route path="teams" element={<TeamsPage />} />
        <Route path="execution" element={<ExecutionPage />} />
        <Route path="execution/:id" element={<ExecutionPage />} />
        <Route path="models" element={<ModelConfigManager />} />
      </Route>
    </Routes>
  )
}

export default App
