import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router";
import {
  useDropzone,
  FileRejection,
  DropEvent,
  DropzoneOptions,
} from "react-dropzone";
import { Document, DocumentCreate } from "../../types/document";
import { useDocuments } from "../../hooks/useDocument";

interface DocumentUploadProps {
  evidenceSeekerUuid: string;
  onUploadSuccess?: (document: Document) => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  evidenceSeekerUuid,
  onUploadSuccess,
}) => {
  const navigate = useNavigate();
  const { uploadDocument } = useDocuments(evidenceSeekerUuid);
  const [uploadState, setUploadState] = useState<{
    loading: boolean;
    error: string | null;
    progress: number;
  }>({
    loading: false,
    error: null,
    progress: 0,
  });

  const [formData, setFormData] = useState({
    title: "",
    description: "",
  });

  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const onDrop = useCallback(
    (
      acceptedFiles: File[],
      fileRejections: FileRejection[],
      event: DropEvent
    ) => {
      // Clear previous errors
      setUploadState((prev) => ({ ...prev, error: null }));

      if (fileRejections.length > 0) {
        const error = fileRejections[0].errors[0];
        let errorMessage = error.message;

        // Provide more user-friendly error messages
        if (error.code === "file-too-large") {
          errorMessage = "File is too large. Maximum size is 10MB.";
        } else if (error.code === "file-invalid-type") {
          errorMessage =
            "Invalid file type. Only PDF and TXT files are allowed.";
        }

        setUploadState((prev) => ({ ...prev, error: errorMessage }));
        return;
      }

      if (acceptedFiles.length > 0) {
        setSelectedFile(acceptedFiles[0]);
        setUploadState((prev) => ({ ...prev, error: null }));
      }
    },
    []
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: {
      "application/pdf": [".pdf"],
      "text/plain": [".txt"],
    },
    maxSize: 10 * 1024 * 1024, // 10MB
  } as any as DropzoneOptions);

  const clearSelectedFile = () => {
    setSelectedFile(null);
    setFormData({ title: "", description: "" });
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedFile) {
      setUploadState((prev) => ({ ...prev, error: "Please select a file" }));
      return;
    }

    if (!formData.title.trim()) {
      setUploadState((prev) => ({ ...prev, error: "Title is required" }));
      return;
    }

    setUploadState({ loading: true, error: null, progress: 0 });

    try {
      const uploadData: DocumentCreate = {
        file: selectedFile,
        title: formData.title.trim(),
        description: formData.description.trim(),
      };

      const uploadedDocument = await uploadDocument(uploadData);

      if (uploadedDocument) {
        setFormData({ title: "", description: "" });
        setSelectedFile(null);
        onUploadSuccess?.(uploadedDocument);
        setUploadState({ loading: false, error: null, progress: 100 });

        // Navigate back to document list after successful upload
        setTimeout(() => {
          navigate(`/evidence-seekers/${evidenceSeekerUuid}/documents`);
        }, 1500); // Small delay to show success state
      } else {
        setUploadState((prev) => ({
          ...prev,
          loading: false,
          error: "Upload failed. Please try again.",
        }));
      }
    } catch (err) {
      setUploadState({
        loading: false,
        error: "An error occurred during upload. Please try again.",
        progress: 0,
      });
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white shadow-sm rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            Upload Document
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Add documents to your evidence seeker (PDF or TXT, max 10MB)
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {uploadState.error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="text-red-800">{uploadState.error}</div>
            </div>
          )}

          {/* File Drop Zone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Document File *
            </label>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                isDragActive
                  ? "border-blue-400 bg-blue-50"
                  : "border-gray-300 hover:border-gray-400"
              }`}
            >
              <input
                {...(getInputProps() as React.InputHTMLAttributes<HTMLInputElement>)}
              />
              {selectedFile ? (
                <div className="space-y-2">
                  <div className="text-green-600 font-medium">
                    File selected:
                  </div>
                  <div className="text-sm text-gray-600">
                    {selectedFile.name} ({formatFileSize(selectedFile.size)})
                  </div>
                </div>
              ) : (
                <div>
                  <div className="text-gray-600 mb-2">
                    {isDragActive
                      ? "Drop the file here..."
                      : "Drag & drop a file here, or click to select"}
                  </div>
                  <div className="text-sm text-gray-500">
                    Supports PDF and TXT files (max 10MB)
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Title Input */}
          <div>
            <label
              htmlFor="title"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Title *
            </label>
            <input
              type="text"
              id="title"
              name="title"
              value={formData.title}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter document title"
            />
          </div>

          {/* Description Input */}
          <div>
            <label
              htmlFor="description"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Description
            </label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Optional description of the document"
            />
          </div>

          {/* Upload Progress */}
          {uploadState.loading && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Uploading...</span>
                <span>{uploadState.progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadState.progress}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={uploadState.loading || !selectedFile}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploadState.loading ? "Uploading..." : "Upload Document"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default DocumentUpload;
