import React, { useEffect, useState } from "react";
import PageLayout from "../PageLayout";

interface UploadProgressProps {
  file: File;
  title: string;
  onCancel: () => void;
  progress?: number;
}

const UploadProgress: React.FC<UploadProgressProps> = ({
  file,
  title,
  onCancel,
  progress = 0,
}) => {
  const [animatedProgress, setAnimatedProgress] = useState(0);

  // Animate progress changes for smoother UX
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedProgress(progress);
    }, 100);
    return () => clearTimeout(timer);
  }, [progress]);

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

  const getProgressMessage = () => {
    if (progress < 30) return "Preparing upload...";
    if (progress < 70) return "Uploading to server...";
    if (progress < 100) return "Finalizing upload...";
    return "Upload complete!";
  };

  return (
    <PageLayout variant="narrow">
      <div className="bg-white shadow-sm rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="brand-title text-xl text-gray-900">
            📤 Uploading Document
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Please wait while your document is being uploaded
          </p>
        </div>

        <div className="p-6">
          <div className="space-y-6">
            {/* File Information */}
            <div className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
              <div className="text-3xl">{getFileIcon(file.type)}</div>
              <div className="flex-1">
                <h3 className="font-medium text-gray-900 truncate">{title}</h3>
                <p className="text-sm text-gray-600 truncate">📁 {file.name}</p>
                <p className="text-sm text-gray-500">
                  📏 {formatFileSize(file.size)}
                </p>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">{getProgressMessage()}</span>
                <span className="text-gray-900 font-medium">
                  {Math.round(animatedProgress)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-primary h-full rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${animatedProgress}%` }}
                />
              </div>
            </div>

            {/* Status Message */}
            <div className="text-center">
              <p className="text-sm text-gray-600">
                {progress < 100
                  ? "Please keep this window open during upload"
                  : "Processing your document..."}
              </p>
            </div>

            {/* Cancel Button */}
            {progress < 100 && (
              <div className="flex justify-center">
                <button
                  onClick={onCancel}
                  className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                >
                  Cancel Upload
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  );
};

export default UploadProgress;
