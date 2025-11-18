/**
 * Evidence Seeker configuration console combining pipeline settings and API keys.
 */

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Beaker,
  CheckCircle2,
  FlaskConical,
  Key,
  Loader2,
  RefreshCw,
  Save,
} from "lucide-react";
import { useAPIKeys } from "../../hooks/useConfig";
import { useEvidenceSeekerSettings } from "../../hooks/useEvidenceSeekerSettings";
import { APIKeyManager } from "../Config/APIKeyManager";
import { ConfigurationStatusBadge } from "../Configuration/ConfigurationStatusBadge";
import type { SetupMode } from "../../types/evidenceSeeker";

interface EvidenceSeekerConfigProps {
  evidenceSeekerUuid: string;
}

type EditableSettings = {
  defaultModel: string;
  temperature: string;
  topK: string;
  rerankK: string;
  maxTokens: string;
  language: string;
  embedBackendType: string;
  embedBaseUrl: string;
  embedBillTo: string;
  trustRemoteCode: string;
  metadataFilters: string;
  pipelineOverrides: string;
  huggingfaceApiKeyId: string;
};

const emptySettings: EditableSettings = {
  defaultModel: "",
  temperature: "",
  topK: "",
  rerankK: "",
  maxTokens: "",
  language: "",
  embedBackendType: "huggingface",
  embedBaseUrl: "",
  embedBillTo: "",
  trustRemoteCode: "",
  metadataFilters: "{}",
  pipelineOverrides: "{}",
  huggingfaceApiKeyId: "",
};

const backendOptions: Array<{ value: string; label: string }> = [
  {
    value: "huggingface",
    label: "Hugging Face (download model locally)",
  },
  {
    value: "huggingface_inference_api",
    label: "Hugging Face Inference API",
  },
  {
    value: "tei",
    label: "Text Embeddings Inference (HF TEI endpoint)",
  },
  {
    value: "huggingface_instruct_prefix",
    label: "Hugging Face (Instruct prefix)",
  },
  {
    value: "ollama",
    label: "Ollama",
  },
];

