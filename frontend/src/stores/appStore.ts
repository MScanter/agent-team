import { create } from 'zustand'
import type { Agent, Team, Execution } from '@/types'

interface AppState {
  // UI state
  sidebarOpen: boolean
  toggleSidebar: () => void

  // Selected items
  selectedAgent: Agent | null
  selectedTeam: Team | null
  selectedExecution: Execution | null
  setSelectedAgent: (agent: Agent | null) => void
  setSelectedTeam: (team: Team | null) => void
  setSelectedExecution: (execution: Execution | null) => void

  // Modals
  agentModalOpen: boolean
  teamModalOpen: boolean
  executionModalOpen: boolean
  openAgentModal: (agent?: Agent) => void
  openTeamModal: (team?: Team) => void
  openExecutionModal: (team?: Team) => void
  closeModals: () => void

  // Execution state
  activeExecutionId: string | null
  setActiveExecution: (id: string | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  selectedAgent: null,
  selectedTeam: null,
  selectedExecution: null,
  setSelectedAgent: (agent) => set({ selectedAgent: agent }),
  setSelectedTeam: (team) => set({ selectedTeam: team }),
  setSelectedExecution: (execution) => set({ selectedExecution: execution }),

  agentModalOpen: false,
  teamModalOpen: false,
  executionModalOpen: false,
  openAgentModal: (agent) => set({ agentModalOpen: true, selectedAgent: agent || null }),
  openTeamModal: (team) => set({ teamModalOpen: true, selectedTeam: team || null }),
  openExecutionModal: (team) => set({ executionModalOpen: true, selectedTeam: team || null }),
  closeModals: () => set({ agentModalOpen: false, teamModalOpen: false, executionModalOpen: false }),

  activeExecutionId: null,
  setActiveExecution: (id) => set({ activeExecutionId: id }),
}))
