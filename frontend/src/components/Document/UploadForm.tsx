import React, { useState, useCallback } from "react";
import {
  useDropzone,
  FileRejection,
  DropEvent,
  DropzoneOptions,
} from "react-dropzone";
import PageLayout from "../PageLayout";

interface UploadFormProps {
  onStartUpload: (
    file: File,
    title: string,
    description: string,
    sourceUrl?: string
  ) => void;
}

const UploadForm: React.FC<UploadFormProps> = ({ onStartUpload }) => {
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    sourceUrl: "",
  });

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (
      acceptedFiles: File[],
      fileRejections: FileRejection[],
      _event: DropEvent
    ) => {
      // Clear previous errors
      setError(null);

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

        setError(errorMessage);
        return;
      }

      if (acceptedFiles.length > 0) {
        setSelectedFile(acceptedFiles[0]);
        setError(null);
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

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (_event: React.FormEvent) => {
    _event.preventDefault();

    if (!selectedFile) {
      setError("Please select a file");
      return;
    }

    if (!formData.title.trim()) {
      setError("Title is required");
      return;
    }

    // Clear any existing errors and start upload
    setError(null);
    let urlToSubmit = formData.sourceUrl.trim();
    if (urlToSubmit) {
      try {
        const parsed = new URL(urlToSubmit);
        if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
          throw new Error("URL must start with http or https");
        }
        urlToSubmit = parsed.toString();
      } catch (err: any) {
        setError(
          err?.message ??
            "Invalid URL. Please use a fully qualified http(s) link."
        );
        return;
      }
    }

    onStartUpload(
      selectedFile,
      formData.title.trim(),
      formData.description.trim(),
      urlToSubmit
    );
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <PageLayout variant="narrow">
      <div className="bg-white shadow-sm rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="brand-title text-xl text-gray-900">
            Upload Document
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Add documents to your evidence seeker (PDF or TXT, max 10MB)
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="text-red-800">{error}</div>
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
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
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
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
              placeholder="Optional description of the document"
            />
          </div>

          <div>
            <label
              htmlFor="sourceUrl"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Public download URL
            </label>
            <input
              type="url"
              id="sourceUrl"
              name="sourceUrl"
              value={formData.sourceUrl}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
              placeholder="https://example.com/my-document.pdf (optional)"
            />
            <p className="text-xs text-gray-500 mt-1">
              Link to an external copy users can access publicly.
            </p>
          </div>

          {/* Submit Button */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={!selectedFile}
              className="btn-primary px-4 py-2 text-sm"
            >
              Upload Document
            </button>
          </div>
        </form>
      </div>
    </PageLayout>
  );
};

export default UploadForm;
