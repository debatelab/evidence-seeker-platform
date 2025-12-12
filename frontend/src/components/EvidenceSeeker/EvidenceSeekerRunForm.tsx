import React, { useState } from "react";
import { useNavigate } from "react-router";
import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
  Play,
} from "lucide-react";
import { useEvidenceSeekerRuns } from "../../hooks/useEvidenceSeekerRuns";
import { useConfigurationStatus } from "../../hooks/useConfigurationStatus";
import { ConfigurationBlockedNotice } from "../Configuration/ConfigurationBlockedNotice";

interface EvidenceSeekerRunFormProps {
  evidenceSeekerUuid?: string;
  showHeader?: boolean;
  navigateOnCreate?: boolean;
  onRunCreated?: (runUuid: string) => void;
}

const numberFromInput = (value: string): number | undefined => {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    throw new Error("Must be a valid number.");
  }
  return parsed;
};

const parseMetadataFilters = (
  input: string
): Record<string, unknown> | undefined => {
  if (!input.trim()) return undefined;
  const parsed = JSON.parse(input);
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Metadata filters must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
};

const EvidenceSeekerRunForm: React.FC<EvidenceSeekerRunFormProps> = ({
  evidenceSeekerUuid,
  showHeader = true,
  navigateOnCreate = true,
  onRunCreated,
}) => {
  const navigate = useNavigate();
  const {
    creating,
    error,
    createRun,
  } = useEvidenceSeekerRuns(evidenceSeekerUuid);
  const {
    status: configurationStatus,
    loading: statusLoading,
    error: statusError,
  } = useConfigurationStatus(evidenceSeekerUuid ?? "");
  const isConfigured = configurationStatus?.isReady ?? false;

  const [statement, setStatement] = useState("");
  const [topK, setTopK] = useState("");
  const [temperature, setTemperature] = useState("");
  const [maxTokens, setMaxTokens] = useState("");
  const [language, setLanguage] = useState("");
  const [metadataFiltersRaw, setMetadataFiltersRaw] = useState("");
  const [documentUuidsRaw, setDocumentUuidsRaw] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const resetForm = () => {
    setStatement("");
    setTopK("");
    setTemperature("");
    setMaxTokens("");
    setLanguage("");
    setMetadataFiltersRaw("");
    setDocumentUuidsRaw("");
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!statement.trim()) {
      setFormError("Enter a statement to fact-check.");
      return;
    }

    const overrides: Record<string, unknown> = {};

    try {
      const maybeTopK = numberFromInput(topK);
      if (typeof maybeTopK === "number") {
        overrides.top_k = maybeTopK;
      }
    } catch (err) {
      setFormError("Top K must be numeric.");
      return;
    }

    try {
      const maybeMaxTokens = numberFromInput(maxTokens);
      if (typeof maybeMaxTokens === "number") {
        overrides.max_tokens = maybeMaxTokens;
      }
    } catch (err) {
      setFormError("Max tokens must be numeric.");
      return;
    }

    try {
      const maybeTemperature = numberFromInput(temperature);
      if (typeof maybeTemperature === "number") {
        overrides.temperature = maybeTemperature;
      }
    } catch (err) {
      setFormError("Temperature must be numeric.");
      return;
    }

    if (language.trim()) {
      overrides.language = language.trim();
    }

    let metadataFilters: Record<string, unknown> | undefined;
    try {
      metadataFilters = parseMetadataFilters(metadataFiltersRaw);
    } catch (err: any) {
      setFormError(err?.message ?? "Invalid metadata filters.");
      return;
    }

    if (documentUuidsRaw.trim()) {
      const ids = documentUuidsRaw
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
      if (ids.length > 0) {
        metadataFilters = {
          ...(metadataFilters ?? {}),
          document_uuid: ids,
        };
      }
    }

    if (metadataFilters && Object.keys(metadataFilters).length > 0) {
      overrides.metadata_filters = metadataFilters;
    }

    const payloadOverrides =
      Object.keys(overrides).length > 0 ? overrides : undefined;

    try {
      const run = await createRun({
        statement: statement.trim(),
        overrides: payloadOverrides,
      });
      if (run) {
        setFormError(null);
        resetForm();
        onRunCreated?.(run.uuid);
        if (navigateOnCreate && evidenceSeekerUuid) {
          navigate(
            `/app/evidence-seekers/${evidenceSeekerUuid}/manage/fact-checks/${run.uuid}`
          );
        }
      }
    } catch (err: any) {
      setFormError(err?.message ?? "Failed to create fact-check run.");
    }
  };

  if (statusLoading) {
    return (
      <div className="flex justify-center items-center p-10">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
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

  if (!isConfigured) {
    return (
      <ConfigurationBlockedNotice
        status={configurationStatus}
        onConfigure={() =>
          navigate(
            `/app/evidence-seekers/${evidenceSeekerUuid}/manage/settings`
          )
        }
        description="Complete configuration before submitting or rerunning fact-check jobs."
      />
    );
  }

  return (
    <section className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 space-y-4">
      {showHeader && (
        <header>
          <h2 className="brand-title text-lg text-gray-900">
            Run a Fact Check
          </h2>
          <p className="text-sm text-gray-600">
            Submit a claim to verify against this Evidence Seeker.
          </p>
        </header>
      )}

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Statement
          </label>
          <textarea
            value={statement}
            onChange={(event) => setStatement(event.target.value)}
            rows={3}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="Enter the claim you want to verify…"
            required
          />
        </div>

        <button
          type="button"
          onClick={() => setAdvancedOpen((prev) => !prev)}
          className="flex items-center text-sm text-primary hover:text-primary-strong"
        >
          {advancedOpen ? (
            <ChevronUp className="h-4 w-4 mr-1" />
          ) : (
            <ChevronDown className="h-4 w-4 mr-1" />
          )}
          Advanced overrides
        </button>

        {advancedOpen && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border border-gray-200 rounded-lg p-4 bg-gray-50">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Top K
              </label>
              <input
                type="number"
                min={1}
                value={topK}
                onChange={(event) => setTopK(event.target.value)}
                placeholder="e.g. 10"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Temperature
              </label>
              <input
                type="number"
                step="0.1"
                value={temperature}
                onChange={(event) => setTemperature(event.target.value)}
                placeholder="e.g. 0.2"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max tokens
              </label>
              <input
                type="number"
                min={1}
                value={maxTokens}
                onChange={(event) => setMaxTokens(event.target.value)}
                placeholder="e.g. 1200"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Language
              </label>
              <input
                type="text"
                value={language}
                onChange={(event) => setLanguage(event.target.value)}
                placeholder="e.g. en"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Metadata filters (JSON)
              </label>
              <textarea
                value={metadataFiltersRaw}
                onChange={(event) => setMetadataFiltersRaw(event.target.value)}
                rows={3}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder='{"topic": "climate"}'
              />
              <p className="text-xs text-gray-500 mt-1">
                Overrides merge with the seeker’s default metadata filters.
              </p>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Restrict to document UUIDs (comma separated)
              </label>
              <input
                type="text"
                value={documentUuidsRaw}
                onChange={(event) => setDocumentUuidsRaw(event.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="uuid-1, uuid-2"
              />
            </div>
          </div>
        )}

        {(formError || error) && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            <span>{formError ?? error}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <button
            type="submit"
            disabled={creating}
            className="btn-primary px-4 py-2 flex items-center gap-2 justify-center disabled:opacity-50"
          >
            {creating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Starting run…</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                <span>Run Fact Check</span>
              </>
            )}
          </button>
          <button
            type="button"
            onClick={resetForm}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Clear fields
          </button>
        </div>
      </form>
    </section>
  );
};

export default EvidenceSeekerRunForm;
