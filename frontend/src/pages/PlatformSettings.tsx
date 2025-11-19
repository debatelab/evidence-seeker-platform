import React from "react";
import { Shield } from "lucide-react";
import { usePermissions } from "../hooks/usePermissions";
import { AccessDeniedMessage } from "../components/Error/AccessDeniedMessage";
import { UserManagement } from "../components/Platform/UserManagement";
// import { PlatformConfiguration } from "../components/Platform/PlatformConfiguration";
// import { AccessControlSettings } from "../components/Platform/AccessControlSettings";

const PlatformSettings: React.FC = () => {
  const { hasPlatformAdminAccess } = usePermissions();

  if (!hasPlatformAdminAccess()) {
    return (
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <AccessDeniedMessage message="You need platform administrator access to view this page." />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-3 mb-2">
            <Shield className="h-8 w-8 text-purple-600" />
            <h1 className="brand-title text-2xl text-gray-900">
              Platform Administration
            </h1>
          </div>
          <p className="text-gray-600">
            Manage platform-wide user permissions and access control
          </p>
        </div>

        {/* Main Content Area */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <UserManagement />
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlatformSettings;
