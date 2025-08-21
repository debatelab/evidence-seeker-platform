import React, { useState, useEffect } from "react";
import { useAuth } from "./hooks/useAuth";
import AuthLayout from "./components/Auth/AuthLayout";
import LoginForm from "./components/Auth/LoginForm";
import RegisterForm from "./components/Auth/RegisterForm";

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

  // No handleLoginSuccess needed - AuthContext state update will trigger re-render

  const handleRegisterSuccess = () => {
    // Handle successful registration - switch to login mode
    console.log("Registration successful!");
    setIsLoginMode(true);
  };

  const handleSwitchToRegister = () => {
    setIsLoginMode(false);
  };

  const handleSwitchToLogin = () => {
    setIsLoginMode(true);
  };

  if (isAuthenticated && user) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
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
                <h1 className="ml-3 text-2xl font-bold text-gray-900">
                  Evidence Seeker Platform
                </h1>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-700">
                  Welcome, {user.email}
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
        </header>

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
                You are successfully authenticated! This is Iteration 1 of the
                platform.
              </p>
              <div className="bg-gray-100 rounded-md p-4 text-left">
                <h4 className="font-medium text-gray-900 mb-2">
                  Your Account Info:
                </h4>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>
                    <strong>Email:</strong> {user.email}
                  </li>
                  <li>
                    <strong>User ID:</strong> {user.id}
                  </li>
                  <li>
                    <strong>Active:</strong> {user.is_active ? "Yes" : "No"}
                  </li>
                  <li>
                    <strong>Verified:</strong> {user.is_verified ? "Yes" : "No"}
                  </li>
                  <li>
                    <strong>Superuser:</strong>{" "}
                    {user.is_superuser ? "Yes" : "No"}
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
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
};

export default App;
