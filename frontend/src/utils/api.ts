import axios, {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";

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
