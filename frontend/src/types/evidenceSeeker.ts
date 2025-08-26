export interface EvidenceSeeker {
  id: number;
  uuid: string; // External API identifier
  title: string;
  description: string;
  logoUrl: string | null;
  isPublic: boolean;
  createdBy: number;
  createdAt: string;
  updatedAt: string;
}

export interface EvidenceSeekerCreate {
  title: string;
  description: string;
  isPublic?: boolean;
}

export interface EvidenceSeekerUpdate {
  title?: string;
  description?: string;
  isPublic?: boolean;
}

export interface Permission {
  id: number;
  userId: number;
  evidenceSeekerId: number;
  role: "evse_admin" | "evse_reader";
  createdAt: string;
}

export interface PermissionCreate {
  userId: number;
  evidenceSeekerId: number;
  role: "evse_admin" | "evse_reader";
}
