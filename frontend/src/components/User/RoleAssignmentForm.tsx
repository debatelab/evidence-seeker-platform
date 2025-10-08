import React, { useState } from "react";
import { UserSearchResult } from "../../types/user";
import { PermissionRole } from "../../types/permission";
import { UserSearch } from "./UserSearch";
import { useUserManagement } from "../../hooks/useUserManagement";
import { useAuth } from "../../context/AuthContext";

interface RoleAssignmentFormProps {
  evidenceSeekerId: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export const RoleAssignmentForm: React.FC<RoleAssignmentFormProps> = ({
  evidenceSeekerId,
  onSuccess,
  onCancel,
}) => {
  const [selectedUser, setSelectedUser] = useState<UserSearchResult | null>(
    null
  );
  const [selectedRole, setSelectedRole] = useState<PermissionRole>(
    PermissionRole.EVSE_READER
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { assignRole, isLoading: _isLoading, error } = useUserManagement();
  const { refreshPermissions } = useAuth();

  const handleUserSelect = (user: UserSearchResult) => {
    setSelectedUser(user);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedUser) return;

    setIsSubmitting(true);
    try {
      await assignRole(selectedUser.id, evidenceSeekerId, selectedRole);
      onSuccess?.();

      // Refresh permissions after successful role assignment
      await refreshPermissions();

      // Reset form
      setSelectedUser(null);
      setSelectedRole(PermissionRole.EVSE_READER);
    } catch (err) {
      console.error("Failed to assign role:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setSelectedUser(null);
    setSelectedRole(PermissionRole.EVSE_READER);
    onCancel?.();
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        Assign User Role
      </h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* User Search */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Search User
          </label>
          <UserSearch
            onUserSelect={handleUserSelect}
            placeholder="Search users by username..."
          />
          {selectedUser && (
            <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded-md">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-blue-900">
                    {selectedUser.username}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedUser(null)}
                  className="text-blue-600 hover:text-blue-800"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Role Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Role
          </label>
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value as PermissionRole)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value={PermissionRole.EVSE_READER}>
              Reader - Can view and test
            </option>
            <option value={PermissionRole.EVSE_ADMIN}>
              Admin - Full control
            </option>
          </select>
          <div className="mt-1 text-sm text-gray-500">
            {selectedRole === PermissionRole.EVSE_READER &&
              "Readers can view the evidence seeker and run tests, but cannot modify settings or manage users."}
            {selectedRole === PermissionRole.EVSE_ADMIN &&
              "Admins have full control over the evidence seeker, including managing users and modifying settings."}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
            {error}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            onClick={handleCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!selectedUser || isSubmitting}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Assigning...
              </div>
            ) : (
              "Assign Role"
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
