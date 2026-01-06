import { useState } from 'react';
import { X } from 'lucide-react';
import type { ModelConfig, ModelConfigCreate, ModelConfigUpdate } from '@/types';
import { useCreateModelConfig, useUpdateModelConfig, useTestModelConfig } from '@/hooks';

interface Props {
  config?: ModelConfig | null;
  onClose: () => void;
}

export default function ModelConfigForm({ config, onClose }: Props) {
  const isEdit = !!config;
  const createModelConfig = useCreateModelConfig();
  const updateModelConfig = useUpdateModelConfig();
  const testModelConfig = useTestModelConfig();

  const [form, setForm] = useState<ModelConfigCreate>({
    name: config?.name || '',
    description: config?.description || '',
    provider: 'openai_compatible',
    model_id: config?.model_id || '',
    api_key: '',
    base_url: config?.base_url || '',
  });

  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isEdit && config) {
        const update: ModelConfigUpdate = {
          name: form.name,
          description: form.description,
          provider: form.provider,
          model_id: form.model_id,
          base_url: form.base_url,
        };
        if (form.api_key?.trim()) {
          update.api_key = form.api_key;
        }
        await updateModelConfig.mutateAsync({ id: config.id, data: update });
      } else {
        await createModelConfig.mutateAsync(form);
      }
      onClose();
    } catch (error) {
      console.error('Error saving model config:', error);
    }
  };

  const handleTest = async () => {
    if (!config) return;
    
    setIsTesting(true);
    setTestResult(null);
    setTestError(null);
    
    try {
      const result = await testModelConfig.mutateAsync({ id: config.id });
      setTestResult(result.response_preview || result.message);
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      const detailText = typeof detail === 'string' ? detail : detail ? JSON.stringify(detail, null, 2) : null;
      setTestError(detailText || error.message || '测试失败');
    } finally {
      setIsTesting(false);
    }
  };

  const handleChange = (field: keyof ModelConfigCreate, value: string) => {
    setForm({ ...form, [field]: value });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-semibold text-white">
            {isEdit ? '编辑模型配置' : '创建模型配置'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">配置名称</label>
            <input
              type="text"
              className="input w-full"
              value={form.name}
              onChange={(e) => handleChange('name', e.target.value)}
              required
            />
            <p className="text-xs text-gray-400 mt-1">为您的模型配置起一个名称</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">描述</label>
            <textarea
              className="input w-full h-20"
              value={form.description || ''}
              onChange={(e) => handleChange('description', e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">提供商</label>
            <div className="input w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-gray-300">
              OpenAI兼容API
            </div>
            <input
              type="hidden"
              value="openai_compatible"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">模型ID</label>
              <input
                type="text"
                className="input w-full"
                value={form.model_id}
                onChange={(e) => handleChange('model_id', e.target.value)}
                required
                placeholder="例如: gpt-4o, llama3.1"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">API密钥</label>
            <input
              type="password"
              className="input w-full"
              value={form.api_key}
              onChange={(e) => handleChange('api_key', e.target.value)}
              placeholder={isEdit ? '留空保持当前密钥' : '输入您的API密钥'}
            />
            <p className="text-xs text-gray-400 mt-1">
              OpenAI兼容API的密钥
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">API基础URL</label>
            <input
              type="text"
              className="input w-full"
              value={form.base_url || ''}
              onChange={(e) => handleChange('base_url', e.target.value)}
              placeholder="例如: https://api.openai.com/v1（不要填到 /chat/completions）"
            />
            <p className="text-xs text-gray-400 mt-1">
              填 OpenAI 兼容 API 的 Base URL；如果文档写的是 `/v1/chat/completions`，这里通常应填到 `/v1`。
            </p>
          </div>

          <div className="flex justify-between pt-4 border-t border-gray-700">
            <div className="flex gap-2">
              {isEdit && (
                <button
                  type="button"
                  onClick={handleTest}
                  disabled={isTesting || testModelConfig.isPending}
                  className="btn btn-secondary"
                >
                  {isTesting || testModelConfig.isPending ? '测试中...' : '测试配置'}
                </button>
              )}
              {testResult && (
                <div className="text-sm text-green-400 bg-gray-700 p-2 rounded">
                  {testResult}
                </div>
              )}
              {testError && (
                <div className="text-sm text-red-400 bg-gray-700 p-2 rounded">
                  {testError}
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button type="button" onClick={onClose} className="btn btn-secondary">
                取消
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={createModelConfig.isPending || updateModelConfig.isPending}
              >
                {createModelConfig.isPending || updateModelConfig.isPending ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
