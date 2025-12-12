import React, { useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate } from "react-router";
import { KeyRound, CheckCircle2 } from "lucide-react";
import {
  ConfigurationStatus,
  EvidenceSeeker,
  EvidenceSeekerCreate,
  EvidenceSeekerUpdate,
} from "../../types/evidenceSeeker";
import { useEvidenceSeekers } from "../../hooks/useEvidenceSeeker";
import PageLayout from "../PageLayout";
import { useConfigurationStatus } from "../../hooks/useConfigurationStatus";
import WizardDocumentStep from "./Wizard/WizardDocumentStep";
import apiClient, { evidenceSeekerAPI } from "../../utils/api";
import { useAuth } from "../../hooks/useAuth";
import {
  DEFAULT_LANGUAGE,
  SUPPORTED_LANGUAGES,
} from "../../constants/languages";

interface EvidenceSeekerFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

const steps = [
  { id: 0, label: "Describe Evidence Seeker" },
  { id: 1, label: "Connect inference" },
  { id: 2, label: "Upload documents" },
  { id: 3, label: "Review & finish" },
];

const WIZARD_API_KEY_NAME = "Onboarding key";

type WizardDetailsState = {
  title: string;
  description: string;
  isPublic: boolean;
  language: string;
};

interface WizardDraftStorage {
  step: number;
  details: WizardDetailsState;
  credentialsBillTo?: string;
  credentialsApiKey?: string;
  wizardSeeker: EvidenceSeeker | null;
  onboardingToken: string | null;
  skipAcknowledged: boolean;
  documentRequirementMet: boolean;
  appliedBillTo?: string;
  appliedApiKey?: string;
}

