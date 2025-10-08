export enum PermissionRole {
  PLATFORM_ADMIN = "PLATFORM_ADMIN",
  EVSE_ADMIN = "EVSE_ADMIN",
  EVSE_READER = "EVSE_READER",
}

export interface PermissionBase {
  userId: number;
  evidenceSeekerId?: number | null;
  role: PermissionRole;
}

export interface Permission extends PermissionBase {
  id: number;
  createdAt: string;
}

export type PermissionCreate = PermissionBase

export interface PermissionUpdate {
  role?: PermissionRole;
}

export interface UserPermissions {
  userId: number;
  permissions: Permission[];
}
