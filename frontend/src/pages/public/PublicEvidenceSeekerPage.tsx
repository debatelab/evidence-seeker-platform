import axios from "axios";
import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { FileText } from "lucide-react";
import PublicLayout from "../../components/Public/PublicLayout";
import FactCheckSummaryCard from "../../components/Public/FactCheckSummaryCard";
import { publicAPI } from "../../utils/api";
import {
  PublicDocument,
  PublicEvidenceSeekerDetailResponse,
  PublicFactCheckRunSummary,
} from "../../types/public";
import {
  aggregateResultSummary,
  type ConfirmationSummaryDisplay,
} from "../../utils/factCheckSummaries";

const formatDateTime = (value?: string | null) => {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return new Date(value).toLocaleString();
  }
};

const PublicEvidenceSeekerPage: React.FC = () => {
  const { seekerUuid } = useParams<{ seekerUuid: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<PublicEvidenceSeekerDetailResponse | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statement, setStatement] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [runSummaries, setRunSummaries] = useState<
    Record<string, ConfirmationSummaryDisplay[]>
  >({});
  const [runSummariesLoading, setRunSummariesLoading] = useState(false);

  useEffect(() => {
    if (!seekerUuid) return;
    let isMounted = true;
    const fetchSeeker = async () => {
      setLoading(true);
      try {
        const response = await publicAPI.getEvidenceSeeker(seekerUuid);
        if (!isMounted) return;
        setData(response);
        setError(null);
      } catch (err) {
        console.error(err);
        if (isMounted) {
          setError("This Evidence Seeker is not public right now.");
          setData(null);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchSeeker();
    return () => {
      isMounted = false;
    };
  }, [seekerUuid]);

  const handleFactCheckSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!seekerUuid || !statement.trim()) return;
    setIsSubmitting(true);
    setSubmissionError(null);
    try {
      const run = await publicAPI.createFactCheckRun(seekerUuid, {
        statement,
      });
      setStatement("");
      navigate(`/fact-checks/${run.uuid}`, {
        state: { fromSeeker: seekerUuid },
      });
    } catch (err) {
      console.error(err);
      if (axios.isAxiosError(err)) {
        const detail =
          typeof err.response?.data?.detail === "string"
            ? err.response?.data.detail
            : null;
        if (err.response?.status === 429) {
          setSubmissionError(
            detail ??
              "Rate limit hit. Please wait a moment before running another public fact check."
          );
        } else if (err.response?.status === 409) {
          setSubmissionError(
            detail ??
              "This Evidence Seeker already has several public runs queued. Try again shortly."
          );
        } else {
          setSubmissionError(
            detail ??
              "Unable to start a fact check right now. Please try again in a moment."
          );
        }
      } else {
        setSubmissionError(
          "Unable to start a fact check right now. Please try again in a moment."
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const documentGroups = useMemo(() => {
    if (!data) {
      return [];
    }
    const initial: Record<string, PublicDocument[]> = {};
    data.documents.forEach((doc) => {
      const key = new Date(doc.createdAt).getFullYear().toString();
      if (!initial[key]) initial[key] = [];
      initial[key].push(doc);
    });
    return Object.entries(initial).sort(
      ([yearA], [yearB]) => Number(yearB) - Number(yearA)
    );
  }, [data]);

  const recentFactChecks = useMemo(() => data?.recentFactChecks ?? [], [data]);

  useEffect(() => {
    if (!recentFactChecks.length) {
      setRunSummaries({});
      setRunSummariesLoading(false);
      return;
    }
    let isMounted = true;
    setRunSummariesLoading(true);
    const fetchSummaries = async () => {
      try {
        const summaryEntries = await Promise.all(
          recentFactChecks.map(async (run) => {
            try {
              const detail = await publicAPI.getFactCheck(run.uuid);
              return [
                run.uuid,
                aggregateResultSummary(detail.results),
              ] as const;
            } catch (err) {
              console.error(err);
              return [run.uuid, [] as ConfirmationSummaryDisplay[]] as const;
            }
          })
        );
        if (!isMounted) return;
        const map: Record<string, ConfirmationSummaryDisplay[]> = {};
        summaryEntries.forEach(([uuid, summaries]) => {
          map[uuid] = summaries;
        });
        setRunSummaries(map);
      } finally {
        if (isMounted) {
          setRunSummariesLoading(false);
        }
      }
    };
    void fetchSummaries();
    return () => {
      isMounted = false;
    };
  }, [recentFactChecks]);

  if (loading) {
    return (
      <PublicLayout>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center text-gray-500">
          Loading Evidence Seeker...
        </div>
      </PublicLayout>
    );
  }

  if (error || !data || !seekerUuid) {
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

  const seeker = data.seeker;

  return (
    <PublicLayout>
      <section className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6 mt-4">
            <div>
              <h1 className="brand-title text-3xl text-gray-900">
                {seeker.title}
              </h1>
              <p className="mt-3 text-gray-600 max-w-2xl">
                {seeker.description || "No public description yet."}
              </p>
            </div>
          </div>
          <dl className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <dt className="text-sm text-gray-500">Documents</dt>
              <dd className="text-2xl font-semibold text-gray-900">
                {seeker.documentCount}
              </dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Published</dt>
              <dd className="text-2xl font-semibold text-gray-900">
                {seeker.publishedAt ? formatDateTime(seeker.publishedAt) : "—"}
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <section
        id="run-fact-check"
        className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12"
      >
        <div className="bg-white border border-gray-100 rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="brand-title text-xl text-gray-900">
                Test this Evidence Seeker
              </h2>
            </div>
            <p className="text-sm text-gray-500">
              Runs finish asynchronously. Bookmark the result link.
            </p>
          </div>
          <form onSubmit={handleFactCheckSubmit} className="space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-gray-700">
                Claim to verify
              </span>
              <textarea
                value={statement}
                onChange={(event) => setStatement(event.target.value)}
                rows={4}
                className="mt-2 block w-full rounded-lg border border-gray-200 bg-gray-50/80 p-4 text-base text-gray-900 shadow-sm focus:border-primary focus:ring-primary"
                placeholder="Enter a statement you want to validate..."
              />
            </label>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <button
                type="submit"
                className="btn-primary px-6 py-3 text-base"
              >
                {isSubmitting ? "Redirecting..." : "Run fact check"}
              </button>
              <p className="text-xs text-gray-500">
                You&apos;ll be taken to a live progress view. Public runs are
                limited to 3 per minute with only 10 queued at a time.
              </p>
            </div>
            {submissionError && (
              <p className="text-sm text-red-600">{submissionError}</p>
            )}
          </form>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h2 className="brand-title text-2xl text-gray-900 mb-6">
          Recent Fact Checks
        </h2>
        {recentFactChecks.length === 0 ? (
          <p className="text-gray-500">
            No public runs yet. Be the first to try it!
          </p>
        ) : (
          <div className="space-y-4">
            {recentFactChecks.map(
              (run: PublicFactCheckRunSummary, index: number) => {
                const summaries = runSummaries[run.uuid] ?? [];
                const publishedLabel =
                  run.publishedAt || run.completedAt
                    ? formatDateTime(run.publishedAt ?? run.completedAt)
                    : "Awaiting publication";
                return (
                  <FactCheckSummaryCard
                    key={run.uuid}
                    run={run}
                    index={index}
                    publishedLabel={publishedLabel}
                    summaries={summaries}
                    isLoading={runSummariesLoading}
                  />
                );
              }
            )}
          </div>
        )}
      </section>

      <section className="bg-gray-50 border-t border-b border-gray-100 py-12">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-sm font-semibold text-primary uppercase tracking-wide">
                Document Library
              </p>
              <h2 className="brand-title text-2xl text-gray-900">
                Source material
              </h2>
            </div>
            <p className="text-sm text-gray-500">
              Downloads require platform access.
            </p>
          </div>
          {data.documents.length === 0 ? (
            <p className="text-gray-500">
              This Evidence Seeker hasn&apos;t published any documents yet.
            </p>
          ) : (
            documentGroups.map(([year, documents]) => (
              <div key={year} className="mb-8">
                <h3 className="text-lg font-semibold text-gray-800 mb-3">
                  {year}
                </h3>
                <div className="space-y-3">
                  {documents.map((doc) => {
                    const docWithDownload = doc as PublicDocument & {
                      downloadUrl?: string | null;
                    };
                    const downloadUrl = docWithDownload.downloadUrl ?? null;
                    return (
                      <div
                        key={doc.uuid}
                        className="bg-white border border-gray-100 rounded-lg p-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div className="flex items-start gap-4">
                          <span className="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-primary-soft text-primary">
                            <FileText className="h-5 w-5" />
                          </span>
                          <div>
                            <p className="font-medium text-gray-900">
                              {doc.title}
                            </p>
                            {doc.description && (
                              <p className="text-sm text-gray-600">
                                {doc.description}
                              </p>
                            )}
                            <p className="text-xs text-gray-500 mt-1">
                              Uploaded {formatDateTime(doc.createdAt)}
                            </p>
                          </div>
                        </div>
                        {downloadUrl && (
                          <a
                            href={downloadUrl}
                            className="btn-primary-outline text-sm font-semibold"
                          >
                            Download
                          </a>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </PublicLayout>
  );
};

export default PublicEvidenceSeekerPage;