const EvidenceSeekerForm: React.FC<EvidenceSeekerFormProps> = ({
  onSuccess,
  onCancel,
}) => {
  const debugWizard = import.meta.env.DEV;
  const wizardLog = (...args: unknown[]) => {
    if (!debugWizard) return;
    console.log("[wizard]", ...args);
  };

  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    createEvidenceSeeker,
    updateEvidenceSeeker,
    finishOnboarding: completeOnboarding,
    skipDocuments: acknowledgeSkip,
  } = useEvidenceSeekers();
  const draftKey = useMemo(
    () => (user ? `wizard-draft:${user.id}` : null),
    [user?.id]
  );

  const [step, setStep] = useState(0);
  const [provisioning, setProvisioning] = useState(false);
  const [finishLoading, setFinishLoading] = useState(false);
  const [statusPolling, setStatusPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [finishError, setFinishError] = useState<string | null>(null);

  const normaliseDetails = useCallback(
    (value?: Partial<WizardDetailsState>): WizardDetailsState => ({
      title: value?.title ?? "",
      description: value?.description ?? "",
      isPublic: value?.isPublic ?? false,
      language: value?.language ?? DEFAULT_LANGUAGE,
    }),
    []
  );

  const [details, setDetails] = useState<WizardDetailsState>(() =>
    normaliseDetails()
  );
  const [credentials, setCredentials] = useState<{
    apiKeyValue: string;
    billTo: string | undefined;
  }>({
    apiKeyValue: "",
    billTo: "",
  });
  const [detailErrors, setDetailErrors] = useState<Record<string, string>>({});
  const [credentialErrors, setCredentialErrors] = useState<
    Record<string, string>
  >({});
  const [wizardSeeker, setWizardSeeker] = useState<EvidenceSeeker | null>(null);
  const [onboardingToken, setOnboardingToken] = useState<string | null>(null);
  const [documentRequirementMet, setDocumentRequirementMet] = useState(false);
  const [skipAcknowledged, setSkipAcknowledged] = useState(false);
  const [appliedCredentials, setAppliedCredentials] = useState<{
    apiKeyValue: string;
    billTo: string | undefined;
  }>(() => ({
    apiKeyValue: "",
    billTo: "",
  }));
  const [draftHydrated, setDraftHydrated] = useState(false);
  const { status: wizardStatus } = useConfigurationStatus(wizardSeeker?.uuid);
  const clearDraft = useCallback(() => {
    if (!draftKey || typeof window === "undefined") {
      return;
    }
    wizardLog("clearing draft", draftKey);
    window.sessionStorage.removeItem(draftKey);
  }, [draftKey]);

  useEffect(() => {
    wizardLog("mount");
    return () => wizardLog("unmount");
  }, []);

  useEffect(() => {
    wizardLog("step change", { step });
  }, [step]);

  useEffect(() => {
    if (!draftKey || typeof window === "undefined") {
      return;
    }
    const stored = window.sessionStorage.getItem(draftKey);
    if (!stored) {
      return;
    }
    try {
      const parsed = JSON.parse(stored) as WizardDraftStorage;
      wizardLog("hydrating from draft", {
        step: parsed.step,
        hasSeeker: Boolean(parsed.wizardSeeker),
        apiKeyLen: parsed.credentialsApiKey?.length ?? 0,
      });
      if (typeof parsed.step === "number") {
        setStep(Math.min(Math.max(parsed.step, 0), steps.length - 1));
      }
      if (parsed.details) {
        setDetails(normaliseDetails(parsed.details));
      }
      if (typeof parsed.credentialsApiKey === "string") {
        setCredentials((prev) => ({
          ...prev,
          apiKeyValue: parsed.credentialsApiKey ?? prev.apiKeyValue,
        }));
      }
      if (typeof parsed.credentialsBillTo === "string") {
        setCredentials((prev) => ({
          ...prev,
          billTo: parsed.credentialsBillTo,
        }));
      }
      if (parsed.wizardSeeker) {
        setWizardSeeker(parsed.wizardSeeker);
      }
      if (parsed.onboardingToken !== undefined) {
        setOnboardingToken(parsed.onboardingToken);
      }
      if (typeof parsed.skipAcknowledged === "boolean") {
        setSkipAcknowledged(parsed.skipAcknowledged);
      }
      if (typeof parsed.documentRequirementMet === "boolean") {
        setDocumentRequirementMet(parsed.documentRequirementMet);
      }
      if (typeof parsed.appliedBillTo === "string") {
        setAppliedCredentials({
          apiKeyValue: parsed.appliedApiKey ?? "",
          billTo: parsed.appliedBillTo,
        });
      }
      if (
        typeof parsed.appliedApiKey === "string" &&
        typeof parsed.appliedBillTo !== "string"
      ) {
        setAppliedCredentials((prev) => ({
          ...prev,
          apiKeyValue: parsed.appliedApiKey ?? prev.apiKeyValue,
        }));
      }
    } catch (err) {
      console.warn("Failed to restore wizard draft", err);
    } finally {
      setDraftHydrated(true);
      wizardLog("draft hydration complete");
    }
  }, [draftKey]);

  useEffect(() => {
    if (!draftHydrated) {
      return;
    }
    if (!draftKey || typeof window === "undefined") {
      return;
    }
    const payload: WizardDraftStorage = {
      step,
      details,
      credentialsBillTo: credentials.billTo,
      credentialsApiKey: credentials.apiKeyValue,
      wizardSeeker: wizardSeeker ?? null,
      onboardingToken: onboardingToken ?? null,
      skipAcknowledged,
      documentRequirementMet,
      appliedBillTo: appliedCredentials.billTo,
      appliedApiKey: appliedCredentials.apiKeyValue,
    };
    try {
      wizardLog("persisting draft", {
        step,
        titleLen: details.title.length,
        descLen: details.description.length,
        apiKeyLen: credentials.apiKeyValue.length,
        hasSeeker: Boolean(wizardSeeker),
      });
      window.sessionStorage.setItem(draftKey, JSON.stringify(payload));
    } catch (err) {
      console.warn("Failed to persist wizard draft", err);
    }
  }, [
    draftKey,
    step,
    details,
    credentials.billTo,
    credentials.apiKeyValue,
    wizardSeeker,
    onboardingToken,
    skipAcknowledged,
    documentRequirementMet,
    appliedCredentials.billTo,
    appliedCredentials.apiKeyValue,
    draftHydrated,
  ]);

  useEffect(() => {
    if (wizardStatus?.documentSkipAcknowledged !== undefined) {
      setSkipAcknowledged(wizardStatus.documentSkipAcknowledged);
    }
  }, [wizardStatus?.documentSkipAcknowledged]);

  const validateDetails = () => {
    const errors: Record<string, string> = {};
    if (!details.title.trim()) {
      errors.title = "Title is required.";
    } else if (details.title.length > 100) {
      errors.title = "Title must be 100 characters or fewer.";
    }
    if (details.description.length > 500) {
      errors.description = "Description must be 500 characters or fewer.";
    }
    const supportedLanguageValues = SUPPORTED_LANGUAGES.map(
      (option) => option.value
    );
    if (
      !details.language ||
      !supportedLanguageValues.includes(details.language as any)
    ) {
      errors.language = "Select a supported language.";
    }
    setDetailErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const validateCredentials = () => {
    const errors: Record<string, string> = {};
    if (!credentials.apiKeyValue.trim()) {
      errors.apiKeyValue = "Paste your Hugging Face API key.";
    } else if (!credentials.apiKeyValue.trim().startsWith("hf_")) {
      errors.apiKeyValue = "Hugging Face keys typically start with hf_.";
    }
    setCredentialErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleNext = async () => {
    if (step === 0) {
      if (!validateDetails()) {
        return;
      }
      setStep(1);
      return;
    }
    if (step === 1) {
      const success = await ensureSeekerProvisioned();
      if (success) {
        setStep(2);
      }
      return;
    }
    if (step === 2) {
      if (!documentRequirementMet && !skipAcknowledged) {
        setError("Upload at least one document or confirm the skip option.");
        return;
      }
      setError(null);
      setStep(3);
    }
  };

  const handleBack = () => {
    setStep((prev) => Math.max(prev - 1, 0));
  };

  const summary = useMemo(
    () => [
      { label: "Title", value: details.title },
      { label: "Description", value: details.description || "—" },
      {
        label: "Language",
        value:
          SUPPORTED_LANGUAGES.find(
            (option) => option.value === details.language
          )?.label ||
          details.language ||
          "—",
      },
      { label: "Visibility", value: details.isPublic ? "Public" : "Private" },
      { label: "Billing reference", value: credentials.billTo || "—" },
      {
        label: "Documents",
        value: skipAcknowledged
          ? "Will add later"
          : documentRequirementMet
            ? "At least one uploaded"
            : "Pending upload",
      },
    ],
    [details, credentials, skipAcknowledged, documentRequirementMet]
  );

  const snapshotCredentials = () => ({
    apiKeyValue: credentials.apiKeyValue,
    billTo: credentials.billTo,
  });

  const persistBasicDetails = async (seekerRecord: EvidenceSeeker) => {
    const updates: EvidenceSeekerUpdate = {};
    if (details.title.trim() && details.title.trim() !== seekerRecord.title) {
      updates.title = details.title.trim();
    }
    if ((details.description || "") !== (seekerRecord.description ?? "")) {
      updates.description = details.description.trim();
    }
    if (details.isPublic !== seekerRecord.isPublic) {
      updates.isPublic = details.isPublic;
    }
    const normalizedLanguage = details.language || null;
    if ((seekerRecord.language ?? null) !== normalizedLanguage) {
      updates.language = normalizedLanguage;
    }
    if (Object.keys(updates).length === 0) {
      return;
    }
    await updateEvidenceSeeker(seekerRecord.id, updates);
    setWizardSeeker((prev) => (prev ? { ...prev, ...updates } : prev));
  };

  const rotateCredentialsIfNeeded = async (seekerRecord: EvidenceSeeker) => {
    const valueChanged =
      appliedCredentials.apiKeyValue !== credentials.apiKeyValue;
    const billToChanged = appliedCredentials.billTo !== credentials.billTo;

    if (!valueChanged && !billToChanged) {
      return;
    }

    if (valueChanged) {
      const response = await apiClient.post(
        `/config/${seekerRecord.uuid}/api-keys`,
        {
          provider: "huggingface",
          name: WIZARD_API_KEY_NAME,
          api_key: credentials.apiKeyValue.trim(),
          description: "Wizard credential",
        }
      );
      const keyId = response.data?.id;
      if (!keyId) {
        throw new Error("Failed to store API key.");
      }
      await evidenceSeekerAPI.updateSettings(seekerRecord.uuid, {
        huggingfaceApiKeyId: keyId,
        embedBillTo: credentials.billTo?.trim() || undefined,
      });
    } else if (billToChanged) {
      await evidenceSeekerAPI.updateSettings(seekerRecord.uuid, {
        embedBillTo: credentials.billTo?.trim() || undefined,
      });
    }
    setAppliedCredentials(snapshotCredentials());
  };

  const ensureSeekerProvisioned = async (): Promise<boolean> => {
    if (!validateDetails() || !validateCredentials()) {
      return false;
    }
    setProvisioning(true);
    setError(null);
    try {
      if (!wizardSeeker) {
        const payload: EvidenceSeekerCreate = {
          title: details.title.trim(),
          description: details.description.trim(),
          isPublic: details.isPublic,
          language: details.language,
          initialConfiguration: {
            apiKeyName: WIZARD_API_KEY_NAME,
            apiKeyValue: credentials.apiKeyValue.trim(),
            billTo: credentials.billTo?.trim() || undefined,
            setupMode: "SIMPLE",
          },
        };
        const created = await createEvidenceSeeker(payload);
        if (!created) {
          throw new Error("Failed to create Evidence Seeker.");
        }
        setWizardSeeker(created);
        setOnboardingToken(created.onboardingToken ?? null);
        setSkipAcknowledged(created.documentSkipAcknowledged ?? false);
        setAppliedCredentials(snapshotCredentials());
        return true;
      }
      await persistBasicDetails(wizardSeeker);
      await rotateCredentialsIfNeeded(wizardSeeker);
      return true;
    } catch (err: any) {
      setError(err?.message ?? "Failed to save configuration.");
      return false;
    } finally {
      setProvisioning(false);
    }
  };

  const handleSkipDocuments = async () => {
    if (!wizardSeeker) {
      throw new Error("Create the Evidence Seeker before skipping documents.");
    }
    const status = await acknowledgeSkip(wizardSeeker.uuid);
    setSkipAcknowledged(status.documentSkipAcknowledged);
    return status;
  };

  const delay = (ms: number) =>
    new Promise((resolve) => {
      setTimeout(resolve, ms);
    });

  const waitForReady = async (): Promise<ConfigurationStatus | null> => {
    if (!wizardSeeker) {
      return null;
    }
    setStatusPolling(true);
    try {
      for (let attempt = 0; attempt < 12; attempt += 1) {
        const status = await evidenceSeekerAPI.getConfigurationStatus(
          wizardSeeker.uuid
        );
        if (status.isReady) {
          return status;
        }
        await delay(5000);
      }
      throw new Error(
        "Documents are still processing. Give it a moment and try finishing again."
      );
    } finally {
      setStatusPolling(false);
    }
  };

  const handleFinish = async () => {
    if (!wizardSeeker) {
      return;
    }
    setFinishError(null);
    setFinishLoading(true);
    try {
      await completeOnboarding(wizardSeeker.uuid);
      clearDraft();
      if (skipAcknowledged) {
        navigate(`/app/evidence-seekers/${wizardSeeker.uuid}/manage/documents`);
        onSuccess?.();
        return;
      }
      await waitForReady();
      navigate(
        `/app/evidence-seekers/${wizardSeeker.uuid}/manage/fact-checks`,
        {
          state: { showOnboardingHint: true },
        }
      );
      onSuccess?.();
    } catch (err: any) {
      setFinishError(err?.message ?? "Failed to finish onboarding.");
    } finally {
      setFinishLoading(false);
    }
  };

  return (
    <PageLayout variant="narrow">
      <div className="bg-white shadow-sm rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="brand-title text-xl text-gray-900">
            Guided Evidence Seeker setup
          </h2>
          <p className="text-sm text-gray-600">
            Three quick steps to make your Evidence Seeker upload-ready.
          </p>
        </div>

        <div className="px-6 py-4 border-b border-gray-200">
          <ol className="flex items-center gap-3">
            {steps.map((item, index) => (
              <li key={item.id} className="flex items-center gap-2">
                <div
                  className={`h-8 w-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    index === step
                      ? "bg-primary text-white"
                      : index < step
                        ? "bg-primary-soft text-primary-strong"
                        : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {index + 1}
                </div>
                <span
                  className={`text-sm ${
                    index === step
                      ? "text-gray-900 font-medium"
                      : "text-gray-500"
                  }`}
                >
                  {item.label}
                </span>
                {index < steps.length - 1 && (
                  <div className="h-px w-6 bg-gray-200" />
                )}
              </li>
            ))}
          </ol>
        </div>

        <div className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4 text-sm text-red-800">
              {error}
            </div>
          )}

          {step === 0 && (
            <section className="space-y-4">
              <div>
                <label
                  htmlFor="title"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  What should we call this Evidence Seeker?
                </label>
                <input
                  type="text"
                  id="title"
                  value={details.title}
                  onChange={(event) =>
                    setDetails((prev) => ({
                      ...prev,
                      title: event.target.value,
                    }))
                  }
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary ${
                    detailErrors.title ? "border-red-300" : "border-gray-300"
                  }`}
                  placeholder="e.g. Climate Policy Evidence Seeker"
                />
                {detailErrors.title && (
                  <p className="text-sm text-red-600 mt-1">
                    {detailErrors.title}
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  {details.title.length}/100 characters
                </p>
              </div>

              <div>
                <label
                  htmlFor="description"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Short description
                </label>
                <textarea
                  id="description"
                  value={details.description}
                  onChange={(event) =>
                    setDetails((prev) => ({
                      ...prev,
                      description: event.target.value,
                    }))
                  }
                  rows={4}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary ${
                    detailErrors.description
                      ? "border-red-300"
                      : "border-gray-300"
                  }`}
                  placeholder="Describe the corpus or topic this Evidence Seeker will focus on."
                />
                {detailErrors.description && (
                  <p className="text-sm text-red-600 mt-1">
                    {detailErrors.description}
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  {details.description.length}/500 characters
                </p>
              </div>

              <div>
                <label
                  htmlFor="language"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Primary language
                </label>
                <select
                  id="language"
                  value={details.language}
                  onChange={(event) =>
                    setDetails((prev) => ({
                      ...prev,
                      language: event.target.value,
                    }))
                  }
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary ${
                    detailErrors.language ? "border-red-300" : "border-gray-300"
                  }`}
                >
                  {SUPPORTED_LANGUAGES.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {detailErrors.language && (
                  <p className="text-sm text-red-600 mt-1">
                    {detailErrors.language}
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  Determines which language is sent to preprocessing.
                </p>
              </div>

              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  id="isPublic"
                  checked={details.isPublic}
                  onChange={(event) =>
                    setDetails((prev) => ({
                      ...prev,
                      isPublic: event.target.checked,
                    }))
                  }
                  className="mt-1 h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary"
                />
                <div>
                  <label
                    htmlFor="isPublic"
                    className="text-sm font-medium text-gray-900"
                  >
                    Make this Evidence Seeker public
                  </label>
                  <p className="text-sm text-gray-600">
                    Public seekers can be browsed and tested by anyone with the
                    link.
                  </p>
                </div>
              </div>
            </section>
          )}

          {step === 1 && (
            <section className="space-y-5">
              <div className="rounded-lg border border-primary-border bg-primary-soft p-4 text-sm text-primary-strong flex items-start gap-3">
                <KeyRound className="h-5 w-5 mt-1" />
                <div>
                  <p className="font-medium">
                    Connect Hugging Face credentials
                  </p>
                  <p>
                    We store this key encrypted and use it to run embeddings and
                    inference. You can rotate or remove it at any time.
                  </p>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Hugging Face API key
                </label>
                <input
                  type="password"
                  value={credentials.apiKeyValue}
                  onChange={(event) =>
                    setCredentials((prev) => ({
                      ...prev,
                      apiKeyValue: event.target.value,
                    }))
                  }
                  className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-primary ${
                    credentialErrors.apiKeyValue
                      ? "border-red-300"
                      : "border-gray-300"
                  }`}
                  placeholder="hf_..."
                />
                {credentialErrors.apiKeyValue && (
                  <p className="text-sm text-red-600 mt-1">
                    {credentialErrors.apiKeyValue}
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  Required for embeddings and inference. We encrypt it at rest.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Billing reference (optional)
                </label>
                <input
                  type="text"
                  value={credentials.billTo}
                  onChange={(event) =>
                    setCredentials((prev) => ({
                      ...prev,
                      billTo: event.target.value,
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary"
                  placeholder="hf_organisation"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Only needed if you track usage by organization.
                </p>
              </div>
            </section>
          )}

          {step === 2 && (
            <section className="space-y-4">
              {wizardSeeker ? (
                <WizardDocumentStep
                  evidenceSeekerUuid={wizardSeeker.uuid}
                  onboardingToken={onboardingToken ?? undefined}
                  skipAcknowledged={skipAcknowledged}
                  onRequirementChange={setDocumentRequirementMet}
                  onSkipDocuments={handleSkipDocuments}
                />
              ) : (
                <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  Complete the previous steps to unlock document uploads.
                </div>
              )}
            </section>
          )}

          {step === 3 && (
            <section className="space-y-4">
              <div className="rounded-lg border border-green-100 bg-green-50 p-4 text-sm text-green-900 flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 mt-1" />
                <div>
                  <p className="font-medium">Review & confirm</p>
                  <p>
                    We will create the Evidence Seeker and store your API key
                    securely. You can fine-tune settings later from the
                    configuration tab.
                  </p>
                </div>
              </div>
              {wizardStatus && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="border border-gray-200 rounded-lg p-4">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      Inference credentials
                    </p>
                    <p className="text-sm text-gray-900 mt-1">
                      {wizardStatus.missingRequirements.includes("CREDENTIALS")
                        ? "Pending verification"
                        : "Connected"}
                    </p>
                  </div>
                  <div className="border border-gray-200 rounded-lg p-4">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      Document uploads
                    </p>
                    <p className="text-sm text-gray-900 mt-1">
                      {skipAcknowledged
                        ? "Skipping for now"
                        : documentRequirementMet
                          ? "At least one uploaded"
                          : "Waiting for uploads"}
                    </p>
                  </div>
                </div>
              )}
              <dl className="grid grid-cols-1 gap-4">
                {summary.map((item) => (
                  <div
                    key={item.label}
                    className="border border-gray-200 rounded-lg p-4 bg-gray-50"
                  >
                    <dt className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                      {item.label}
                    </dt>
                    <dd className="text-sm text-gray-900 mt-1">
                      {item.value || "—"}
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          <div className="flex flex-col-reverse sm:flex-row sm:justify-between gap-3 pt-4 border-t border-gray-100">
            <div className="flex gap-2">
              {onCancel && (
                <button
                  type="button"
                  onClick={onCancel}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  Cancel
                </button>
              )}
              {step > 0 && (
                <button
                  type="button"
                  onClick={handleBack}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  Back
                </button>
              )}
            </div>
            <div className="flex gap-2">
              {step < steps.length - 1 && (
                <button
                  type="button"
                  onClick={() => {
                    void handleNext();
                  }}
                  disabled={
                    (step === 1 && provisioning) ||
                    (step === 2 && !documentRequirementMet && !skipAcknowledged)
                  }
                  className="btn-primary px-4 py-2 text-sm disabled:opacity-60"
                >
                  {step === 2 ? "Review setup" : "Continue"}
                </button>
              )}
              {step === steps.length - 1 && (
                <button
                  type="button"
                  onClick={() => {
                    void handleFinish();
                  }}
                  disabled={finishLoading || statusPolling}
                  className="btn-primary px-4 py-2 text-sm disabled:opacity-50"
                >
                  {finishLoading || statusPolling
                    ? "Finalizing…"
                    : skipAcknowledged
                      ? "Finish with missing documents"
                      : "Finish setup"}
                </button>
              )}
            </div>
          </div>
          {finishError && (
            <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {finishError}
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
};

export default EvidenceSeekerForm;
