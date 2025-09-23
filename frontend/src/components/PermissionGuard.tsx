import React from "react";
import { usePermissions } from "../hooks/usePermissions";
import { PermissionRole } from "../types/permission";

interface PermissionGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  requiredRole?: PermissionRole;
  evidenceSeekerId?: string;
  platformAdminOnly?: boolean;
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  children,
  fallback = null,
  requiredRole,
  evidenceSeekerId,
  platformAdminOnly = false,
}) => {
  const { hasPlatformAdminAccess, hasEvidenceSeekerAccess } = usePermissions();

  if (platformAdminOnly && !hasPlatformAdminAccess()) {
    return <>{fallback}</>;
  }

  if (
    requiredRole &&
    evidenceSeekerId &&
    !hasEvidenceSeekerAccess(evidenceSeekerId, requiredRole)
  ) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};
