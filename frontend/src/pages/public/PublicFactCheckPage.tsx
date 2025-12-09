import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  CircleSlash2,
  XCircle,
  ShieldCheck,
  Loader2,
} from "lucide-react";
import PublicLayout from "../../components/Public/PublicLayout";
import { publicAPI } from "../../utils/api";
import type { PublicFactCheckRunDetailResponse } from "../../types/public";

type ConfirmationDisplay = {
  label: string;
  bg: string;
  text: string;
  border: string;
  icon: LucideIcon;
};

type ConfirmationDisplayWithKey = ConfirmationDisplay & { key: string };

type ConfirmationSummary = ConfirmationDisplayWithKey & { count: number };

const confirmationLevelStyles: Record<string, ConfirmationDisplay> = {
  strongly_confirmed: {
    label: "Strongly confirmed",
    bg: "bg-emerald-50",
    text: "text-emerald-800",
    border: "border-emerald-200",
    icon: ShieldCheck,
  },
  confirmed: {
    label: "Confirmed",
    bg: "bg-green-50",
    text: "text-green-800",
    border: "border-green-200",
    icon: CheckCircle2,
  },
  weakly_confirmed: {
    label: "Weakly confirmed",
    bg: "bg-lime-50",
    text: "text-lime-800",
    border: "border-lime-200",
    icon: CheckCircle2,
  },
  inconclusive_confirmation: {
    label: "Inconclusive confirmation",
    bg: "bg-amber-50",
    text: "text-amber-800",
    border: "border-amber-200",
    icon: AlertCircle,
  },
  weakly_disconfirmed: {
    label: "Weakly disconfirmed",
    bg: "bg-orange-50",
    text: "text-orange-800",
    border: "border-orange-200",
    icon: CircleSlash2,
  },
  disconfirmed: {
    label: "Disconfirmed",
    bg: "bg-red-50",
    text: "text-red-800",
    border: "border-red-200",
    icon: XCircle,
  },
  strongly_disconfirmed: {
    label: "Strongly disconfirmed",
    bg: "bg-rose-50",
    text: "text-rose-800",
    border: "border-rose-200",
    icon: AlertTriangle,
  },
};

const fallbackConfirmationStyle: ConfirmationDisplay = {
  label: "Pending interpretation",
  bg: "bg-gray-100",
  text: "text-gray-700",
  border: "border-gray-200",
  icon: HelpCircle,
};

const toTitleCase = (value: string) =>
  value
    .replace(/_/g, " ")
    .replace(
      /\w\S*/g,
      (word) => word[0].toUpperCase() + word.slice(1).toLowerCase()
    );

const getConfirmationDisplay = (
  level?: string | null
): ConfirmationDisplayWithKey => {
  if (!level) {
    return { key: "pending", ...fallbackConfirmationStyle };
  }
  const normalized = level.toLowerCase();
  if (confirmationLevelStyles[normalized]) {
    return { key: normalized, ...confirmationLevelStyles[normalized] };
  }
  return {
    key: normalized,
    ...fallbackConfirmationStyle,
    label: toTitleCase(level),
  };
};

const formatDateTime = (value?: string | null) => {
  if (!value) return null;
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    }).format(new Date(value));
  } catch {
    return new Date(value).toLocaleString();
  }
};

const isTerminalStatus = (status?: string | null): boolean => {
  if (!status) return false;
  return ["SUCCEEDED", "FAILED", "CANCELLED"].includes(status.toUpperCase());
};

const getErrorDetail = (error: unknown, fallback: string): string => {
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
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
};

