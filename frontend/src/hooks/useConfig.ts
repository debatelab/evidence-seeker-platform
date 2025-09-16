/**
 * React hooks for configuration management
 */

import { useState, useEffect, useCallback } from "react";
import api from "../utils/api";
import {
  APIKeyCreate,
  APIKeyUpdate,
  APIKeyRead,
  APIKeyValidation,
  APIKeyValidationResponse,
  AIConfig,
  SystemStats,
  SupportedProviders,
  DecryptedAPIKeyResponse,
} from "../types/config";

export const useAPIKeys = (evidenceSeekerUuid?: string) => {
  const [apiKeys, setApiKeys] = useState<APIKeyRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchApiKeys = useCallback(
    async (provider?: string) => {
      if (!evidenceSeekerUuid) return;

      setLoading(true);
      setError(null);

      try {
        const params = provider ? `?provider=${provider}` : "";
        const response = await api.get(
          `/config/${evidenceSeekerUuid}/api-keys${params}`
        );
        setApiKeys(response.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to fetch API keys");
      } finally {
        setLoading(false);
      }
    },
    [evidenceSeekerUuid]
  );

  useEffect(() => {
    fetchApiKeys();
  }, [fetchApiKeys]);

  const createApiKey = useCallback(
    async (apiKeyData: APIKeyCreate) => {
      if (!evidenceSeekerUuid) throw new Error("Evidence Seeker UUID required");

      setLoading(true);
      setError(null);

      try {
        const response = await api.post(
          `/config/${evidenceSeekerUuid}/api-keys`,
          apiKeyData
        );
        const newApiKey = response.data;
        setApiKeys((prev) => [...prev, newApiKey]);
        return newApiKey;
      } catch (err: any) {
        const errorMessage =
          err.response?.data?.detail || "Failed to create API key";
        setError(errorMessage);
        throw new Error(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [evidenceSeekerUuid]
  );

  const updateApiKey = useCallback(
    async (apiKeyId: number, updates: APIKeyUpdate) => {
      if (!evidenceSeekerUuid) throw new Error("Evidence Seeker UUID required");

      setLoading(true);
      setError(null);

      try {
        const response = await api.put(
          `/config/${evidenceSeekerUuid}/api-keys/${apiKeyId}`,
          updates
        );
        const updatedApiKey = response.data;
        setApiKeys((prev) =>
          prev.map((key) => (key.id === apiKeyId ? updatedApiKey : key))
        );
        return updatedApiKey;
      } catch (err: any) {
        const errorMessage =
          err.response?.data?.detail || "Failed to update API key";
        setError(errorMessage);
        throw new Error(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [evidenceSeekerUuid]
  );

  const deleteApiKey = useCallback(
    async (apiKeyId: number) => {
      if (!evidenceSeekerUuid) throw new Error("Evidence Seeker UUID required");

      setLoading(true);
      setError(null);

      try {
        await api.delete(`/config/${evidenceSeekerUuid}/api-keys/${apiKeyId}`);
        setApiKeys((prev) => prev.filter((key) => key.id !== apiKeyId));
      } catch (err: any) {
        const errorMessage =
          err.response?.data?.detail || "Failed to delete API key";
        setError(errorMessage);
        throw new Error(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [evidenceSeekerUuid]
  );

  return {
    apiKeys,
    loading,
    error,
    refetch: fetchApiKeys,
    createApiKey,
    updateApiKey,
    deleteApiKey,
  };
};

export const useAPIKeyValidation = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateApiKey = useCallback(async (validation: APIKeyValidation) => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.post("/config/api-keys/validate", validation);
      return response.data as APIKeyValidationResponse;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to validate API key";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  return { validateApiKey, loading, error };
};

export const useAIConfig = () => {
  const [config, setConfig] = useState<AIConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.get("/config/ai-config");
      setConfig(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch AI config");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  return { config, loading, error, refetch: fetchConfig };
};

export const useSystemStats = () => {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.get("/config/system-stats");
      setStats(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch system stats");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return { stats, loading, error, refetch: fetchStats };
};

export const useSupportedProviders = () => {
  const [providers, setProviders] = useState<SupportedProviders | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProviders = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.get("/config/providers");
      setProviders(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch providers");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  return { providers, loading, error, refetch: fetchProviders };
};

export const useDecryptedAPIKey = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getDecryptedKey = useCallback(
    async (evidenceSeekerUuid: string, apiKeyId: number) => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.post(
          `/config/${evidenceSeekerUuid}/api-keys/${apiKeyId}/decrypt`
        );
        return response.data as DecryptedAPIKeyResponse;
      } catch (err: any) {
        const errorMessage =
          err.response?.data?.detail || "Failed to decrypt API key";
        setError(errorMessage);
        throw new Error(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return { getDecryptedKey, loading, error };
};
