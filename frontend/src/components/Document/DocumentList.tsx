import React, { useState } from "react";
import { Link, useParams } from "react-router";
import { Document } from "../../types/document";
import { useDocuments } from "../../hooks/useDocument";

interface DocumentListProps {
  evidenceSeekerUuid: string;
  onDocumentSelect?: (document: Document) => void;
}

const DocumentList: React.FC<DocumentListProps> = ({
  evidenceSeekerUuid,
  onDocumentSelect,
}) => {
  const { documents, loading, error, deleteDocument } =
    useDocuments(evidenceSeekerUuid);
  const [deleteLoading, setDeleteLoading] = useState<number | null>(null);

  const handleDelete = async (uuid: string) => {
    setDeleteLoading(null); // Remove loading state since we don't have the ID anymore
    const success = await deleteDocument(uuid);
    if (!success) {
      alert("Failed to delete document");
    }
  };

  const handleDownload = async (doc: Document) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/documents/${doc.uuid}/download`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Download failed");
      }

      const blob = await response.blob();
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

  if (loading) {
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

  if (error) {
    return (
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="text-red-800">{error}</div>
          </div>
        </div>
      </main>
    );
  }

  if (documents.length === 0) {
    return (
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="text-center py-12">
            <div className="text-4xl mb-4">📂</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No Documents
            </h3>
            <p className="text-gray-500 mb-6">
              Upload your first document to get started.
            </p>
            <Link
              to={`/evidence-seekers/${evidenceSeekerUuid}/documents/upload`}
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
            >
              Upload Document
            </Link>
          </div>
        </div>
      </main>
    );
  }
  console.log(documents);
  return (
    <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium text-gray-900">
              Documents ({documents.length})
            </h3>
            <Link
              to={`/evidence-seekers/${evidenceSeekerUuid}/documents/upload`}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm"
            >
              Upload Document
            </Link>
          </div>

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
        </div>
      </div>
    </main>
  );
};

export default DocumentList;
