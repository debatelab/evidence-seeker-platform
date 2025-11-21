/**
 * Fact-check management console backed by EvidenceSeeker pipeline APIs.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import {
  Activity,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  Loader2,
  Play,
  RefreshCw,
  ShieldCheck,
  StopCircle,
} from "lucide-react";
import {
  FactCheckResult,
  FactCheckRun,
  FactCheckRunDetail,
} from "../../types/factCheck";
import { useEvidenceSeekerRuns } from "../../hooks/useEvidenceSeekerRuns";
import { useProgressUpdates } from "../../hooks/useSearch";
import { useConfigurationStatus } from "../../hooks/useConfigurationStatus";
import { ConfigurationBlockedNotice } from "../Configuration/ConfigurationBlockedNotice";

interface EvidenceSeekerFactChecksProps {
  evidenceSeekerUuid: string;
}

type RunStatus = FactCheckRun["status"];

const statusTone: Record<RunStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  RUNNING: "bg-primary-soft text-primary-strong",
  SUCCEEDED: "bg-green-100 text-green-800",
  FAILED: "bg-red-100 text-red-800",
  CANCELLED: "bg-gray-100 text-gray-600",
};

const terminalStatuses: RunStatus[] = ["SUCCEEDED", "FAILED", "CANCELLED"];

const isTerminal = (status: string | undefined): boolean => {
  if (!status) return false;
  return ["COMPLETED", "FAILED", "CANCELLED", "SUCCEEDED"].includes(
    status.toUpperCase()
  );
};

const numberFromInput = (value: string): number | undefined => {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    throw new Error("Must be a valid number.");
  }
  return parsed;
};

const parseMetadataFilters = (
  input: string
): Record<string, unknown> | undefined => {
  if (!input.trim()) return undefined;
  const parsed = JSON.parse(input);
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Metadata filters must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
};

const EvidenceSeekerFactChecks: React.FC<EvidenceSeekerFactChecksProps> = ({
  evidenceSeekerUuid,
}) => {
  const navigate = useNavigate();
  const {
    runs,
    loading,
    creating,
    error,
    refresh,
    createRun,
    cancelRun,
    rerun,
    getRunDetail,
    getRunResults,
  } = useEvidenceSeekerRuns(evidenceSeekerUuid);
  const {
    status: configurationStatus,
    loading: statusLoading,
    error: statusError,
  } = useConfigurationStatus(evidenceSeekerUuid);
  const isConfigured = configurationStatus?.isReady ?? false;

  const [statement, setStatement] = useState("");
  const [topK, setTopK] = useState("");
  const [temperature, setTemperature] = useState("");
  const [maxTokens, setMaxTokens] = useState("");
  const [language, setLanguage] = useState("");
  const [metadataFiltersRaw, setMetadataFiltersRaw] = useState("");
  const [documentUuidsRaw, setDocumentUuidsRaw] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const location = useLocation();
  const [showHint, setShowHint] = useState(
    Boolean(
      (location.state as { showOnboardingHint?: boolean } | null)
        ?.showOnboardingHint
    )
  );

  const [selectedRunUuid, setSelectedRunUuid] = useState<string | null>(null);
  const [runDetail, setRunDetail] = useState<FactCheckRunDetail | null>(null);
  const [results, setResults] = useState<FactCheckResult[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const activeRun = useMemo(
    () =>
      runs.find(
        (runItem) =>
          runItem.status === "RUNNING" || runItem.status === "PENDING"
      ) ?? null,
    [runs]
  );

  const {
    currentUpdate,
    connected: progressConnected,
    error: progressError,
  } = useProgressUpdates(activeRun?.operationId ?? null);

  useEffect(() => {
    if (!selectedRunUuid && runs.length > 0) {
      void loadRun(runs[0].uuid);
    }
  }, [runs, selectedRunUuid]);

  useEffect(() => {
    if (!activeRun || !currentUpdate?.status) {
      return;
    }

    if (isTerminal(currentUpdate.status)) {
      void refresh();
      void loadRun(activeRun.uuid);
    }
  }, [activeRun, currentUpdate?.status, refresh]);

  useEffect(() => {
    if (showHint) {
      navigate(".", { replace: true, state: {} });
    }
  }, [showHint, navigate]);

  const loadRun = useCallback(
    async (runUuid: string) => {
      setDetailLoading(true);
      setDetailError(null);
      setSelectedRunUuid(runUuid);
      try {
        const detail = await getRunDetail(runUuid);
        const runResults = await getRunResults(runUuid);
        if (!detail) {
          setRunDetail(null);
          setResults([]);
          setDetailError("Run not found.");
          return;
        }
        setRunDetail(detail);
        setResults(runResults);
      } catch (err: any) {
        setDetailError(err?.message ?? "Failed to load run details.");
      } finally {
        setDetailLoading(false);
      }
    },
    [getRunDetail, getRunResults]
  );

  const resetForm = () => {
    setStatement("");
    setTopK("");
    setTemperature("");
    setMaxTokens("");
    setLanguage("");
    setMetadataFiltersRaw("");
    setDocumentUuidsRaw("");
  };

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    event.preventDefault();
    if (!statement.trim()) {
      setFormError("Enter a statement to fact-check.");
      return;
    }

    const overrides: Record<string, unknown> = {};

    try {
      const maybeTopK = numberFromInput(topK);
      if (typeof maybeTopK === "number") {
        overrides.top_k = maybeTopK;
      }
    } catch (err) {
      setFormError("Top K must be numeric.");
      return;
    }

    try {
      const maybeMaxTokens = numberFromInput(maxTokens);
      if (typeof maybeMaxTokens === "number") {
        overrides.max_tokens = maybeMaxTokens;
      }
    } catch (err) {
      setFormError("Max tokens must be numeric.");
      return;
    }

    try {
      const maybeTemperature = numberFromInput(temperature);
      if (typeof maybeTemperature === "number") {
        overrides.temperature = maybeTemperature;
      }
    } catch (err) {
      setFormError("Temperature must be numeric.");
      return;
    }

    if (language.trim()) {
      overrides.language = language.trim();
    }

    let metadataFilters: Record<string, unknown> | undefined;
    try {
      metadataFilters = parseMetadataFilters(metadataFiltersRaw);
    } catch (err: any) {
      setFormError(err?.message ?? "Invalid metadata filters.");
      return;
    }

    if (documentUuidsRaw.trim()) {
      const ids = documentUuidsRaw
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
      if (ids.length > 0) {
        metadataFilters = {
          ...(metadataFilters ?? {}),
          document_uuid: ids,
        };
      }
    }

    if (metadataFilters && Object.keys(metadataFilters).length > 0) {
      overrides.metadata_filters = metadataFilters;
    }

    const payloadOverrides =
      Object.keys(overrides).length > 0 ? overrides : undefined;

    try {
      const run = await createRun({
        statement: statement.trim(),
        overrides: payloadOverrides,
      });
      if (run) {
        setFormError(null);
        resetForm();
        await loadRun(run.uuid);
      }
    } catch (err: any) {
      setFormError(err?.message ?? "Failed to create fact-check run.");
    }
  };

  const handleCancelRun = async (runUuid: string) => {
    const confirmed = window.confirm("Cancel this fact-check run?");
    if (!confirmed) return;
    const success = await cancelRun(runUuid);
    if (success) {
      await refresh();
      await loadRun(runUuid);
    }
  };

  const handleRerun = async (runUuid: string) => {
    try {
      const newRun = await rerun(runUuid);
      if (newRun) {
        await loadRun(newRun.uuid);
      }
    } catch (err: any) {
      setDetailError(err?.message ?? "Failed to rerun fact check.");
    }
  };

  const progressValue = Math.round(currentUpdate?.progress ?? 0);
  const progressLabel = currentUpdate?.message ?? "Processing";

  if (statusLoading) {
    return (
      <div className="flex justify-center items-center p-10">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (statusError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4 text-red-800">
        {statusError}
      </div>
    );
  }

  if (!isConfigured) {
    return (
      <ConfigurationBlockedNotice
        status={configurationStatus}
        onConfigure={() =>
          navigate(`/app/evidence-seekers/${evidenceSeekerUuid}/manage/config`)
        }
        description="Complete configuration before submitting or rerunning fact-check jobs."
      />
    );
  }

  return (
    <div className="space-y-6">
      {showHint && (
        <div className="rounded-lg border border-primary-border bg-primary-soft p-4 flex items-start justify-between">
          <div className="text-sm text-primary space-y-1">
            <p className="font-semibold text-primary-strong">
              You're ready to run your first fact check!
            </p>
            <p>
              Enter a statement below and click Run Fact Check to validate it
              against your newly uploaded documents.
            </p>
          </div>
          <button
            type="button"
            className="text-sm text-primary hover:text-primary-strong"
            onClick={() => setShowHint(false)}
          >
            Dismiss
          </button>
        </div>
      )}
      <section className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 space-y-4">
        <header>
          <h2 className="brand-title text-lg text-gray-900 flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            Run a Fact Check
          </h2>
          <p className="text-sm text-gray-600">
            Submit a claim to verify against the indexed EvidenceSeeker corpus.
          </p>
        </header>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Statement
            </label>
            <textarea
              value={statement}
              onChange={(event) => setStatement(event.target.value)}
              rows={3}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Enter the claim you want to verify…"
              required
            />
          </div>

          <button
            type="button"
            onClick={() => setAdvancedOpen((prev) => !prev)}
            className="flex items-center text-sm text-primary hover:text-primary-strong"
          >
            {advancedOpen ? (
              <ChevronUp className="h-4 w-4 mr-1" />
            ) : (
              <ChevronDown className="h-4 w-4 mr-1" />
            )}
            Advanced overrides
          </button>

          {advancedOpen && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border border-gray-200 rounded-lg p-4 bg-gray-50">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Top K
                </label>
                <input
                  type="number"
                  min={1}
                  value={topK}
                  onChange={(event) => setTopK(event.target.value)}
                  placeholder="e.g. 10"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Temperature
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={temperature}
                  onChange={(event) => setTemperature(event.target.value)}
                  placeholder="e.g. 0.2"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max tokens
                </label>
                <input
                  type="number"
                  min={1}
                  value={maxTokens}
                  onChange={(event) => setMaxTokens(event.target.value)}
                  placeholder="e.g. 1200"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Language
                </label>
                <input
                  type="text"
                  value={language}
                  onChange={(event) => setLanguage(event.target.value)}
                  placeholder="e.g. en"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Metadata filters (JSON)
                </label>
                <textarea
                  value={metadataFiltersRaw}
                  onChange={(event) =>
                    setMetadataFiltersRaw(event.target.value)
                  }
                  rows={3}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder='{"topic": "climate"}'
                />
                <p className="text-xs text-gray-500 mt-1">
                  Overrides merge with the seeker’s default metadata filters.
                </p>
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Restrict to document UUIDs (comma separated)
                </label>
                <input
                  type="text"
                  value={documentUuidsRaw}
                  onChange={(event) => setDocumentUuidsRaw(event.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="uuid-1, uuid-2"
                />
              </div>
            </div>
          )}

          {(formError || error) && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              <span>{formError ?? error}</span>
            </div>
          )}

          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <button
              type="submit"
              disabled={creating}
              className="btn-primary px-4 py-2 flex items-center gap-2 justify-center disabled:opacity-50"
            >
              {creating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Starting run…</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  <span>Run Fact Check</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={resetForm}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Clear fields
            </button>
          </div>
        </form>
      </section>

      {activeRun && (
        <section className="bg-white border border-primary-border rounded-lg shadow-sm p-5 space-y-3">
          <header className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              <div>
                <h3 className="text-sm font-semibold text-primary-strong">
                  Active run in progress
                </h3>
                <p className="text-xs text-primary">
                  {progressLabel} •{" "}
                  {progressConnected ? "Tracking" : "Awaiting updates"}
                </p>
              </div>
            </div>
            {!terminalStatuses.includes(activeRun.status) && (
              <button
                onClick={() => void handleCancelRun(activeRun.uuid)}
                className="text-xs text-red-600 hover:text-red-800 flex items-center gap-1"
              >
                <StopCircle className="h-4 w-4" />
                Cancel run
              </button>
            )}
          </header>
          <div>
            <p className="text-sm text-gray-700 mb-2">
              {activeRun.statement.slice(0, 200)}
              {activeRun.statement.length > 200 ? "…" : ""}
            </p>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div
                className="bg-primary h-2 rounded-full transition-all"
                style={{ width: `${Math.min(progressValue, 100)}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Status: {activeRun.status}
              {progressError && ` • ${progressError}`}
            </p>
          </div>
        </section>
      )}

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <ClipboardList className="h-4 w-4 text-gray-500" />
              Run history
            </h3>
            <button
              onClick={() => void refresh()}
              className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
            >
              <RefreshCw className="h-3 w-3" />
              Refresh
            </button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span className="ml-2 text-sm text-gray-600">Loading runs…</span>
            </div>
          ) : runs.length === 0 ? (
            <p className="text-sm text-gray-500">
              No fact-check runs yet. Submit a statement above to get started.
            </p>
          ) : (
            <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
              {runs.map((run) => {
                const isSelected = run.uuid === selectedRunUuid;
                return (
                  <button
                    key={run.uuid}
                    onClick={() => void loadRun(run.uuid)}
                    className={`w-full text-left border rounded-lg p-4 transition shadow-sm ${
                      isSelected
                        ? "border-primary-border bg-primary-soft"
                        : "border-gray-200 bg-white hover:border-primary-border"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusTone[run.status]}`}
                      >
                        {run.status}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(run.createdAt).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-800 line-clamp-2">
                      {run.statement}
                    </p>
                    <div className="flex items-center gap-3 mt-3 text-xs text-gray-500">
                      {run.completedAt ? (
                        <span>
                          Completed{" "}
                          {new Date(run.completedAt).toLocaleTimeString()}
                        </span>
                      ) : (
                        <span>In progress</span>
                      )}
                      <button
                        type="button"
                        className="text-primary hover:text-primary-strong"
                        onClick={(event) => {
                          event.stopPropagation();
                          void handleRerun(run.uuid);
                        }}
                      >
                        Rerun
                      </button>
                      {!terminalStatuses.includes(run.status) && (
                        <button
                          type="button"
                          className="text-red-600 hover:text-red-800"
                          onClick={(event) => {
                            event.stopPropagation();
                            void handleCancelRun(run.uuid);
                          }}
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5 space-y-4">
          <header className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <Activity className="h-4 w-4 text-gray-500" />
              Run details
            </h3>
            {runDetail && (
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusTone[runDetail.status as RunStatus]}`}
              >
                {runDetail.status}
              </span>
            )}
          </header>

          {detailLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span className="ml-2 text-sm text-gray-600">
                Loading run details…
              </span>
            </div>
          ) : detailError ? (
            <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              <span>{detailError}</span>
            </div>
          ) : !runDetail ? (
            <p className="text-sm text-gray-500">
              Select a run on the left to inspect results.
            </p>
          ) : (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-semibold text-gray-800">
                  Statement
                </h4>
                <p className="text-sm text-gray-700 mt-1">
                  {runDetail.statement}
                </p>
              </div>

              {runDetail.metrics && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-800">
                    Metrics
                  </h4>
                  <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-gray-600">
                    {Object.entries(runDetail.metrics).map(([key, value]) => (
                      <div key={key} className="bg-gray-50 rounded-md p-2">
                        <span className="font-medium">{key}</span>:{" "}
                        {String(value)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-gray-800">
                  Interpretations
                </h4>
                {results.length === 0 ? (
                  <p className="text-sm text-gray-500">
                    No interpretations available yet.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {results.map((result) => (
                      <div
                        key={result.id}
                        className="border border-gray-200 rounded-lg p-3"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-semibold text-gray-800">
                              #{result.interpretationIndex + 1}{" "}
                              {result.interpretationType}
                            </p>
                            {result.confirmationLevel && (
                              <p className="text-xs text-gray-500">
                                Confirmation: {result.confirmationLevel}
                              </p>
                            )}
                          </div>
                          {typeof result.confidenceScore === "number" && (
                            <span className="text-xs text-gray-500">
                              Confidence:{" "}
                              {(result.confidenceScore * 100).toFixed(1)}%
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-700 mt-2">
                          {result.interpretationText}
                        </p>
                        {result.summary && (
                          <p className="text-xs text-gray-500 mt-2">
                            Summary: {result.summary}
                          </p>
                        )}
                        <div className="mt-3 space-y-2">
                          <p className="text-xs font-semibold text-gray-700">
                            Evidence
                          </p>
                          {result.evidence.length === 0 ? (
                            <p className="text-xs text-gray-500">
                              No evidence supplied.
                            </p>
                          ) : (
                            result.evidence.map((item) => (
                              <div
                                key={`${result.id}-${item.libraryNodeId ?? item.documentUuid ?? item.chunkLabel}`}
                                className="bg-gray-50 border border-gray-200 rounded-md p-2 text-xs text-gray-700 space-y-1"
                              >
                                <p className="font-medium">
                                  {item.stance}: {item.evidenceText}
                                </p>
                                {typeof item.score === "number" && (
                                  <p>Score: {(item.score * 100).toFixed(1)}%</p>
                                )}
                                {item.documentUuid && (
                                  <p>Document UUID: {item.documentUuid}</p>
                                )}
                                {item.metadata && (
                                  <p className="text-gray-500">
                                    Metadata:{" "}
                                    {JSON.stringify(item.metadata, null, 2)}
                                  </p>
                                )}
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

export default EvidenceSeekerFactChecks;
