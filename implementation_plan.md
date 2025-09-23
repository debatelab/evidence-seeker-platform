# URL-Based Subroutes for Evidence Seeker Management

## Overview
Implement URL-based routing for Evidence Seeker management tabs to solve the issue where the active tab resets to "Documents" after user management operations. This will provide persistent tab state, bookmarkable URLs, and better browser navigation support.

## Current State Analysis

### Problem
- **Single Route**: `/evidence-seekers/:id/manage` renders one component with client-side tabs
- **State Loss**: Tab state is lost on re-renders (when user management operations complete)
- **No URL Persistence**: Active tab isn't reflected in the URL
- **Re-render Reset**: Operations in `UserRoleManager` cause parent re-renders that reset `activeTab` to "documents"

### Current Architecture
```
App.tsx Route: /evidence-seekers/:evidenceSeekerId/manage
├── EvidenceSeekerManagementWrapper
    └── EvidenceSeekerManagement (with client-side tabs)
        ├── DocumentList
        ├── SearchInterface
        ├── EvidenceSeekerSettings
        ├── UserRoleManager
        └── APIKeyManager
```

## Implementation Strategy

### Target Architecture
```
App.tsx Routes:
├── /evidence-seekers/:evidenceSeekerId/manage (redirects to /documents)
├── /evidence-seekers/:evidenceSeekerId/manage/documents
├── /evidence-seekers/:evidenceSeekerId/manage/search
├── /evidence-seekers/:evidenceSeekerId/manage/settings
├── /evidence-seekers/:evidenceSeekerId/manage/users
└── /evidence-seekers/:evidenceSeekerId/manage/config

EvidenceSeekerManagementWrapper
└── EvidenceSeekerManagement (layout with navigation)
    └── <Outlet /> (renders child routes)
```

## Detailed Implementation Steps

### Phase 1: Update App.tsx Routing

#### 1.1 Add Nested Routes Structure
```typescript
// In App.tsx router configuration
{
  path: "/evidence-seekers/:evidenceSeekerId/manage",
  element: (
    <AppLayout>
      <EvidenceSeekerManagementWrapper />
    </AppLayout>
  ),
  children: [
    {
      path: "documents",
      element: <DocumentWrapper Component={DocumentList} />
    },
    {
      path: "search",
      element: <DocumentWrapper Component={SearchInterface} />
    },
    {
      path: "settings",
      element: <DocumentWrapper Component={EvidenceSeekerSettings} />
    },
    {
      path: "users",
      element: <DocumentWrapper Component={UserRoleManager} />
    },
    {
      path: "config",
      element: <DocumentWrapper Component={APIKeyManager} />
    },
    {
      index: true,
      element: <Navigate to="documents" replace />
    }
  ]
}
```

#### 1.2 Update DocumentWrapper for All Components
Currently `DocumentWrapper` only handles components that need `evidenceSeekerUuid`. Update it to work with all tab components:

```typescript
const TabWrapper = ({
  Component,
  needsEvidenceSeeker = true
}: {
  Component: React.ComponentType<any>;
  needsEvidenceSeeker?: boolean;
}) => {
  // ... existing Evidence Seeker resolution logic ...

  if (needsEvidenceSeeker && !evidenceSeeker) {
    return <LoadingComponent />;
  }

  return needsEvidenceSeeker
    ? <Component evidenceSeekerUuid={evidenceSeeker.uuid} />
    : <Component evidenceSeekerId={evidenceSeekerId} />;
};
```

### Phase 2: Refactor EvidenceSeekerManagement Component

#### 2.1 Remove Client-Side Tab State
```typescript
// Remove these state variables
const [activeTab, setActiveTab] = useState<TabType>("documents");

// Remove this useEffect that sets default tab
```

#### 2.2 Add Route-Based Navigation Logic
```typescript
import { useLocation, useNavigate } from "react-router";

// Get current tab from URL
const location = useLocation();
const navigate = useNavigate();

const getActiveTabFromPath = (): TabType => {
  const pathParts = location.pathname.split('/');
  const lastPart = pathParts[pathParts.length - 1];
  return (tabs.find(tab => tab.id === lastPart)?.id as TabType) || "documents";
};

const activeTab = getActiveTabFromPath();
```

#### 2.3 Update Tab Navigation
```typescript
// Replace onClick handlers
onClick={() => setActiveTab(tab.id)}

// With navigation
onClick={() => navigate(tab.id)}
```

