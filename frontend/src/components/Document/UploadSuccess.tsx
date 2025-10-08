import React from "react";
import { useNavigate } from "react-router";
import PageLayout from "../PageLayout";

interface UploadSuccessProps {
  file: File;
  title: string;
  onUploadAnother: () => void;
  evidenceSeekerUuid: string;
}

const UploadSuccess: React.FC<UploadSuccessProps> = ({
  file,
  title,
  onUploadAnother,
  evidenceSeekerUuid,
}) => {
  const navigate = useNavigate();

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

  const handleViewDocuments = () => {
    navigate(`/evidence-seekers/${evidenceSeekerUuid}/manage`);
  };

  return (
    <PageLayout variant="narrow">
      <div className="bg-white shadow-sm rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="text-2xl">✅</div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                Upload Complete!
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                Your document has been uploaded successfully
              </p>
            </div>
          </div>
        </div>

        <div className="p-6">
          <div className="space-y-6">
            {/* Success Message */}
            <div className="text-center">
              <div className="text-6xl mb-4">🎉</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Document Uploaded Successfully!
              </h3>
              <p className="text-sm text-gray-600">
                Your document is now ready to be used in your evidence seeker.
              </p>
            </div>

            {/* File Information */}
            <div className="flex items-center space-x-4 p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="text-3xl">{getFileIcon(file.type)}</div>
              <div className="flex-1">
                <h4 className="font-medium text-gray-900 truncate">{title}</h4>
                <p className="text-sm text-gray-600 truncate">📁 {file.name}</p>
                <p className="text-sm text-gray-500">
                  📏 {formatFileSize(file.size)}
                </p>
              </div>
              <div className="text-green-600">
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
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={onUploadAnother}
                className="px-6 py-3 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                📤 Upload Another Document
              </button>

              <button
                onClick={handleViewDocuments}
                className="px-6 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                📂 View All Documents
              </button>
            </div>

            {/* Additional Info */}
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-blue-400"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <h4 className="text-sm font-medium text-blue-800">
                    What\u2019s Next?
                  </h4>
                  <div className="mt-2 text-sm text-blue-700">
                    <ul className="list-disc list-inside space-y-1">
                      <li>Your document is now being processed</li>
                      <li>You can start using it in your evidence seeker</li>
                      <li>
                        Upload more documents to improve your AI responses
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
};

export default UploadSuccess;
