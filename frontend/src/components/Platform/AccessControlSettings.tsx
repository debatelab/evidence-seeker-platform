import React from "react";
import { Shield, Lock, Key, Users } from "lucide-react";

export const AccessControlSettings: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-3">
        <Shield className="h-6 w-6 text-red-600" />
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Access Control & Security
          </h3>
          <p className="text-sm text-gray-600">
            Manage security policies, authentication settings, and access
            controls
          </p>
        </div>
      </div>

      {/* Security Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Authentication Settings */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Lock className="h-5 w-5 text-blue-600" />
            <h4 className="text-md font-medium text-gray-900">
              Authentication Settings
            </h4>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Configure password policies, session timeouts, and login
            requirements.
          </p>
          <div className="text-center py-8">
            <Lock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-xs text-gray-400">
              Authentication settings coming soon
            </p>
          </div>
        </div>

        {/* Permission Management */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Key className="h-5 w-5 text-purple-600" />
            <h4 className="text-md font-medium text-gray-900">
              Permission Management
            </h4>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Define roles, permissions, and access control policies.
          </p>
          <div className="text-center py-8">
            <Key className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-xs text-gray-400">
              Permission management coming soon
            </p>
          </div>
        </div>

        {/* Audit Logging */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Users className="h-5 w-5 text-green-600" />
            <h4 className="text-md font-medium text-gray-900">Audit Logging</h4>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Monitor user activities and system access for security compliance.
          </p>
          <div className="text-center py-8">
            <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-xs text-gray-400">Audit logging coming soon</p>
          </div>
        </div>

        {/* Security Policies */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Shield className="h-5 w-5 text-orange-600" />
            <h4 className="text-md font-medium text-gray-900">
              Security Policies
            </h4>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Configure security policies, data protection, and compliance
            settings.
          </p>
          <div className="text-center py-8">
            <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-xs text-gray-400">
              Security policies coming soon
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
