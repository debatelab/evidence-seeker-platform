import { useState, useEffect } from "react";
import {
  EvidenceSeeker,
  EvidenceSeekerCreate,
  EvidenceSeekerUpdate,
} from "../types/evidenceSeeker";
import api from "../utils/api";

export const useEvidenceSeekers = () => {
  const [evidenceSeekers, setEvidenceSeekers] = useState<EvidenceSeeker[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEvidenceSeekers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get("/evidence-seekers");
      setEvidenceSeekers(response.data);
    } catch (err) {
      setError("Failed to fetch evidence seekers");
    } finally {
      setLoading(false);
    }
  };

  const createEvidenceSeeker = async (
    data: EvidenceSeekerCreate
  ): Promise<EvidenceSeeker | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post("/evidence-seekers", data);
      const newSeeker = response.data;
      setEvidenceSeekers((prev) => [...prev, newSeeker]);
      return newSeeker;
    } catch (err) {
      setError("Failed to create evidence seeker");
      return null;
    } finally {
      setLoading(false);
    }
  };

  const updateEvidenceSeeker = async (
    id: number,
    data: EvidenceSeekerUpdate
  ): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.put(`/evidence-seekers/${id}`, data);
      const updatedSeeker = response.data;
      setEvidenceSeekers((prev) =>
        prev.map((seeker) => (seeker.id === id ? updatedSeeker : seeker))
      );
      return true;
    } catch (err) {
      setError("Failed to update evidence seeker");
      return false;
    } finally {
      setLoading(false);
    }
  };

  const deleteEvidenceSeeker = async (id: number): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await api.delete(`/evidence-seekers/${id}`);
      setEvidenceSeekers((prev) => prev.filter((seeker) => seeker.id !== id));
      return true;
    } catch (err) {
      setError("Failed to delete evidence seeker");
      return false;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidenceSeekers();
  }, []);

  return {
    evidenceSeekers,
    loading,
    error,
    fetchEvidenceSeekers,
    createEvidenceSeeker,
    updateEvidenceSeeker,
    deleteEvidenceSeeker,
  };
};

export const useEvidenceSeeker = (id: number) => {
  const [evidenceSeeker, setEvidenceSeeker] = useState<EvidenceSeeker | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEvidenceSeeker = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/evidence-seekers/${id}`);
      setEvidenceSeeker(response.data);
    } catch (err) {
      setError("Failed to fetch evidence seeker");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchEvidenceSeeker();
    }
  }, [id]);

  return {
    evidenceSeeker,
    loading,
    error,
    fetchEvidenceSeeker,
  };
};