const PublicFactCheckPage: React.FC = () => {
  const { runUuid } = useParams<{ runUuid: string }>();
  const [data, setData] = useState<PublicFactCheckRunDetailResponse | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [shareCopied, setShareCopied] = useState(false);
  const [pollError, setPollError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const pollIntervalRef = useRef<number | null>(null);
  const pollInFlight = useRef(false);
  const [openSources, setOpenSources] = useState<Record<number, boolean>>({});
  const [openEvidence, setOpenEvidence] = useState<Record<string, boolean>>({});

  const fetchRunDetail = useCallback(
    async (mode: "initial" | "poll" = "initial") => {
      if (!runUuid) return null;
      try {
        const response = await publicAPI.getFactCheck(runUuid);
        setData(response);
        setError(null);
        setPollError(null);
        setLastUpdatedAt(new Date());
        return response;
      } catch (err) {
        console.error(err);
        const detail = getErrorDetail(err, "Fact check not available.");
        if (mode === "initial") {
          setError(detail);
          setData(null);
        } else {
          setPollError(detail);
        }
        throw err;
      }
    },
    [runUuid]
  );

  useEffect(() => {
    if (!runUuid) return;
    let isMounted = true;
    setLoading(true);
    fetchRunDetail("initial")
      .catch(() => {
        /* errors handled in fetchRunDetail */
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [runUuid, fetchRunDetail]);

  useEffect(() => {
    if (!data?.run?.status || !runUuid) {
      return;
    }

    if (isTerminalStatus(data.run.status)) {
      if (pollIntervalRef.current) {
        window.clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      setIsPolling(false);
      return;
    }

    if (pollIntervalRef.current) {
      return;
    }

    setIsPolling(true);
    pollIntervalRef.current = window.setInterval(() => {
      if (document.hidden || pollInFlight.current) {
        return;
      }
      pollInFlight.current = true;
      fetchRunDetail("poll")
        .catch(() => {
          /* errors handled via pollError state */
        })
        .finally(() => {
          pollInFlight.current = false;
        });
    }, 3000);

    return () => {
      if (pollIntervalRef.current) {
        window.clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [data?.run?.status, runUuid, fetchRunDetail]);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        window.clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const handleShare = async () => {
    if (!runUuid) return;
    try {
      await navigator.clipboard.writeText(
        `${window.location.origin}/fact-checks/${runUuid}`
      );
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
    } catch (err) {
      console.error(err);
    }
  };

  const results = useMemo(() => data?.results ?? [], [data?.results]);
  const summaryEntries = useMemo(() => {
    if (results.length === 0) return [];
    const summaryMap: Record<string, ConfirmationSummary> = {};
    results.forEach((result) => {
      const confirmationDisplay = getConfirmationDisplay(
        result.confirmationLevel
      );
      if (!summaryMap[confirmationDisplay.key]) {
        summaryMap[confirmationDisplay.key] = {
          ...confirmationDisplay,
          count: 0,
        };
      }
      summaryMap[confirmationDisplay.key].count += 1;
    });
    return Object.values(summaryMap).sort((a, b) => b.count - a.count);
  }, [results]);

  const toggleSources = (resultId: number) => {
    setOpenSources((prev) => ({
      ...prev,
      [resultId]: !prev[resultId],
    }));
  };

  const toggleEvidence = (resultId: number, evidenceId: number) => {
    const key = `${resultId}-${evidenceId}`;
    setOpenEvidence((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const truncateText = (text: string, max = 220) => {
    if (text.length <= max) return text;
    return `${text.slice(0, max)}…`;
  };

  const extractContext = (
    metadata?: Record<string, unknown> | null
  ): string | null => {
    if (!metadata) return null;
    const candidates = [
      "context",
      "full_text",
      "fullText",
      "passage",
      "excerpt",
    ];
    for (const key of candidates) {
      const value = metadata[key];
      if (typeof value === "string" && value.trim()) {
        return value;
      }
    }
    return null;
  };

  const extractMetadataEntries = (
    metadata?: Record<string, unknown> | null
  ): Array<[string, string]> => {
    if (!metadata) return [];
    const skipKeys = new Set([
      "context",
      "full_text",
      "fullText",
      "passage",
      "excerpt",
    ]);
    return Object.entries(metadata).flatMap(([key, value]) => {
      if (skipKeys.has(key)) return [];
      if (typeof value === "string" || typeof value === "number") {
        return [[key, String(value)]];
      }
      return [];
    });
  };

  if (loading) {
    return (
      <PublicLayout>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center text-gray-500">
          Loading fact check...
        </div>
      </PublicLayout>
    );
  }

  if (error || !data) {
    return (
      <PublicLayout>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <p className="text-lg text-gray-600">{error}</p>
          <Link to="/" className="mt-4 btn-primary px-5 py-3 text-base">
            Back to homepage
          </Link>
        </div>
      </PublicLayout>
    );
  }

  const { run, seeker } = data;
  const submittedAt = formatDateTime(run.createdAt);
  const showStatusAsError =
    run.status === "FAILED" ||
    run.status === "CANCELLED" ||
    Boolean(run.errorMessage);
  const runInProgress = !isTerminalStatus(run.status);
  const hasResults = results.length > 0;
  const awaitingInterpretations = runInProgress && !hasResults;
  const runCompletedWithoutResults = !runInProgress && !hasResults;
  const emptyInterpretationMessage = (() => {
    if (hasResults) {
      return null;
    }
    if (awaitingInterpretations) {
      return "Interpretations will appear as soon as this run finishes processing.";
    }
    if (run.status === "FAILED") {
      return "This run failed before interpretations could be generated.";
    }
    if (run.status === "CANCELLED") {
      return "This run was cancelled before interpretations were generated.";
    }
    return "This run completed but no interpretations were generated.";
  })();
  const progressCopy =
    run.status === "RUNNING"
      ? {
          title: "Analyzing evidence",
          description:
            "Interpretations will appear below as soon as analysis completes.",
        }
      : {
          title: "Queued for processing",
          description: "Waiting for an available worker to start this run.",
        };

  return (
    <PublicLayout>
      <section className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm font-semibold">
            <Link
              to={`/evidence-seekers/${seeker.uuid}`}
              className="inline-flex items-center gap-2 text-primary hover:text-primary-strong"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to {seeker.title}
            </Link>
            <button
              onClick={handleShare}
              className="inline-flex items-center justify-center rounded-full border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:border-gray-400 transition"
            >
              {shareCopied ? "Link copied" : "Share"}
            </button>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Fact check result
            </p>
            <h1 className="brand-title mt-2 text-3xl text-gray-900">
              {run.statement}
            </h1>
            <p className="mt-2 text-sm text-gray-500">
              Powered by{" "}
              <Link
                to={`/evidence-seekers/${seeker.uuid}`}
                className="font-semibold text-primary hover:text-primary-strong"
              >
                {seeker.title}
              </Link>
            </p>
            <p className="mt-4 text-base text-gray-600">
              Submitted {submittedAt ? submittedAt : "—"}
            </p>
          </div>
          {showStatusAsError && (
            <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              <div>
                <p className="font-semibold">
                  {run.status === "FAILED"
                    ? "Run failed"
                    : run.status === "CANCELLED"
                      ? "Run was cancelled"
                      : "Run issue"}
                </p>
                {run.errorMessage && (
                  <p className="mt-1 text-sm text-red-700">
                    {run.errorMessage}
                  </p>
                )}
              </div>
            </div>
          )}

          {runInProgress && (
            <div className="flex flex-col gap-3 rounded-lg border border-primary-border bg-primary-soft px-4 py-4">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/70 text-primary">
                  <Loader2
                    className={`h-5 w-5 ${
                      run.status === "RUNNING" ? "animate-spin" : ""
                    }`}
                  />
                </span>
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-primary">
                    Run in progress
                  </p>
                  <p className="text-lg font-bold text-primary-strong">
                    {progressCopy.title}
                  </p>
                  <p className="text-sm text-primary">
                    {progressCopy.description} Stay on this page—results update
                    automatically.
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap items-center justify-between text-xs text-primary-strong">
                <span>
                  Backend status:{" "}
                  <span className="font-semibold">{run.status}</span>
                </span>
                {lastUpdatedAt && (
                  <span>
                    Last updated {lastUpdatedAt.toLocaleTimeString(undefined, {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </span>
                )}
                {isPolling && (
                  <span className="text-primary">
                    Refreshing every few seconds...
                  </span>
                )}
              </div>
            </div>
          )}

          {pollError && (
            <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900">
              <AlertCircle className="h-5 w-5 shrink-0" />
              <div>
                <p className="font-semibold">Connection issue</p>
                <p className="text-sm">
                  {pollError} We&apos;ll keep retrying—refresh the page if this
                  persists.
                </p>
              </div>
            </div>
          )}

          <div className="space-y-6">
            <div className="rounded-lg border border-gray-100 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-end justify-between gap-4">
                {emptyInterpretationMessage && (
                  <div>
                    <p className="text-sm text-gray-500">
                      {emptyInterpretationMessage}
                    </p>
                  </div>
                )}
              </div>
              {summaryEntries.length > 0 && (
                <div className="flex flex-wrap gap-6 mt-6">
                  {summaryEntries.map((entry) => {
                    const Icon = entry.icon;
                    return (
                      <div
                        key={entry.key}
                        className={`rounded-lg border-2 ${entry.border} ${entry.bg} p-5 transition`}
                      >
                        <div className="flex items-center gap-4">
                          <div className="flex flex-col">
                            <div className="flex flex-row gap-2 items-center content-center justify-center mb-1">
                              <span
                                className={`items-center justify-center rounded-full bg-white/70 ${entry.text}`}
                              >
                                <Icon className="h-6 w-6" />
                              </span>
                              <p className={`text-xl font-bold ${entry.text}`}>
                                {entry.count}
                              </p>
                            </div>
                            <p className="text-sm font-semibold text-gray-700">
                              {entry.label}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-8">
        <div>
          <h2 className="brand-title text-2xl text-gray-900 mb-4">
            Interpretations
          </h2>
          {results.length === 0 ? (
            <p className="text-gray-500">
              {runCompletedWithoutResults
                ? run.status === "SUCCEEDED"
                  ? "This fact check finished, but no interpretations were produced. Try rephrasing the claim or adding more supporting documents."
                  : emptyInterpretationMessage
                : "This fact check has not produced any interpretations yet."}
            </p>
          ) : (
            <div className="space-y-6">
              {results.map((result) => {
                const confirmationDisplay = getConfirmationDisplay(
                  result.confirmationLevel
                );
                const ConfirmationIcon = confirmationDisplay.icon;
                const evidenceCount = result.evidence.length;
                const isSourcesOpen = openSources[result.id] ?? false;
                return (
                  <div
                    key={result.id}
                    className="border border-gray-100 rounded-lg p-6 shadow-sm bg-white space-y-5"
                  >
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                      <div>
                        <p className="text-sm text-gray-500">
                          Interpretation #{result.interpretationIndex + 1}
                        </p>
                        <h3 className="text-xl font-semibold text-gray-900">
                          {result.interpretationText}
                        </h3>
                      </div>
                      <div
                        className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${confirmationDisplay.border} ${confirmationDisplay.bg}`}
                      >
                        <span
                          className={`inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/80 ${confirmationDisplay.text}`}
                        >
                          <ConfirmationIcon className="h-5 w-5" />
                        </span>
                        <div>
                          <p
                            className={`text-lg font-bold ${confirmationDisplay.text}`}
                          >
                            {confirmationDisplay.label}
                          </p>
                          {typeof result.confidenceScore === "number" && (
                            <p className="text-xs text-gray-600">
                              Confidence{" "}
                              {Math.round(result.confidenceScore * 100)}%
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                    {result.summary && (
                      <p className="text-gray-700">{result.summary}</p>
                    )}
                    <div className="border border-dashed border-gray-200 rounded-lg">
                      <button
                        type="button"
                        onClick={() => toggleSources(result.id)}
                        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition"
                      >
                        <div>
                          <p className="text-sm font-semibold text-gray-900">
                            Sources ({evidenceCount})
                          </p>
                          <p className="text-xs text-gray-500">
                            Click to {isSourcesOpen ? "hide" : "show"} evidence
                            excerpts
                          </p>
                        </div>
                        <span className="text-primary font-semibold text-sm">
                          {isSourcesOpen ? "Collapse" : "Expand"}
                        </span>
                      </button>
                      {isSourcesOpen && (
                        <div className="border-t border-gray-100">
                          <div className="divide-y divide-gray-100">
                            {result.evidence.map((evidence) => {
                              const context = extractContext(
                                evidence.metadata as Record<string, unknown> | null
                              );
                              const metadataEntries = extractMetadataEntries(
                                evidence.metadata as Record<string, unknown> | null
                              );
                              const evidenceKey = `${result.id}-${evidence.id}`;
                              const isOpen = openEvidence[evidenceKey] ?? false;
                              return (
                                <div
                                  key={evidence.id}
                                  className="p-4 bg-gray-50"
                                >
                                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                                    <div>
                                      <p className="text-sm font-semibold text-gray-900">
                                        {evidence.chunkLabel ||
                                          evidence.libraryNodeId ||
                                          "Evidence snippet"}
                                      </p>
                                      <p className="mt-1 text-xs text-gray-500">
                                        {evidence.stance}
                                      </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                      {typeof evidence.score === "number" && (
                                        <span className="inline-flex items-center rounded-full bg-white px-3 py-1 text-xs font-semibold text-gray-700 border border-gray-200">
                                          Score {evidence.score.toFixed(2)}
                                        </span>
                                      )}
                                      <button
                                        type="button"
                                        onClick={() =>
                                          toggleEvidence(result.id, evidence.id)
                                        }
                                        className="text-primary text-sm font-semibold"
                                      >
                                        {isOpen ? "Hide excerpt" : "Show full excerpt"}
                                      </button>
                                    </div>
                                  </div>

                                  <p className="mt-2 text-sm text-gray-800 whitespace-pre-wrap">
                                    {isOpen
                                      ? evidence.evidenceText
                                      : truncateText(evidence.evidenceText)}
                                  </p>

                                  {isOpen && context && (
                                    <div className="mt-3 rounded-md bg-white border border-gray-200 p-3">
                                      <p className="text-xs font-semibold text-gray-700 mb-1">
                                        Wider context
                                      </p>
                                      <p className="text-sm text-gray-800 whitespace-pre-wrap">
                                        {context}
                                      </p>
                                    </div>
                                  )}

                                  {isOpen && metadataEntries.length > 0 && (
                                    <div className="mt-3 flex flex-wrap gap-2">
                                      {metadataEntries.map(([key, value]) => (
                                        <span
                                          key={key}
                                          className="inline-flex items-center gap-1 rounded-full bg-white border border-gray-200 px-3 py-1 text-xs text-gray-700"
                                        >
                                          <span className="font-semibold">
                                            {key}:
                                          </span>
                                          <span>{value}</span>
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-primary-soft border border-primary-border rounded-lg p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-primary uppercase tracking-wide">
              Continue
            </p>
            <p className="text-lg text-primary-strong font-medium">
              Want to build a custom Evidence Seeker?
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/register"
              className="btn-primary px-5 py-2"
            >
              Create your seeker
            </Link>
            <Link
              to={`/evidence-seekers/${seeker.uuid}`}
              className="btn-primary-outline text-sm font-semibold"
            >
              Explore this seeker
            </Link>
          </div>
        </div>
      </section>
    </PublicLayout>
  );
};

export default PublicFactCheckPage;
