import React, { useMemo } from "react";
import { Link, useNavigate } from "react-router";
import { Document } from "../../types/document";
import { useDocuments } from "../../hooks/useDocument";
import { documentsAPI } from "../../utils/api";
import { useIndexJobs } from "../../hooks/useIndexJobs";
import { useEvidenceSeekerSettings } from "../../hooks/useEvidenceSeekerSettings";
import type { IndexJob } from "../../types/indexJob";
import { useConfigurationStatus } from "../../hooks/useConfigurationStatus";
import { ConfigurationBlockedNotice } from "../Configuration/ConfigurationBlockedNotice";

interface DocumentListProps {
  evidenceSeekerUuid: string;
  onDocumentSelect?: (document: Document) => void;
}

const DocumentList: React.FC<DocumentListProps> = ({
  evidenceSeekerUuid,
  onDocumentSelect,
}) => {
  const navigate = useNavigate();
  const {
    status: configurationStatus,
    loading: statusLoading,
    error: statusError,
  } = useConfigurationStatus(evidenceSeekerUuid);
  const statusState = configurationStatus?.state;
  const allowDocumentWork =
    statusState === "READY" || statusState === "MISSING_DOCUMENTS";

  const {
    documents,
    loading: documentsLoading,
    error: documentsError,
    deleteDocument,
  } = useDocuments(evidenceSeekerUuid, { enabled: allowDocumentWork });
  const {
    jobs,
    loading: jobsLoading,
    error: jobsError,
    triggering: reindexing,
    triggerReindex,
  } = useIndexJobs(evidenceSeekerUuid, { pollIntervalMs: 5000 });
  const {
    settings,
    loading: settingsLoading,
    error: settingsError,
    metadataPreview,
  } = useEvidenceSeekerSettings(evidenceSeekerUuid);

  const handleDelete = async (uuid: string) => {
    const success = await deleteDocument(uuid);
    if (!success) alert("Failed to delete document");
  };

  const handleDownload = async (doc: Document) => {
    try {
      const blob = await documentsAPI.downloadDocument(doc.uuid);
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = doc.originalFilename;
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(a);
    } catch (error) {
      alert("Failed to download document");
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (!bytes || bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const getFileIcon = (mimeType: string): string => {
    if (!mimeType) return "📎"; // Fallback for undefined/null mimeType
    if (mimeType.includes("pdf")) return "📄";
    if (mimeType.includes("text")) return "📝";
    return "📎";
  };

  const statusClassName = useMemo(
    () =>
      (status: IndexJob["status"]) => {
        switch (status) {
          case "SUCCEEDED":
            return "bg-green-100 text-green-800";
          case "RUNNING":
            return "bg-blue-100 text-blue-800";
          case "FAILED":
            return "bg-red-100 text-red-800";
          case "CANCELLED":
            return "bg-gray-100 text-gray-600";
          default:
            return "bg-yellow-100 text-yellow-800";
        }
      },
    []
  );

  const handleReindex = async () => {
    try {
      await triggerReindex();
      alert("Reindex job queued.");
    } catch (err: any) {
      alert(err?.message ?? "Failed to trigger reindex");
    }
  };

  const renderJobStatus = (job: IndexJob) => {
    const labelClasses = statusClassName(job.status);
    const created = new Date(job.createdAt).toLocaleString();
    const completed = job.completedAt
      ? new Date(job.completedAt).toLocaleString()
      : null;

    return (
      <div
        key={job.uuid}
        className="border border-gray-200 rounded-lg p-4 shadow-sm bg-white"
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-900">
              {job.jobType.toUpperCase()}
            </p>
            <p className="text-xs text-gray-500">
              Submitted at {created}
              {completed ? ` • Completed ${completed}` : ""}
            </p>
          </div>
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${labelClasses}`}
          >
            {job.status}
          </span>
        </div>
        {job.errorMessage && (
          <p className="mt-2 text-xs text-red-600">{job.errorMessage}</p>
        )}
      </div>
    );
  };

  if (statusLoading) {
    return (
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="flex justify-center items-center p-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </main>
    );
  }

  if (!allowDocumentWork) {
    return (
      <main className="max-w-4xl mx-auto py-10 sm:px-6 lg:px-8">
        <ConfigurationBlockedNotice
          status={configurationStatus}
          onConfigure={() =>
            navigate(`/app/evidence-seekers/${evidenceSeekerUuid}/manage/config`)
          }
          description="Complete configuration before managing documents."
        />
      </main>
    );
  }

  if (documentsLoading) {
    return (
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="flex justify-center items-center p-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </main>
    );
  }

  if (statusError || documentsError) {
    return (
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="text-red-800">
              {statusError ?? documentsError ?? "Something went wrong."}
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        <div className="space-y-6">
          <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h3 className="text-lg font-medium text-gray-900">
                Documents ({documents.length})
              </h3>
              <p className="text-sm text-gray-500">
                Uploaded files are automatically indexed via EvidenceSeeker.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <button
                onClick={handleReindex}
                disabled={reindexing}
                className="bg-white border border-blue-600 text-blue-600 px-4 py-2 rounded-md hover:bg-blue-50 disabled:opacity-60 text-sm"
              >
                {reindexing ? "Queuing…" : "Rebuild Index"}
              </button>
              <Link
                to={`/app/evidence-seekers/${evidenceSeekerUuid}/documents/upload`}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm text-center"
              >
                Upload Document
              </Link>
            </div>
          </header>
          {statusState === "MISSING_DOCUMENTS" && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              Upload at least one document to unlock Fact Check and Search workflows.
            </div>
          )}

          {documents.length === 0 ? (
            <div className="text-center py-12 bg-white border border-gray-200 rounded-lg">
              <div className="text-4xl mb-4">📂</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No Documents
              </h3>
              <p className="text-gray-500 mb-6">
                Upload your first document to get started.
              </p>
              <Link
                to={`/app/evidence-seekers/${evidenceSeekerUuid}/documents/upload`}
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
              >
                Upload Document
              </Link>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {documents.map((document) => (
                <div
                  key={document.id}
                  className="bg-white border border-gray-200 rounded-lg shadow-sm p-4 hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => onDocumentSelect?.(document)}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className="text-2xl">
                        {getFileIcon(document.mimeType)}
                      </div>
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {document.title}
                        </h4>
                        <p className="text-xs text-gray-500 truncate">
                          📁 {document.originalFilename}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatFileSize(document.fileSize || 0)} •{" "}
                          {document.mimeType || "Unknown"}
                        </p>
                      </div>
                    </div>
                    <div className="flex space-x-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDownload(document);
                        }}
                        className="text-blue-600 hover:text-blue-800 p-1"
                        title="Download"
                      >
                        📥
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(document.uuid);
                        }}
                        className="text-red-600 hover:text-red-800 p-1"
                        title="Delete"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>

                  {document.description && (
                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                      {document.description}
                    </p>
                  )}

                  <div className="text-xs text-gray-500">
                    Uploaded{" "}
                    {document.createdAt
                      ? new Date(document.createdAt).toLocaleDateString()
                      : "Unknown date"}
                  </div>
                </div>
              ))}
            </div>
          )}

          <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-gray-900">
                  Index Jobs
                </h4>
                {jobsLoading && (
                  <span className="text-xs text-gray-500">Refreshing…</span>
                )}
              </div>
              {jobsError && (
                <p className="text-xs text-red-600">{jobsError}</p>
              )}
              {jobs.length === 0 ? (
                <p className="text-sm text-gray-500">
                  No indexing jobs found yet. Upload a document or trigger a
                  rebuild to populate this list.
                </p>
              ) : (
                <div className="space-y-3">
                  {jobs.slice(0, 6).map((job) => renderJobStatus(job))}
                </div>
              )}
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-gray-900">
                  Default Metadata Filters
                </h4>
                {settingsLoading && (
                  <span className="text-xs text-gray-500">Loading…</span>
                )}
              </div>
              {settingsError && (
                <p className="text-xs text-red-600">{settingsError}</p>
              )}
              <pre className="bg-gray-50 border border-gray-200 rounded-md text-xs p-3 overflow-auto max-h-48">
                {metadataPreview}
              </pre>
              {settings && (
                <div className="text-xs text-gray-500 space-y-1">
                  <p>
                    Model:{" "}
                    <span className="font-medium">
                      {settings.defaultModel ?? "Not set"}
                    </span>
                  </p>
                  <p>
                    Top K:{" "}
                    <span className="font-medium">
                      {settings.topK ?? "Default"}
                    </span>
                  </p>
                  {settings.lastValidatedAt && (
                    <p>
                      Last tested:{" "}
                      {new Date(settings.lastValidatedAt).toLocaleString()}
                    </p>
                  )}
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
};

export default DocumentList;
