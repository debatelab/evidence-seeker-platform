import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import PublicLayout from "../../components/Public/PublicLayout";
import EvidenceSeekerCard from "../../components/Public/EvidenceSeekerCard";
import FactCheckSummaryCard from "../../components/Public/FactCheckSummaryCard";
import { useAuth } from "../../hooks/useAuth";
import { publicAPI } from "../../utils/api";
import type {
  PublicEvidenceSeekerSummary,
  PublicFactCheckRunSummary,
} from "../../types/public";
import {
  aggregateResultSummary,
  type ConfirmationSummaryDisplay,
} from "../../utils/factCheckSummaries";

const formatDateTime = (value?: string | null) => {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return new Date(value).toLocaleString();
  }
};

const PublicHomePage: React.FC = () => {
  const [seekers, setSeekers] = useState<PublicEvidenceSeekerSummary[]>([]);
  const [factChecks, setFactChecks] = useState<PublicFactCheckRunSummary[]>([]);
  const [factCheckSummaries, setFactCheckSummaries] = useState<
    Record<string, ConfirmationSummaryDisplay[]>
  >({});
  const [factCheckSummariesLoading, setFactCheckSummariesLoading] =
    useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      try {
        const [seekerResponse, factCheckResponse] = await Promise.all([
          publicAPI.listEvidenceSeekers(1, 6),
          publicAPI.listFactChecks(1, 6),
        ]);
        if (!isMounted) {
          return;
        }
        setSeekers(seekerResponse.items);
        setFactChecks(factCheckResponse.items);
      } catch (err) {
        console.error(err);
        if (isMounted) {
          setError("Unable to load public data. Please try again later.");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchData();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!factChecks.length) {
      setFactCheckSummaries({});
      setFactCheckSummariesLoading(false);
      return;
    }
    let isMounted = true;
    setFactCheckSummariesLoading(true);
    const fetchSummaries = async () => {
      try {
        const entries = await Promise.all(
          factChecks.map(async (run) => {
            try {
              const detail = await publicAPI.getFactCheck(run.uuid);
              return [
                run.uuid,
                aggregateResultSummary(detail.results),
              ] as const;
            } catch (err) {
              console.error(err);
              return [run.uuid, [] as ConfirmationSummaryDisplay[]] as const;
            }
          })
        );
        if (!isMounted) return;
        const map: Record<string, ConfirmationSummaryDisplay[]> = {};
        entries.forEach(([uuid, summaries]) => {
          map[uuid] = summaries;
        });
        setFactCheckSummaries(map);
      } finally {
        if (isMounted) {
          setFactCheckSummariesLoading(false);
        }
      }
    };
    void fetchSummaries();
    return () => {
      isMounted = false;
    };
  }, [factChecks]);

  const primaryCtaHref = isAuthenticated
    ? "/app/evidence-seekers"
    : "/register";

  const getPublishedLabel = (run: PublicFactCheckRunSummary) =>
    run.publishedAt || run.completedAt
      ? formatDateTime(run.publishedAt ?? run.completedAt)
      : "Awaiting publication";

  return (
    <PublicLayout>
      <section className="bg-gradient-to-b from-[color:var(--color-primary-soft)] to-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h1 className="brand-title mt-4 text-4xl text-gray-900 sm:text-5xl">
                Open-source AI fact-checking
              </h1>
              <p className="mt-6 text-lg text-gray-600">
                Explore community Evidence Seekers, inspect their document
                libraries, and run transparent fact checks in real time.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <button
                  onClick={() => navigate(primaryCtaHref)}
                  className="btn-primary px-6 py-3 text-base shadow"
                >
                  Create your own Evidence Seeker
                </button>
                <a
                  href="#public-evidence-seekers"
                  className="px-6 py-3 rounded-lg border border-gray-300 text-gray-700 font-semibold hover:border-gray-400 transition"
                >
                  Explore Seekers
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div
          className="flex items-center justify-between mb-8"
          id="fact-checks"
        >
          <h2 className="brand-title text-2xl text-gray-900">
            Latest Fact Checks
          </h2>
          <Link
            to="/login"
            className="text-sm font-semibold text-primary hover:text-primary-hover"
          >
            Share your own →
          </Link>
        </div>
        {error ? (
          <p className="text-red-600">{error}</p>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {factChecks.length === 0 && !loading ? (
              <p className="text-gray-500">
                No public fact checks available yet.
              </p>
            ) : (
              factChecks.map((run, index) => (
                <FactCheckSummaryCard
                  key={run.uuid}
                  run={run}
                  index={index}
                  publishedLabel={getPublishedLabel(run)}
                  summaries={factCheckSummaries[run.uuid] ?? []}
                  isLoading={factCheckSummariesLoading}
                />
              ))
            )}
          </div>
        )}
      </section>

      <section
        id="public-evidence-seekers"
        className="bg-gray-50 border-t border-b border-gray-100 py-16"
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="brand-title text-2xl text-gray-900">
                Featured Evidence Seekers
              </h2>
            </div>
            <Link
              to={isAuthenticated ? "/app/evidence-seekers" : "/register"}
              className="text-sm font-semibold text-primary hover:text-primary-hover"
            >
              Publish yours →
            </Link>
          </div>
          {loading ? (
            <p className="text-gray-400">Loading evidence seekers...</p>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {seekers.length === 0 ? (
                <p className="text-gray-500">
                  No public Evidence Seekers yet. Create the first one!
                </p>
              ) : (
                seekers.map((seeker) => (
                  <EvidenceSeekerCard key={seeker.uuid} seeker={seeker} />
                ))
              )}
            </div>
          )}
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
        <p className="text-sm font-semibold text-primary uppercase tracking-wide">
          Ready to build?
        </p>
        <h2 className="brand-title mt-4 text-3xl text-gray-900">
          Make AI fact-checking part of your workflow
        </h2>
        <p className="mt-3 text-gray-600">
          Upload your own documents, configure the retrieval pipeline, and share
          public results with a single link.
        </p>
        <div className="mt-8 flex flex-wrap gap-4 justify-center">
          <button
            onClick={() => navigate(primaryCtaHref)}
            className="btn-primary px-6 py-3 text-base"
          >
            Create an Evidence Seeker
          </button>
          <Link
            to="/login"
            className="px-6 py-3 rounded-lg border border-gray-300 text-gray-700 font-semibold hover:border-gray-400 transition"
          >
            Sign in to dashboard
          </Link>
        </div>
      </section>
    </PublicLayout>
  );
};

export default PublicHomePage;
