import { PermissionRole } from "./permission";

export interface User {
  id: number;
  email: string;
  username: string;
  isActive: boolean;
  permissions: Permission[];
}

export interface Permission {
  id: number;
  evidenceSeekerId?: string;
  role: PermissionRole;
  createdAt: string;
}

export interface UserWithPermissions extends User {
  permissions: Permission[];
}

export interface UserSearchResult {
  id: number;
  username: string;
}

export interface UserRoleAssignment {
  userId: number;
  evidenceSeekerId: string;
  role: PermissionRole;
}

export interface UserRoleUpdate {
  role: PermissionRole;
}
