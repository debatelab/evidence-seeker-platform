import React, { useState, useEffect, useCallback } from "react";
import { Users, UserPlus, Edit2, Trash2, Shield, Eye } from "lucide-react";
import { PermissionRole } from "../../types/permission";
import { useUserManagement } from "../../hooks/useUserManagement";
import { usePermissions } from "../../hooks/usePermissions";
import { useAuth } from "../../context/AuthContext";
import { PermissionGuard } from "../PermissionGuard";
import { RoleAssignmentForm } from "../User/RoleAssignmentForm";

interface EvidenceSeekerUser {
  id: number;
  username: string;
  role: PermissionRole;
}

interface UserRoleManagerProps {
  evidenceSeekerUuid: string;
}

export const UserRoleManager: React.FC<UserRoleManagerProps> = ({
  evidenceSeekerUuid,
}) => {
  const [users, setUsers] = useState<EvidenceSeekerUser[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingUser, setEditingUser] = useState<EvidenceSeekerUser | null>(
    null
  );

  const {
    getUsersWithRoles,
    assignRole,
    updateRole: _updateRole,
    removeRole,
    isLoading,
    error,
  } = useUserManagement();
  const { canManageEvidenceSeeker } = usePermissions();
  const { refreshPermissions } = useAuth();

  const loadUsers = useCallback(async () => {
    try {
      const data = await getUsersWithRoles(evidenceSeekerUuid);
      setUsers(data);
    } catch (err) {
      console.error("Failed to load users:", err);
    }
  }, [getUsersWithRoles, evidenceSeekerUuid]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleRoleUpdate = async (userId: number, newRole: PermissionRole) => {
    try {
      // Update the role using the assign endpoint (handles both create and update)
      await assignRole(userId, evidenceSeekerUuid, newRole);
      setUsers(
        users.map((user) =>
          user.id === userId ? { ...user, role: newRole } : user
        )
      );
      setEditingUser(null);

      // Refresh permissions after successful role update
      await refreshPermissions();
    } catch (err) {
      console.error("Failed to update role:", err);
    }
  };

  const handleRemoveUser = async (userId: number) => {
    if (!confirm("Are you sure you want to remove this user's access?")) {
      return;
    }

    try {
      await removeRole(userId, evidenceSeekerUuid);
      await loadUsers();

      // Refresh permissions after successful user removal
      await refreshPermissions();
    } catch (err) {
      console.error("Failed to remove user:", err);
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case "EVSE_ADMIN":
        return <Shield className="h-4 w-4 text-purple-600" />;
      case "EVSE_READER":
        return <Eye className="h-4 w-4 text-primary" />;
      default:
        return <Users className="h-4 w-4 text-gray-600" />;
    }
  };

  const getRoleLabel = (role: string) => {
    switch (role) {
      case "EVSE_ADMIN":
        return "Admin";
      case "EVSE_READER":
        return "Reader";
      default:
        return role;
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case "EVSE_ADMIN":
        return "bg-purple-100 text-purple-800";
      case "EVSE_READER":
        return "bg-primary-soft text-primary-strong";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  if (!canManageEvidenceSeeker(evidenceSeekerUuid)) {
    return (
      <div className="text-center py-8">
        <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Access Restricted
        </h3>
        <p className="text-gray-600">
          You need admin permissions to manage users for this evidence seeker.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Users className="h-6 w-6 text-primary" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              User Management
            </h3>
            <p className="text-sm text-gray-600">
              Manage who can access and modify this evidence seeker
            </p>
          </div>
        </div>

        <PermissionGuard
          requiredRole={PermissionRole.EVSE_ADMIN}
          evidenceSeekerId={evidenceSeekerUuid}
        >
          <button
            onClick={() => setShowAddForm(true)}
            className="btn-primary px-4 py-2 flex items-center space-x-2"
          >
            <UserPlus className="h-4 w-4" />
            <span>Add User</span>
          </button>
        </PermissionGuard>
      </div>

      {/* Add User Form */}
      {showAddForm && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <RoleAssignmentForm
            evidenceSeekerId={evidenceSeekerUuid}
            onSuccess={() => {
              setShowAddForm(false);
              loadUsers();
            }}
            onCancel={() => setShowAddForm(false)}
          />
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
        </div>
      )}

      {/* Users List */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6">
          <h4 className="text-md font-medium text-gray-900 mb-4">
            Current Users ({users.length})
          </h4>

          {isLoading ? (
            <div className="flex justify-center items-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              <span className="ml-2 text-gray-600">Loading users...</span>
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-8">
              <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No users assigned
              </h3>
              <p className="text-gray-600 mb-4">
                Add users to grant them access to this evidence seeker.
              </p>
              <button
                onClick={() => setShowAddForm(true)}
                className="btn-primary px-4 py-2 flex items-center space-x-2"
              >
                <UserPlus className="h-4 w-4" />
                <span>Add First User</span>
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {users.map((user) => (
                <div
                  key={user.id}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-center space-x-3">
                    <div className="flex-shrink-0">
                      {getRoleIcon(user.role)}
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">
                        {user.username}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRoleColor(
                        user.role
                      )}`}
                    >
                      {getRoleLabel(user.role)}
                    </span>

                    <div className="flex space-x-2">
                      <button
                        onClick={() => setEditingUser(user)}
                        className="text-gray-400 hover:text-primary p-1"
                        title="Edit role"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleRemoveUser(user.id)}
                        className="text-gray-400 hover:text-red-600 p-1"
                        title="Remove user"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Edit Role Modal */}
      {editingUser && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Edit User Role
              </h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Role
                  </label>
                  <select
                    value={editingUser.role}
                    onChange={(e) =>
                      setEditingUser({
                        ...editingUser,
                        role: e.target.value as PermissionRole,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
                  >
                    <option value="EVSE_READER">
                      Reader - Can view and test
                    </option>
                    <option value="EVSE_ADMIN">Admin - Full control</option>
                  </select>
                </div>

                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => setEditingUser(null)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() =>
                      handleRoleUpdate(editingUser.id, editingUser.role)
                    }
                    className="btn-primary px-4 py-2 text-sm"
                  >
                    Update Role
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
