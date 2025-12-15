import React, { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { Document, DocumentCreate } from "../../types/document";
import { useDocuments } from "../../hooks/useDocument";
import UploadForm from "./UploadForm";
import UploadProgress from "./UploadProgress";
import UploadError from "./UploadError";
import { useConfigurationStatus } from "../../hooks/useConfigurationStatus";
import { ConfigurationBlockedNotice } from "../Configuration/ConfigurationBlockedNotice";

type UploadState = "form-input" | "uploading" | "error";

interface DocumentUploadProps {
  evidenceSeekerUuid: string;
  onUploadSuccess?: (document: Document) => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  evidenceSeekerUuid,
  onUploadSuccess,
}) => {
  const navigate = useNavigate();
  const {
    status: configurationStatus,
    loading: statusLoading,
    error: statusError,
  } = useConfigurationStatus(evidenceSeekerUuid);
  const statusState = configurationStatus?.state;
  const canUpload =
    statusState === "READY" || statusState === "MISSING_DOCUMENTS";
  const { uploadDocument } = useDocuments(evidenceSeekerUuid, {
    enabled: canUpload,
  });

  const [uploadState, setUploadState] = useState<UploadState>("form-input");
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [currentTitle, setCurrentTitle] = useState<string>("");
  const [currentDescription, setCurrentDescription] = useState<string>("");
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploadError, setUploadError] = useState<string>("");
  const progressIntervalRef = useRef<number | null>(null);
  const [currentSourceUrl, setCurrentSourceUrl] = useState<string>("");

  const clearProgressInterval = () => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  };

  const handleStartUpload = async (
    file: File,
    title: string,
    description: string,
    sourceUrl?: string
  ) => {
    // Store current upload data
    setCurrentFile(file);
    setCurrentTitle(title);
    setCurrentDescription(description);
    setCurrentSourceUrl(sourceUrl ?? "");
    setUploadState("uploading");
    setUploadProgress(0);

    try {
      // Simulate progress updates during upload
      progressIntervalRef.current = window.setInterval(() => {
        setUploadProgress((prev) => {
          if (prev < 90) {
            return prev + Math.random() * 15;
          }
          return prev;
        });
      }, 200);

      const uploadData: DocumentCreate = {
        file,
        title: title.trim(),
        description: description.trim() || null,
        sourceUrl: sourceUrl?.trim() || null,
      };

      const result = await uploadDocument(uploadData);

      clearProgressInterval();
      setUploadProgress(100);

      if (result) {
        onUploadSuccess?.(result.document);
        navigate(
          `/app/evidence-seekers/${evidenceSeekerUuid}/manage/documents`
        );
      } else {
        setUploadError("Upload failed. Please try again.");
        setUploadState("error");
      }
    } catch (err) {
      setUploadError("An error occurred during upload. Please try again.");
      setUploadState("error");
      setUploadProgress(0);
    } finally {
      clearProgressInterval();
    }
  };

  const handleCancel = () => {
    clearProgressInterval();
    setUploadState("form-input");
    setUploadProgress(0);
    setUploadError("");
    setCurrentFile(null);
    setCurrentTitle("");
    setCurrentDescription("");
    setCurrentSourceUrl("");
  };

  const handleRetry = () => {
    if (currentFile) {
      handleStartUpload(
        currentFile,
        currentTitle,
        currentDescription,
        currentSourceUrl
      );
    } else {
      setUploadState("form-input");
    }
  };

  const handleChooseDifferent = () => {
    setUploadState("form-input");
    setUploadProgress(0);
    setUploadError("");
    setCurrentFile(null);
    setCurrentTitle("");
    setCurrentDescription("");
  };

  if (statusLoading) {
    return (
      <div className="flex justify-center items-center p-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (statusError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4 text-red-800">
        {statusError}
      </div>
    );
  }

  if (!canUpload) {
    return (
      <ConfigurationBlockedNotice
        status={configurationStatus}
        onConfigure={() =>
          navigate(`/app/evidence-seekers/${evidenceSeekerUuid}/manage/settings`)
        }
        description="Finish connecting your inference provider before uploading new documents."
      />
    );
  }

  // Render the appropriate component based on state
  switch (uploadState) {
    case "form-input":
      return (
        <div className="space-y-4">
          {statusState === "MISSING_DOCUMENTS" && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              Upload at least one document to finish setup.
            </div>
          )}
          <UploadForm onStartUpload={handleStartUpload} />
        </div>
      );

    case "uploading":
      return currentFile ? (
        <UploadProgress
          file={currentFile}
          title={currentTitle}
          onCancel={handleCancel}
          progress={uploadProgress}
        />
      ) : (
        <UploadForm onStartUpload={handleStartUpload} />
      );

    case "error":
      return currentFile ? (
        <UploadError
          file={currentFile}
          title={currentTitle}
          error={uploadError}
          onRetry={handleRetry}
          onChooseDifferent={handleChooseDifferent}
        />
      ) : (
        <UploadForm onStartUpload={handleStartUpload} />
      );

    default:
      return <UploadForm onStartUpload={handleStartUpload} />;
  }
};

export default DocumentUpload;
