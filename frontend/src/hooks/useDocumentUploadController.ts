import { useCallback, useEffect, useMemo, useState } from "react";
import type { Document } from "../types/document";
import type { IndexJob } from "../types/indexJob";
import { useDocuments } from "./useDocument";
import { useIndexJobs } from "./useIndexJobs";

export type UploadJobStatus =
  | "queued"
  | "uploading"
  | "embedding"
  | "ready"
  | "failed";

export interface UploadQueueItem {
  id: string;
  file?: File;
  title: string;
  size: number;
  status: UploadJobStatus;
  progress: number;
  document?: Document;
  jobUuid?: string;
  operationId?: string | null;
  error?: string | null;
}

interface ControllerOptions {
  onboardingToken?: string;
}

const titleFromFilename = (filename: string): string => {
  const trimmed = filename.trim();
  if (!trimmed.includes(".")) {
    return trimmed;
  }
  return trimmed.slice(0, trimmed.lastIndexOf("."));
};

const formatSize = (file?: File): number => (file ? file.size : 0);

export const useDocumentUploadController = (
  evidenceSeekerUuid: string | undefined,
  options: ControllerOptions = {}
) => {
  const {
    documents,
    uploadDocument,
    loading: documentsLoading,
    error: documentsError,
  } = useDocuments(evidenceSeekerUuid ?? "", {
    enabled: Boolean(evidenceSeekerUuid),
  });
  const { jobs } = useIndexJobs(evidenceSeekerUuid, {
    pollIntervalMs: evidenceSeekerUuid ? 5000 : undefined,
  });
  const [queue, setQueue] = useState<UploadQueueItem[]>([]);
  const onboardingToken = options.onboardingToken;

  // Seed queue with existing documents so returning users can see their uploads
  useEffect(() => {
    if (!documents || documents.length === 0) {
      return;
    }
    setQueue((current) => {
      const known = new Set(current.map((item) => item.document?.uuid ?? item.id));
      const seeded: UploadQueueItem[] = [];
      documents.forEach((doc) => {
        if (known.has(doc.uuid)) {
          return;
        }
        seeded.push({
          id: doc.uuid,
          title: doc.title,
          size: doc.fileSize,
          status: "ready",
          progress: 100,
          document: doc,
        });
      });
      if (seeded.length === 0) {
        return current;
      }
      return [...seeded, ...current];
    });
  }, [documents]);

  // Update queue entries when index jobs complete/fail
  useEffect(() => {
    if (!jobs || jobs.length === 0) {
      return;
    }
    setQueue((current) =>
      current.map((item) => {
        if (!item.jobUuid) {
          return item;
        }
        const job = jobs.find((candidate: IndexJob) => candidate.uuid === item.jobUuid);
        if (!job) {
          return item;
        }
        if (job.status === "SUCCEEDED" && item.status !== "ready") {
          return { ...item, status: "ready", progress: 100 };
        }
        if (job.status === "FAILED" && item.status !== "failed") {
          return {
            ...item,
            status: "failed",
            error: job.errorMessage ?? "Indexing failed",
          };
        }
        if (job.status === "RUNNING" && item.status === "embedding") {
          return { ...item, progress: Math.min(90, item.progress || 50) };
        }
        return item;
      })
    );
  }, [jobs]);

  const uploadSingle = useCallback(
    async (itemId: string, snapshot?: UploadQueueItem) => {
      if (!evidenceSeekerUuid) {
        return;
      }
      setQueue((current) =>
        current.map((entry) =>
          entry.id === itemId
            ? { ...entry, status: "uploading", progress: 10, error: null }
            : entry
        )
      );
      const active = snapshot ?? queue.find((item) => item.id === itemId);
      if (!active?.file) {
        setQueue((current) =>
          current.map((entry) =>
            entry.id === itemId
              ? {
                  ...entry,
                  status: "failed",
                  error: "File not found. Please choose the file again.",
                }
              : entry
          )
        );
        return;
      }
      try {
        const response = await uploadDocument(
          {
            file: active.file,
            title: active.title,
            description: "",
          },
          onboardingToken ? { onboardingToken } : undefined
        );
        if (!response) {
          throw new Error("Upload failed");
        }
        setQueue((current) =>
          current.map((entry) =>
            entry.id === itemId
              ? {
                  ...entry,
                  status: "embedding",
                  progress: 75,
                  document: response.document,
                  jobUuid: response.jobUuid,
                  operationId: response.operationId ?? null,
                }
              : entry
          )
        );
      } catch (err: any) {
        setQueue((current) =>
          current.map((entry) =>
            entry.id === itemId
              ? {
                  ...entry,
                  status: "failed",
                  error: err?.message ?? "Upload failed",
                }
              : entry
          )
        );
      }
    },
    [evidenceSeekerUuid, onboardingToken, queue, uploadDocument]
  );

  const enqueueFiles = useCallback(
    (files: File[]) => {
      if (!files || files.length === 0) {
        return;
      }
      if (!evidenceSeekerUuid) {
        throw new Error(
          "Evidence Seeker must be created before uploading documents."
        );
      }
      const newItems = files.map<UploadQueueItem>((file) => ({
        id: generateId(),
        file,
        title: titleFromFilename(file.name),
        size: formatSize(file),
        status: "queued",
        progress: 0,
      }));
      setQueue((prev) => [...newItems, ...prev]);
      newItems.forEach((item) => {
        void uploadSingle(item.id, item);
      });
    },
    [evidenceSeekerUuid, uploadSingle]
  );

  const retryItem = useCallback(
    async (itemId: string) => {
      const current = queue.find((item) => item.id === itemId);
      if (!current?.file) {
        return;
      }
      await uploadSingle(itemId, current);
    },
    [queue, uploadSingle]
  );

  const removeItem = useCallback((itemId: string) => {
    setQueue((current) => current.filter((item) => item.id !== itemId));
  }, []);

  const hasReadyDocument = useMemo(() => {
    return queue.some((item) => item.status === "ready" || item.status === "embedding");
  }, [queue]);

  return {
    queue,
    enqueueFiles,
    retryItem,
    removeItem,
    hasReadyDocument,
    uploading: queue.some((item) => item.status === "uploading"),
    documentsLoading,
    documentsError,
  };
};
const generateId = (): string => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2);
};
