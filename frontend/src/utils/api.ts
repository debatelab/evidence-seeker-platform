import axios, {
  AxiosInstance,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import type { Document, DocumentIngestionResponse } from "../types/document";
import type {
  ConfigurationStatus,
  EvidenceSeekerSettings,
  EvidenceSeekerTestSettingsResponse,
} from "../types/evidenceSeeker";
import type { IndexJob } from "../types/indexJob";
import type {
  CreateFactCheckRunRequest,
  FactCheckResult,
  FactCheckRun,
  FactCheckRunDetail,
  RerunFactCheckRequest,
} from "../types/factCheck";
import type {
  EvidenceSearchRequest,
  EvidenceSearchResponse,
} from "../types/search";
import type {
  PaginatedPublicEvidenceSeekers,
  PublicEvidenceSeekerDetailResponse,
  PublicFactCheckRunDetailResponse,
  PublicFactCheckRunsResponse,
} from "../types/public";

// API base URL - will be replaced by environment variable in production
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// Create axios instance with default configuration
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  validateStatus: (status) => status < 400, // Throw for 4xx/5xx responses
  // Remove default Content-Type to allow automatic setting for FormData
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (
    config: InternalAxiosRequestConfig<any>
  ): InternalAxiosRequestConfig<any> => {
    const token = localStorage.getItem("access_token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle common errors
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login on unauthorized
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    } else if (error.response?.status === 403) {
      // Handle forbidden access - user doesn't have permission
      console.warn(
        "Access forbidden:",
        error.response.data?.detail || "Insufficient permissions"
      );
    }
    return Promise.reject(error);
  }
);

// Authentication API endpoints
export const authAPI = {
  login: async (email: string, password: string) => {
    const response = await apiClient.post(
      "/auth/jwt/login",
      new URLSearchParams({
        username: email, // fastapi-users expects 'username' field
        password: password,
      }),
      {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      }
    );
    return response.data;
  },

  register: async (email: string, username: string, password: string) => {
    const response = await apiClient.post("/auth/register", {
      email,
      username,
      password,
    });
    // Explicitly check for error status codes since axios might not throw in some cases
    if (response.status >= 400) {
      throw new Error(response.data?.detail || "Registration failed");
    }
    return response.data;
  },

  logout: async () => {
    const response = await apiClient.post("/auth/logout");
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await apiClient.get("/auth/me");
    return response.data;
  },

  refreshToken: async () => {
    // JWT doesn't typically need refresh, but this is where you would implement it
    const response = await apiClient.post("/auth/refresh");
    return response.data;
  },
};

// User management API endpoints
export const userAPI = {
  getCurrentUser: async () => {
    const response = await apiClient.get("/users/me");
    return response.data;
  },

  updateCurrentUser: async (userData: any) => {
    const response = await apiClient.put("/users/me", userData);
    return response.data;
  },

  deleteCurrentUser: async () => {
    const response = await apiClient.delete("/users/me");
    return response.data;
  },
};

// Permissions API endpoints
export const permissionsAPI = {
  getMyPermissions: async () => {
    const response = await apiClient.get("/permissions/me");
    return response.data;
  },
};

// Documents API endpoints
export const documentsAPI = {
  listDocuments: async (evidenceSeekerUuid: string): Promise<Document[]> => {
    const response = await apiClient.get<Document[]>("/documents", {
      params: { evidence_seeker_uuid: evidenceSeekerUuid },
    });
    return response.data;
  },

  uploadDocument: async (
    evidenceSeekerUuid: string,
    payload: { file: File; title: string; description?: string | null },
    options?: { onboardingToken?: string }
  ): Promise<DocumentIngestionResponse> => {
    const formData = new FormData();
    formData.append("file", payload.file);
    formData.append("title", payload.title);
    formData.append("description", payload.description ?? "");
    formData.append("evidence_seeker_uuid", evidenceSeekerUuid);

    const response = await apiClient.post<DocumentIngestionResponse>(
      "/documents/upload",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
          ...(options?.onboardingToken
            ? { "X-Onboarding-Token": options.onboardingToken }
            : {}),
        },
      }
    );
    return response.data;
  },

  deleteDocument: async (
    documentUuid: string
  ): Promise<{ detail: string; jobUuid?: string; operationId?: string | null }> => {
    const response = await apiClient.delete<
      { detail: string; jobUuid?: string; operationId?: string | null }
    >(`/documents/${documentUuid}`);
    return response.data;
  },

  downloadDocument: async (documentUuid: string): Promise<Blob> => {
    const response = await apiClient.get(
      `/documents/${documentUuid}/download`,
      {
        responseType: "blob",
      }
    );
    return response.data;
  },
};

