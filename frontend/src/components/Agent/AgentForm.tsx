import { useState } from 'react'
import { X } from 'lucide-react'
import type { Agent, AgentCreate } from '@/types'
import { useCreateAgent, useModelConfigs, useUpdateAgent } from '@/hooks'

interface Props {
  agent?: Agent | null
  onClose: () => void
}

export default function AgentForm({ agent, onClose }: Props) {
  const isEdit = !!agent
  const createAgent = useCreateAgent()
  const updateAgent = useUpdateAgent()
  const { data: modelConfigs } = useModelConfigs({ includeSystem: false })

  const [form, setForm] = useState<AgentCreate>({
    name: agent?.name || '',
    description: agent?.description || '',
    system_prompt: agent?.system_prompt || '',
    model_id: agent?.model_id,
    temperature: agent?.temperature ?? 0.7,
    max_tokens: agent?.max_tokens ?? 2000,
    collaboration_style: agent?.collaboration_style || 'supportive',
    tags: agent?.tags || [],
  })

  const [tagInput, setTagInput] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const payload: AgentCreate = {
      ...form,
      model_id: form.model_id ? form.model_id : undefined,
    }
    if (isEdit && agent) {
      await updateAgent.mutateAsync({ id: agent.id, data: payload })
    } else {
      await createAgent.mutateAsync(payload)
    }
    onClose()
  }

  const addTag = () => {
    if (tagInput.trim() && !form.tags?.includes(tagInput.trim())) {
      setForm({ ...form, tags: [...(form.tags || []), tagInput.trim()] })
      setTagInput('')
    }
  }

  const removeTag = (tag: string) => {
    setForm({ ...form, tags: form.tags?.filter((t) => t !== tag) })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-semibold text-white">
            {isEdit ? '编辑 Agent' : '创建 Agent'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">名称</label>
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
            <label className="block text-sm font-medium text-gray-300 mb-1">系统提示词</label>
            <textarea
              className="input w-full h-32 font-mono text-sm"
              value={form.system_prompt}
              onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">模型配置</label>
            <select
              className="input w-full"
              value={form.model_id || ''}
              onChange={(e) => setForm({ ...form, model_id: e.target.value || undefined })}
            >
              <option value="">默认（使用本地默认配置）</option>
              {(modelConfigs || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.model_id})
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-400 mt-1">在“API配置”里创建模型配置后可在这里绑定</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Temperature: {form.temperature}
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                className="w-full"
                value={form.temperature}
                onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Max Tokens</label>
              <input
                type="number"
                className="input w-full"
                value={form.max_tokens}
                onChange={(e) => setForm({ ...form, max_tokens: parseInt(e.target.value) })}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">协作风格</label>
            <select
              className="input w-full"
              value={form.collaboration_style}
              onChange={(e) => setForm({ ...form, collaboration_style: e.target.value as AgentCreate['collaboration_style'] })}
            >
              <option value="supportive">支持型</option>
              <option value="dominant">主导型</option>
              <option value="critical">批判型</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">标签</label>
            <div className="flex gap-2 mb-2 flex-wrap">
              {form.tags?.map((tag) => (
                <span key={tag} className="px-2 py-1 bg-primary-600 text-white rounded-full text-sm flex items-center">
                  {tag}
                  <button type="button" onClick={() => removeTag(tag)} className="ml-1">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                className="input flex-1"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                placeholder="添加标签"
              />
              <button type="button" onClick={addTag} className="btn btn-secondary">
                添加
              </button>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-700">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              取消
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={createAgent.isPending || updateAgent.isPending}
            >
              {createAgent.isPending || updateAgent.isPending ? '保存中...' : '保存'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
