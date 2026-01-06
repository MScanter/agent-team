import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentApi } from '@/services/api'
import type { AgentCreate } from '@/types'

export function useAgents(params?: {
  page?: number
  page_size?: number
  search?: string
  tags?: string
  is_template?: boolean
}) {
  return useQuery({
    queryKey: ['agents', params],
    queryFn: () => agentApi.list(params),
  })
}

export function useAgent(id: string) {
  return useQuery({
    queryKey: ['agent', id],
    queryFn: () => agentApi.get(id),
    enabled: !!id,
  })
}

export function useAgentTemplates() {
  return useQuery({
    queryKey: ['agent-templates'],
    queryFn: () => agentApi.getTemplates(),
  })
}

export function useCreateAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: AgentCreate) => agentApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

export function useUpdateAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AgentCreate> }) =>
      agentApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      queryClient.invalidateQueries({ queryKey: ['agent', id] })
    },
  })
}

export function useDeleteAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => agentApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

export function useDuplicateAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, newName }: { id: string; newName?: string }) =>
      agentApi.duplicate(id, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}
