import axios from 'axios'
import type {
  Agent, AgentCreate, AgentListItem,
  Team, TeamCreate, TeamListItem,
  Execution, ExecutionCreate,
  ModelConfig, ModelConfigCreate, ModelConfigUpdate, TestModelResponse,
  PaginatedResponse
} from '@/types'

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
    const { data } = await api.get('/agents', { params })
    return data
  },

  get: async (id: string): Promise<Agent> => {
    const { data } = await api.get(`/agents/${id}`)
    return data
  },

  create: async (agent: AgentCreate): Promise<Agent> => {
    const { data } = await api.post('/agents', agent)
    return data
  },

  update: async (id: string, agent: Partial<AgentCreate>): Promise<Agent> => {
    const { data } = await api.put(`/agents/${id}`, agent)
    return data
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/agents/${id}`)
  },

  getTemplates: async (): Promise<Agent[]> => {
    const { data } = await api.get('/agents/templates')
    return data
  },

  duplicate: async (id: string, newName?: string): Promise<Agent> => {
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
    const { data } = await api.get('/teams', { params })
    return data
  },

  get: async (id: string): Promise<Team> => {
    const { data } = await api.get(`/teams/${id}`)
    return data
  },

  create: async (team: TeamCreate): Promise<Team> => {
    const { data } = await api.post('/teams', team)
    return data
  },

  update: async (id: string, team: Partial<TeamCreate>): Promise<Team> => {
    const { data } = await api.put(`/teams/${id}`, team)
    return data
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/teams/${id}`)
  },

  addMember: async (teamId: string, member: { agent_id: string; position?: number }) => {
    const { data } = await api.post(`/teams/${teamId}/members`, member)
    return data
  },

  removeMember: async (teamId: string, agentId: string): Promise<void> => {
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
    const { data } = await api.get('/executions', { params })
    return data
  },

  get: async (id: string): Promise<Execution> => {
    const { data } = await api.get(`/executions/${id}`)
    return data
  },

  create: async (execution: ExecutionCreate): Promise<Execution> => {
    const { data } = await api.post('/executions', execution)
    return data
  },

  start: async (id: string): Promise<void> => {
    await api.post(`/executions/${id}/start`)
  },

  control: async (id: string, action: string, params?: Record<string, unknown>): Promise<void> => {
    await api.post(`/executions/${id}/control`, { action, params })
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/executions/${id}`)
  },

  stream: (id: string): EventSource => {
    const base = API_BASE_URL.replace(/\/$/, '')
    return new EventSource(`${base}/executions/${id}/stream`)
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
