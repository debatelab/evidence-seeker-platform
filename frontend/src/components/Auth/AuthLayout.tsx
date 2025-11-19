import React from "react";
import Logo from "../Logo";

interface AuthLayoutProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
}

const AuthLayout: React.FC<AuthLayoutProps> = ({
  children,
  title = "Welcome",
  subtitle = "Please sign in to continue",
}) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="mx-auto h-20 w-20 flex items-center justify-center">
            <Logo showText={false} iconClassName="h-16" />
          </div>
          <h2 className="brand-title mt-6 text-3xl text-gray-900">
            {title}
          </h2>
          <p className="mt-2 text-sm text-gray-600">{subtitle}</p>
        </div>

        <div className="mt-8">{children}</div>

        <div className="mt-8 text-center text-xs text-gray-500">
          <p>Evidence Seeker Platform - Iteration 4</p>
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;
