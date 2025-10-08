import { useState } from "react";
import { UserSearchResult } from "../types/user";
import { PermissionRole } from "../types/permission";
import apiClient from "../utils/api";

export const useUserManagement = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const searchUsers = async (query: string): Promise<UserSearchResult[]> => {
    if (!query.trim()) return [];

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.get(
        `/users/search-for-assignment?q=${encodeURIComponent(query)}`
      );
      return response.data || [];
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to search users";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const assignRole = async (
    userId: number,
    evidenceSeekerId: string,
    role: PermissionRole
  ): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await apiClient.post(
        `/permissions/evidence-seeker/${evidenceSeekerId}/assign`,
        {
          user_id: userId,
          role,
        }
      );
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to assign role";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const updateRole = async (
    permissionId: number,
    role: PermissionRole
  ): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await apiClient.put(`/permissions/${permissionId}`, {
        role,
      });
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to update role";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const removeRole = async (
    userId: number,
    evidenceSeekerId: string
  ): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await apiClient.delete(
        `/permissions/evidence-seeker/${evidenceSeekerId}/users/${userId}`
      );
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to remove role";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const getUsersWithRoles = async (evidenceSeekerId: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.get(
        `/permissions/evidence-seeker/${evidenceSeekerId}/users`
      );
      return response.data || [];
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to fetch users with roles";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const getAllUsers = async (): Promise<{ users: any[] }> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.get("/users");
      return response.data;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to fetch users";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteUser = async (userId: number): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await apiClient.delete(`/users/${userId}`);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to delete user";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const grantPlatformAdmin = async (userId: number): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await apiClient.post(`/permissions/platform-admin/${userId}`);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to grant platform admin access";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const revokePlatformAdmin = async (userId: number): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await apiClient.delete(`/permissions/platform-admin/${userId}`);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to revoke platform admin access";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    searchUsers,
    assignRole,
    updateRole,
    removeRole,
    getUsersWithRoles,
    getAllUsers,
    deleteUser,
    grantPlatformAdmin,
    revokePlatformAdmin,
    isLoading,
    error,
  };
};
