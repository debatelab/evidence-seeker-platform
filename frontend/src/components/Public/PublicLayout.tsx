import React from "react";
import { Link } from "react-router";
import { useAuth } from "../../hooks/useAuth";
import Logo from "../Logo";

interface PublicLayoutProps {
  children: React.ReactNode;
}

const PublicLayout: React.FC<PublicLayoutProps> = ({ children }) => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen flex flex-col bg-white">
      <header className="border-b border-gray-100 bg-white/90 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-2">
            <Logo iconClassName="h-10" />
          </Link>
          <div className="flex items-center space-x-3">
            {isAuthenticated ? (
              <Link to="/app" className="btn-primary px-4 py-2 rounded-md">
                Go to Dashboard
              </Link>
            ) : (
              <>
                <Link
                  to="/login"
                  className="px-4 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-gray-900"
                >
                  Log in
                </Link>
                <Link
                  to="/register"
                  className="btn-primary px-4 py-2 rounded-md"
                >
                  Get started
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-gray-100 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col sm:flex-row justify-between text-sm text-gray-500 gap-4">
          <p>© {new Date().getFullYear()} Evidence Seeker Platform</p>
          <div className="flex space-x-4">
            <Link to="/login" className="hover:text-gray-900">
              Login
            </Link>
            <Link to="/register" className="hover:text-gray-900">
              Create account
            </Link>
            <a
              href="mailto:hello@evidence-seeker.io"
              className="hover:text-gray-900"
            >
              Contact
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default PublicLayout;
