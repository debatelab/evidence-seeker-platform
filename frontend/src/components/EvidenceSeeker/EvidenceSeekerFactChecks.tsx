import React, { useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import FactCheckSummaryCard from "../Public/FactCheckSummaryCard";
import { useEvidenceSeekerRuns } from "../../hooks/useEvidenceSeekerRuns";
import { evidenceSeekerAPI } from "../../utils/api";
import {
  aggregateResultSummary,
  type ConfirmationSummaryDisplay,
} from "../../utils/factCheckSummaries";
import { formatRelativeTime } from "../../utils/dates";
import type { FactCheckRun } from "../../types/factCheck";
import EvidenceSeekerRunForm from "./EvidenceSeekerRunForm";

interface EvidenceSeekerFactChecksProps {
  evidenceSeekerUuid: string;
}

const EvidenceSeekerFactChecks: React.FC<EvidenceSeekerFactChecksProps> = ({
  evidenceSeekerUuid,
}) => {
  const { runs, loading, error, refresh, updatePublication, deleteRun } =
    useEvidenceSeekerRuns(evidenceSeekerUuid);
  const [summaries, setSummaries] = useState<
    Record<string, ConfirmationSummaryDisplay[]>
  >({});
  const [summariesLoading, setSummariesLoading] = useState(false);
  const [showPublishedOnly, setShowPublishedOnly] = useState(false);

  useEffect(() => {
    let isMounted = true;
    if (!runs.length) {
      setSummaries({});
      setSummariesLoading(false);
      return () => {
        isMounted = false;
      };
    }

    setSummariesLoading(true);
    const loadSummaries = async () => {
      try {
        const limitedRuns = runs.slice(0, 20);
        const entries = await Promise.all(
          limitedRuns.map(async (run) => {
            const precomputed = (run as FactCheckRun & {
              confirmationSummary?: ConfirmationSummaryDisplay[];
            }).confirmationSummary;
            if (precomputed) {
              return [run.uuid, precomputed] as const;
            }
            try {
              const results = await evidenceSeekerAPI.getFactCheckResults(
                evidenceSeekerUuid,
                run.uuid
              );
              return [run.uuid, aggregateResultSummary(results)] as const;
            } catch (err) {
              console.error(err);
              return [run.uuid, [] as ConfirmationSummaryDisplay[]] as const;
            }
          })
        );
        if (!isMounted) return;
        const map: Record<string, ConfirmationSummaryDisplay[]> = {};
        entries.forEach(([uuid, summary]) => {
          map[uuid] = summary;
        });
        setSummaries(map);
      } finally {
        if (isMounted) {
          setSummariesLoading(false);
        }
      }
    };
    void loadSummaries();
    return () => {
      isMounted = false;
    };
  }, [runs, evidenceSeekerUuid]);

  const publishedLabel = (run: FactCheckRun) =>
    formatRelativeTime(run.publishedAt ?? run.completedAt, "Awaiting publication");

  const visibleRuns = useMemo(
    () => (showPublishedOnly ? runs.filter((run) => run.isPublic) : runs),
    [runs, showPublishedOnly]
  );

  const handleVisibility = async (
    runUuid: string,
    visibility: "PUBLIC" | "UNLISTED"
  ) => {
    await updatePublication(runUuid, visibility);
    void refresh();
  };

  const handleDelete = async (runUuid: string) => {
    const ok = await deleteRun(runUuid);
    if (ok) {
      void refresh();
    }
  };

  return (
    <div className="space-y-6">
      <EvidenceSeekerRunForm
        evidenceSeekerUuid={evidenceSeekerUuid}
        showHeader={true}
        onRunCreated={() => void refresh()}
      />

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <div>
          <h2 className="brand-title text-lg text-gray-900">Fact-check runs</h2>
          <p className="text-sm text-gray-600">
            Browse every run (published and unpublished). Click a card to open
            the shared detail view.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setShowPublishedOnly((prev) => !prev)}
            className={`px-3 py-2 text-sm rounded-md border ${
              showPublishedOnly
                ? "border-primary text-primary bg-primary-soft"
                : "border-gray-300 text-gray-700 hover:border-gray-400"
            }`}
          >
            {showPublishedOnly ? "Showing published" : "All runs"}
          </button>
          <button
            onClick={() => void refresh()}
            className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 px-2 py-2"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700 flex items-center gap-2">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="ml-2 text-sm text-gray-600">
            Loading fact-check runs…
          </span>
        </div>
      ) : visibleRuns.length === 0 ? (
        <div className="border border-dashed border-gray-200 rounded-lg p-6 text-sm text-gray-600">
          {showPublishedOnly
            ? "No published runs yet. Clear the filter to see all runs."
            : "No fact-check runs yet. Start by running your first fact check."}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {visibleRuns.map((run, index) => (
            <div key={run.uuid} className="space-y-3">
              <FactCheckSummaryCard
                run={{
                  uuid: run.uuid,
                  statement: run.statement,
                  status: run.status,
                  completedAt: run.completedAt ?? null,
                  publishedAt: run.publishedAt ?? null,
                  featuredAt: run.featuredAt ?? null,
                  visibility: run.visibility,
                  evidenceSeekerUuid,
                  evidenceSeekerId: run.evidenceSeekerId,
                  evidenceSeekerTitle: "",
                }}
                index={index}
                publishedLabel={publishedLabel(run)}
                summaries={summaries[run.uuid] ?? []}
                isLoading={summariesLoading}
                emptyMessage={
                  run.status === "SUCCEEDED"
                    ? "Interpretations not available yet."
                    : "Run is still in progress."
                }
                toOverride={`/app/evidence-seekers/${evidenceSeekerUuid}/manage/fact-checks/${run.uuid}`}
                meta={[
                  { label: run.status },
                  { label: run.visibility, tone: run.visibility === "PUBLIC" ? "green" : "gray" },
                ]}
              />
              <div className="flex flex-wrap gap-2">
                {run.status === "SUCCEEDED" && run.visibility !== "PUBLIC" && (
                  <button
                    className="btn-primary px-3 py-2 text-sm"
                    onClick={() => void handleVisibility(run.uuid, "PUBLIC")}
                  >
                    Feature
                  </button>
                )}
                {run.visibility === "PUBLIC" && (
                  <button
                    className="btn-secondary px-3 py-2 text-sm"
                    onClick={() => void handleVisibility(run.uuid, "UNLISTED")}
                  >
                    Remove from featured
                  </button>
                )}
                <button
                  className="btn-tertiary px-3 py-2 text-sm text-red-700"
                  onClick={() => void handleDelete(run.uuid)}
                >
                  Delete run
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default EvidenceSeekerFactChecks;
