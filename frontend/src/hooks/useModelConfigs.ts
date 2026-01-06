import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { 
  ModelConfig, 
  ModelConfigCreate, 
  ModelConfigUpdate, 
  TestModelResponse 
} from '@/types';
import { api } from '@/services/api';
import {
  createModelConfig,
  deleteModelConfig,
  getModelConfig,
  listModelConfigs,
  updateModelConfig,
} from '@/services/modelConfigStore';

// 获取模型配置列表
export function useModelConfigs(params?: { includeSystem?: boolean }) {
  return useQuery<ModelConfig[]>({
    queryKey: ['modelConfigs', params],
    queryFn: async () => {
      void params;
      return listModelConfigs();
    },
  });
}

// 获取单个模型配置
export function useModelConfig(id: string) {
  return useQuery<ModelConfig>({
    queryKey: ['modelConfig', id],
    queryFn: async () => {
      const config = getModelConfig(id);
      if (!config) throw new Error('Model config not found');
      return config;
    },
  });
}

// 创建模型配置
export function useCreateModelConfig() {
  const queryClient = useQueryClient();
  
  return useMutation<ModelConfig, Error, ModelConfigCreate>({
    mutationFn: async (data) => {
      return createModelConfig(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modelConfigs'] });
    },
  });
}

// 更新模型配置
export function useUpdateModelConfig() {
  const queryClient = useQueryClient();
  
  return useMutation<ModelConfig, Error, { id: string; data: ModelConfigUpdate }>({
    mutationFn: async ({ id, data }) => {
      return updateModelConfig(id, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modelConfigs'] });
      queryClient.invalidateQueries({ queryKey: ['modelConfig'] });
    },
  });
}

// 删除模型配置
export function useDeleteModelConfig() {
  const queryClient = useQueryClient();
  
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      deleteModelConfig(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modelConfigs'] });
    },
  });
}

// 测试模型配置
export function useTestModelConfig() {
  return useMutation<TestModelResponse, Error, { id: string; testMessage?: string }>({
    mutationFn: async ({ id, testMessage }) => {
      const config = getModelConfig(id);
      if (!config?.api_key?.trim()) throw new Error('请先填写 API 密钥');

      const payload = {
        config: {
          provider: 'openai_compatible',
          model_id: config.model_id,
          api_key: config.api_key,
          base_url: config.base_url,
          max_context_length: config.max_context_length,
          supports_tools: config.supports_tools,
          supports_vision: config.supports_vision,
        },
        test_message: testMessage || 'Hello, can you hear me?',
      };

      const response = await api.post('/llm/test', payload);
      return {
        message: response.data.message,
        config_id: id,
        response_preview: response.data.response_preview,
        tokens_used: response.data.tokens_used,
      };
    },
  });
}
