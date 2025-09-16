/**
 * React hooks for search operations
 */

import { useState, useEffect, useCallback } from "react";
import api from "../utils/api";
import {
  SearchQuery,
  SearchResponse,
  EmbeddingSearchQuery,
  EmbeddingSearchResponse,
  DocumentChunk,
  DocumentChunksResponse,
  SearchStatistics,
  SimilarDocumentsQuery,
  SimilarDocumentsResponse,
  AnalysisQuery,
  AnalysisResult,
  ProgressUpdate,
} from "../types/search";

export const useSearch = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (query: SearchQuery) => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.post("/search", query);
      return response.data as SearchResponse;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || "Search failed";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  return { search, loading, error };
};

export const useEmbeddingSearch = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const searchByEmbedding = useCallback(async (query: EmbeddingSearchQuery) => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.post("/search/embedding", query);
      return response.data as EmbeddingSearchResponse;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Embedding search failed";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  return { searchByEmbedding, loading, error };
};

export const useDocumentChunks = (documentId: number) => {
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchChunks = useCallback(async () => {
    if (!documentId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.get(`/search/document/${documentId}/chunks`);
      const data = response.data as DocumentChunksResponse;
      setChunks(data.chunks);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch document chunks");
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    fetchChunks();
  }, [fetchChunks]);

  return { chunks, loading, error, refetch: fetchChunks };
};

export const useSearchStatistics = () => {
  const [stats, setStats] = useState<SearchStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.get("/search/statistics");
      setStats(response.data);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || "Failed to fetch search statistics"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return { stats, loading, error, refetch: fetchStats };
};

export const useSimilarDocuments = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const findSimilar = useCallback(async (query: SimilarDocumentsQuery) => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.post("/search/similar", query);
      return response.data as SimilarDocumentsResponse;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to find similar documents";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  return { findSimilar, loading, error };
};

export const useAnalysis = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(async (query: AnalysisQuery) => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.post("/search/analyze", query);
      return response.data as AnalysisResult;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || "Analysis failed";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  return { analyze, loading, error };
};

export const useProgressUpdates = (operationId: string) => {
  const [updates, setUpdates] = useState<ProgressUpdate[]>([]);
  const [currentUpdate, setCurrentUpdate] = useState<ProgressUpdate | null>(
    null
  );
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!operationId) return;

    // In a real implementation, this would connect to WebSocket
    // For now, we'll simulate with polling
    const pollProgress = async () => {
      try {
        const response = await api.get(`/progress/operations/${operationId}`);
        const operation = response.data;

        const update: ProgressUpdate = {
          operation_id: operation.operation_id,
          progress: operation.progress,
          status: operation.status,
          message: operation.message,
          current_step: operation.current_step,
          total_steps: operation.total_steps,
          estimated_time_remaining: operation.estimated_time_remaining,
          timestamp: operation.updated_at,
          metadata: operation.metadata,
        };

        setCurrentUpdate(update);
        setUpdates((prev) => [...prev, update]);
        setConnected(true);
        setError(null);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to get progress");
        setConnected(false);
      }
    };

    // Initial poll
    pollProgress();

    // Set up polling interval
    const interval = setInterval(pollProgress, 2000); // Poll every 2 seconds

    return () => {
      clearInterval(interval);
      setConnected(false);
    };
  }, [operationId]);

  return { updates, currentUpdate, connected, error };
};