export const publicAPI = {
  listEvidenceSeekers: async (
    page = 1,
    pageSize = 12,
    search?: string
  ): Promise<PaginatedPublicEvidenceSeekers> => {
    const response = await apiClient.get<PaginatedPublicEvidenceSeekers>(
      "/public/evidence-seekers",
      {
        params: {
          page,
          page_size: pageSize,
          ...(search ? { search } : {}),
        },
      }
    );
    return response.data;
  },

  getEvidenceSeeker: async (
    seekerUuid: string
  ): Promise<PublicEvidenceSeekerDetailResponse> => {
    const response = await apiClient.get<PublicEvidenceSeekerDetailResponse>(
      `/public/evidence-seekers/${seekerUuid}`
    );
    return response.data;
  },

  createFactCheckRun: async (
    seekerUuid: string,
    payload: CreateFactCheckRunRequest
  ): Promise<FactCheckRun> => {
    const response = await apiClient.post<FactCheckRun>(
      `/public/evidence-seekers/${seekerUuid}/fact-checks`,
      payload
    );
    return response.data;
  },

  listFactChecks: async (
    page = 1,
    pageSize = 10
  ): Promise<PublicFactCheckRunsResponse> => {
    const response = await apiClient.get<PublicFactCheckRunsResponse>(
      "/public/fact-checks",
      { params: { page, page_size: pageSize } }
    );
    return response.data;
  },

  getFactCheck: async (
    runUuid: string
  ): Promise<PublicFactCheckRunDetailResponse> => {
    const response = await apiClient.get<PublicFactCheckRunDetailResponse>(
      `/public/fact-checks/${runUuid}`
    );
    return response.data;
  },
};