#### 2.4 Replace renderTabContent with Outlet
```typescript
// Remove renderTabContent function
// Remove the content area that renders based on activeTab

// Add Outlet for child routes
import { Outlet } from "react-router";

<div className="p-6">
  {/* Tab Description */}
  <div className="mb-6">
    {tabs.map((tab) => {
      if (tab.id === activeTab) {
        // ... existing tab description logic ...
      }
      return null;
    })}
  </div>

  {/* Content - now rendered by child routes */}
  <Outlet />
</div>
```

### Phase 3: Update Component Props

#### 3.1 Update UserRoleManager Props
`UserRoleManager` currently receives `evidenceSeekerId` as a string ID, but needs to work with UUID. Update the component to accept `evidenceSeekerUuid`:

```typescript
interface UserRoleManagerProps {
  evidenceSeekerUuid: string;  // Changed from evidenceSeekerId
}
```

#### 3.2 Update All Tab Components
Ensure all tab components can receive `evidenceSeekerUuid` prop consistently.

### Phase 4: Add Backward Compatibility

#### 4.1 Add Redirect from Old Route
```typescript
// In App.tsx, add a catch-all redirect
{
  path: "/evidence-seekers/:evidenceSeekerId/manage",
  element: <Navigate to="/evidence-seekers/:evidenceSeekerId/manage/documents" replace />,
  // Only when there are no child routes matched
}
```

#### 4.2 Handle Direct Links
Ensure all internal navigation uses the new routes.

### Phase 5: Testing & Validation

#### 5.1 Test Tab Persistence
- Navigate to different tabs
- Perform user management operations
- Verify tab stays active after operations complete
- Test browser back/forward buttons

#### 5.2 Test URL Behavior
- Bookmark specific tabs
- Refresh page on different tabs
- Share URLs with team members

#### 5.3 Test Navigation Flow
- Click tab navigation
- Use browser navigation
- Test mobile responsiveness

#### 5.4 Update Tests
- Update existing component tests
- Add routing integration tests
- Test error boundaries

### Phase 6: Documentation Updates

#### 6.1 Update README.md
- Document new URL structure
- Update navigation examples

#### 6.2 Update Component Documentation
- Update EvidenceSeekerManagement component docs
- Document new prop interfaces

## Implementation Checklist

### Phase 1: Routing Updates
- [ ] Update App.tsx with nested routes structure
- [ ] Add Navigate component for index route
- [ ] Update DocumentWrapper to TabWrapper for all components
- [ ] Test route navigation works

### Phase 2: Component Refactoring
- [ ] Remove client-side tab state from EvidenceSeekerManagement
- [ ] Add useLocation/useNavigate hooks
- [ ] Implement getActiveTabFromPath logic
- [ ] Update tab navigation to use navigate()
- [ ] Replace renderTabContent with Outlet

### Phase 3: Component Updates
- [ ] Update UserRoleManager to accept evidenceSeekerUuid
- [ ] Ensure all tab components work with consistent props
- [ ] Update any component-specific prop passing

### Phase 4: Compatibility
- [ ] Add backward compatibility redirects
- [ ] Update any hardcoded navigation links
- [ ] Test existing functionality still works

### Phase 5: Testing
- [ ] Test tab persistence across operations
- [ ] Test URL bookmarking and sharing
- [ ] Test browser navigation (back/forward)
- [ ] Update and run test suites

### Phase 6: Documentation
- [ ] Update README with new URL structure
- [ ] Document component interface changes
- [ ] Update any user-facing documentation

## Success Criteria

1. **Tab Persistence**: Active tab survives user management operations
2. **URL Reflection**: Current tab is shown in browser URL
3. **Bookmarkable**: Users can bookmark and share specific tab URLs
4. **Browser Navigation**: Back/forward buttons work correctly
5. **Backward Compatibility**: Old links redirect to appropriate tabs
6. **No Route Changes**: User management operations don't trigger navigation

## Rollback Plan

If issues arise:
1. Revert App.tsx route changes
2. Restore client-side tab logic in EvidenceSeekerManagement
3. Keep existing component interfaces
4. No database changes needed

## Risk Assessment

- **Low Risk**: Adding routes alongside existing functionality
- **Low Risk**: Outlet pattern is standard React Router practice
- **Medium Risk**: Component prop interface changes
- **Low Risk**: Backward compatibility redirects prevent breaking changes

## Dependencies

- React Router DOM (already installed)
- No backend changes required
- No database changes required

## Timeline Estimate

- Phase 1 (Routing): 1-2 hours
- Phase 2 (Component Refactor): 2-3 hours
- Phase 3 (Component Updates): 1 hour
- Phase 4 (Compatibility): 30 minutes
- Phase 5 (Testing): 1-2 hours
- Phase 6 (Documentation): 30 minutes

**Total Estimate**: 6-9 hours
