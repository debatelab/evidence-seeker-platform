import React, { useState, useEffect } from "react";
import {
  createBrowserRouter,
  RouterProvider,
  Link,
  useParams,
  Navigate,
} from "react-router";
import { useAuth } from "./hooks/useAuth";
import { usePermissions } from "./hooks/usePermissions";
import AuthLayout from "./components/Auth/AuthLayout";
import LoginForm from "./components/Auth/LoginForm";
import RegisterForm from "./components/Auth/RegisterForm";
import EvidenceSeekerList from "./components/EvidenceSeeker/EvidenceSeekerList";
import EvidenceSeekerForm from "./components/EvidenceSeeker/EvidenceSeekerForm";
import EvidenceSeekerManagementWrapper from "./components/EvidenceSeeker/EvidenceSeekerManagementWrapper";
import DocumentList from "./components/Document/DocumentList";
import DocumentUpload from "./components/Document/DocumentUpload";
import { SearchInterface } from "./components/Search/SearchInterface";
import EvidenceSeekerSettings from "./components/EvidenceSeeker/EvidenceSeekerSettings";
import { UserRoleManager } from "./components/EvidenceSeeker/UserRoleManager";
import { APIKeyManager } from "./components/Config/APIKeyManager";
import ErrorBoundary from "./components/ErrorBoundary";
import PlatformSettings from "./pages/PlatformSettings";
import { useEvidenceSeekers } from "./hooks/useEvidenceSeeker";
import { EvidenceSeeker } from "./types/evidenceSeeker";

// Wrapper component to provide Evidence Seeker UUID to tab components
const TabWrapper = ({
  Component,
  needsEvidenceSeeker = true,
}: {
  Component: React.ComponentType<any>;
  needsEvidenceSeeker?: boolean;
}) => {
  const { evidenceSeekerId } = useParams<{ evidenceSeekerId: string }>();
  const { evidenceSeekers } = useEvidenceSeekers();
  const [evidenceSeeker, setEvidenceSeeker] = useState<EvidenceSeeker | null>(
    null
  );

  useEffect(() => {
    if (evidenceSeekers.length > 0 && evidenceSeekerId) {
      // Find the evidence seeker by UUID or ID
      const seeker = evidenceSeekers.find(
        (es) =>
          es.uuid === evidenceSeekerId || es.id.toString() === evidenceSeekerId
      );
      setEvidenceSeeker(seeker || null);
    }
  }, [evidenceSeekers, evidenceSeekerId]);

  if (needsEvidenceSeeker && !evidenceSeeker) {
    return (
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="text-center">
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Loading Evidence Seeker...
            </h3>
          </div>
        </div>
      </div>
    );
  }

  return needsEvidenceSeeker ? (
    <Component evidenceSeekerUuid={evidenceSeeker!.uuid} />
  ) : (
    <Component evidenceSeekerUuid={evidenceSeekerId} />
  );
};

