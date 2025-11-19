import React from "react";
import PageLayout from "../PageLayout";

interface UploadErrorProps {
  file: File;
  title: string;
  error: string;
  onRetry: () => void;
  onChooseDifferent: () => void;
}

const UploadError: React.FC<UploadErrorProps> = ({
  file,
  title,
  error,
  onRetry,
  onChooseDifferent,
}) => {
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const getFileIcon = (mimeType: string): string => {
    if (mimeType.includes("pdf")) return "📄";
    if (mimeType.includes("text")) return "📝";
    return "📎";
  };

  const getErrorIcon = (errorType: string) => {
    if (errorType.includes("size") || errorType.includes("large")) {
      return "📏"; // Size related error
    }
    if (errorType.includes("type") || errorType.includes("format")) {
      return "📄"; // File type error
    }
    if (errorType.includes("network") || errorType.includes("connection")) {
      return "🌐"; // Network error
    }
    return "❌"; // Generic error
  };

  const getErrorTitle = (errorType: string) => {
    if (errorType.includes("size") || errorType.includes("large")) {
      return "File Too Large";
    }
    if (errorType.includes("type") || errorType.includes("format")) {
      return "Invalid File Type";
    }
    if (errorType.includes("network") || errorType.includes("connection")) {
      return "Connection Error";
    }
    return "Upload Failed";
  };

  const getErrorSuggestions = (errorType: string) => {
    if (errorType.includes("size") || errorType.includes("large")) {
      return [
        "Reduce the file size by compressing the document",
        "Split large documents into smaller parts",
        "Contact support if you need to upload larger files",
      ];
    }
    if (errorType.includes("type") || errorType.includes("format")) {
      return [
        "Upload PDF or TXT files only",
        "Convert your document to PDF format",
        "Check that the file isn't corrupted",
      ];
    }
    if (errorType.includes("network") || errorType.includes("connection")) {
      return [
        "Check your internet connection",
        "Try again in a few moments",
        "Contact support if the problem persists",
      ];
    }
    return [
      "Check your file and try again",
      "Ensure you have a stable internet connection",
      "Contact support if the problem continues",
    ];
  };

  return (
    <PageLayout variant="narrow">
      <div className="bg-white shadow-sm rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="text-2xl">❌</div>
            <div>
              <h2 className="brand-title text-xl text-gray-900">
                {getErrorTitle(error)}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                We couldn\u2019t upload your document
              </p>
            </div>
          </div>
        </div>

        <div className="p-6">
          <div className="space-y-6">
            {/* Error Message */}
            <div className="text-center">
              <div className="text-6xl mb-4">{getErrorIcon(error)}</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {getErrorTitle(error)}
              </h3>
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
                {error}
              </p>
            </div>

            {/* File Information */}
            <div className="flex items-center space-x-4 p-4 bg-red-50 rounded-lg border border-red-200">
              <div className="text-3xl">{getFileIcon(file.type)}</div>
              <div className="flex-1">
                <h4 className="font-medium text-gray-900 truncate">{title}</h4>
                <p className="text-sm text-gray-600 truncate">📁 {file.name}</p>
                <p className="text-sm text-gray-500">
                  📏 {formatFileSize(file.size)}
                </p>
              </div>
              <div className="text-red-600">
                <svg
                  className="h-6 w-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </div>
            </div>

            {/* Suggestions */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-yellow-400"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      fillRule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <h4 className="text-sm font-medium text-yellow-800">
                    What you can try:
                  </h4>
                  <div className="mt-2 text-sm text-yellow-700">
                    <ul className="list-disc list-inside space-y-1">
                      {getErrorSuggestions(error).map((suggestion, index) => (
                        <li key={index}>{suggestion}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={onRetry}
                className="btn-primary px-6 py-3 text-sm"
              >
                🔄 Try Again
              </button>

              <button
                onClick={onChooseDifferent}
                className="px-6 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
              >
                📁 Choose Different File
              </button>
            </div>

            {/* Support Info */}
            <div className="text-center">
              <p className="text-xs text-gray-500">
                Still having trouble?{" "}
                <a
                  href="#"
                  className="text-primary hover:text-primary-strong underline"
                  onClick={(e) => {
                    e.preventDefault();
                    // Could open a support modal or navigate to help
                    alert("Support contact would go here");
                  }}
                >
                  Contact Support
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
};

export default UploadError;
