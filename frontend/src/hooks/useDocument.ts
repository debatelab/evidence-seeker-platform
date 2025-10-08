import { useState, useEffect, useCallback } from "react";
import { Document, DocumentCreate } from "../types/document";
import api from "../utils/api";

export const useDocuments = (evidenceSeekerUuid: string) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(
        `/documents?evidence_seeker_uuid=${evidenceSeekerUuid}`
      );
      setDocuments(response.data);
    } catch (err) {
      setError("Failed to fetch documents");
    } finally {
      setLoading(false);
    }
  }, [evidenceSeekerUuid]);

  const uploadDocument = async (
    data: DocumentCreate
  ): Promise<Document | null> => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", data.file);
      formData.append("title", data.title);
      formData.append("description", data.description);
      formData.append("evidence_seeker_uuid", evidenceSeekerUuid);
      console.log(data);
      const response = await api.post("/documents/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      const newDocument = response.data;
      setDocuments((prev) => [...prev, newDocument]);
      return newDocument;
    } catch (err) {
      setError("Failed to upload document");
      return null;
    } finally {
      setLoading(false);
    }
  };

  const deleteDocument = async (uuid: string): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await api.delete(`/documents/${uuid}`);
      setDocuments((prev) => prev.filter((doc) => doc.uuid !== uuid));
      return true;
    } catch (err) {
      setError("Failed to delete document");
      return false;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (evidenceSeekerUuid) {
      fetchDocuments();
    }
  }, [evidenceSeekerUuid, fetchDocuments]);

  return {
    documents,
    loading,
    error,
    fetchDocuments,
    uploadDocument,
    deleteDocument,
  };
};

export const useDocument = (id: number) => {
  const [document, setDocument] = useState<Document | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocument = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/documents/${id}`);
      setDocument(response.data);
    } catch (err) {
      setError("Failed to fetch document");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      fetchDocument();
    }
  }, [id, fetchDocument]);

  return {
    document,
    loading,
    error,
    fetchDocument,
  };
};
