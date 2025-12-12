import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router";
import FactCheckRunDetailView from "../../components/FactCheck/FactCheckRunDetailView";
import type { PublicFactCheckRunDetailResponse } from "../../types/public";
import { evidenceSeekerAPI } from "../../utils/api";
import { useEvidenceSeekers } from "../../hooks/useEvidenceSeeker";

interface AdminFactCheckRunPageProps {
  evidenceSeekerUuid?: string;
}

const isTerminalStatus = (status?: string | null): boolean => {
  if (!status) return false;
  return ["SUCCEEDED", "FAILED", "CANCELLED"].includes(status.toUpperCase());
};

const getErrorDetail = (error: unknown, fallback: string): string => {
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
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
};

const AdminFactCheckRunPage: React.FC<AdminFactCheckRunPageProps> = ({
  evidenceSeekerUuid,
}) => {
  const { runUuid } = useParams<{ runUuid: string }>();
  const { evidenceSeekers } = useEvidenceSeekers();
  const seeker = useMemo(
    () =>
      evidenceSeekers.find((item) => item.uuid === evidenceSeekerUuid) ?? null,
    [evidenceSeekers, evidenceSeekerUuid]
  );

  const [data, setData] = useState<PublicFactCheckRunDetailResponse | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const pollIntervalRef = useRef<number | null>(null);
  const pollInFlight = useRef(false);

  const seekerSummary = useMemo(() => {
    if (!seeker) return null;
    return {
      uuid: seeker.uuid,
      title: seeker.title,
      description: seeker.description ?? null,
      language: seeker.language ?? null,
      logoUrl: seeker.logoUrl ?? null,
      publishedAt: seeker.publishedAt ?? null,
      documentCount: 0,
      latestFactCheckAt: null,
    };
  }, [seeker]);

  const backHref = evidenceSeekerUuid
    ? `/app/evidence-seekers/${evidenceSeekerUuid}/manage/fact-checks`
    : "/app/evidence-seekers";

  const fetchRunDetail = useCallback(
    async (mode: "initial" | "poll" = "initial") => {
      if (!runUuid || !evidenceSeekerUuid || !seekerSummary) return null;
      try {
        const [run, results] = await Promise.all([
          evidenceSeekerAPI.getFactCheckRun(evidenceSeekerUuid, runUuid),
          evidenceSeekerAPI.getFactCheckResults(evidenceSeekerUuid, runUuid),
        ]);
        const response: PublicFactCheckRunDetailResponse = {
          run,
          seeker: seekerSummary,
          results,
        };
        setData(response);
        setError(null);
        setPollError(null);
        setLastUpdatedAt(new Date());
        return response;
      } catch (err) {
        console.error(err);
        const detail = getErrorDetail(err, "Fact check not available.");
        if (mode === "initial") {
          setError(detail);
          setData(null);
        } else {
          setPollError(detail);
        }
        throw err;
      }
    },
    [evidenceSeekerUuid, runUuid, seekerSummary]
  );

  useEffect(() => {
    if (!runUuid || !evidenceSeekerUuid || !seekerSummary) return;
    let isMounted = true;
    setLoading(true);
    fetchRunDetail("initial")
      .catch(() => {
        /* handled above */
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [runUuid, evidenceSeekerUuid, seekerSummary, fetchRunDetail]);

  useEffect(() => {
    if (!data?.run?.status || !runUuid) {
      return;
    }

    if (isTerminalStatus(data.run.status)) {
      if (pollIntervalRef.current) {
        window.clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      setIsPolling(false);
      return;
    }

    if (pollIntervalRef.current) {
      return;
    }

    setIsPolling(true);
    pollIntervalRef.current = window.setInterval(() => {
      if (document.hidden || pollInFlight.current) {
        return;
      }
      pollInFlight.current = true;
      fetchRunDetail("poll")
        .catch(() => {
          /* errors handled via pollError state */
        })
        .finally(() => {
          pollInFlight.current = false;
        });
    }, 3000);

    return () => {
      if (pollIntervalRef.current) {
        window.clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [data?.run?.status, runUuid, fetchRunDetail]);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        window.clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  if (!evidenceSeekerUuid) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <p className="text-gray-700">
          Evidence Seeker context is required to view this run.
        </p>
      </div>
    );
  }

  return (
    <FactCheckRunDetailView
      data={data}
      loading={loading}
      error={error}
      backHref={backHref}
      showShare={false}
      pollError={pollError}
      isPolling={isPolling}
      lastUpdatedAt={lastUpdatedAt}
      seekerOverride={seekerSummary ?? undefined}
    />
  );
};

export default AdminFactCheckRunPage;