const App: React.FC = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const [isLoginMode, setIsLoginMode] = useState(true);

  // Add this useEffect for debugging
  useEffect(() => {
    console.log("App - isAuthenticated:", isAuthenticated);
    console.log("App - user:", user);
    if (isAuthenticated && user) {
      console.log("App - User is authenticated, should show welcome page.");
    }
  }, [isAuthenticated, user]);

  const handleRegisterSuccess = () => {
    console.log("Registration successful!");
    setIsLoginMode(true);
  };

  const handleSwitchToRegister = () => {
    setIsLoginMode(false);
  };

  const handleSwitchToLogin = () => {
    setIsLoginMode(true);
  };

  // Dashboard component
  const Dashboard = () => (
    <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        <div className="border-4 border-dashed border-gray-200 rounded-lg p-12 text-center">
          <div className="h-16 w-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="h-8 w-8 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Welcome to Evidence Seeker Platform
          </h3>
          <p className="text-gray-500 mb-4">
            You are successfully authenticated! This is Iteration 2 of the
            platform.
          </p>
          <div className="bg-gray-100 rounded-md p-4 text-left max-w-md mx-auto">
            <h4 className="font-medium text-gray-900 mb-2">
              Your Account Info:
            </h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>
                <strong>Email:</strong> {user?.email}
              </li>
              <li>
                <strong>User ID:</strong> {user?.id}
              </li>
              <li>
                <strong>Active:</strong> {user?.is_active ? "Yes" : "No"}
              </li>
              <li>
                <strong>Verified:</strong> {user?.is_verified ? "Yes" : "No"}
              </li>
              <li>
                <strong>Superuser:</strong> {user?.is_superuser ? "Yes" : "No"}
              </li>
            </ul>
          </div>
          <div className="mt-6">
            <Link
              to="/evidence-seekers"
              className="bg-blue-600 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Manage Evidence Seekers
            </Link>
          </div>
        </div>
      </div>
    </main>
  );

  // Layout component with navigation
  const AppLayout = ({ children }: { children: React.ReactNode }) => {
    const { hasPlatformAdminAccess } = usePermissions();
    console.log({ hasPlatformAdminAccess: hasPlatformAdminAccess() });
    return (
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              <div className="flex items-center space-x-8">
                <div className="flex items-center">
                  <div className="h-8 w-8 bg-blue-600 rounded-full flex items-center justify-center">
                    <svg
                      className="h-5 w-5 text-white"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                      />
                    </svg>
                  </div>
                  <h1 className="ml-3 text-xl font-bold text-gray-900">
                    Evidence Seeker Platform
                  </h1>
                </div>
                <div className="flex space-x-4">
                  <Link
                    to="/"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Dashboard
                  </Link>
                  <Link
                    to="/evidence-seekers"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Evidence Seekers
                  </Link>
                  {hasPlatformAdminAccess() && (
                    <Link
                      to="/platform-settings"
                      className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                    >
                      Platform Admin
                    </Link>
                  )}
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-700">
                  Welcome, {user?.email}
                </span>
                <button
                  onClick={logout}
                  className="bg-red-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </nav>
        {children}
      </div>
    );
  };

  // Auth component
  const AuthPage = () => (
    <AuthLayout
      title={isLoginMode ? "Welcome Back" : "Create Account"}
      subtitle={
        isLoginMode
          ? "Please sign in to continue"
          : "Join Evidence Seeker Platform"
      }
    >
      {isLoginMode ? (
        <LoginForm onSwitchToRegister={handleSwitchToRegister} />
      ) : (
        <RegisterForm
          onSuccess={handleRegisterSuccess}
          onSwitchToLogin={handleSwitchToLogin}
        />
      )}
    </AuthLayout>
  );

  // Create router configuration
  const router = createBrowserRouter([
    {
      path: "/",
      element:
        isAuthenticated && user ? (
          <AppLayout>
            <Dashboard />
          </AppLayout>
        ) : (
          <AuthPage />
        ),
    },
    {
      path: "/evidence-seekers",
      element:
        isAuthenticated && user ? (
          <AppLayout>
            <EvidenceSeekerList />
          </AppLayout>
        ) : (
          <AuthPage />
        ),
    },
    {
      path: "/evidence-seekers/new",
      element:
        isAuthenticated && user ? (
          <AppLayout>
            <EvidenceSeekerForm />
          </AppLayout>
        ) : (
          <AuthPage />
        ),
    },

    {
      path: "/evidence-seekers/:evidenceSeekerId/manage",
      element:
        isAuthenticated && user ? (
          <AppLayout>
            <EvidenceSeekerManagementWrapper />
          </AppLayout>
        ) : (
          <AuthPage />
        ),
      children: [
        {
          path: "documents",
          element: <TabWrapper Component={DocumentList} />,
        },
        {
          path: "search",
          element: <TabWrapper Component={SearchInterface} />,
        },
        {
          path: "settings",
          element: <TabWrapper Component={EvidenceSeekerSettings} />,
        },
        {
          path: "users",
          element: (
            <TabWrapper
              Component={UserRoleManager}
              needsEvidenceSeeker={false}
            />
          ),
        },
        {
          path: "config",
          element: <TabWrapper Component={APIKeyManager} />,
        },
        {
          index: true,
          element: <Navigate to="documents" replace />,
        },
      ],
    },
    {
      path: "/evidence-seekers/:evidenceSeekerId/documents/upload",
      element:
        isAuthenticated && user ? (
          <AppLayout>
            <TabWrapper Component={DocumentUpload} />
          </AppLayout>
        ) : (
          <AuthPage />
        ),
    },
    {
      path: "/platform-settings",
      element:
        isAuthenticated && user ? (
          <AppLayout>
            <PlatformSettings />
          </AppLayout>
        ) : (
          <AuthPage />
        ),
    },
  ]);

  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
};

export default App;
