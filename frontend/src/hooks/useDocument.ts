import { useState, useEffect, useCallback } from "react";
import type {
  Document,
  DocumentCreate,
  DocumentIngestionResponse,
  DocumentUpdate,
} from "../types/document";
import { documentsAPI } from "../utils/api";

interface UseDocumentsOptions {
  enabled?: boolean;
}

const toErrorMessage = (error: unknown, fallback: string): string => {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    error.response !== null &&
    "data" in error.response
  ) {
    const detail =
      (error.response as { data?: { detail?: unknown } }).data?.detail ?? null;
    if (typeof detail === "string") {
      return detail;
    }
    if (
      detail &&
      typeof detail === "object" &&
      "message" in detail &&
      typeof (detail as Record<string, unknown>).message === "string"
    ) {
      return (detail as { message: string }).message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
};

export const useDocuments = (
  evidenceSeekerUuid: string,
  options: UseDocumentsOptions = {}
) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await documentsAPI.listDocuments(evidenceSeekerUuid);
      setDocuments(data);
    } catch (err) {
      setError(toErrorMessage(err, "Failed to fetch documents"));
    } finally {
      setLoading(false);
    }
  }, [evidenceSeekerUuid]);

  const uploadDocument = async (
    data: DocumentCreate,
    options?: { onboardingToken?: string }
  ): Promise<DocumentIngestionResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await documentsAPI.uploadDocument(
        evidenceSeekerUuid,
        data,
        options
      );
      setDocuments((prev) => [...prev, response.document]);
      return response;
    } catch (err) {
      setError(toErrorMessage(err, "Failed to upload document"));
      return null;
    } finally {
      setLoading(false);
    }
  };

  const deleteDocument = async (uuid: string): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await documentsAPI.deleteDocument(uuid);
      setDocuments((prev) => prev.filter((doc) => doc.uuid !== uuid));
      return true;
    } catch (err) {
      setError(toErrorMessage(err, "Failed to delete document"));
      return false;
    } finally {
      setLoading(false);
    }
  };

  const updateDocument = async (
    uuid: string,
    payload: DocumentUpdate
  ): Promise<Document | null> => {
    setLoading(true);
    setError(null);
    try {
      const updated = await documentsAPI.updateDocument(uuid, payload);
      setDocuments((prev) =>
        prev.map((doc) => (doc.uuid === uuid ? updated : doc))
      );
      return updated;
    } catch (err) {
      setError(toErrorMessage(err, "Failed to update document"));
      return null;
    } finally {
      setLoading(false);
    }
  };

  const enabled = options.enabled ?? true;

  useEffect(() => {
    if (evidenceSeekerUuid && enabled) {
      fetchDocuments();
    }
  }, [evidenceSeekerUuid, fetchDocuments, enabled]);

  return {
    documents,
    loading,
    error,
    fetchDocuments,
    uploadDocument,
    deleteDocument,
    updateDocument,
  };
};
