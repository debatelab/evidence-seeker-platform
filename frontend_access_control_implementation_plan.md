# Frontend Access Control Implementation Plan

## Overview

Implement comprehensive frontend access control system integrating user authentication, role-based permissions, direct user role assignment, and access error handling. The system will support three user roles (PLATFORM_ADMIN, EVSE_ADMIN, EVSE_READER) with appropriate UI restrictions and management interfaces.

**Simplified Approach**: EVSE admins can directly assign roles to existing users. Users receive email notifications when roles are assigned/removed. If users aren't registered yet, they need to register normally to access the system.

## Backend Requirements

### New Models and APIs Needed

**Email Notification Model:**
- `id`: Primary key
- `recipient_email`: Email address to notify
- `notification_type`: Enum (ROLE_ASSIGNED, ROLE_REMOVED, ACCESS_GRANTED, etc.)
- `evidence_seeker_id`: Related evidence seeker (optional)
- `role`: UserRole that was assigned/removed (optional)
- `sent_by`: User ID who triggered the notification
- `status`: Enum (PENDING, SENT, FAILED)
- `created_at`: Datetime

**Email Service (Simple Implementation):**
- Store email sending requests in database
- No actual SMTP sending yet
- Basic email template system for role changes

**Additional Permission APIs:**
- `GET /api/v1/permissions/users` - List all users with their roles (platform admin only)
- `GET /api/v1/users` - List all registered users (for role assignment)
- Enhanced permission APIs for role assignment/removal with email notifications

## Frontend Implementation

### Phase 1: Authentication & Error Handling

#### Files to Create/Modify:

**1. Enhanced Auth Context (`frontend/src/context/AuthContext.tsx`)**
- Add user role information to auth state
- Add permission checking utilities
- Handle 401/403 errors globally

**2. Permission Hooks (`frontend/src/hooks/usePermissions.ts`)**
```typescript
// Permission checking utilities
const usePermissions = () => {
  const { user } = useAuth();

  const hasPlatformAdminAccess = () => {
    return user?.permissions?.some(p => p.role === 'PLATFORM_ADMIN');
  };

  const hasEvidenceSeekerAccess = (evidenceSeekerId: string, requiredRole: UserRole) => {
    // Check if user has required role for specific evidence seeker
  };

  const canManageEvidenceSeeker = (evidenceSeekerId: string) => {
    return hasEvidenceSeekerAccess(evidenceSeekerId, 'EVSE_ADMIN') ||
           hasPlatformAdminAccess();
  };

  return { hasPlatformAdminAccess, hasEvidenceSeekerAccess, canManageEvidenceSeeker };
};
```

**3. Error Boundary Enhancement (`frontend/src/components/ErrorBoundary.tsx`)**
- Handle authentication errors
- Show appropriate error messages for 401/403 responses
- Redirect to login on authentication failures

**4. API Error Handling (`frontend/src/utils/api.ts`)**
- Global error interceptor for auth errors
- Automatic token refresh on 401
- User-friendly error messages for permission denied

### Phase 2: User Role Assignment System

#### Files to Create:

**1. User Types (`frontend/src/types/user.ts`)**
```typescript
export interface User {
  id: string;
  email: string;
  isActive: boolean;
  permissions: Permission[];
}

export interface Permission {
  id: string;
  evidenceSeekerId?: string;
  role: UserRole;
  createdAt: string;
}
```

**2. User Management Components:**

**UserSearch (`frontend/src/components/User/UserSearch.tsx`)**
- Search input for finding users by email
- User selection dropdown/list
- Loading states and error handling

**RoleAssignmentForm (`frontend/src/components/User/RoleAssignmentForm.tsx`)**
- User selection (via UserSearch)
- Role selection dropdown (EVSE_ADMIN/EVSE_READER)
- Submit button with confirmation
- Success/error feedback

**3. User Management Hooks (`frontend/src/hooks/useUserManagement.ts`)**
```typescript
export const useUserManagement = () => {
  const searchUsers = async (query: string) => {
    // Search users by email
  };

  const assignRole = async (userId: string, evidenceSeekerId: string, role: UserRole) => {
    // Assign role to user with email notification
  };

  const removeRole = async (userId: string, evidenceSeekerId: string) => {
    // Remove user's role with email notification
  };

  const getUsersWithRoles = async (evidenceSeekerId: string) => {
    // Get all users with roles for evidence seeker
  };

  return { searchUsers, assignRole, removeRole, getUsersWithRoles };
};
```

### Phase 3: Role Management UI

#### Evidence Seeker Role Management

