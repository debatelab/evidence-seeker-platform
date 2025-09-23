import React from "react";
import { Settings, Database, Key, Mail } from "lucide-react";

export const PlatformConfiguration: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-3">
        <Settings className="h-6 w-6 text-green-600" />
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Platform Configuration
          </h3>
          <p className="text-sm text-gray-600">
            Configure system-wide settings and platform behavior
          </p>
        </div>
      </div>

      {/* Configuration Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Database Settings */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Database className="h-5 w-5 text-blue-600" />
            <h4 className="text-md font-medium text-gray-900">
              Database Settings
            </h4>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Configure database connections and performance settings.
          </p>
          <div className="text-center py-8">
            <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-xs text-gray-400">
              Database configuration coming soon
            </p>
          </div>
        </div>

        {/* API Settings */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Key className="h-5 w-5 text-purple-600" />
            <h4 className="text-md font-medium text-gray-900">
              API Configuration
            </h4>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Manage API keys, rate limits, and external integrations.
          </p>
          <div className="text-center py-8">
            <Key className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-xs text-gray-400">
              API configuration coming soon
            </p>
          </div>
        </div>

        {/* Email Settings */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Mail className="h-5 w-5 text-green-600" />
            <h4 className="text-md font-medium text-gray-900">
              Email Settings
            </h4>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Configure email notifications and SMTP settings.
          </p>
          <div className="text-center py-8">
            <Mail className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-xs text-gray-400">
              Email configuration coming soon
            </p>
          </div>
        </div>

        {/* System Settings */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Settings className="h-5 w-5 text-orange-600" />
            <h4 className="text-md font-medium text-gray-900">
              System Settings
            </h4>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            General system configuration and maintenance settings.
          </p>
          <div className="text-center py-8">
            <Settings className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-xs text-gray-400">System settings coming soon</p>
          </div>
        </div>
      </div>
    </div>
  );
};
