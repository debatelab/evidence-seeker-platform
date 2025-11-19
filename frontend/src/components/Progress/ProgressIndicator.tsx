/**
 * Progress Indicator component for real-time progress updates
 */

import React, { useEffect, useState } from "react";
import {
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
} from "lucide-react";
import { useProgressUpdates } from "../../hooks/useSearch";
import { ProgressUpdate } from "../../types/search";

interface ProgressIndicatorProps {
  operationId: string | null;
  onComplete?: (update: ProgressUpdate) => void;
  onError?: (update: ProgressUpdate) => void;
  className?: string;
}

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  operationId,
  onComplete,
  onError,
  className = "",
}) => {
  const { currentUpdate, connected, error } = useProgressUpdates(
    operationId || ""
  );
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    if (currentUpdate) {
      if (currentUpdate.status === "COMPLETED" && onComplete) {
        onComplete(currentUpdate);
      } else if (currentUpdate.status === "FAILED" && onError) {
        onError(currentUpdate);
      }
    }
  }, [currentUpdate, onComplete, onError]);

  if (!operationId || !currentUpdate) {
    return null;
  }

  const getStatusIcon = () => {
    switch (currentUpdate.status) {
      case "PENDING":
        return <Clock className="h-5 w-5 text-yellow-600" />;
      case "RUNNING":
        return <Loader2 className="h-5 w-5 text-primary animate-spin" />;
      case "COMPLETED":
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case "FAILED":
        return <XCircle className="h-5 w-5 text-red-600" />;
      case "CANCELLED":
        return <AlertCircle className="h-5 w-5 text-gray-600" />;
      default:
        return <Clock className="h-5 w-5 text-gray-600" />;
    }
  };

  const getStatusColor = () => {
    switch (currentUpdate.status) {
      case "PENDING":
        return "border-yellow-200 bg-yellow-50";
      case "RUNNING":
        return "border-primary-border bg-primary-soft";
      case "COMPLETED":
        return "border-green-200 bg-green-50";
      case "FAILED":
        return "border-red-200 bg-red-50";
      case "CANCELLED":
        return "border-gray-200 bg-gray-50";
      default:
        return "border-gray-200 bg-gray-50";
    }
  };

  const getProgressColor = () => {
    switch (currentUpdate.status) {
      case "RUNNING":
        return "bg-primary";
      case "COMPLETED":
        return "bg-green-600";
      case "FAILED":
        return "bg-red-600";
      default:
        return "bg-gray-600";
    }
  };

  const formatTimeRemaining = (seconds?: number) => {
    if (!seconds || seconds <= 0) return null;

    if (seconds < 60) {
      return `${seconds}s remaining`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds}s remaining`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${minutes}m remaining`;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <div className={`rounded-lg border p-4 ${getStatusColor()} ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {getStatusIcon()}
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h4 className="font-medium text-gray-900">
                {currentUpdate.message}
              </h4>
              <span className="text-sm text-gray-600">
                ({currentUpdate.progress.toFixed(1)}%)
              </span>
            </div>

            <div className="mt-2">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-300 ${getProgressColor()}`}
                  style={{ width: `${currentUpdate.progress}%` }}
                />
              </div>
            </div>

            <div className="flex items-center justify-between mt-2 text-xs text-gray-600">
              <div className="flex items-center space-x-4">
                {currentUpdate.current_step && currentUpdate.total_steps && (
                  <span>
                    Step {currentUpdate.current_step} of{" "}
                    {currentUpdate.total_steps}
                  </span>
                )}
                {currentUpdate.estimated_time_remaining && (
                  <span>
                    {formatTimeRemaining(
                      currentUpdate.estimated_time_remaining
                    )}
                  </span>
                )}
                {currentUpdate.timestamp && (
                  <span>{formatTimestamp(currentUpdate.timestamp)}</span>
                )}
              </div>

              {!connected && (
                <span className="text-yellow-600 flex items-center space-x-1">
                  <AlertCircle className="h-3 w-3" />
                  <span>Reconnecting...</span>
                </span>
              )}
            </div>
          </div>
        </div>

        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-gray-600 hover:text-gray-800 text-sm underline"
        >
          {showDetails ? "Hide Details" : "Show Details"}
        </button>
      </div>

      {showDetails &&
        currentUpdate.metadata &&
        Object.keys(currentUpdate.metadata).length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <h5 className="text-sm font-medium text-gray-900 mb-2">Details</h5>
            <div className="bg-white rounded p-3 text-xs font-mono">
              <pre className="whitespace-pre-wrap">
                {JSON.stringify(currentUpdate.metadata, null, 2)}
              </pre>
            </div>
          </div>
        )}

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800">
          <div className="flex items-center space-x-2">
            <XCircle className="h-4 w-4" />
            <span>Connection error: {error}</span>
          </div>
        </div>
      )}
    </div>
  );
};

// Compact version for inline use
interface CompactProgressIndicatorProps {
  operationId: string | null;
  className?: string;
}

export const CompactProgressIndicator: React.FC<
  CompactProgressIndicatorProps
> = ({ operationId, className = "" }) => {
  const { currentUpdate, connected } = useProgressUpdates(operationId || "");

  if (!operationId || !currentUpdate) {
    return null;
  }

  return (
    <div className={`flex items-center space-x-2 text-sm ${className}`}>
      <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
      <span className="text-gray-700">{currentUpdate.message}</span>
      <span className="text-gray-500">
        ({currentUpdate.progress.toFixed(0)}%)
      </span>
      {!connected && (
        <span className="text-yellow-600 text-xs">(Reconnecting...)</span>
      )}
    </div>
  );
};

// Progress list for multiple operations
interface ProgressListProps {
  operationIds: string[];
  onOperationComplete?: (operationId: string, update: ProgressUpdate) => void;
  onOperationError?: (operationId: string, update: ProgressUpdate) => void;
  className?: string;
}

export const ProgressList: React.FC<ProgressListProps> = ({
  operationIds,
  onOperationComplete,
  onOperationError,
  className = "",
}) => {
  const [activeOperations, setActiveOperations] =
    useState<string[]>(operationIds);

  const handleComplete = (operationId: string, update: ProgressUpdate) => {
    setActiveOperations((prev) => prev.filter((id) => id !== operationId));
    onOperationComplete?.(operationId, update);
  };

  const handleError = (operationId: string, update: ProgressUpdate) => {
    setActiveOperations((prev) => prev.filter((id) => id !== operationId));
    onOperationError?.(operationId, update);
  };

  if (activeOperations.length === 0) {
    return null;
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {activeOperations.map((operationId) => (
        <ProgressIndicator
          key={operationId}
          operationId={operationId}
          onComplete={(update) => handleComplete(operationId, update)}
          onError={(update) => handleError(operationId, update)}
        />
      ))}
    </div>
  );
};