**Enhanced EvidenceSeekerSettings (`frontend/src/components/EvidenceSeeker/EvidenceSeekerSettings.tsx`)**
- Add "User Management" tab/section
- Show current users with roles for this evidence seeker
- Add user search and role assignment form
- Role modification dropdowns (EVSE_ADMIN ↔ EVSE_READER)
- Remove user functionality

**UserRoleManager (`frontend/src/components/EvidenceSeeker/UserRoleManager.tsx`)**
- List users with access to current evidence seeker
- User search component for finding existing users
- Role assignment form with confirmation
- Change existing user roles
- Remove user access (with confirmation)

#### Platform Admin Panel

**PlatformSettings Page (`frontend/src/pages/PlatformSettings.tsx`)**
- New route: `/platform-settings`
- Only accessible to PLATFORM_ADMIN users
- User management across entire platform

**PlatformUserManager (`frontend/src/components/Platform/PlatformUserManager.tsx`)**
- List all users in system with their roles
- Grant/revoke PLATFORM_ADMIN role to/from users
- View user permissions across all evidence seekers
- Search and filter users

### Phase 4: UI Permission Guards

#### Permission-Based Components:

**1. PermissionGuard (`frontend/src/components/PermissionGuard.tsx`)**
```typescript
interface PermissionGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  requiredRole?: UserRole;
  evidenceSeekerId?: string;
  platformAdminOnly?: boolean;
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  children,
  fallback = null,
  requiredRole,
  evidenceSeekerId,
  platformAdminOnly = false
}) => {
  const { hasPlatformAdminAccess, hasEvidenceSeekerAccess } = usePermissions();

  if (platformAdminOnly && !hasPlatformAdminAccess()) {
    return <>{fallback}</>;
  }

  if (requiredRole && evidenceSeekerId && !hasEvidenceSeekerAccess(evidenceSeekerId, requiredRole)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};
```

**2. Conditional UI Elements:**
- Hide/show buttons based on permissions
- Disable form fields for read-only users
- Show different navigation options

### Phase 5: Enhanced Error Handling

#### Error Components:

**1. AccessDeniedMessage (`frontend/src/components/Error/AccessDeniedMessage.tsx`)**
- User-friendly message for 403 errors
- Contact admin information
- Request access functionality

**2. AuthRequiredMessage (`frontend/src/components/Error/AuthRequiredMessage.tsx`)**
- Message for 401 errors
- Login prompt
- Redirect to login page

**3. Global Error Handler:**
- Intercept API errors in api utility
- Show toast notifications for auth errors
- Handle token expiration gracefully

## Implementation Order

### Week 1: Core Authentication & Permissions
1. Enhance AuthContext with role information
2. Create usePermissions hook
3. Implement PermissionGuard component
4. Add global error handling for auth errors
5. Update existing components to use permission guards

### Week 2: User Role Assignment System
1. Create User types and schemas
2. Implement user search API and component
3. Create role assignment form component
4. Build useUserManagement hook
5. Add email notification system (database storage)

### Week 3: Evidence Seeker Role Management
1. Enhance EvidenceSeekerSettings with user management tab
2. Create UserRoleManager component for evidence seekers
3. Implement role assignment/removal functionality
4. Add user search and role change UI
5. Integrate with permission system

### Week 4: Platform Admin Panel
1. Create PlatformSettings page and routing
2. Implement PlatformUserManager component
3. Add platform-wide user management
4. Enable PLATFORM_ADMIN role assignment/removal
5. Complete user search and management UI

### Week 5: Testing & Polish
1. Comprehensive testing of permission guards
2. Error handling edge cases
3. UI/UX improvements for role management
4. Documentation updates

## Dependencies

- Existing: React, TypeScript, React Router, Axios
- New: None required (all built with existing stack)

## Testing Strategy

### Unit Tests:
- Permission checking utilities
- Permission guard components
- API error handling

### Integration Tests:
- Complete user invitation flow
- Role assignment workflows
- Access control scenarios

### E2E Tests:
- Login → Access restricted content
- User invitation → Registration → Role assignment
- Permission-based UI state changes

## Security Considerations

1. **Client-side Security**: Remember client-side permission checks are for UX only - all server-side checks remain critical
2. **Token Management**: Implement proper token refresh and expiration handling
3. **Error Information**: Avoid exposing sensitive information in error messages
4. **Invitation Tokens**: Secure token generation and expiration
5. **Audit Logging**: Track permission changes and invitations for security auditing

## Future Enhancements

1. **Email Integration**: Replace database email storage with actual SMTP service
2. **Bulk Operations**: Allow bulk user invitations and role assignments
3. **Advanced Permissions**: Time-based permissions, conditional access rules
4. **User Groups**: Organize users into groups with inherited permissions
5. **Audit Dashboard**: Admin interface for viewing permission change history
