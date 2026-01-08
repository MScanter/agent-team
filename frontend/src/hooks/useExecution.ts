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

function buildWsUrl(path: string) {
  const base = (import.meta as any).env?.VITE_API_BASE_URL || '/api'
  const baseStr = String(base).replace(/\/$/, '')
  if (baseStr.startsWith('http://') || baseStr.startsWith('https://')) {
    const url = new URL(baseStr)
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${url.host}${url.pathname}${path}`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${baseStr}${path}`
}

export function useExecutionSocket(executionId: string | null) {
  const [messages, setMessages] = useState<ExecutionMessage[]>([])
  const [status, setStatus] = useState<'idle' | 'connecting' | 'connected' | 'completed' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const completedRef = useRef(false)
  const socketRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    setMessages([])
    setStatus('idle')
    setError(null)
    completedRef.current = false
    socketRef.current?.close()
    socketRef.current = null
  }, [executionId])

  const connect = useCallback(() => {
    if (!executionId) return

    completedRef.current = false
    setError(null)
    setStatus('connecting')
    const wsUrl = buildWsUrl(`/executions/${executionId}/ws`)
    const socket = new WebSocket(wsUrl)
    socketRef.current = socket

    socket.onopen = () => setStatus('connected')

    socket.onmessage = (event) => {
      try {
        const data: StreamEvent = JSON.parse(event.data)

        if (data.event_type === 'pong') {
          return
        }
        if (data.event_type === 'ping') {
          socket.send(JSON.stringify({ type: 'pong' }))
          return
        }

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

        if (data.event_type === 'error') {
          setError(data.data.message as string)
          setStatus('error')
          return
        }

        if (data.event_type === 'status') {
          const phase = (data.data.phase as string) || ''
          const statusField = (data.data.status as string) || ''
          const hasMessage =
            typeof (data.data.message as unknown) === 'string' &&
            Boolean((data.data.message as string).trim())

          if (hasMessage) {
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
          }

          if (statusField) {
            queryClient.invalidateQueries({ queryKey: ['execution', executionId] })
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
        }
      } catch {
        // ignore parse errors
      }
    }

    socket.onerror = () => {
      if (!completedRef.current) {
        setStatus('error')
        setError('WebSocket 连接失败，请刷新页面或检查后端是否在运行')
      }
    }

    socket.onclose = () => {
      if (!completedRef.current) {
        setStatus('error')
        setError('WebSocket 已断开连接')
      }
    }

    return () => socket.close()
  }, [executionId, queryClient])

  useEffect(() => {
    const cleanup = connect()
    return () => cleanup?.()
  }, [connect])

  useEffect(() => {
    const socket = socketRef.current
    if (!socket) return
    if (status !== 'connected') return

    const interval = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'ping' }))
      }
    }, 20000)

    return () => window.clearInterval(interval)
  }, [status])

  const sendFollowup = useCallback((input: string, targetAgentId?: string) => {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      connect()
      setStatus('error')
      setError('WebSocket 未连接')
      return false
    }
    completedRef.current = false
    setStatus('connected')
    setError(null)
    socket.send(
      JSON.stringify({
        type: 'followup',
        input,
        target_agent_id: targetAgentId,
      })
    )
    return true
  }, [])

  return { messages, status, error, reconnect: connect, sendFollowup }
}
