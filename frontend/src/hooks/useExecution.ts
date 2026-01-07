import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect, useCallback, useRef } from 'react'
import { executionApi } from '@/services/api'
import type { ExecutionCreate, ExecutionMessage } from '@/types'

export function useExecutions(params?: {
  page?: number
  page_size?: number
  team_id?: string
  status_filter?: string
}) {
  return useQuery({
    queryKey: ['executions', params],
    queryFn: () => executionApi.list(params),
  })
}

export function useExecution(id: string) {
  return useQuery({
    queryKey: ['execution', id],
    queryFn: () => executionApi.get(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = (query.state.data as any)?.status
      if (status === 'pending' || status === 'running' || status === 'paused') return 1000
      return false
    },
  })
}

export function useCreateExecution() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: ExecutionCreate) => executionApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['executions'] })
    },
  })
}

export function useControlExecution() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, action, params }: { id: string; action: string; params?: Record<string, unknown> }) =>
      executionApi.control(id, action, params),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['execution', id] })
    },
  })
}

export function useDeleteExecution() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => executionApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['executions'] })
    },
  })
}

interface StreamEvent {
  event_type: string
  data: Record<string, unknown>
  agent_id?: string
  sequence: number
}

export function useExecutionStream(executionId: string | null) {
  const [messages, setMessages] = useState<ExecutionMessage[]>([])
  const [status, setStatus] = useState<'idle' | 'connecting' | 'connected' | 'completed' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const completedRef = useRef(false)

  useEffect(() => {
    setMessages([])
    setStatus('idle')
    setError(null)
    completedRef.current = false
  }, [executionId])

  const connect = useCallback(() => {
    if (!executionId) return

    completedRef.current = false
    setError(null)
    setStatus('connecting')
    const eventSource = executionApi.stream(executionId)

    eventSource.onopen = () => setStatus('connected')

    eventSource.onmessage = (event) => {
      try {
        const data: StreamEvent = JSON.parse(event.data)

        if (data.event_type === 'user') {
          const msg: ExecutionMessage = {
            id: (data.data.message_id as string) || `${executionId}-${data.sequence}`,
            sequence: (data.data.message_sequence as number) || data.sequence,
            round: (data.data.round as number) || 0,
            phase: (data.data.phase as string) || 'user',
            sender_type: 'user',
            sender_id: undefined,
            sender_name: 'you',
            content: (data.data.content as string) || '',
            content_type: 'text',
            confidence: undefined,
            wants_to_continue: true,
            input_tokens: 0,
            output_tokens: 0,
            metadata: {},
            created_at: new Date().toISOString(),
          }
          setMessages((prev) => [...prev, msg])
          return
        }

        if (data.event_type === 'await_input') {
          const msg: ExecutionMessage = {
            id: (data.data.message_id as string) || `${executionId}-${data.sequence}`,
            sequence: (data.data.message_sequence as number) || data.sequence,
            round: (data.data.round as number) || 0,
            phase: (data.data.phase as string) || 'awaiting_user_input',
            sender_type: 'system',
            sender_id: undefined,
            sender_name: 'system',
            content: (data.data.message as string) || '等待你的输入',
            content_type: 'text',
            confidence: undefined,
            wants_to_continue: true,
            input_tokens: 0,
            output_tokens: 0,
            metadata: {},
            created_at: new Date().toISOString(),
          }
          setMessages((prev) => [...prev, msg])

          completedRef.current = true
          setStatus('completed')
          queryClient.invalidateQueries({ queryKey: ['execution', executionId] })
          eventSource.close()
          return
        }

        if (data.event_type === 'error') {
          setError(data.data.message as string)
          setStatus('error')
          eventSource.close()
          return
        }

        if (data.event_type === 'status') {
          const phase = (data.data.phase as string) || ''
          const statusField = (data.data.status as string) || ''
          const hasMessage = typeof (data.data.message as unknown) === 'string' && Boolean((data.data.message as string).trim())
          if (!hasMessage && statusField) {
            completedRef.current = true
            setStatus('completed')
            queryClient.invalidateQueries({ queryKey: ['execution', executionId] })
            eventSource.close()
            return
          }
          const msg: ExecutionMessage = {
            id: `${executionId}-${data.sequence}`,
            sequence: data.sequence,
            round: (data.data.round as number) || 0,
            phase: phase || 'status',
            sender_type: 'system',
            sender_id: undefined,
            sender_name: 'system',
            content: (data.data.message as string) || JSON.stringify(data.data),
            content_type: 'text',
            confidence: undefined,
            wants_to_continue: true,
            input_tokens: 0,
            output_tokens: 0,
            metadata: {},
            created_at: new Date().toISOString(),
          }
          setMessages((prev) => [...prev, msg])

          // If backend immediately paused (e.g. awaiting user input) or returned a non-streaming status,
          // close the EventSource without showing a scary error.
          if (
            phase === 'awaiting_user_input' ||
            (statusField && !['pending', 'running'].includes(statusField)) ||
            (statusField && !hasMessage)
          ) {
            completedRef.current = true
            setStatus('completed')
            queryClient.invalidateQueries({ queryKey: ['execution', executionId] })
            eventSource.close()
          }
          return
        }

        if (data.event_type === 'opinion' || data.event_type === 'summary' || data.event_type === 'done') {
          const phase =
            (data.data.phase as string) ||
            (typeof data.data.stage === 'number' ? `stage_${data.data.stage}` : data.event_type)
          const msg: ExecutionMessage = {
            id: (data.data.message_id as string) || `${executionId}-${data.sequence}`,
            sequence: (data.data.message_sequence as number) || data.sequence,
            round: (data.data.round as number) || 0,
            phase,
            sender_type: data.agent_id ? 'agent' : 'system',
            sender_id: data.agent_id,
            sender_name: (data.data.agent_name as string) || (data.agent_id ? undefined : 'system'),
            content:
              (data.data.content as string) ||
              (data.data.summary as string) ||
              (data.data.final_output as string) ||
              (data.data.final_summary as string) ||
              '',
            content_type: 'text',
            confidence: data.data.confidence as number,
            wants_to_continue: (data.data.wants_to_continue as boolean) ?? true,
            input_tokens: 0,
            output_tokens: 0,
            metadata: {},
            created_at: new Date().toISOString(),
          }
          setMessages((prev) => [...prev, msg])
        }

        if (data.event_type === 'done' || data.event_type === 'completed') {
          completedRef.current = true
          setStatus('completed')
          queryClient.invalidateQueries({ queryKey: ['execution', executionId] })
          eventSource.close()
        }
      } catch {
        // ignore parse errors
      }
    }

    eventSource.onerror = () => {
      // Don't show error if stream completed normally
      if (!completedRef.current) {
        setStatus('error')
        setError('SSE 连接失败，请刷新页面或检查后端是否在运行')
      }
      eventSource.close()
    }

    return () => eventSource.close()
  }, [executionId, queryClient])

  useEffect(() => {
    const cleanup = connect()
    return () => cleanup?.()
  }, [connect])

  return { messages, status, error, reconnect: connect }
}
