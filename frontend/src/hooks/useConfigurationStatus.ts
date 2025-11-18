import { useCallback, useEffect, useState } from "react";
import type { ConfigurationStatus } from "../types/evidenceSeeker";
import { evidenceSeekerAPI } from "../utils/api";

interface UseConfigurationStatusResult {
  status: ConfigurationStatus | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const toErrorMessage = (error: unknown): string => {
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
      (error.response as { data?: { detail?: string | Record<string, unknown> } })
        .data?.detail ?? null;
    if (typeof detail === "string") {
      return detail;
    }
    if (
      detail &&
      typeof detail === "object" &&
      "message" in detail &&
      typeof detail.message === "string"
    ) {
      return detail.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Failed to load configuration status.";
};

export const useConfigurationStatus = (
  evidenceSeekerUuid: string | undefined
): UseConfigurationStatusResult => {
  const [status, setStatus] = useState<ConfigurationStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!evidenceSeekerUuid) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await evidenceSeekerAPI.getConfigurationStatus(
        evidenceSeekerUuid
      );
      setStatus(data);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [evidenceSeekerUuid]);

  useEffect(() => {
    void fetchStatus();
  }, [fetchStatus]);

  return {
    status,
    loading,
    error,
    refresh: fetchStatus,
  };
};
