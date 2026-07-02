import { create } from 'zustand'
import {
  DEFAULT_PROVIDER_CAPABILITIES,
  createApiKeyForProvider,
  createProviderConfig,
  deleteProviderConfig,
  fetchProviderConfigs,
  fetchProviderModels,
  fetchProviderPresets,
  getApiErrorMessage,
  testProviderConfig,
} from '../api/providers'
import type {
  CreateProviderFromPresetInput,
  CreateRelayProviderInput,
  ProviderConfig,
  ProviderHealthResult,
  ProviderModelsResult,
  ProviderPreset,
} from '../types'

interface ProviderStore {
  presets: ProviderPreset[]
  providers: ProviderConfig[]
  modelsByProviderId: Record<string, ProviderModelsResult>
  healthByProviderId: Record<string, ProviderHealthResult>
  isLoading: boolean
  isSaving: boolean
  testingProviderId: string | null
  error: string | null
  validationError: string | null

  fetchProviderSettings: () => Promise<void>
  createRelayProvider: (input: CreateRelayProviderInput) => Promise<void>
  createProviderFromPreset: (input: CreateProviderFromPresetInput) => Promise<void>
  testProviderConfig: (providerId: string, modelId?: string) => Promise<void>
  loadProviderModels: (providerId: string) => Promise<void>
  deleteProviderConfig: (providerId: string) => Promise<void>
  clearError: () => void
}

function validateRelayProvider(input: CreateRelayProviderInput): string | null {
  if (!input.displayName.trim()) return 'Display name is required.'
  if (!input.baseUrl.trim()) return 'Base URL is required.'
  if (!input.baseUrl.startsWith('http://') && !input.baseUrl.startsWith('https://')) {
    return 'Base URL must start with http:// or https://.'
  }
  if (!input.apiKey.trim()) return 'API Key is required.'
  if (!input.defaultModel.trim()) return 'Default model is required.'
  return null
}

function validatePresetProvider(input: CreateProviderFromPresetInput): string | null {
  if (!input.displayName.trim()) return 'Display name is required.'
  if (input.baseUrl && !input.baseUrl.startsWith('http://') && !input.baseUrl.startsWith('https://')) {
    return 'Base URL must start with http:// or https://.'
  }
  if (!input.apiKey.trim()) return 'API Key is required.'
  if (!input.defaultModel.trim()) return 'Default model is required.'
  return null
}

export const useProviderStore = create<ProviderStore>((set) => ({
  presets: [],
  providers: [],
  modelsByProviderId: {},
  healthByProviderId: {},
  isLoading: false,
  isSaving: false,
  testingProviderId: null,
  error: null,
  validationError: null,

  fetchProviderSettings: async () => {
    set({ isLoading: true, error: null })
    try {
      const [presets, providers] = await Promise.all([
        fetchProviderPresets(),
        fetchProviderConfigs(),
      ])
      set({ presets, providers, isLoading: false })
    } catch (err) {
      set({ isLoading: false, error: getApiErrorMessage(err) })
    }
  },

  createRelayProvider: async (input) => {
    const validationError = validateRelayProvider(input)
    if (validationError) {
      set({ validationError })
      return
    }

    set({ isSaving: true, error: null, validationError: null })
    try {
      const key = await createApiKeyForProvider('openai_compatible', input.apiKey)
      const provider = await createProviderConfig({
        providerType: 'openai_compatible',
        apiKeyId: key.id,
        displayName: input.displayName,
        baseUrl: input.baseUrl,
        defaultModel: input.defaultModel,
        capabilities: {
          ...DEFAULT_PROVIDER_CAPABILITIES,
          chat: true,
          streaming: input.streamingEnabled,
          tool_calling: input.toolCallingEnabled,
        },
        streamingEnabled: input.streamingEnabled,
        toolCallingEnabled: input.toolCallingEnabled,
        timeoutSeconds: input.timeoutSeconds,
      })
      set((state) => ({
        providers: [...state.providers, provider],
        isSaving: false,
      }))
    } catch (err) {
      set({ isSaving: false, error: getApiErrorMessage(err) })
    }
  },

  createProviderFromPreset: async (input) => {
    const validationError = validatePresetProvider(input)
    if (validationError) {
      set({ validationError })
      return
    }

    set({ isSaving: true, error: null, validationError: null })
    try {
      const key = await createApiKeyForProvider(input.providerType, input.apiKey)
      const provider = await createProviderConfig({
        providerType: input.providerType,
        apiKeyId: key.id,
        displayName: input.displayName,
        baseUrl: input.baseUrl,
        defaultModel: input.defaultModel,
        capabilities: input.capabilities,
        streamingEnabled: input.streamingEnabled,
        toolCallingEnabled: input.toolCallingEnabled,
        timeoutSeconds: input.timeoutSeconds,
      })
      set((state) => ({
        providers: [...state.providers, provider],
        isSaving: false,
      }))
    } catch (err) {
      set({ isSaving: false, error: getApiErrorMessage(err) })
    }
  },

  testProviderConfig: async (providerId, modelId) => {
    set({ testingProviderId: providerId, error: null })
    try {
      const result = await testProviderConfig(providerId, modelId)
      set((state) => ({
        testingProviderId: null,
        healthByProviderId: {
          ...state.healthByProviderId,
          [providerId]: result,
        },
      }))
    } catch (err) {
      set({ testingProviderId: null, error: getApiErrorMessage(err) })
    }
  },

  loadProviderModels: async (providerId) => {
    try {
      const result = await fetchProviderModels(providerId)
      set((state) => ({
        modelsByProviderId: {
          ...state.modelsByProviderId,
          [providerId]: result,
        },
      }))
    } catch (err) {
      set({ error: getApiErrorMessage(err) })
    }
  },

  deleteProviderConfig: async (providerId) => {
    set({ error: null })
    try {
      await deleteProviderConfig(providerId)
      set((state) => ({
        providers: state.providers.filter((provider) => provider.id !== providerId),
      }))
    } catch (err) {
      set({ error: getApiErrorMessage(err) })
    }
  },

  clearError: () => set({ error: null, validationError: null }),
}))
