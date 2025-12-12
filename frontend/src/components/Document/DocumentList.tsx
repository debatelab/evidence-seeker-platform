import React, { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import { Document } from "../../types/document";
import { useDocuments } from "../../hooks/useDocument";
import { documentsAPI } from "../../utils/api";
import { useIndexJobs } from "../../hooks/useIndexJobs";
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
    updateDocument,
  } = useDocuments(evidenceSeekerUuid, { enabled: allowDocumentWork });
  const {
    jobs,
    triggering: reindexing,
    triggerReindex,
  } = useIndexJobs(evidenceSeekerUuid, { pollIntervalMs: 5000 });
  const [editingDocument, setEditingDocument] = useState<Document | null>(null);
  const [editingTitle, setEditingTitle] = useState<string>("");
  const [editingDescription, setEditingDescription] = useState<string>("");
  const [editingSourceUrl, setEditingSourceUrl] = useState<string>("");
  const [editError, setEditError] = useState<string | null>(null);
  const [savingEdit, setSavingEdit] = useState<boolean>(false);

  const handleDelete = async (uuid: string) => {
    const success = await deleteDocument(uuid);
    if (!success) alert("Failed to delete document");
  };

  const handleEdit = (document: Document) => {
    setEditingDocument(document);
    setEditingTitle(document.title);
    setEditingDescription(document.description ?? "");
    setEditingSourceUrl(document.sourceUrl ?? "");
    setEditError(null);
  };

  const handleUpdate = async () => {
    if (!editingDocument) return;
    let normalizedUrl = editingSourceUrl.trim();
    if (normalizedUrl) {
      try {
        const parsed = new URL(normalizedUrl);
        if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
          throw new Error("URL must start with http or https");
        }
        normalizedUrl = parsed.toString();
      } catch (err: any) {
        setEditError(
          err?.message ??
            "Invalid URL. Please enter a fully qualified http(s) link."
        );
        return;
      }
    }
    setSavingEdit(true);
    setEditError(null);
    const payload = {
      title: editingTitle.trim() || editingDocument.title,
      description: editingDescription.trim() || null,
      sourceUrl: normalizedUrl || null,
    };
    const result = await updateDocument(editingDocument.uuid, payload);
    if (!result) {
      setEditError("Failed to update document. Please try again.");
      setSavingEdit(false);
      return;
    }
    setSavingEdit(false);
    setEditingDocument(null);
  };

  const closeEditModal = () => {
    if (savingEdit) return;
    setEditingDocument(null);
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
    () => (status: IndexJob["status"]) => {
      switch (status) {
        case "SUCCEEDED":
          return "bg-green-100 text-green-800";
        case "RUNNING":
          return "bg-primary-soft text-primary-strong";
        case "QUEUED":
          return "bg-yellow-100 text-yellow-800";
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

  const extractDocumentUuids = (job: IndexJob): string[] | null => {
    if (job.documentUuids && job.documentUuids.length > 0) {
      return job.documentUuids.filter(Boolean) as string[];
    }
    if (job.documentUuid) {
      return [job.documentUuid];
    }
    const payload = job.payload as Record<string, unknown> | null;
    const payloadUuids =
      payload && (payload["document_uuids"] || payload["documentUuids"]);
    if (Array.isArray(payloadUuids)) {
      return payloadUuids.filter(Boolean) as string[];
    }
    return null;
  };

  const documentJobs = useMemo(() => {
    const priority: Record<string, number> = {
      RUNNING: 4,
      QUEUED: 3,
      FAILED: 2,
      SUCCEEDED: 1,
      CANCELLED: 0,
    };

    const selectBest = (existing: IndexJob | undefined, candidate: IndexJob) => {
      if (!existing) return candidate;
      const existingPriority = priority[existing.status] ?? -1;
      const candidatePriority = priority[candidate.status] ?? -1;
      if (candidatePriority > existingPriority) {
        return candidate;
      }
      if (
        candidatePriority === existingPriority &&
        new Date(candidate.createdAt).getTime() >
          new Date(existing.createdAt).getTime()
      ) {
        return candidate;
      }
      return existing;
    };

    const mapping: Record<string, IndexJob> = {};
    const globalJobs: IndexJob[] = [];

    jobs.forEach((job) => {
      const targets = extractDocumentUuids(job);
      if (targets && targets.length > 0) {
        targets.forEach((uuid) => {
          mapping[uuid] = selectBest(mapping[uuid], job);
        });
      } else {
        globalJobs.push(job);
      }
    });

    if (globalJobs.length > 0) {
      documents.forEach((doc) => {
        globalJobs.forEach((job) => {
          mapping[doc.uuid] = selectBest(mapping[doc.uuid], job);
        });
      });
    }

    return mapping;
  }, [documents, jobs]);

  const jobLabel = (job: IndexJob | undefined) => {
    if (!job) return { text: "Indexed", style: "bg-green-50 text-green-700" };
    switch (job.status) {
      case "RUNNING":
        return { text: "Indexing…", style: statusClassName(job.status) };
      case "QUEUED":
        return { text: "Queued", style: statusClassName(job.status) };
      case "FAILED":
        return { text: "Failed", style: statusClassName(job.status) };
      case "CANCELLED":
        return { text: "Cancelled", style: statusClassName(job.status) };
      case "SUCCEEDED":
      default:
        return { text: "Indexed", style: statusClassName("SUCCEEDED") };
    }
  };

  if (statusLoading) {
    return (
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="flex justify-center items-center p-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
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
            navigate(
              `/app/evidence-seekers/${evidenceSeekerUuid}/manage/settings`
            )
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
                className="btn-primary-outline text-sm disabled:opacity-60"
              >
                {reindexing ? "Queuing…" : "Rebuild Index"}
              </button>
              <Link
                to={`/app/evidence-seekers/${evidenceSeekerUuid}/documents/upload`}
                className="btn-primary text-sm"
              >
                Upload Document
              </Link>
            </div>
          </header>
          {statusState === "MISSING_DOCUMENTS" && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              Upload at least one document to unlock Fact Check and Search
              workflows.
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
                className="btn-primary px-6 py-2"
              >
                Upload Document
              </Link>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {documents.map((document) => {
                const job = documentJobs[document.uuid];
                const label = jobLabel(job);
                const hasJobError = Boolean(job?.errorMessage);
                return (
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
                      <div className="flex items-center space-x-1">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${label.style}`}
                        >
                          {label.text}
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleEdit(document);
                          }}
                          className="text-gray-600 hover:text-gray-900 p-1"
                          title="Edit"
                        >
                          ✏️
                        </button>
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

                    {document.sourceUrl && (
                      <a
                        href={document.sourceUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="text-sm text-primary hover:text-primary-strong inline-flex items-center gap-1 mb-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        External download
                      </a>
                    )}

                    {hasJobError && (
                      <div className="text-xs text-red-600 mb-2">
                        {job?.errorMessage}
                      </div>
                    )}

                    <div className="text-xs text-gray-500">
                      Uploaded{" "}
                      {document.createdAt
                        ? new Date(document.createdAt).toLocaleDateString()
                        : "Unknown date"}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {editingDocument && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-lg w-full max-w-lg p-6 relative">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">
              Edit document
            </h4>
            {editError && (
              <div className="mb-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                {editError}
              </div>
            )}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Title
                </label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
                  value={editingTitle}
                  onChange={(e) => setEditingTitle(e.target.value)}
                  disabled={savingEdit}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
                  rows={3}
                  value={editingDescription}
                  onChange={(e) => setEditingDescription(e.target.value)}
                  disabled={savingEdit}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Public download URL
                </label>
                <input
                  type="url"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
                  value={editingSourceUrl}
                  onChange={(e) => setEditingSourceUrl(e.target.value)}
                  placeholder="https://example.com/document.pdf"
                  disabled={savingEdit}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Optional link to a public copy users can access.
                </p>
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={closeEditModal}
                className="btn-primary-outline text-sm"
                disabled={savingEdit}
              >
                Cancel
              </button>
              <button
                onClick={handleUpdate}
                className="btn-primary text-sm disabled:opacity-70"
                disabled={savingEdit}
              >
                {savingEdit ? "Saving…" : "Save changes"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
};

export default DocumentList;
