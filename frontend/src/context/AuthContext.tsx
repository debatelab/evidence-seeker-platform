import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import { AuthState, LoginRequest, RegisterRequest } from "../types/auth";
import { authAPI, permissionsAPI, apiUtils } from "../utils/api";

// Polling configuration
const PERMISSION_POLLING_CONFIG = {
  interval: 60000, // 60 seconds
  enabled: true,
  maxRetries: 3,
  backoffMultiplier: 2,
};

interface AuthContextProps extends AuthState {
  login: (
    credentials: LoginRequest
  ) => Promise<{ success: boolean; data?: any; error?: string }>;
  register: (
    userData: RegisterRequest
  ) => Promise<{ success: boolean; data?: any; error?: string }>;
  logout: () => Promise<{ success: boolean }>;
  clearError: () => void;
  checkAuthStatus: () => Promise<boolean>;
  refreshPermissions: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextProps | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  });

  // Initialize auth state from localStorage
  useEffect(() => {
    const token = apiUtils.getToken();
    const user = apiUtils.getUser();

    if (token && user) {
      setAuthState({
        user,
        token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } else {
      setAuthState((prev) => ({
        ...prev,
        isLoading: false,
      }));
    }
  }, []);

  const login = useCallback(async (credentials: LoginRequest) => {
    try {
      setAuthState((prev) => ({ ...prev, isLoading: true, error: null }));

      const response = await authAPI.login(
        credentials.email,
        credentials.password
      );

      // Store token
      apiUtils.setToken(response.access_token);

      // Fetch user data after successful login
      const userResponse = await authAPI.getCurrentUser();
      const user = userResponse;

      // Fetch user permissions
      try {
        const permissionsData = await permissionsAPI.getMyPermissions();
        user.permissions = permissionsData.permissions || [];
      } catch (error) {
        console.warn("Failed to fetch user permissions:", error);
        user.permissions = [];
      }

      apiUtils.setUser(user);

      setAuthState({
        user,
        token: response.access_token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });

      return { success: true, data: response };
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail || "Login failed. Please try again.";
      setAuthState((prev) => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      return { success: false, error: errorMessage };
    }
  }, []);

  const register = useCallback(async (userData: RegisterRequest) => {
    try {
      setAuthState((prev) => ({ ...prev, isLoading: true, error: null }));

      const response = await authAPI.register(
        userData.email,
        userData.username,
        userData.password
      );

      setAuthState((prev) => ({
        ...prev,
        isLoading: false,
        error: null,
      }));

      return { success: true, data: response };
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail ||
        "Registration failed. Please try again.";
      setAuthState((prev) => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      return { success: false, error: errorMessage };
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      setAuthState((prev) => ({ ...prev, isLoading: true }));
      await authAPI.logout();
    } catch {
      // ignore logout errors
    } finally {
      apiUtils.removeToken();
      apiUtils.removeUser();
      setAuthState({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    }
    return { success: true };
  }, []);

  const clearError = useCallback(() => {
    setAuthState((prev) => ({ ...prev, error: null }));
  }, []);

  const checkAuthStatus = useCallback(async () => {
    if (!authState.token) return false;
    try {
      await authAPI.getCurrentUser();
      return true;
    } catch {
      await logout();
      return false;
    }
  }, [authState.token, logout]);

  const refreshPermissions = useCallback(async (): Promise<boolean> => {
    if (!authState.isAuthenticated || !authState.user) {
      return false;
    }

    try {
      const permissionsData = await permissionsAPI.getMyPermissions();
      const updatedUser = {
        ...authState.user,
        permissions: permissionsData.permissions || [],
      };

      // Update localStorage
      apiUtils.setUser(updatedUser);

      // Update state
      setAuthState((prev) => ({
        ...prev,
        user: updatedUser,
      }));

      return true;
    } catch (error) {
      console.warn("Failed to refresh permissions:", error);
      return false;
    }
  }, [authState.isAuthenticated, authState.user]);

  // Permission polling effect
  useEffect(() => {
    if (!PERMISSION_POLLING_CONFIG.enabled || !authState.isAuthenticated) {
      return;
    }

    const pollPermissions = async () => {
      // Only poll if document is visible
      if (document.hidden) {
        return;
      }

      await refreshPermissions();
    };

    // Set up polling interval
    const intervalId = setInterval(
      pollPermissions,
      PERMISSION_POLLING_CONFIG.interval
    );

    // Handle visibility change to pause/resume polling
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // Tab became visible, refresh permissions immediately
        refreshPermissions();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    // Cleanup
    return () => {
      clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [authState.isAuthenticated, refreshPermissions]);

  return (
    <AuthContext.Provider
      value={{
        ...authState,
        login,
        register,
        logout,
        clearError,
        checkAuthStatus,
        refreshPermissions,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
