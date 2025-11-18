import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  EvidenceSeekerSettings,
  EvidenceSeekerTestSettingsResponse,
} from "../types/evidenceSeeker";
import { evidenceSeekerAPI } from "../utils/api";

interface UseEvidenceSeekerSettings {
  settings: EvidenceSeekerSettings | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  testResult: EvidenceSeekerTestSettingsResponse | null;
  testing: boolean;
  testError: string | null;
  refresh: () => Promise<void>;
  updateSettings: (
    updates: Record<string, unknown>
  ) => Promise<EvidenceSeekerSettings | null>;
  testSettings: (
    payload: Record<string, unknown>
  ) => Promise<EvidenceSeekerTestSettingsResponse | null>;
  metadataPreview: string;
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

  return "Unexpected error while processing settings.";
};

export const useEvidenceSeekerSettings = (
  evidenceSeekerUuid: string | undefined
): UseEvidenceSeekerSettings => {
  const [settings, setSettings] = useState<EvidenceSeekerSettings | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] =
    useState<EvidenceSeekerTestSettingsResponse | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const fetchSettings = useCallback(async () => {
    if (!evidenceSeekerUuid) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await evidenceSeekerAPI.getSettings(evidenceSeekerUuid);
      setSettings(data);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [evidenceSeekerUuid]);

  useEffect(() => {
    void fetchSettings();
  }, [fetchSettings]);

  const updateSettings = useCallback(
    async (updates: Record<string, unknown>) => {
      if (!evidenceSeekerUuid) {
        setError("Evidence Seeker UUID is required.");
        return null;
      }
      setSaving(true);
      setError(null);
      try {
        const data = await evidenceSeekerAPI.updateSettings(
          evidenceSeekerUuid,
          updates
        );
        setSettings(data);
        return data;
      } catch (err) {
        const message = toErrorMessage(err);
        setError(message);
        throw new Error(message);
      } finally {
        setSaving(false);
      }
    },
    [evidenceSeekerUuid]
  );

  const testSettings = useCallback(
    async (payload: Record<string, unknown>) => {
      if (!evidenceSeekerUuid) {
        setTestError("Evidence Seeker UUID is required.");
        return null;
      }
      setTesting(true);
      setTestError(null);
      setTestResult(null);
      try {
        const data = await evidenceSeekerAPI.testSettings(
          evidenceSeekerUuid,
          payload
        );
        setTestResult(data);
        return data;
      } catch (err) {
        const message = toErrorMessage(err);
        setTestError(message);
        throw new Error(message);
      } finally {
        setTesting(false);
      }
    },
    [evidenceSeekerUuid]
  );

  const metadataPreview = useMemo(() => {
    if (!settings?.metadataFilters) {
      return "{}";
    }
    try {
      return JSON.stringify(settings.metadataFilters, null, 2);
    } catch {
      return "{}";
    }
  }, [settings]);

  return {
    settings,
    loading,
    saving,
    error,
    testResult,
    testing,
    testError,
    refresh: fetchSettings,
    updateSettings,
    testSettings,
    metadataPreview,
  };
};
