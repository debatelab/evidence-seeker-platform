import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import {
  AlertCircle,
  CheckCircle2,
  FilePlus2,
  Loader2,
  Repeat2,
  Trash2,
} from "lucide-react";
import {
  UploadJobStatus,
  UploadQueueItem,
  useDocumentUploadController,
} from "../../../hooks/useDocumentUploadController";
import type { ConfigurationStatus } from "../../../types/evidenceSeeker";

interface WizardDocumentStepProps {
  evidenceSeekerUuid: string;
  onboardingToken?: string;
  skipAcknowledged: boolean;
  onRequirementChange: (met: boolean) => void;
  onSkipDocuments: () => Promise<ConfigurationStatus | void>;
}

const statusCopy: Record<
  UploadJobStatus,
  { label: string; tone: string; icon?: React.ReactNode }
> = {
  queued: { label: "Queued", tone: "text-gray-500" },
  uploading: {
    label: "Uploading",
    tone: "text-blue-600",
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
  },
  embedding: {
    label: "Processing",
    tone: "text-amber-600",
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
  },
  ready: {
    label: "Ready",
    tone: "text-green-600",
    icon: <CheckCircle2 className="h-4 w-4" />,
  },
  failed: {
    label: "Failed",
    tone: "text-red-600",
    icon: <AlertCircle className="h-4 w-4" />,
  },
};

const formatFileSize = (bytes: number): string => {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length);
  const value = bytes / 1024 ** index;
  return `${value.toFixed(1)} ${units[index]}`;
};

export const WizardDocumentStep: React.FC<WizardDocumentStepProps> = ({
  evidenceSeekerUuid,
  onboardingToken,
  skipAcknowledged,
  onRequirementChange,
  onSkipDocuments,
}) => {
  const controller = useDocumentUploadController(evidenceSeekerUuid, {
    onboardingToken,
  });
  const [validationError, setValidationError] = useState<string | null>(null);
  const [skipModalOpen, setSkipModalOpen] = useState(false);
  const [skipLoading, setSkipLoading] = useState(false);
  const [skipError, setSkipError] = useState<string | null>(null);

  useEffect(() => {
    onRequirementChange(controller.hasReadyDocument);
  }, [controller.hasReadyDocument, onRequirementChange]);

  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: any[]) => {
      setValidationError(null);
      if (fileRejections.length > 0) {
        const error = fileRejections[0].errors[0];
        if (error.code === "file-too-large") {
          setValidationError("File is too large. Maximum size is 10MB.");
        } else if (error.code === "file-invalid-type") {
          setValidationError("Unsupported file format. Upload PDF or TXT files.");
        } else {
          setValidationError(error.message);
        }
        return;
      }
      if (acceptedFiles.length === 0) {
        return;
      }
      controller.enqueueFiles(acceptedFiles);
    },
    [controller]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    accept: {
      "application/pdf": [".pdf"],
      "text/plain": [".txt"],
    },
    maxSize: 10 * 1024 * 1024,
  });

  const renderRow = useCallback(
    (item: UploadQueueItem) => {
      const tone = statusCopy[item.status];
      return (
        <li
          key={item.id}
          className="flex items-center justify-between border border-gray-200 rounded-lg px-4 py-3 bg-white"
        >
          <div>
            <p className="text-sm font-medium text-gray-900">{item.title}</p>
            <p className="text-xs text-gray-500">{formatFileSize(item.size)}</p>
          </div>
          <div className="flex items-center space-x-4">
            <div className={`flex items-center space-x-2 text-sm ${tone.tone}`}>
              {tone.icon}
              <span>{tone.label}</span>
            </div>
            <div className="flex items-center space-x-2">
              {item.status === "failed" && (
                <button
                  type="button"
                  className="text-sm text-blue-600 hover:text-blue-800 inline-flex items-center space-x-1"
                  onClick={() => controller.retryItem(item.id)}
                >
                  <Repeat2 className="h-4 w-4" />
                  <span>Retry</span>
                </button>
              )}
              <button
                type="button"
                className="text-sm text-gray-500 hover:text-gray-700 inline-flex items-center space-x-1"
                onClick={() => controller.removeItem(item.id)}
              >
                <Trash2 className="h-4 w-4" />
                <span>Remove</span>
              </button>
            </div>
          </div>
        </li>
      );
    },
    [controller]
  );

  const queueContent = useMemo(() => {
    if (controller.queue.length === 0) {
      return (
        <p className="text-sm text-gray-500 text-center py-6">
          No files yet. Drag and drop PDFs or TXT files to start processing.
        </p>
      );
    }
    return (
      <ul className="space-y-3">
        {controller.queue.map((item) => renderRow(item))}
      </ul>
    );
  }, [controller.queue, renderRow]);

  const openSkipModal = () => {
    setSkipError(null);
    setSkipModalOpen(true);
  };

  const confirmSkip = async () => {
    setSkipLoading(true);
    setSkipError(null);
    try {
      await onSkipDocuments();
      setSkipModalOpen(false);
    } catch (err: any) {
      setSkipError(err?.message ?? "Failed to update skip preference.");
    } finally {
      setSkipLoading(false);
    }
  };

  return (
    <section className="space-y-6">
      <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6">
        <div
          {...getRootProps()}
          className={`flex flex-col items-center justify-center border-2 border-dashed rounded-lg px-6 py-10 cursor-pointer transition ${
            isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300"
          }`}
        >
          <input {...getInputProps()} />
          <FilePlus2 className="h-10 w-10 text-blue-500 mb-3" />
          <p className="text-base font-medium text-gray-900">
            Drag & drop files here, or click to browse
          </p>
          <p className="text-sm text-gray-500">
            Supported formats: PDF, TXT • Max size: 10MB
          </p>
          {validationError && (
            <p className="text-sm text-red-600 mt-3">{validationError}</p>
          )}
        </div>
      </div>

      {skipAcknowledged && (
        <div className="rounded-lg border border-orange-200 bg-orange-50 p-4 text-sm text-orange-900">
          You chose to finish setup without documents. Uploading at least one file
          here will unlock Fact Check and Search tabs.
        </div>
      )}

      {controller.documentsError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {controller.documentsError}
        </div>
      )}

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-900">Upload queue</h3>
          {controller.uploading && (
            <span className="text-xs text-gray-500 inline-flex items-center space-x-1">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>Processing…</span>
            </span>
          )}
        </div>
        {queueContent}
      </div>

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <button
          type="button"
          onClick={openSkipModal}
          className="text-sm font-medium text-gray-600 hover:text-gray-800 underline"
        >
          Continue without documents
        </button>
        <p className="text-xs text-gray-500 text-right">
          At least one successful upload unlocks Fact Check and Search tabs.
        </p>
      </div>

      {skipModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center space-x-3">
              <AlertCircle className="h-6 w-6 text-amber-600" />
              <div>
                <h4 className="text-base font-semibold text-gray-900">
                  Finish without documents?
                </h4>
                <p className="text-sm text-gray-600">
                  Fact Check and Search remain disabled until you upload at least one
                  document. You can come back any time.
                </p>
              </div>
            </div>
            {skipError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-2">
                {skipError}
              </p>
            )}
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800"
                onClick={() => setSkipModalOpen(false)}
                disabled={skipLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-md disabled:opacity-60"
                onClick={confirmSkip}
                disabled={skipLoading}
              >
                {skipLoading ? "Saving…" : "Confirm skip"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default WizardDocumentStep;
