import React, { useState } from "react";
// navigate removed (unused)
import { Document, DocumentCreate } from "../../types/document";
import { useDocuments } from "../../hooks/useDocument";
import UploadForm from "./UploadForm";
import UploadProgress from "./UploadProgress";
import UploadSuccess from "./UploadSuccess";
import UploadError from "./UploadError";

type UploadState = "form-input" | "uploading" | "success" | "error";

interface DocumentUploadProps {
  evidenceSeekerUuid: string;
  onUploadSuccess?: (document: Document) => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  evidenceSeekerUuid,
  onUploadSuccess,
}) => {
  const { uploadDocument } = useDocuments(evidenceSeekerUuid);

  const [uploadState, setUploadState] = useState<UploadState>("form-input");
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [currentTitle, setCurrentTitle] = useState<string>("");
  const [currentDescription, setCurrentDescription] = useState<string>("");
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploadError, setUploadError] = useState<string>("");
  const [_uploadedDocument, setUploadedDocument] = useState<Document | null>(
    null
  ); // underscored to satisfy no-unused-vars rule

  const handleStartUpload = async (
    file: File,
    title: string,
    description: string
  ) => {
    // Store current upload data
    setCurrentFile(file);
    setCurrentTitle(title);
    setCurrentDescription(description);
    setUploadState("uploading");
    setUploadProgress(0);

    try {
      // Simulate progress updates during upload
      const progressInterval = setInterval(() => {
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
        description: description.trim(),
      };

      const result = await uploadDocument(uploadData);

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (result) {
        setUploadedDocument(result);
        setUploadState("success");
        onUploadSuccess?.(result);
      } else {
        setUploadError("Upload failed. Please try again.");
        setUploadState("error");
      }
    } catch (err) {
      setUploadError("An error occurred during upload. Please try again.");
      setUploadState("error");
      setUploadProgress(0);
    }
  };

  const handleCancel = () => {
    setUploadState("form-input");
    setUploadProgress(0);
    setUploadError("");
    setCurrentFile(null);
    setCurrentTitle("");
    setCurrentDescription("");
  };

  const handleUploadAnother = () => {
    setUploadState("form-input");
    setUploadProgress(0);
    setUploadError("");
    setCurrentFile(null);
    setCurrentTitle("");
    setCurrentDescription("");
    setUploadedDocument(null);
  };

  const handleRetry = () => {
    if (currentFile) {
      handleStartUpload(currentFile, currentTitle, currentDescription);
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

  // Render the appropriate component based on state
  switch (uploadState) {
    case "form-input":
      return <UploadForm onStartUpload={handleStartUpload} />;

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

    case "success":
      return currentFile ? (
        <UploadSuccess
          file={currentFile}
          title={currentTitle}
          onUploadAnother={handleUploadAnother}
          evidenceSeekerUuid={evidenceSeekerUuid}
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
