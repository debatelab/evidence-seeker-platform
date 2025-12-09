import { useCallback, useEffect, useRef, useState } from "react";
import type { IndexJob } from "../types/indexJob";
import { evidenceSeekerAPI } from "../utils/api";

interface UseIndexJobsOptions {
  pollIntervalMs?: number;
}

interface UseIndexJobsResult {
  jobs: IndexJob[];
  loading: boolean;
  error: string | null;
  triggering: boolean;
  refresh: () => Promise<void>;
  triggerReindex: () => Promise<IndexJob | null>;
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
      (error.response as { data?: { detail?: string } }).data?.detail;
    if (typeof detail === "string" && detail.length > 0) {
      return detail;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected error while processing index jobs.";
};

export const useIndexJobs = (
  evidenceSeekerUuid: string | undefined,
  options: UseIndexJobsOptions = {}
): UseIndexJobsResult => {
  const [jobs, setJobs] = useState<IndexJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const pollInterval = useRef<number | undefined>(undefined);

  const fetchJobs = useCallback(async (showLoading = true) => {
    if (!evidenceSeekerUuid) {
      return;
    }
    if (showLoading) {
      setLoading(true);
    }
    setError(null);
    try {
      const data = await evidenceSeekerAPI.listIndexJobs(evidenceSeekerUuid);
      setJobs(data);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }, [evidenceSeekerUuid]);

  useEffect(() => {
    void fetchJobs();
  }, [fetchJobs]);

  useEffect(() => {
    if (!options.pollIntervalMs || !evidenceSeekerUuid) {
      return undefined;
    }
    pollInterval.current = window.setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) {
        return;
      }
      void fetchJobs(false);
    }, options.pollIntervalMs);

    return () => {
      if (pollInterval.current !== undefined) {
        window.clearInterval(pollInterval.current);
      }
    };
  }, [options.pollIntervalMs, evidenceSeekerUuid, fetchJobs]);

  const triggerReindex = useCallback(async () => {
    if (!evidenceSeekerUuid) {
      setError("Evidence Seeker UUID is required.");
      return null;
    }
    setTriggering(true);
    setError(null);

    try {
      const job = await evidenceSeekerAPI.triggerReindex(evidenceSeekerUuid);
      setJobs((prev) => {
        const next = [job, ...prev];
        const deduped = new Map(next.map((item) => [item.uuid, item]));
        return Array.from(deduped.values());
      });
      return job;
    } catch (err) {
      const message = toErrorMessage(err);
      setError(message);
      throw new Error(message);
    } finally {
      setTriggering(false);
    }
  }, [evidenceSeekerUuid]);

  return {
    jobs,
    loading,
    error,
    triggering,
    refresh: fetchJobs,
    triggerReindex,
  };
};
