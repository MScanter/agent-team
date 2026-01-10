import axios from 'axios'
import type {
  Agent, AgentCreate, AgentListItem,
  Team, TeamCreate, TeamListItem,
  Execution, ExecutionCreate,
  FileEntry,
  ModelConfig, ModelConfigCreate, ModelConfigUpdate, TestModelResponse,
  PaginatedResponse
} from '@/types'
import { isTauriApp, tauriInvoke } from '@/services/tauri'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Agent API
export const agentApi = {
  list: async (params?: {
    page?: number
    page_size?: number
    search?: string
    tags?: string
    is_template?: boolean
  }): Promise<PaginatedResponse<AgentListItem>> => {
    if (isTauriApp()) {
      return tauriInvoke('list_agents', params as any)
    }
    const { data } = await api.get('/agents', { params })
    return data
  },

  get: async (id: string): Promise<Agent> => {
    if (isTauriApp()) {
      return tauriInvoke('get_agent', { id })
    }
    const { data } = await api.get(`/agents/${id}`)
    return data
  },

  create: async (agent: AgentCreate): Promise<Agent> => {
    if (isTauriApp()) {
      return tauriInvoke('create_agent', { agent })
    }
    const { data } = await api.post('/agents', agent)
    return data
  },

  update: async (id: string, agent: Partial<AgentCreate>): Promise<Agent> => {
    if (isTauriApp()) {
      return tauriInvoke('update_agent', { id, update: agent })
    }
    const { data } = await api.put(`/agents/${id}`, agent)
    return data
  },

  delete: async (id: string): Promise<void> => {
    if (isTauriApp()) {
      await tauriInvoke('delete_agent', { id })
      return
    }
    await api.delete(`/agents/${id}`)
  },

  getTemplates: async (): Promise<Agent[]> => {
    const { data } = await api.get('/agents/templates')
    return data
  },

  duplicate: async (id: string, newName?: string): Promise<Agent> => {
    if (isTauriApp()) {
      return tauriInvoke('duplicate_agent', { id, new_name: newName })
    }
    const { data } = await api.post(`/agents/${id}/duplicate`, null, {
      params: { new_name: newName },
    })
    return data
  },
}

// Team API
export const teamApi = {
  list: async (params?: {
    page?: number
    page_size?: number
    search?: string
    collaboration_mode?: string
    is_template?: boolean
  }): Promise<PaginatedResponse<TeamListItem>> => {
    if (isTauriApp()) {
      return tauriInvoke('list_teams', params as any)
    }
    const { data } = await api.get('/teams', { params })
    return data
  },

  get: async (id: string): Promise<Team> => {
    if (isTauriApp()) {
      return tauriInvoke('get_team', { id })
    }
    const { data } = await api.get(`/teams/${id}`)
    return data
  },

  create: async (team: TeamCreate): Promise<Team> => {
    if (isTauriApp()) {
      return tauriInvoke('create_team', { team })
    }
    const { data } = await api.post('/teams', team)
    return data
  },

  update: async (id: string, team: Partial<TeamCreate>): Promise<Team> => {
    if (isTauriApp()) {
      return tauriInvoke('update_team', { id, update: team })
    }
    const { data } = await api.put(`/teams/${id}`, team)
    return data
  },

  delete: async (id: string): Promise<void> => {
    if (isTauriApp()) {
      await tauriInvoke('delete_team', { id })
      return
    }
    await api.delete(`/teams/${id}`)
  },

  addMember: async (teamId: string, member: { agent_id: string; position?: number }) => {
    if (isTauriApp()) {
      return tauriInvoke('add_team_member', { team_id: teamId, member })
    }
    const { data } = await api.post(`/teams/${teamId}/members`, member)
    return data
  },

  removeMember: async (teamId: string, agentId: string): Promise<void> => {
    if (isTauriApp()) {
      await tauriInvoke('remove_team_member', { team_id: teamId, agent_id: agentId })
      return
    }
    await api.delete(`/teams/${teamId}/members/${agentId}`)
  },
}

// Execution API
export const executionApi = {
  list: async (params?: {
    page?: number
    page_size?: number
    team_id?: string
    status_filter?: string
  }): Promise<PaginatedResponse<Execution>> => {
    if (isTauriApp()) {
      return tauriInvoke('list_executions', params as any)
    }
    const { data } = await api.get('/executions', { params })
    return data
  },

  get: async (id: string): Promise<Execution> => {
    if (isTauriApp()) {
      return tauriInvoke('get_execution', { id })
    }
    const { data } = await api.get(`/executions/${id}`)
    return data
  },

  create: async (execution: ExecutionCreate): Promise<Execution> => {
    if (isTauriApp()) {
      return tauriInvoke('create_execution', { execution })
    }
    const { data } = await api.post('/executions', execution)
    return data
  },

  setWorkspace: async (id: string, workspacePath: string | null): Promise<Execution> => {
    if (isTauriApp()) {
      return tauriInvoke('set_execution_workspace', { id, workspace_path: workspacePath })
    }
    throw new Error('Workspace is only supported in the Tauri app')
  },

  listFiles: async (executionId: string, dir?: string): Promise<FileEntry[]> => {
    if (isTauriApp()) {
      return tauriInvoke('list_files', { execution_id: executionId, dir: dir ? dir : null })
    }
    throw new Error('File operations are only supported in the Tauri app')
  },

  readFile: async (executionId: string, path: string): Promise<string> => {
    if (isTauriApp()) {
      return tauriInvoke('read_file', { execution_id: executionId, path })
    }
    throw new Error('File operations are only supported in the Tauri app')
  },

  writeFile: async (executionId: string, path: string, content: string): Promise<void> => {
    if (isTauriApp()) {
      await tauriInvoke('write_file', { execution_id: executionId, path, content })
      return
    }
    throw new Error('File operations are only supported in the Tauri app')
  },

  control: async (id: string, action: string, params?: Record<string, unknown>): Promise<void> => {
    if (isTauriApp()) {
      await tauriInvoke('control_execution', { id, action, params })
      return
    }
    await api.post(`/executions/${id}/control`, { action, params })
  },

  delete: async (id: string): Promise<void> => {
    if (isTauriApp()) {
      await tauriInvoke('delete_execution', { id })
      return
    }
    await api.delete(`/executions/${id}`)
  },
}

// Model Config API
export const modelConfigApi = {
  list: async (params?: {
    include_system?: boolean
  }): Promise<ModelConfig[]> => {
    const { data } = await api.get('/models', { params })
    return data
  },

  get: async (id: string): Promise<ModelConfig> => {
    const { data } = await api.get(`/models/${id}`)
    return data
  },

  create: async (config: ModelConfigCreate): Promise<ModelConfig> => {
    const { data } = await api.post('/models', config)
    return data
  },

  update: async (id: string, config: ModelConfigUpdate): Promise<ModelConfig> => {
    const { data } = await api.put(`/models/${id}`, config)
    return data
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/models/${id}`)
  },

  test: async (id: string, testMessage?: string): Promise<TestModelResponse> => {
    const params = testMessage ? { test_message: testMessage } : {}
    const { data } = await api.post(`/models/${id}/test`, {}, { params })
    return data
  },
}

export default api
