import { useAuth } from "./useAuth";
import { PermissionRole } from "../types/permission";

export const usePermissions = () => {
  const { user } = useAuth();

  const hasPlatformAdminAccess = (): boolean => {
    return (
      user?.permissions?.some(
        (p) => p.role === PermissionRole.PLATFORM_ADMIN
      ) ?? false
    );
  };

  const hasEvidenceSeekerAccess = (
    evidenceSeekerId: string,
    requiredRole: PermissionRole
  ): boolean => {
    if (!user?.permissions) return false;

    // Platform admin has access to all evidence seekers
    if (hasPlatformAdminAccess()) return true;

    // Check if user has the required role for this specific evidence seeker
    return user.permissions.some(
      (p) =>
        p.evidenceSeekerId?.toString() === evidenceSeekerId &&
        p.role === requiredRole
    );
  };

  const canManageEvidenceSeeker = (evidenceSeekerId: string): boolean => {
    return (
      hasEvidenceSeekerAccess(evidenceSeekerId, PermissionRole.EVSE_ADMIN) ||
      hasPlatformAdminAccess()
    );
  };

  const canViewEvidenceSeeker = (evidenceSeekerId: string): boolean => {
    return (
      hasEvidenceSeekerAccess(evidenceSeekerId, PermissionRole.EVSE_ADMIN) ||
      hasEvidenceSeekerAccess(evidenceSeekerId, PermissionRole.EVSE_READER) ||
      hasPlatformAdminAccess()
    );
  };

  const getUserRoleForEvidenceSeeker = (
    evidenceSeekerId: string
  ): PermissionRole | null => {
    if (!user?.permissions) return null;

    const permission = user.permissions.find(
      (p) => p.evidenceSeekerId?.toString() === evidenceSeekerId
    );
    return permission?.role ?? null;
  };

  const isEvidenceSeekerAdmin = (evidenceSeekerId: string): boolean => {
    return hasEvidenceSeekerAccess(evidenceSeekerId, PermissionRole.EVSE_ADMIN);
  };

  const isEvidenceSeekerReader = (evidenceSeekerId: string): boolean => {
    return hasEvidenceSeekerAccess(
      evidenceSeekerId,
      PermissionRole.EVSE_READER
    );
  };

  return {
    hasPlatformAdminAccess,
    hasEvidenceSeekerAccess,
    canManageEvidenceSeeker,
    canViewEvidenceSeeker,
    getUserRoleForEvidenceSeeker,
    isEvidenceSeekerAdmin,
    isEvidenceSeekerReader,
  };
};
