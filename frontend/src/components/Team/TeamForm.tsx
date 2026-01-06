import { useState } from 'react'
import { X, Plus, GripVertical, Trash2 } from 'lucide-react'
import type { Team, TeamCreate, AgentListItem } from '@/types'
import { useCreateTeam, useUpdateTeam, useAgents } from '@/hooks'

interface Props {
  team?: Team | null
  onClose: () => void
}

export default function TeamForm({ team, onClose }: Props) {
  const isEdit = !!team
  const createTeam = useCreateTeam()
  const updateTeam = useUpdateTeam()
  const { data: agentsData } = useAgents({ page_size: 100 })

  const [form, setForm] = useState<TeamCreate>({
    name: team?.name || '',
    description: team?.description || '',
    collaboration_mode: team?.collaboration_mode || 'roundtable',
    members: team?.members?.map((m) => ({
      agent_id: m.agent_id,
      position: m.position,
    })) || [],
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (isEdit && team) {
      await updateTeam.mutateAsync({ id: team.id, data: form })
    } else {
      await createTeam.mutateAsync(form)
    }
    onClose()
  }

  const addMember = (agentId: string) => {
    if (!form.members?.find((m) => m.agent_id === agentId)) {
      setForm({
        ...form,
        members: [...(form.members || []), { agent_id: agentId, position: form.members?.length || 0 }],
      })
    }
  }

  const removeMember = (agentId: string) => {
    setForm({
      ...form,
      members: form.members?.filter((m) => m.agent_id !== agentId),
    })
  }

  const getAgentName = (agentId: string) => {
    return agentsData?.items.find((a: AgentListItem) => a.id === agentId)?.name || agentId
  }

  const availableAgents = agentsData?.items.filter(
    (a: AgentListItem) => !form.members?.find((m) => m.agent_id === a.id)
  ) || []

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-semibold text-white">
            {isEdit ? '编辑团队' : '创建团队'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">团队名称</label>
            <input
              type="text"
              className="input w-full"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">描述</label>
            <textarea
              className="input w-full h-20"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">协作模式</label>
            <select
              className="input w-full"
              value={form.collaboration_mode}
              onChange={(e) => setForm({ ...form, collaboration_mode: e.target.value as TeamCreate['collaboration_mode'] })}
            >
              <option value="roundtable">圆桌讨论</option>
              <option value="pipeline">流水线</option>
              <option value="debate">辩论</option>
              <option value="freeform">自由讨论</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">团队成员</label>
            <div className="space-y-2 mb-3">
              {form.members?.map((member, idx) => (
                <div key={member.agent_id} className="flex items-center gap-2 bg-gray-700 p-2 rounded">
                  <GripVertical className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-400">{idx + 1}.</span>
                  <span className="flex-1 text-white">{getAgentName(member.agent_id)}</span>
                  <button
                    type="button"
                    onClick={() => removeMember(member.agent_id)}
                    className="text-red-400 hover:text-red-300"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>

            {availableAgents.length > 0 && (
              <div className="flex gap-2">
                <select
                  className="input flex-1"
                  onChange={(e) => e.target.value && addMember(e.target.value)}
                  value=""
                >
                  <option value="">选择 Agent 添加...</option>
                  {availableAgents.map((agent: AgentListItem) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
                <button type="button" className="btn btn-secondary">
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-700">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              取消
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={createTeam.isPending || updateTeam.isPending}
            >
              {createTeam.isPending || updateTeam.isPending ? '保存中...' : '保存'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
