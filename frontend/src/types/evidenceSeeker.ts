export type ConfigurationState =
  | "UNCONFIGURED"
  | "MISSING_CREDENTIALS"
  | "MISSING_DOCUMENTS"
  | "READY"
  | "ERROR";

export type SetupMode = "SIMPLE" | "EXPERT";
export type FactCheckPublicationMode = "AUTOPUBLISH" | "MANUAL";

export interface ConfigurationStatus {
  state: ConfigurationState;
  setupMode: SetupMode;
  configuredAt: string | null;
  missingRequirements: string[];
  isReady: boolean;
  documentSkipAcknowledged: boolean;
}

export interface EvidenceSeeker {
  id: number;
  uuid: string; // External API identifier
  title: string;
  description: string;
  language?: string | null;
  logoUrl: string | null;
  isPublic: boolean;
  factCheckPublicationMode: FactCheckPublicationMode;
  publishedAt?: string | null;
  createdBy: number;
  createdAt: string;
  updatedAt: string;
  configurationState?: ConfigurationState | null;
  missingRequirements?: string[];
  configuredAt?: string | null;
  setupMode?: SetupMode | null;
  documentSkipAcknowledged?: boolean;
  onboardingToken?: string | null;
}

export interface EvidenceSeekerInitialConfiguration {
  apiKeyName: string;
  apiKeyValue: string;
  billTo?: string;
  setupMode?: SetupMode;
}

export interface EvidenceSeekerCreate {
  title: string;
  description: string;
  isPublic?: boolean;
  factCheckPublicationMode?: FactCheckPublicationMode;
  language?: string;
  initialConfiguration?: EvidenceSeekerInitialConfiguration;
}

export interface EvidenceSeekerUpdate {
  title?: string;
  description?: string;
  isPublic?: boolean;
  factCheckPublicationMode?: FactCheckPublicationMode;
  language?: string | null;
}

export interface EvidenceSeekerSettings {
  evidenceSeekerId: number;
  defaultModel?: string | null;
  temperature?: number | null;
  topK?: number | null;
  rerankK?: number | null;
  maxTokens?: number | null;
  language?: string | null;
  embedBackendType: string;
  embedBaseUrl?: string | null;
  embedBillTo?: string | null;
  trustRemoteCode?: boolean | null;
  metadataFilters: Record<string, unknown>;
  pipelineOverrides?: Record<string, unknown> | null;
  huggingfaceApiKeyId?: number | null;
  lastValidatedAt?: string | null;
  updatedAt?: string | null;
  setupMode: SetupMode;
  configurationState: ConfigurationState;
  configuredAt?: string | null;
  missingRequirements: string[];
}

export interface EvidenceSeekerTestSettingsResponse {
  detail: string;
  metadataFilters: Record<string, unknown>;
}

export interface Permission {
  id: number;
  userId: number;
  evidenceSeekerId: number;
  role: "EVSE_ADMIN" | "EVSE_READER";
  createdAt: string;
}

export interface PermissionCreate {
  userId: number;
  evidenceSeekerId: number;
  role: "EVSE_ADMIN" | "EVSE_READER";
}
