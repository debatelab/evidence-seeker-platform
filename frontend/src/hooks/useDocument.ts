import { useState, useEffect } from "react";
import { Document, DocumentCreate } from "../types/document";
import api from "../utils/api";

export const useDocuments = (evidenceSeekerUuid: string) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = async () => {
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
  };

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

  const deleteDocument = async (id: number): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await api.delete(`/documents/${id}`);
      setDocuments((prev) => prev.filter((doc) => doc.id !== id));
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
  }, [evidenceSeekerUuid]);

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

  const fetchDocument = async () => {
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
  };

  useEffect(() => {
    if (id) {
      fetchDocument();
    }
  }, [id]);

  return {
    document,
    loading,
    error,
    fetchDocument,
  };
};
