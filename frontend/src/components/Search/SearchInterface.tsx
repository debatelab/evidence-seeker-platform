/**
 * Main search interface component for AI-powered document search
 */

import React, { useState } from "react";
import { Search, Loader2, FileText, Clock, Target } from "lucide-react";
import {
  useSearch,
  useSearchStatistics,
  useProgressUpdates,
} from "../../hooks/useSearch";
import { SearchQuery, SearchResult } from "../../types/search";

interface SearchInterfaceProps {
  evidenceSeekerUuid: string;
  onResultSelect?: (result: SearchResult) => void;
}

export const SearchInterface: React.FC<SearchInterfaceProps> = ({
  evidenceSeekerUuid: _evidenceSeekerUuid,
  onResultSelect,
}) => {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(10);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.1);
  const [_selectedDocumentIds, _setSelectedDocumentIds] = useState<number[]>(
    []
  );
  const [currentOperationId, _setCurrentOperationId] = useState<string | null>(
    null
  );

  const { search, loading: searchLoading, error: searchError } = useSearch();
  const { stats, loading: _statsLoading } = useSearchStatistics();
  const { currentUpdate, connected: _connected } = useProgressUpdates(
    currentOperationId || ""
  );

  const [results, setResults] = useState<SearchResult[]>([]);
  const [_searchPerformed, _setSearchPerformed] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;

    try {
      const searchQuery: SearchQuery = {
        query: query.trim(),
        limit,
        similarity_threshold: similarityThreshold,
        // document_ids intentionally omitted (underscore placeholder state)
      };

      const response = await search(searchQuery);
      setResults(response.results);
      _setSearchPerformed(true);
    } catch (error) {
      console.error("Search failed:", error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !searchLoading) {
      handleSearch();
    }
  };

  const formatSimilarity = (score: number) => {
    return `${(score * 100).toFixed(1)}%`;
  };

  // formatDate removed (unused)

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          AI-Powered Document Search
        </h1>
        <p className="text-gray-600">
          Search through your documents using natural language queries powered
          by AI
        </p>
      </div>

      {/* Search Statistics */}
      {stats && (
        <div className="bg-white rounded-lg shadow-sm border p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {stats.total_embeddings.toLocaleString()}
              </div>
              <div className="text-sm text-gray-600">Total Embeddings</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {stats.documents_with_embeddings}
              </div>
              <div className="text-sm text-gray-600">
                Documents with Embeddings
              </div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {stats.embedding_models.length}
              </div>
              <div className="text-sm text-gray-600">AI Models</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {stats.vector_dimensions}
              </div>
              <div className="text-sm text-gray-600">Vector Dimensions</div>
            </div>
          </div>
        </div>
      )}

      {/* Search Form */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="space-y-4">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter your search query..."
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={searchLoading}
            />
          </div>

          {/* Search Options */}
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">
                Results:
              </label>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="border border-gray-300 rounded px-3 py-1 text-sm"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">
                Similarity:
              </label>
              <input
                type="range"
                min="0.01"
                max="0.5"
                step="0.01"
                value={similarityThreshold}
                onChange={(e) => setSimilarityThreshold(Number(e.target.value))}
                className="w-20"
              />
              <span className="text-sm text-gray-600 w-12">
                {(similarityThreshold * 100).toFixed(0)}%
              </span>
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
              <span>{searchLoading ? "Searching..." : "Search"}</span>
            </button>
          </div>

          {/* Progress Indicator */}
          {currentUpdate && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                <span className="text-sm font-medium text-blue-800">
                  {currentUpdate.message}
                </span>
              </div>
              <div className="w-full bg-blue-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${currentUpdate.progress}%` }}
                />
              </div>
              <div className="text-xs text-blue-600 mt-1">
                {currentUpdate.progress.toFixed(1)}% complete
                {currentUpdate.estimated_time_remaining && (
                  <span className="ml-2">
                    ~{Math.ceil(currentUpdate.estimated_time_remaining / 60)}{" "}
                    min remaining
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {searchError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">
            <strong>Error:</strong> {searchError}
          </div>
        </div>
      )}

      {/* Search Results */}
      {_searchPerformed && (
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Search Results ({results.length})
            </h2>
          </div>

          {results.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No results found for your query.</p>
              <p className="text-sm mt-2">
                Try adjusting your search terms or similarity threshold.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {results.map((result, index) => (
                <div
                  key={`${result.document_id}-${result.chunk_index}`}
                  className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => onResultSelect?.(result)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="text-sm font-medium text-blue-600">
                          Document #{result.document_id}
                        </span>
                        <span className="text-xs text-gray-500">
                          Chunk {result.chunk_index}
                        </span>
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          {formatSimilarity(result.similarity_score)}
                        </span>
                      </div>

                      <p className="text-gray-900 mb-2 line-clamp-3">
                        {result.chunk_text}
                      </p>

                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span className="flex items-center space-x-1">
                          <Target className="h-3 w-3" />
                          <span>{result.model_name}</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <Clock className="h-3 w-3" />
                          <span>Result {index + 1}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
