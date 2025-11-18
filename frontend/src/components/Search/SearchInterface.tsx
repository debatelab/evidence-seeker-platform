/**
 * EvidenceSeeker-backed search interface for querying indexed documents.
 */

import React, { useState } from "react";
import { useNavigate } from "react-router";
import { ChevronDown, ChevronUp, Loader2, Search } from "lucide-react";
import { useEvidenceSearch, useSystemStatistics } from "../../hooks/useSearch";
import type {
  EvidenceSearchHit,
  EvidenceSearchRequest,
} from "../../types/search";
import { useConfigurationStatus } from "../../hooks/useConfigurationStatus";
import { ConfigurationBlockedNotice } from "../Configuration/ConfigurationBlockedNotice";

interface SearchInterfaceProps {
  evidenceSeekerUuid: string;
  onResultSelect?: (result: EvidenceSearchHit) => void;
}

export const SearchInterface: React.FC<SearchInterfaceProps> = ({
  evidenceSeekerUuid,
  onResultSelect,
}) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(10);
  const [metadataFiltersRaw, setMetadataFiltersRaw] = useState("");
  const [documentUuidsRaw, setDocumentUuidsRaw] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [results, setResults] = useState<EvidenceSearchHit[]>([]);
  const [formError, setFormError] = useState<string | null>(null);

  const { search, loading: searchLoading, error: searchError } =
    useEvidenceSearch(evidenceSeekerUuid);
  const { stats } = useSystemStatistics();
  const {
    status: configurationStatus,
    loading: statusLoading,
    error: statusError,
  } = useConfigurationStatus(evidenceSeekerUuid);
  const isConfigured = configurationStatus?.isReady ?? false;

  const handleSearch = async () => {
    if (!query.trim()) {
      setFormError("Enter a query to search.");
      return;
    }

    const request: EvidenceSearchRequest = {
      query: query.trim(),
      topK,
    };

    if (metadataFiltersRaw.trim()) {
      try {
        request.metadataFilters = JSON.parse(metadataFiltersRaw);
      } catch {
        setFormError("Metadata filters must be valid JSON.");
        return;
      }
    }

    if (documentUuidsRaw.trim()) {
      request.documentUuids = documentUuidsRaw
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
    }

    setFormError(null);

    try {
      const response = await search(request);
      setResults(response.results);
    } catch (err) {
      console.error("Evidence search failed", err);
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !searchLoading) {
      handleSearch();
    }
  };

  const formatScore = (score: number) => `${(score * 100).toFixed(1)}%`;

  if (statusLoading) {
    return (
      <div className="flex justify-center items-center p-10">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (statusError) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4 text-red-800">
          {statusError}
        </div>
      </div>
    );
  }

  if (!isConfigured) {
    return (
      <div className="max-w-4xl mx-auto p-10">
        <ConfigurationBlockedNotice
          status={configurationStatus}
          onConfigure={() =>
            navigate(`/app/evidence-seekers/${evidenceSeekerUuid}/manage/config`)
          }
          description="Connect your inference credentials before running semantic search."
        />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <header className="text-center space-y-2">
        <h1 className="text-3xl font-bold text-gray-900">
          Evidence Search Console
        </h1>
        <p className="text-gray-600">
          Query indexed documents with the EvidenceSeeker retriever.
        </p>
      </header>

      {stats && (
        <section className="bg-white rounded-lg shadow-sm border p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <StatCard label="Documents" value={stats.totalDocuments} tone="blue" />
            <StatCard
              label="Indexed Documents"
              value={stats.indexedDocuments}
              tone="green"
            />
            <StatCard
              label="Fact Check Runs"
              value={stats.factCheckRuns}
              tone="purple"
            />
            <StatCard label="API Keys" value={stats.totalApiKeys} tone="orange" />
          </div>
        </section>
      )}

      <section className="bg-white rounded-lg shadow-sm border p-6 space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Enter a statement or question…"
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={searchLoading}
          />
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Top K:</label>
            <select
              value={topK}
              onChange={(event) => setTopK(Number(event.target.value))}
              className="border border-gray-300 rounded px-3 py-1 text-sm"
            >
              {[5, 10, 20, 50].map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleSearch}
            disabled={searchLoading || !query.trim()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {searchLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            <span>{searchLoading ? "Searching…" : "Search"}</span>
          </button>

          <button
            type="button"
            onClick={() => setAdvancedOpen((prev) => !prev)}
            className="flex items-center text-sm text-blue-600 hover:text-blue-800"
          >
            {advancedOpen ? (
              <ChevronUp className="h-4 w-4 mr-1" />
            ) : (
              <ChevronDown className="h-4 w-4 mr-1" />
            )}
            Advanced options
          </button>
        </div>

        {advancedOpen && (
          <div className="space-y-4 border border-gray-200 rounded-lg p-4 bg-gray-50">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Metadata filters (JSON)
              </label>
              <textarea
                value={metadataFiltersRaw}
                onChange={(event) => setMetadataFiltersRaw(event.target.value)}
                rows={3}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder='e.g. {"topic": "climate"}'
              />
              <p className="text-xs text-gray-500 mt-1">
                Filters are merged with the seeker’s default constraints.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Document UUIDs (comma separated)
              </label>
              <input
                type="text"
                value={documentUuidsRaw}
                onChange={(event) => setDocumentUuidsRaw(event.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="uuid-1, uuid-2"
              />
            </div>
          </div>
        )}

        {(formError || searchError) && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="text-red-800">{formError || searchError}</div>
          </div>
        )}
      </section>

      <section className="bg-white rounded-lg shadow-sm border">
        <header className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Results ({results.length})
          </h2>
          {results.length > 0 && (
            <span className="text-sm text-gray-500">
              Click a result to inspect metadata or open the document.
            </span>
          )}
        </header>

        {results.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="divide-y divide-gray-200">
            {results.map((result, index) => (
              <button
                key={`${result.documentUuid ?? "unknown"}-${index}`}
                type="button"
                onClick={() => onResultSelect?.(result)}
                className="w-full text-left p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-sm font-semibold text-gray-900">
                      Result {index + 1} • {formatScore(result.score)}
                    </div>
                    <div className="text-xs text-gray-500 space-x-3 mt-1">
                      {result.documentId && (
                        <span>Document #{result.documentId}</span>
                      )}
                      {result.documentUuid && (
                        <span className="font-mono text-[11px]">
                          {result.documentUuid}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <p className="mt-3 text-sm text-gray-700 whitespace-pre-line">
                  {result.text}
                </p>

                {result.metadata && (
                  <dl className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-gray-500">
                    {Object.entries(result.metadata).map(([key, value]) => (
                      <div key={key}>
                        <dt className="font-medium">{key}</dt>
                        <dd>{String(value)}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

interface StatCardProps {
  label: string;
  value: number;
  tone: "blue" | "green" | "purple" | "orange";
}

const toneStyles: Record<StatCardProps["tone"], string> = {
  blue: "text-blue-600",
  green: "text-green-600",
  purple: "text-purple-600",
  orange: "text-orange-600",
};

const StatCard: React.FC<StatCardProps> = ({ label, value, tone }) => (
  <div className="text-center">
    <div className={`text-2xl font-bold ${toneStyles[tone]}`}>
      {value.toLocaleString()}
    </div>
    <div className="text-sm text-gray-600">{label}</div>
  </div>
);

const EmptyState = () => (
  <div className="p-8 text-center text-gray-500">
    <div className="text-4xl mb-4">🔎</div>
    <p className="text-lg font-medium">No results yet</p>
    <p className="text-sm mt-2">
      Run a search to see EvidenceSeeker retrieval results.
    </p>
  </div>
);
