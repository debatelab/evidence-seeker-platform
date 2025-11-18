import { useCallback, useEffect, useState } from "react";
import type {
  CreateFactCheckRunRequest,
  FactCheckResult,
  FactCheckRun,
  FactCheckRunDetail,
  RerunFactCheckRequest,
} from "../types/factCheck";
import { evidenceSeekerAPI } from "../utils/api";

interface UseEvidenceSeekerRuns {
  runs: FactCheckRun[];
  loading: boolean;
  creating: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  createRun: (
    payload: CreateFactCheckRunRequest
  ) => Promise<FactCheckRun | null>;
  cancelRun: (runUuid: string) => Promise<boolean>;
  rerun: (
    runUuid: string,
    payload?: RerunFactCheckRequest
  ) => Promise<FactCheckRun | null>;
  getRunDetail: (runUuid: string) => Promise<FactCheckRunDetail | null>;
  getRunResults: (runUuid: string) => Promise<FactCheckResult[]>;
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
  return "Unexpected error while processing fact-check runs.";
};

export const useEvidenceSeekerRuns = (
  evidenceSeekerUuid: string | undefined
): UseEvidenceSeekerRuns => {
  const [runs, setRuns] = useState<FactCheckRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    if (!evidenceSeekerUuid) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await evidenceSeekerAPI.listFactCheckRuns(
        evidenceSeekerUuid
      );
      setRuns(data);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [evidenceSeekerUuid]);

  useEffect(() => {
    void fetchRuns();
  }, [fetchRuns]);

  const createRun = useCallback(
    async (payload: CreateFactCheckRunRequest) => {
      if (!evidenceSeekerUuid) {
        setError("Evidence Seeker UUID is required.");
        return null;
      }
      setCreating(true);
      setError(null);
      try {
        const run = await evidenceSeekerAPI.createFactCheckRun(
          evidenceSeekerUuid,
          payload
        );
        setRuns((prev) => {
          const next = [run, ...prev.filter((item) => item.uuid !== run.uuid)];
          return next;
        });
        return run;
      } catch (err) {
        const message = toErrorMessage(err);
        setError(message);
        throw new Error(message);
      } finally {
        setCreating(false);
      }
    },
    [evidenceSeekerUuid]
  );

  const cancelRun = useCallback(
    async (runUuid: string) => {
      if (!evidenceSeekerUuid) {
        setError("Evidence Seeker UUID is required.");
        return false;
      }
      try {
        await evidenceSeekerAPI.cancelFactCheckRun(
          evidenceSeekerUuid,
          runUuid
        );
        setRuns((prev) =>
          prev.map((run) =>
            run.uuid === runUuid
              ? {
                  ...run,
                  status: "CANCELLED",
                  completedAt: new Date().toISOString(),
                  errorMessage: "Run cancelled by user",
                }
              : run
          )
        );
        return true;
      } catch (err) {
        setError(toErrorMessage(err));
        return false;
      }
    },
    [evidenceSeekerUuid]
  );

  const rerun = useCallback(
    async (runUuid: string, payload: RerunFactCheckRequest = {}) => {
      if (!evidenceSeekerUuid) {
        setError("Evidence Seeker UUID is required.");
        return null;
      }
      setCreating(true);
      setError(null);
      try {
        const run = await evidenceSeekerAPI.rerunFactCheck(
          evidenceSeekerUuid,
          runUuid,
          payload
        );
        setRuns((prev) => {
          const next = [run, ...prev.filter((item) => item.uuid !== run.uuid)];
          return next;
        });
        return run;
      } catch (err) {
        const message = toErrorMessage(err);
        setError(message);
        throw new Error(message);
      } finally {
        setCreating(false);
      }
    },
    [evidenceSeekerUuid]
  );

  const getRunDetail = useCallback(
    async (runUuid: string) => {
      if (!evidenceSeekerUuid) {
        setError("Evidence Seeker UUID is required.");
        return null;
      }
      try {
        return await evidenceSeekerAPI.getFactCheckRun(
          evidenceSeekerUuid,
          runUuid
        );
      } catch (err) {
        setError(toErrorMessage(err));
        return null;
      }
    },
    [evidenceSeekerUuid]
  );

  const getRunResults = useCallback(
    async (runUuid: string) => {
      if (!evidenceSeekerUuid) {
        setError("Evidence Seeker UUID is required.");
        return [];
      }
      try {
        return await evidenceSeekerAPI.getFactCheckResults(
          evidenceSeekerUuid,
          runUuid
        );
      } catch (err) {
        setError(toErrorMessage(err));
        return [];
      }
    },
    [evidenceSeekerUuid]
  );

  return {
    runs,
    loading,
    creating,
    error,
    refresh: fetchRuns,
    createRun,
    cancelRun,
    rerun,
    getRunDetail,
    getRunResults,
  };
};
