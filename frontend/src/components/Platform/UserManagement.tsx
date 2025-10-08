import React, { useState, useEffect, useCallback } from "react";
import {
  Users,
  Trash2,
  Crown,
  UserCheck,
  AlertTriangle,
  Search,
  Shield,
} from "lucide-react";
import { useUserManagement } from "../../hooks/useUserManagement";
import { usePermissions } from "../../hooks/usePermissions";
import { useAuth } from "../../context/AuthContext";

interface PlatformUser {
  id: number;
  username: string;
  email: string;
  isActive: boolean;
  displayRole: string;
  roleSummary: string;
  hasPlatformAdmin: boolean;
  evidenceSeekerRolesCount: number;
}

export const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [filteredUsers, setFilteredUsers] = useState<PlatformUser[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(
    null
  );

  const {
    getAllUsers,
    deleteUser,
    grantPlatformAdmin,
    revokePlatformAdmin,
    isLoading,
    error,
  } = useUserManagement();
  const { hasPlatformAdminAccess } = usePermissions();
  const { user: currentUser } = useAuth();

  const loadUsers = useCallback(async () => {
    try {
      const response = await getAllUsers();
      setUsers(response.users || []);
    } catch (err) {
      console.error("Failed to load users:", err);
    }
  }, [getAllUsers]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    // Filter users based on search query
    if (!searchQuery.trim()) {
      setFilteredUsers(users);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = users.filter(
        (user) =>
          user.username.toLowerCase().includes(query) ||
          user.email.toLowerCase().includes(query)
      );
      setFilteredUsers(filtered);
    }
  }, [users, searchQuery]);

  // loadUsers moved above and memoized with useCallback

  const handleDeleteUser = async (userId: number) => {
    if (
      !confirm(
        "Are you sure you want to permanently delete this user? This action cannot be undone."
      )
    ) {
      return;
    }

    try {
      await deleteUser(userId);
      setUsers(users.filter((user) => user.id !== userId));
      setShowDeleteConfirm(null);
    } catch (err) {
      console.error("Failed to delete user:", err);
    }
  };

  const handleTogglePlatformAdmin = async (user: PlatformUser) => {
    try {
      if (user.hasPlatformAdmin) {
        await revokePlatformAdmin(user.id);
        // Update local state
        setUsers(
          users.map((u) =>
            u.id === user.id
              ? {
                  ...u,
                  hasPlatformAdmin: false,
                  displayRole:
                    u.evidenceSeekerRolesCount > 0
                      ? "EVSE_ACCESS"
                      : "NO_ACCESS",
                  roleSummary:
                    u.evidenceSeekerRolesCount > 0
                      ? `Evidence Seeker Access (${u.evidenceSeekerRolesCount} role${u.evidenceSeekerRolesCount !== 1 ? "s" : ""})`
                      : "No roles assigned",
                }
              : u
          )
        );
      } else {
        await grantPlatformAdmin(user.id);
        // Update local state
        setUsers(
          users.map((u) =>
            u.id === user.id
              ? {
                  ...u,
                  hasPlatformAdmin: true,
                  displayRole: "PLATFORM_ADMIN",
                  roleSummary:
                    u.evidenceSeekerRolesCount > 0
                      ? `Platform Admin + ${u.evidenceSeekerRolesCount} Evidence Seeker role${u.evidenceSeekerRolesCount !== 1 ? "s" : ""}`
                      : "Platform Admin",
                }
              : u
          )
        );
      }
    } catch (err) {
      console.error("Failed to update platform admin status:", err);
    }
  };

  const getRoleIcon = (displayRole: string) => {
    switch (displayRole) {
      case "PLATFORM_ADMIN":
        return <Crown className="h-4 w-4 text-purple-600" />;
      case "EVSE_ACCESS":
        return <Shield className="h-4 w-4 text-blue-600" />;
      default:
        return <UserCheck className="h-4 w-4 text-gray-600" />;
    }
  };

  const getRoleBadge = (user: PlatformUser) => {
    if (user.displayRole === "PLATFORM_ADMIN") {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
          Platform Admin
        </span>
      );
    } else if (user.displayRole === "EVSE_ACCESS") {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          Evidence Seeker Access ({user.evidenceSeekerRolesCount})
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
          No roles assigned
        </span>
      );
    }
  };

  if (!hasPlatformAdminAccess()) {
    return (
      <div className="text-center py-8">
        <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Access Restricted
        </h3>
        <p className="text-gray-600">
          You need platform administrator access to manage users.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Users className="h-6 w-6 text-blue-600" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              User Management
            </h3>
            <p className="text-sm text-gray-600">
              Manage all users on the platform and their access permissions
            </p>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-red-400 mr-2" />
            <div className="text-red-800">{error}</div>
          </div>
        </div>
      )}

      {/* Search and Users List */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-md font-medium text-gray-900">
              All Users ({filteredUsers.length}
              {users.length !== filteredUsers.length
                ? ` of ${users.length}`
                : ""}
              )
            </h4>
          </div>

          {/* Search Input */}
          <div className="mb-4">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                placeholder="Search by username or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {isLoading ? (
            <div className="flex justify-center items-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">Loading users...</span>
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-8">
              <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No users found
              </h3>
              <p className="text-gray-600 mb-4">
                Users will appear here once they register on the platform.
              </p>
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="text-center py-8">
              <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No users found
              </h3>
              <p className="text-gray-600">
                No users match your search criteria.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredUsers.map((user) => {
                const isCurrentUser = user.id === currentUser?.id;

                return (
                  <div
                    key={user.id}
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0">
                        {getRoleIcon(user.displayRole)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-medium text-gray-900">
                          {user.username}
                          {isCurrentUser && (
                            <span className="ml-2 text-xs text-blue-600 font-normal">
                              (You)
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-500 truncate">
                          {user.email}
                        </div>
                        <div className="text-sm text-gray-500 mt-1">
                          {getRoleBadge(user)}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleTogglePlatformAdmin(user)}
                        className={`px-3 py-1 text-xs font-medium rounded ${
                          user.hasPlatformAdmin
                            ? "bg-purple-100 text-purple-800 hover:bg-purple-200"
                            : "bg-gray-100 text-gray-800 hover:bg-gray-200"
                        } ${isCurrentUser ? "opacity-50 cursor-not-allowed" : ""}`}
                        title={
                          user.hasPlatformAdmin
                            ? "Revoke platform admin access"
                            : "Grant platform admin access"
                        }
                        disabled={isCurrentUser}
                      >
                        {user.hasPlatformAdmin ? "Revoke Admin" : "Grant Admin"}
                      </button>
                      <button
                        onClick={() => setShowDeleteConfirm(user.id)}
                        className={`p-1 ${isCurrentUser ? "text-gray-300 cursor-not-allowed" : "text-gray-400 hover:text-red-600"}`}
                        title="Delete user"
                        disabled={isCurrentUser}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <div className="flex items-center mb-4">
                <AlertTriangle className="h-6 w-6 text-red-500 mr-3" />
                <h3 className="text-lg font-medium text-gray-900">
                  Delete User
                </h3>
              </div>

              <div className="mb-4">
                <p className="text-sm text-gray-600">
                  Are you sure you want to permanently delete this user? This
                  action cannot be undone and will remove all their access and
                  data from the platform.
                </p>
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setShowDeleteConfirm(null)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDeleteUser(showDeleteConfirm)}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700"
                >
                  Delete User
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
