import React from "react";
import { Link } from "react-router";
import type { PublicFactCheckRunSummary } from "../../types/public";
import type { ConfirmationSummaryDisplay } from "../../utils/factCheckSummaries";

type MetaTone = "gray" | "green" | "red";

interface FactCheckSummaryCardProps {
  run: PublicFactCheckRunSummary;
  index?: number;
  publishedLabel: string;
  summaries: ConfirmationSummaryDisplay[];
  isLoading: boolean;
  emptyMessage?: string;
  toOverride?: string;
  meta?: Array<{ label: string; tone?: MetaTone }>;
  publishedPrefix?: string;
}

const FactCheckSummaryCard: React.FC<FactCheckSummaryCardProps> = ({
  run,
  index = 0,
  publishedLabel,
  summaries,
  isLoading,
  emptyMessage = "This run has not published interpretations yet.",
  toOverride,
  meta,
  publishedPrefix = "Published",
}) => {
  const metaToneClass: Record<MetaTone, string> = {
    gray: "bg-gray-100 text-gray-700 border-gray-200",
    green: "bg-emerald-50 text-emerald-800 border-emerald-200",
    red: "bg-red-50 text-red-800 border-red-200",
  };

  return (
    <Link
      to={toOverride ?? `/fact-checks/${run.uuid}`}
      className="block border border-gray-100 rounded-lg p-5 space-y-4 bg-white shadow-sm transition hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
    >
      <div className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-gray-500">
          Fact check #{index + 1}
        </p>
        <p className="text-lg font-semibold text-gray-900">{run.statement}</p>
        <p className="text-xs text-gray-500">
          {publishedPrefix} {publishedLabel}
        </p>
        {meta && meta.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {meta.map((item, itemIndex) => (
              <span
                key={`${run.uuid}-meta-${itemIndex}-${item.label}`}
                className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
                  metaToneClass[item.tone ?? "gray"]
                }`}
              >
                {item.label}
              </span>
            ))}
          </div>
        )}
      </div>
      {summaries.length > 0 ? (
        <div className="flex flex-wrap gap-3">
          {summaries.map((entry) => {
            const Icon = entry.icon;
            return (
              <div
                key={`${run.uuid}-${entry.key}`}
                className={`flex items-center gap-3 rounded-lg border px-4 py-2 ${entry.border} ${entry.bg}`}
              >
                <span
                  className={`inline-flex h-8 w-8 items-center justify-center rounded-full bg-white/80 ${entry.text}`}
                >
                  <Icon className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-xs font-semibold text-gray-600">
                    {entry.label}
                  </p>
                  <p className={`text-base font-bold ${entry.text}`}>
                    {entry.count}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-gray-500">
          {isLoading ? "Loading interpretation summary..." : emptyMessage}
        </p>
      )}
      <div className="flex justify-end text-sm font-semibold text-primary">
        View details →
      </div>
    </Link>
  );
};

export default FactCheckSummaryCard;