const EvidenceSeekerConfig: React.FC<EvidenceSeekerConfigProps> = ({
  evidenceSeekerUuid,
}) => {
  const {
    settings,
    loading,
    saving,
    error,
    testResult,
    testing,
    testError,
    refresh,
    updateSettings,
    testSettings,
  } = useEvidenceSeekerSettings(evidenceSeekerUuid);

  const [form, setForm] = useState<EditableSettings>(emptySettings);
  const [localError, setLocalError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [modeUpdating, setModeUpdating] = useState(false);
  const shouldSyncRef = useRef(true);
  const {
    apiKeys,
    loading: apiKeysLoading,
    error: apiKeysError,
  } = useAPIKeys(evidenceSeekerUuid);
  const huggingFaceKeys = useMemo(
    () =>
      apiKeys
        .filter((key) => key.provider === "huggingface")
        .map((key) => ({
          id: key.id,
          name: key.name,
          isActive: key.is_active,
        })),
    [apiKeys]
  );
  const currentSetupMode = (settings?.setupMode ?? "SIMPLE") as SetupMode;
  const expertModeEnabled = currentSetupMode === "EXPERT";
  const isReady = settings?.configurationState === "READY";
  const missingRequirements = settings?.missingRequirements ?? [];
  const requirementCopy: Record<string, string> = {
    CREDENTIALS: "Add a Hugging Face API key and billing reference (if required)",
    DOCUMENTS: "Upload at least one document to finish setup",
  };

  useEffect(() => {
    // Ensure new seeker loads fresh data
    shouldSyncRef.current = true;
    setIsDirty(false);
  }, [evidenceSeekerUuid]);

  useEffect(() => {
    if (!settings) {
      setForm(emptySettings);
      setIsDirty(false);
      return;
    }

    const stringifySafe = (value: unknown, fallback: string) => {
      try {
        if (value === undefined || value === null) {
          return fallback;
        }
        return JSON.stringify(value, null, 2);
      } catch {
        return fallback;
      }
    };

    const shouldSync = shouldSyncRef.current || !isDirty;
    if (!shouldSync) {
      return;
    }

    shouldSyncRef.current = false;
    setForm({
      defaultModel: settings.defaultModel ?? "",
      temperature:
        settings.temperature !== null && settings.temperature !== undefined
          ? String(settings.temperature)
          : "",
      topK:
        settings.topK !== null && settings.topK !== undefined
          ? String(settings.topK)
          : "",
      rerankK:
        settings.rerankK !== null && settings.rerankK !== undefined
          ? String(settings.rerankK)
          : "",
      maxTokens:
        settings.maxTokens !== null && settings.maxTokens !== undefined
          ? String(settings.maxTokens)
          : "",
      language: settings.language ?? "",
      embedBackendType: settings.embedBackendType ?? "huggingface",
      embedBaseUrl: settings.embedBaseUrl ?? "",
      embedBillTo: settings.embedBillTo ?? "",
      trustRemoteCode:
        settings.trustRemoteCode === true
          ? "true"
          : settings.trustRemoteCode === false
          ? "false"
          : "",
      metadataFilters: stringifySafe(settings.metadataFilters ?? {}, "{}"),
      pipelineOverrides: stringifySafe(
        settings.pipelineOverrides ?? {},
        "{}"
      ),
      huggingfaceApiKeyId:
        settings.huggingfaceApiKeyId !== null &&
        settings.huggingfaceApiKeyId !== undefined
          ? String(settings.huggingfaceApiKeyId)
          : "",
    });
    setIsDirty(false);
  }, [settings]);

  const handleInputChange = (
    event: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setLocalError(null);
    setSuccessMessage(null);
    setIsDirty(true);
  };

  const handleSetupModeChange = async (nextMode: SetupMode) => {
    setModeUpdating(true);
    setLocalError(null);
    setSuccessMessage(null);
    try {
      await updateSettings({ setupMode: nextMode });
      shouldSyncRef.current = true;
      await refresh();
      setSuccessMessage(
        nextMode === "EXPERT"
          ? "Expert mode enabled. Advanced controls unlocked."
          : "Expert mode disabled. Simple defaults restored."
      );
    } catch (err: any) {
      setLocalError(err?.message ?? "Failed to update setup mode.");
    } finally {
      setModeUpdating(false);
    }
  };

  const parseOptionalNumber = (value: string) => {
    if (!value.trim()) {
      return undefined;
    }
    const parsed = Number(value);
    if (Number.isNaN(parsed)) {
      throw new Error("Numeric fields must contain valid numbers.");
    }
    return parsed;
  };

  const parseJsonField = (label: string, value: string) => {
    if (!value.trim()) {
      return {};
    }
    try {
      const parsed = JSON.parse(value);
      if (parsed === null || typeof parsed !== "object") {
        throw new Error(`${label} must be a JSON object.`);
      }
      return parsed as Record<string, unknown>;
    } catch (err: any) {
      throw new Error(
        `${label} must be valid JSON. ${err?.message ?? "Invalid JSON."}`
      );
    }
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    setLocalError(null);
    setSuccessMessage(null);
    shouldSyncRef.current = true;

    try {
      shouldSyncRef.current = true;
      const metadataFilters = parseJsonField(
        "Metadata filters",
        form.metadataFilters
      );
      const pipelineOverrides = parseJsonField(
        "Pipeline overrides",
        form.pipelineOverrides
      );

      const payload: Record<string, unknown> = {
        default_model: form.defaultModel || null,
        language: form.language || null,
        metadata_filters: metadataFilters,
        pipeline_overrides: pipelineOverrides,
      };
      payload.embed_backend_type =
        form.embedBackendType?.trim() || "huggingface";
      payload.embed_base_url = form.embedBaseUrl.trim()
        ? form.embedBaseUrl.trim()
        : null;
      payload.embed_bill_to = form.embedBillTo.trim()
        ? form.embedBillTo.trim()
        : null;
      if (form.huggingfaceApiKeyId.trim()) {
        const parsedKeyId = Number(form.huggingfaceApiKeyId);
        if (Number.isNaN(parsedKeyId)) {
          throw new Error("Hugging Face API key selection is invalid.");
        }
        payload.huggingface_api_key_id = parsedKeyId;
      } else {
        payload.huggingface_api_key_id = null;
      }

      if (form.trustRemoteCode === "") {
        payload.trust_remote_code = null;
      } else {
        payload.trust_remote_code = form.trustRemoteCode === "true";
      }

      const maybeTemp = parseOptionalNumber(form.temperature);
      if (maybeTemp !== undefined) {
        payload.temperature = maybeTemp;
      } else {
        payload.temperature = null;
      }

      const maybeTopK = parseOptionalNumber(form.topK);
      if (maybeTopK !== undefined) {
        payload.top_k = maybeTopK;
      } else {
        payload.top_k = null;
      }

      const maybeRerank = parseOptionalNumber(form.rerankK);
      if (maybeRerank !== undefined) {
        payload.rerank_k = maybeRerank;
      } else {
        payload.rerank_k = null;
      }

      const maybeMaxTokens = parseOptionalNumber(form.maxTokens);
      if (maybeMaxTokens !== undefined) {
        payload.max_tokens = maybeMaxTokens;
      } else {
        payload.max_tokens = null;
      }

      await updateSettings(payload);
      setSuccessMessage("Configuration updated successfully.");
      setIsDirty(false);
    } catch (err: any) {
      shouldSyncRef.current = false;
      setLocalError(err?.message ?? "Failed to update configuration.");
    }
  };

  const handleTest = async () => {
    setLocalError(null);
    setSuccessMessage(null);
    try {
      const metadataFilters = parseJsonField(
        "Metadata filters",
        form.metadataFilters
      );
      await testSettings({
        metadataFilters,
      });
    } catch (err: any) {
      setLocalError(err?.message ?? "Failed to test configuration.");
    }
  };

  const testFeedback = useMemo(() => {
    if (testing) {
      return (
        <div className="flex items-center text-sm text-blue-600">
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
          Validating configuration…
        </div>
      );
    }
    if (testError) {
      return (
        <div className="text-sm text-red-600">
          Validation failed: {testError}
        </div>
      );
    }
    if (testResult) {
      return (
        <div className="text-sm text-green-600 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" />
          {testResult.detail}
        </div>
      );
    }
    return null;
  }, [testing, testError, testResult]);

  return (
    <div className="space-y-6">
      <section className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-gray-900">
              Configuration status
            </p>
            <p className="text-sm text-gray-600">
              {isReady
                ? "Ready for document ingestion and analysis."
                : "Complete the quick setup steps before using this Evidence Seeker."}
            </p>
            {missingRequirements.length > 0 && (
              <ul className="list-disc list-inside text-xs text-amber-700 mt-2 space-y-1">
                {missingRequirements.map((item) => (
                  <li key={item}>
                    {requirementCopy[item] ??
                      item.replaceAll("_", " ").toLowerCase()}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <ConfigurationStatusBadge state={settings?.configurationState ?? null} />
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-t border-gray-100 pt-4">
          <div className="text-sm text-gray-600">
            {expertModeEnabled
              ? "Expert mode is active. Advanced retrieval overrides are editable below."
              : "Simple mode keeps advanced overrides hidden. Enable expert mode to fine-tune the pipeline."}
          </div>
          <button
            type="button"
            disabled={(!isReady && !expertModeEnabled) || modeUpdating}
            onClick={() =>
              void handleSetupModeChange(expertModeEnabled ? "SIMPLE" : "EXPERT")
            }
            className={`inline-flex items-center justify-center px-4 py-2 rounded-md text-sm font-medium border ${
              expertModeEnabled
                ? "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                : "bg-blue-600 text-white border-blue-600 hover:bg-blue-700"
            } disabled:opacity-50`}
          >
            {modeUpdating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Updating…
              </>
            ) : expertModeEnabled ? (
              "Disable expert mode"
            ) : (
              "Enable expert mode"
            )}
          </button>
        </div>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 space-y-4">
        <header className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Beaker className="h-5 w-5 text-blue-600" />
              EvidenceSeeker Pipeline Settings
            </h2>
            <p className="text-sm text-gray-600">
              Configure retrieval defaults and pipeline overrides for this
              Evidence Seeker.
            </p>
          </div>
          <button
            onClick={() => {
              shouldSyncRef.current = true;
              void refresh();
            }}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-2"
            type="button"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </header>

        {loading && (
          <div className="flex items-center text-sm text-gray-600">
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
            Loading settings…
          </div>
        )}

        {(error || localError) && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700">
            {localError ?? error}
          </div>
        )}

        {successMessage && (
          <div className="bg-green-50 border border-green-200 rounded-md p-3 text-sm text-green-700">
            {successMessage}
          </div>
        )}

        {expertModeEnabled ? (
          <form className="space-y-4" onSubmit={handleSave}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Default model
              </label>
              <input
                type="text"
                name="defaultModel"
                value={form.defaultModel}
                onChange={handleInputChange}
                placeholder="e.g. mistral-embed"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Language
              </label>
              <input
                type="text"
                name="language"
                value={form.language}
                onChange={handleInputChange}
                placeholder="e.g. en"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Top K
              </label>
              <input
                type="number"
                name="topK"
                min={1}
                value={form.topK}
                onChange={handleInputChange}
                placeholder="Default"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Rerank K
              </label>
              <input
                type="number"
                name="rerankK"
                min={1}
                value={form.rerankK}
                onChange={handleInputChange}
                placeholder="Default"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Temperature
              </label>
              <input
                type="number"
                step="0.1"
                name="temperature"
                value={form.temperature}
                onChange={handleInputChange}
                placeholder="Default"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max tokens
              </label>
              <input
                type="number"
                min={1}
                name="maxTokens"
                value={form.maxTokens}
                onChange={handleInputChange}
                placeholder="Default"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Embedding backend
              </label>
              <select
                name="embedBackendType"
                value={form.embedBackendType}
                onChange={handleInputChange}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                {backendOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Embedding base URL
              </label>
              <input
                type="text"
                name="embedBaseUrl"
                value={form.embedBaseUrl}
                onChange={handleInputChange}
                placeholder="https://api-inference.huggingface.co/models/..."
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Required for Hugging Face Inference API or TEI backends.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Billing organisation (optional)
              </label>
              <input
                type="text"
                name="embedBillTo"
                value={form.embedBillTo}
                onChange={handleInputChange}
                placeholder="hf_organisation"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Hugging Face API key
              </label>
              <select
                name="huggingfaceApiKeyId"
                value={form.huggingfaceApiKeyId}
                onChange={handleInputChange}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="">None</option>
                {huggingFaceKeys.map((key) => (
                  <option
                    key={key.id}
                    value={key.id}
                    disabled={!key.isActive}
                  >
                    {key.name}
                    {!key.isActive ? " (inactive)" : ""}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Select a stored Hugging Face provider key. Manage keys in the
                API Keys section below.
              </p>
              {apiKeysLoading && (
                <p className="text-xs text-gray-500 mt-1">Loading keys…</p>
              )}
              {apiKeysError && (
                <p className="text-xs text-red-600 mt-1">
                  Failed to load API keys: {apiKeysError}
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Trust remote code
              </label>
              <select
                name="trustRemoteCode"
                value={form.trustRemoteCode}
                onChange={handleInputChange}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="">Use model defaults</option>
                <option value="true">Enable</option>
                <option value="false">Disable</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Metadata filters (JSON)
            </label>
            <textarea
              name="metadataFilters"
              value={form.metadataFilters}
              onChange={handleInputChange}
              rows={4}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
            />
            <p className="text-xs text-gray-500 mt-1">
              These filters are applied to every retrieval request to scope the
              index.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Pipeline overrides (JSON)
            </label>
            <textarea
              name="pipelineOverrides"
              value={form.pipelineOverrides}
              onChange={handleInputChange}
              rows={4}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
            />
            <p className="text-xs text-gray-500 mt-1">
              Advanced overrides forwarded to the EvidenceSeeker pipeline
              factory.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
            <button
              type="submit"
              disabled={saving}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save settings
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => void handleTest()}
              className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <FlaskConical className="h-4 w-4" />
              Test configuration
            </button>
            {testFeedback}
          </div>
          </form>
        ) : (
          <div className="border border-dashed border-gray-300 rounded-lg p-6 bg-gray-50 text-sm text-gray-600">
            <p className="font-medium text-gray-900 mb-2">
              Expert mode is disabled
            </p>
            <p>
              Advanced pipeline overrides are hidden while simple mode is active.
              Use the API Keys section below to manage credentials. Enable expert
              mode once setup is complete to edit retrieval parameters.
            </p>
          </div>
        )}
      </section>

      <section className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 space-y-4">
        <header>
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Key className="h-5 w-5 text-blue-600" />
            API Keys
          </h2>
          <p className="text-sm text-gray-600">
            Manage provider credentials used by this Evidence Seeker.
          </p>
        </header>
        <APIKeyManager evidenceSeekerUuid={evidenceSeekerUuid} />
      </section>
    </div>
  );
};

export default EvidenceSeekerConfig;