export const evidenceSeekerAPI = {
  getConfigurationStatus: async (
    evidenceSeekerUuid: string
  ): Promise<ConfigurationStatus> => {
    const response = await apiClient.get<ConfigurationStatus>(
      `/evidence-seekers/${evidenceSeekerUuid}/status`
    );
    return response.data;
  },
  getSettings: async (
    evidenceSeekerUuid: string
  ): Promise<EvidenceSeekerSettings> => {
    const response = await apiClient.get<EvidenceSeekerSettings>(
      `/evidence-seekers/${evidenceSeekerUuid}/settings`
    );
    return response.data;
  },

  updateSettings: async (
    evidenceSeekerUuid: string,
    payload: Record<string, unknown>
  ): Promise<EvidenceSeekerSettings> => {
    const response = await apiClient.put<EvidenceSeekerSettings>(
      `/evidence-seekers/${evidenceSeekerUuid}/settings`,
      payload
    );
    return response.data;
  },

  testSettings: async (
    evidenceSeekerUuid: string,
    payload: { metadataFilters?: Record<string, unknown>; statement?: string }
  ): Promise<EvidenceSeekerTestSettingsResponse> => {
    const response = await apiClient.post<EvidenceSeekerTestSettingsResponse>(
      `/evidence-seekers/${evidenceSeekerUuid}/settings/test`,
      payload
    );
    return response.data;
  },

  triggerReindex: async (
    evidenceSeekerUuid: string
  ): Promise<IndexJob> => {
    const response = await apiClient.post<IndexJob>(
      `/evidence-seekers/${evidenceSeekerUuid}/documents/reindex`
    );
    return response.data;
  },

  listIndexJobs: async (evidenceSeekerUuid: string): Promise<IndexJob[]> => {
    const response = await apiClient.get<IndexJob[]>(
      `/evidence-seekers/${evidenceSeekerUuid}/index-jobs`
    );
    return response.data;
  },

  searchEvidence: async (
    evidenceSeekerUuid: string,
    payload: EvidenceSearchRequest
  ): Promise<EvidenceSearchResponse> => {
    const response = await apiClient.post<EvidenceSearchResponse>(
      `/evidence-seekers/${evidenceSeekerUuid}/search`,
      payload
    );
    return response.data;
  },

  listFactCheckRuns: async (
    evidenceSeekerUuid: string,
    params?: { skip?: number; limit?: number }
  ): Promise<FactCheckRun[]> => {
    const response = await apiClient.get<FactCheckRun[]>(
      `/evidence-seekers/${evidenceSeekerUuid}/runs`,
      {
        params: {
          skip: params?.skip ?? 0,
          limit: params?.limit ?? 50,
        },
      }
    );
    return response.data;
  },

  createFactCheckRun: async (
    evidenceSeekerUuid: string,
    payload: CreateFactCheckRunRequest
  ): Promise<FactCheckRun> => {
    const response = await apiClient.post<FactCheckRun>(
      `/evidence-seekers/${evidenceSeekerUuid}/runs`,
      payload
    );
    return response.data;
  },

  getFactCheckRun: async (
    evidenceSeekerUuid: string,
    runUuid: string
  ): Promise<FactCheckRunDetail> => {
    const response = await apiClient.get<FactCheckRunDetail>(
      `/evidence-seekers/${evidenceSeekerUuid}/runs/${runUuid}`
    );
    return response.data;
  },

  getFactCheckResults: async (
    evidenceSeekerUuid: string,
    runUuid: string
  ): Promise<FactCheckResult[]> => {
    const response = await apiClient.get<FactCheckResult[]>(
      `/evidence-seekers/${evidenceSeekerUuid}/runs/${runUuid}/results`
    );
    return response.data;
  },

  cancelFactCheckRun: async (
    evidenceSeekerUuid: string,
    runUuid: string
  ): Promise<{ detail: string }> => {
    const response = await apiClient.delete<{ detail: string }>(
      `/evidence-seekers/${evidenceSeekerUuid}/runs/${runUuid}`
    );
    return response.data;
  },

  rerunFactCheck: async (
    evidenceSeekerUuid: string,
    runUuid: string,
    payload: RerunFactCheckRequest
  ): Promise<FactCheckRun> => {
    const response = await apiClient.post<FactCheckRun>(
      `/evidence-seekers/${evidenceSeekerUuid}/runs/${runUuid}/rerun`,
      payload
    );
    return response.data;
  },
  skipDocuments: async (
    evidenceSeekerUuid: string
  ): Promise<ConfigurationStatus> => {
    const response = await apiClient.post<ConfigurationStatus>(
      `/evidence-seekers/${evidenceSeekerUuid}/onboarding/skip-documents`
    );
    return response.data;
  },
  finishOnboarding: async (
    evidenceSeekerUuid: string
  ): Promise<ConfigurationStatus> => {
    const response = await apiClient.post<ConfigurationStatus>(
      `/evidence-seekers/${evidenceSeekerUuid}/finish-onboarding`
    );
    return response.data;
  },
};

// Generic API utilities
export const apiUtils = {
  isAuthenticated: (): boolean => {
    const token = localStorage.getItem("access_token");
    return !!token;
  },

  getToken: (): string | null => {
    return localStorage.getItem("access_token");
  },

  setToken: (token: string): void => {
    localStorage.setItem("access_token", token);
  },

  removeToken: (): void => {
    localStorage.removeItem("access_token");
  },

  getUser: (): any => {
    const user = localStorage.getItem("user");
    if (user === null || user === "undefined") {
      // Handle null or "undefined" string
      return null;
    }
    try {
      return JSON.parse(user);
    } catch (e) {
      console.error("Error parsing user from localStorage:", e);
      return null;
    }
  },

  setUser: (user: any): void => {
    localStorage.setItem("user", JSON.stringify(user));
  },

  removeUser: (): void => {
    localStorage.removeItem("user");
  },
};

export default apiClient;
