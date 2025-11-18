import { useCallback, useEffect, useState } from "react";
import apiClient, { evidenceSeekerAPI } from "../utils/api";
import type {
  EvidenceSearchRequest,
  EvidenceSearchResponse,
  ProgressUpdate,
  SystemStatistics,
} from "../types/search";

const toErrorMessage = (error: unknown, fallback: string): string => {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    error.response !== null &&
    "data" in error.response
  ) {
    const detail =
      (error.response as { data?: { detail?: unknown } }).data?.detail ?? null;
    if (typeof detail === "string") {
      return detail;
    }
    if (
      detail &&
      typeof detail === "object" &&
      "message" in detail &&
      typeof (detail as Record<string, unknown>).message === "string"
    ) {
      return (detail as { message: string }).message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
};

export const useEvidenceSearch = (evidenceSeekerUuid: string) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(
    async (request: EvidenceSearchRequest): Promise<EvidenceSearchResponse> => {
      setLoading(true);
      setError(null);
      try {
        const response = await evidenceSeekerAPI.searchEvidence(
          evidenceSeekerUuid,
          request
        );
        return response;
      } catch (err: any) {
        const message = toErrorMessage(err, "Search failed");
        setError(message);
        throw new Error(message);
      } finally {
        setLoading(false);
      }
    },
    [evidenceSeekerUuid]
  );

  return { search, loading, error };
};

export const useSystemStatistics = () => {
  const [stats, setStats] = useState<SystemStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<SystemStatistics>(
        "/config/system-stats"
      );
      setStats(response.data);
    } catch (err: any) {
      const message =
        err?.response?.data?.detail ?? err?.message ?? "Failed to load stats";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchStats();
  }, [fetchStats]);

  return { stats, loading, error, refetch: fetchStats };
};

export const useProgressUpdates = (operationId: string | null) => {
  const [updates, setUpdates] = useState<ProgressUpdate[]>([]);
  const [currentUpdate, setCurrentUpdate] = useState<ProgressUpdate | null>(
    null
  );
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!operationId) {
      setCurrentUpdate(null);
      setUpdates([]);
      return;
    }

    let isMounted = true;
    let intervalId: number | undefined;
    setConnected(false);
    setError(null);

    const isTerminalStatus = (status: string | undefined): boolean => {
      if (!status) return false;
      return ["COMPLETED", "FAILED", "CANCELLED", "SUCCEEDED"].includes(
        status.toUpperCase()
      );
    };

    const poll = async () => {
      try {
        const response = await apiClient.get(
          `/progress/operations/${operationId}`
        );
        if (!isMounted) {
          return;
        }

        const operation = response.data;
        const update: ProgressUpdate = {
          operation_id: operation.operation_id,
          progress: operation.progress ?? 0,
          status: operation.status ?? "UNKNOWN",
          message: operation.message ?? "",
          current_step: operation.current_step,
          total_steps: operation.total_steps,
          estimated_time_remaining: operation.estimated_time_remaining,
          timestamp: operation.updated_at,
          metadata: operation.metadata,
        };

        setCurrentUpdate(update);
        setUpdates((prev) => {
          const next = [...prev, update];
          // Prevent unbounded growth
          return next.slice(-50);
        });
        setConnected(true);

        // Stop polling if status is terminal
        if (isTerminalStatus(update.status)) {
          if (intervalId !== undefined) {
            window.clearInterval(intervalId);
            intervalId = undefined;
          }
        }
      } catch (err: any) {
        if (!isMounted) {
          return;
        }
        const message =
          err?.response?.data?.detail ??
          err?.message ??
          "Failed to fetch progress";
        setError(message);
        setConnected(false);
      }
    };

    // initial fetch
    void poll();

    intervalId = window.setInterval(() => {
      void poll();
    }, 2000);

    return () => {
      isMounted = false;
      if (intervalId !== undefined) {
        window.clearInterval(intervalId);
      }
    };
  }, [operationId]);

  return { updates, currentUpdate, connected, error };
};
