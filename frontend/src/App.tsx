import React, { useState, useEffect } from "react";
import {
  createBrowserRouter,
  RouterProvider,
  Link,
  Navigate,
  useNavigate,
  useParams,
  Outlet,
} from "react-router";
import { useAuth } from "./hooks/useAuth";
import { usePermissions } from "./hooks/usePermissions";
import AuthLayout from "./components/Auth/AuthLayout";
import LoginForm from "./components/Auth/LoginForm";
import RegisterForm from "./components/Auth/RegisterForm";
import EmailVerification from "./components/Auth/EmailVerification";
import ForgotPassword from "./components/Auth/ForgotPassword";
import ResetPassword from "./components/Auth/ResetPassword";
import EvidenceSeekerList from "./components/EvidenceSeeker/EvidenceSeekerList";
import EvidenceSeekerForm from "./components/EvidenceSeeker/EvidenceSeekerForm";
import EvidenceSeekerManagementWrapper from "./components/EvidenceSeeker/EvidenceSeekerManagementWrapper";
import DocumentList from "./components/Document/DocumentList";
import DocumentUpload from "./components/Document/DocumentUpload";
import EvidenceSeekerSettingsAndConfig from "./components/EvidenceSeeker/EvidenceSeekerSettingsAndConfig";
import EvidenceSeekerFactChecks from "./components/EvidenceSeeker/EvidenceSeekerFactChecks";
import EvidenceSeekerRunForm from "./components/EvidenceSeeker/EvidenceSeekerRunForm";
import { UserRoleManager } from "./components/EvidenceSeeker/UserRoleManager";
import ErrorBoundary from "./components/ErrorBoundary";
import PlatformSettings from "./pages/PlatformSettings";
import { useEvidenceSeekers } from "./hooks/useEvidenceSeeker";
import { EvidenceSeeker } from "./types/evidenceSeeker";
import PublicHomePage from "./pages/public/PublicHomePage";
import PublicEvidenceSeekerPage from "./pages/public/PublicEvidenceSeekerPage";
import PublicFactCheckPage from "./pages/public/PublicFactCheckPage";
import AdminFactCheckRunPage from "./pages/app/AdminFactCheckRunPage";
import ReauthModal from "./components/Auth/ReauthModal";
import Logo from "./components/Logo";

// Wrapper component to provide Evidence Seeker UUID to tab components
interface EvidenceSeekerUuidProp {
  evidenceSeekerUuid?: string; // optional when needsEvidenceSeeker=false scenario
}

const TabWrapper = <P extends EvidenceSeekerUuidProp = EvidenceSeekerUuidProp>({
  Component,
  needsEvidenceSeeker = true,
}: {
  Component: React.ComponentType<P>;
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

  if (needsEvidenceSeeker) {
    return (
      <Component {...({ evidenceSeekerUuid: evidenceSeeker!.uuid } as P)} />
    );
  }
  return <Component {...({ evidenceSeekerUuid: evidenceSeekerId } as P)} />;
};

// Layout component with navigation
const AppLayout: React.FC = () => {
  const { hasPlatformAdminAccess } = usePermissions();
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-8">
              <Link
                to="/"
                className="flex items-center hover:opacity-90 transition"
                aria-label="Go to public homepage"
              >
                <Logo
                  className="flex items-center"
                  iconClassName="h-10"
                  textClassName="text-gray-900 text-xl"
                  title="Evidence Seeker"
                  subtitle="Admin"
                />
              </Link>
              <div className="flex space-x-4">
                <Link
                  to="/app/evidence-seekers"
                  className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Evidence Seekers
                </Link>
                {hasPlatformAdminAccess() && (
                  <Link
                    to="/app/platform-settings"
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
              <Link
                to="/"
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                View Public Site
              </Link>
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
      <Outlet />
    </div>
  );
};

  const LoginPage = () => {
    const navigate = useNavigate();
    return (
      <AuthLayout title="Welcome Back" subtitle="Please sign in to continue">
        <LoginForm onSwitchToRegister={() => navigate("/register")} />
      </AuthLayout>
    );
  };

  const RegisterPage = () => {
    const navigate = useNavigate();
    return (
      <AuthLayout
        title="Join Evidence Seeker Platform"
        subtitle="Create your account"
      >
        <RegisterForm onSwitchToLogin={() => navigate("/login")} />
      </AuthLayout>
    );
  };

const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, user } = useAuth();
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

const App: React.FC = () => {
  const { isAuthenticated, user } = useAuth();

  const router = React.useMemo(
    () =>
      createBrowserRouter([
        {
          path: "/",
          element: <PublicHomePage />,
        },
        {
          path: "/login",
          element:
            isAuthenticated && user ? (
              <Navigate to="/app/evidence-seekers" replace />
            ) : (
              <LoginPage />
            ),
        },
        {
          path: "/register",
          element:
            isAuthenticated && user ? (
              <Navigate to="/app/evidence-seekers" replace />
            ) : (
              <RegisterPage />
            ),
        },
        {
          path: "/verify-email",
          element: <EmailVerification />,
        },
        {
          path: "/forgot-password",
          element: <ForgotPassword />,
        },
        {
          path: "/reset-password",
          element: <ResetPassword />,
        },
        {
          path: "/evidence-seekers/:seekerUuid",
          element: <PublicEvidenceSeekerPage />,
        },
        {
          path: "/fact-checks/:runUuid",
          element: <PublicFactCheckPage />,
        },
        {
          path: "/app",
          element: (
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          ),
          children: [
            {
              index: true,
              element: <Navigate to="evidence-seekers" replace />,
            },
            {
              path: "evidence-seekers",
              element: <EvidenceSeekerList />,
            },
            {
              path: "evidence-seekers/new",
              element: <EvidenceSeekerForm />,
            },
            {
              path: "evidence-seekers/:evidenceSeekerId/manage",
              element: <EvidenceSeekerManagementWrapper />,
              children: [
                {
                  path: "documents",
                  element: <TabWrapper Component={DocumentList} />,
                },
                {
                  path: "fact-checks",
                  element: <TabWrapper Component={EvidenceSeekerFactChecks} />,
                },
                {
                  path: "fact-checks/new",
                  element: <TabWrapper Component={EvidenceSeekerRunForm} />,
                },
                {
                  path: "fact-checks/:runUuid",
                  element: <TabWrapper Component={AdminFactCheckRunPage} />,
                },
                {
                  path: "settings",
                  element: (
                    <TabWrapper Component={EvidenceSeekerSettingsAndConfig} />
                  ),
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
                  index: true,
                  element: <Navigate to="documents" replace />,
                },
                {
                  path: "config",
                  element: <Navigate to="../settings" replace />,
                },
              ],
            },
            {
              path: "evidence-seekers/:evidenceSeekerId/documents/upload",
              element: <TabWrapper Component={DocumentUpload} />,
            },
            {
              path: "platform-settings",
              element: <PlatformSettings />,
            },
          ],
        },
      ]),
    [isAuthenticated, user]
  );

  return (
    <ErrorBoundary>
      <>
        <RouterProvider router={router} />
        <ReauthModal />
      </>
    </ErrorBoundary>
  );
};

export default App;
