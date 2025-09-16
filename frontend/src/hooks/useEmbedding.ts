/**
 * React hooks for embedding operations
 */

import { useState, useEffect, useCallback } from "react";
import api from "../utils/api";
import {
  EmbeddingStatus,
  EmbeddingRegenerateRequest,
  EmbeddingModelInfo,
  BatchEmbeddingRequest,
  BatchEmbeddingResponse,
} from "../types/embedding";

export const useEmbeddingStatus = (documentId: number) => {
  const [status, setStatus] = useState<EmbeddingStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!documentId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.get(`/embeddings/status/${documentId}`);
      setStatus(response.data);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || "Failed to fetch embedding status"
      );
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const refetch = useCallback(() => {
    fetchStatus();
  }, [fetchStatus]);

  return { status, loading, error, refetch };
};

export const useRegenerateEmbeddings = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const regenerate = useCallback(async (documentId: number) => {
    setLoading(true);
    setError(null);

    try {
      const request: EmbeddingRegenerateRequest = { document_id: documentId };
      const response = await api.post("/embeddings/regenerate", request);
      return response.data;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to regenerate embeddings";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  return { regenerate, loading, error };
};

export const useEmbeddingModelInfo = () => {
  const [modelInfo, setModelInfo] = useState<EmbeddingModelInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchModelInfo = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.get("/embeddings/model-info");
      setModelInfo(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch model info");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModelInfo();
  }, [fetchModelInfo]);

  return { modelInfo, loading, error, refetch: fetchModelInfo };
};

export const useBatchEmbeddingStatus = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getBatchStatus = useCallback(async (documentIds: number[]) => {
    setLoading(true);
    setError(null);

    try {
      const params = documentIds.map((id) => `document_ids=${id}`).join("&");
      const response = await api.get(`/embeddings/batch-status?${params}`);
      return response.data as BatchEmbeddingResponse;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to get batch status";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  return { getBatchStatus, loading, error };
};
