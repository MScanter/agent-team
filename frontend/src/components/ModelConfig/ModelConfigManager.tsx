import { useState } from 'react';
import { Plus, Settings, Trash2, Edit3 } from 'lucide-react';
import type { ModelConfig } from '@/types';
import { useModelConfigs, useDeleteModelConfig } from '@/hooks';
import ModelConfigForm from './ModelConfigForm';
import { setDefaultModelConfig } from '@/services/modelConfigStore';

export default function ModelConfigManager() {
  const { data: configs, isLoading, refetch } = useModelConfigs({ includeSystem: false });
  const deleteMutation = useDeleteModelConfig();
  const [showForm, setShowForm] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ModelConfig | null>(null);

  const handleDelete = async (id: string) => {
    if (window.confirm('确定要删除此API配置吗？此操作不可撤销。')) {
      try {
        await deleteMutation.mutateAsync(id);
        refetch();
      } catch (error) {
        console.error('删除API配置失败:', error);
      }
    }
  };

  const handleEdit = (config: ModelConfig) => {
    setEditingConfig(config);
    setShowForm(true);
  };

  const handleSetDefault = async (id: string) => {
    setDefaultModelConfig(id);
    await refetch();
  };

  const handleCreate = () => {
    setEditingConfig(null);
    setShowForm(true);
  };

  const handleClose = () => {
    setShowForm(false);
    setEditingConfig(null);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">API配置管理</h1>
        <button
          onClick={handleCreate}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          添加API配置
        </button>
      </div>

      {configs && configs.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {configs.map((config) => (
            <div
              key={config.id}
              className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors"
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    <Settings className="w-5 h-5 text-blue-400" />
                    {config.name}
                  </h3>
                  <p className="text-sm text-gray-400 mt-1">{config.description}</p>
                  <div className="mt-2 text-xs">
                    <div className="text-gray-300">
                      <span className="text-gray-400">提供商:</span> OpenAI兼容API
                    </div>
                    <div className="text-gray-300">
                      <span className="text-gray-400">模型:</span> {config.model_id}
                    </div>
                    <div className="text-gray-300">
                      <span className="text-gray-400">上下文长度:</span> {config.max_context_length.toLocaleString()} tokens
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleEdit(config)}
                    className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
                    title="编辑"
                  >
                    <Edit3 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(config.id)}
                    className="p-2 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded"
                    title="删除"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              <div className="mt-4 flex flex-wrap gap-2">
                {config.supports_tools && (
                  <span className="px-2 py-1 bg-green-900/50 text-green-300 text-xs rounded">
                    工具调用
                  </span>
                )}
                {config.supports_vision && (
                  <span className="px-2 py-1 bg-blue-900/50 text-blue-300 text-xs rounded">
                    视觉
                  </span>
                )}
                {config.is_default && (
                  <span className="px-2 py-1 bg-yellow-900/50 text-yellow-300 text-xs rounded">
                    默认
                  </span>
                )}
                {!config.is_default && (
                  <button
                    type="button"
                    onClick={() => handleSetDefault(config.id)}
                    className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-200 text-xs rounded"
                    title="设为默认（用于未绑定配置的 Agent & 协调器）"
                  >
                    设为默认
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Settings className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-300 mb-2">没有API配置</h3>
          <p className="text-gray-500 mb-6">您还没有创建任何API配置</p>
          <button
            onClick={handleCreate}
            className="btn btn-primary inline-flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            创建第一个API配置
          </button>
        </div>
      )}

      {showForm && (
        <ModelConfigForm
          config={editingConfig}
          onClose={handleClose}
        />
      )}
    </div>
  );
}
