# Unified Operations Dashboard - RBAC Implementation Guide

## Overview

The Unified Operations Dashboard is a shared interface available to **Supervisor**, **Aftersales (follow_up)**, and **Superadmin** roles. Through role-based access control (RBAC), each role sees the same dashboard interface but with restricted access to certain features and data.

## Access Points

### Routes

1. **Shared Admin Route** (for Superadmin oversight)
   - Path: `/admin/operations-dashboard`
   - Accessible by: `superadmin`, `admin`, `supervisor`, `follow_up`
   - Purpose: Centralized monitoring and management

2. **Supervisor Route**
   - Path: `/supervisor/dashboard`
   - Accessible by: Users with role `supervisor` + `SUPERVISOR_DASHBOARD_CAPABILITIES`
   - Purpose: Operations oversight and team management

3. **Aftersales Route**
   - Path: `/follow-up/dashboard`
   - Accessible by: Users with role `follow_up` + `AFTER_SALES_NAV_CAPABILITIES`
   - Purpose: Customer follow-up case management

## Role-Based Features

### Supervisor Dashboard

**Visible Components:**
- Team Size (total technicians)
- Availability Status (available technicians percentage)
- Open Tickets (pending work)
- Overdue Tickets (urgent items)
- Top Performers (technician performance)
- Recent Tickets (latest service updates)

**Role-Based Actions:**

| Action | Capability | Visible | Clickable |
|--------|-----------|---------|-----------|
| View Dispatch Board | `SUPERVISOR_DISPATCH_CAPABILITIES` | conditional | if granted |
| View Service Tickets | `SUPERVISOR_TICKETS_CAPABILITIES` | conditional | if granted |
| Track Technicians | `SUPERVISOR_TRACKING_CAPABILITIES` | conditional | if granted |
| Manage Staff Access | `SUPERVISOR_USER_ACCESS_CAPABILITIES` | conditional | if granted |

**Permission Warning:**
If a supervisor has no capabilities, they see:
> "No actions available. Your access is restricted by your superadmin."

### Aftersales Dashboard

**Visible Components:**
- Total Cases (all case statuses)
- Open Cases (actionable items)
- Overdue Cases (SLA breaches)
- Recent Cases (latest follow-ups)

**Role-Based Actions:**

| Action | Capability | Visible | Clickable |
|--------|-----------|---------|-----------|
| View All Cases | `AFTER_SALES_CASE_CAPABILITIES` | conditional | if granted |

**Permission Warning:**
If an aftersales user has no capabilities, they see:
> "No actions available. Your access is restricted by your superadmin."

### Superadmin/Admin Dashboard

**Capabilities:**
- View full admin dashboard at `/admin/dashboard`
- Access shared operations dashboard at `/admin/operations-dashboard`
- Manage all role capabilities through the user management interface

## Implementation Details

### Component: SharedOperationsDashboard

**File:** `frontend/src/pages/shared/SharedOperationsDashboard.jsx`

**Key Logic:**

1. **Role Detection**
   ```javascript
   const isSupervisor = user?.role === 'supervisor';
   const isAftersales = user?.role === 'follow_up';
   ```

2. **Capability Checks**
   ```javascript
   const canAccessDispatch = hasAnyCapability(user, SUPERVISOR_DISPATCH_CAPABILITIES) && isSupervisor;
   const canAccessCases = hasAnyCapability(user, AFTER_SALES_CASE_CAPABILITIES) && isAftersales;
   ```

3. **Conditional Rendering**
   ```javascript
   {quickLinks.length > 0 && (
     <div className="mb-8">
       <h2>Quick Navigation</h2>
       <QuickNavGrid items={quickLinks} />
     </div>
   )}
   ```

4. **Data Fetching**
   - Fetches role-specific data using `fetchDashboardStats(dashboardType)`
   - Returns filtered metrics based on role
   - Shows only authorized information

### How Permissions Work

#### 1. Initial Load
- User logs in with their role (supervisor/follow_up)
- SharedOperationsDashboard detects the role from `user.role`
- Loads appropriate data endpoint based on role

#### 2. Capability Evaluation
- For each action (Dispatch Board, View Cases, etc.), check:
  ```javascript
  hasAnyCapability(user, REQUIRED_CAPABILITY) && userHasCorrectRole
  ```
- If capability is missing, item is not added to `quickLinks` array
- If no capabilities, permission warning is displayed

#### 3. Dynamic UI Rendering
- Only authorized items are rendered
- Greyed-out items don't appear (not rendered at all)
- Error messages guide users when access is denied

## Superadmin Control Panel

### Granting Access

1. Navigate to `/admin/user-management`
2. Find the target user (supervisor or aftersales)
3. Click "Manage access"
4. Grant/revoke capabilities:
   - **For Supervisors:** Select `SUPERVISOR_DISPATCH_CAPABILITIES`, `SUPERVISOR_TICKETS_CAPABILITIES`, etc.
   - **For Aftersales:** Select `AFTER_SALES_CASE_CAPABILITIES`

5. Save changes
6. User sees updated dashboard on next login or refresh

### Capabilities Reference

**Supervisor Capabilities:**
- `SUPERVISOR_DASHBOARD_VIEW`: View dashboard
- `SUPERVISOR_DISPATCH_CAPABILITIES`: Access dispatch board
- `SUPERVISOR_TICKETS_CAPABILITIES`: View service tickets
- `SUPERVISOR_TRACKING_CAPABILITIES`: Track technicians
- `SUPERVISOR_USER_ACCESS_CAPABILITIES`: Manage staff permissions

**Aftersales Capabilities:**
- `AFTER_SALES_DASHBOARD_VIEW`: View dashboard  
- `AFTER_SALES_CASE_CAPABILITIES`: Manage cases
- `AFTER_SALES_NAV_CAPABILITIES`: Overall aftersales access

## Security Guarantees

### Backend Protection
1. **API Filtering:** Backend returns only data user is authorized to see
2. **Permission Checks:** API endpoints verify capabilities before returning data
3. **Role Verification:** Requests with wrong role are rejected

### Frontend Protection
1. **Route Guards:** `ProtectedRoute` component verifies role before rendering
2. **Capability Checks:** UI conditionally renders based on capabilities
3. **Action Disabling:** Buttons/links only appear if user has permission

### Data Privacy
- Supervisors cannot see aftersales data
- Aftersales users cannot access dispatch/ticket management
- Each role sees only their authorized metrics and actions

## Testing the Implementation

### Test Case 1: Supervisor with Full Access
```
1. Create supervisor user with all capabilities
2. Navigate to /supervisor/dashboard
3. Verify all quick navigation buttons appear
4. Verify team metrics display correctly
5. Click each button to confirm navigation works
```

### Test Case 2: Supervisor with Restricted Access
```
1. Create supervisor user with only SUPERVISOR_DASHBOARD_VIEW
2. Navigate to /supervisor/dashboard
3. Verify only metrics appear, no action buttons
4. Verify permission warning appears
```

### Test Case 3: Aftersales with Full Access
```
1. Create follow_up user with AFTER_SALES_CASE_CAPABILITIES
2. Navigate to /follow-up/dashboard
3. Verify case metrics and quick nav appear
4. Click "All Cases" to confirm navigation
```

### Test Case 4: Superadmin Granting Access
```
1. Login as superadmin
2. Navigate to /admin/user-management
3. Find supervisor user
4. Click "Manage Access"
5. Select SUPERVISOR_DISPATCH_CAPABILITIES
6. Save changes
7. Login as supervisor
8. Verify Dispatch Board button now appears
```

## Future Enhancements

1. **Real-time Updates:** Add WebSocket support for live metrics
2. **Custom Metrics:** Allow superadmin to customize dashboard metrics per role
3. **Export Capabilities:** Add ability to export dashboard data (with role restrictions)
4. **Audit Logging:** Track which users accessed what data
5. **Performance Optimization:** Cache role-specific data sections
6. **Mobile Responsive:** Improve mobile layout for supervisors/aftersales on field devices

## Migration Path

If migrating from separate dashboards:

1. **Phase 1:** Create SharedOperationsDashboard (✓ done)
2. **Phase 2:** Route both roles to shared dashboard (✓ done)
3. **Phase 3:** Keep old dashboards available for 30 days
4. **Phase 4:** Archive old dashboard components
5. **Phase 5:** Promote unified dashboard as primary interface

## Related Files

- **Component:** `/frontend/src/pages/shared/SharedOperationsDashboard.jsx`
- **Routes:** `/frontend/src/App.jsx`
- **RBAC Logic:** `/frontend/src/rbac.js`
- **API:** Backend serves role-specific data from `/api/dashboard-stats/`

## Support & Troubleshooting

### Issue: Dashboard shows permission warning
**Solution:** Superadmin needs to grant capabilities. Navigate to `/admin/user-management` and assign the required capabilities.

### Issue: User can't see dashboard metrics
**Solution:** Verify user has the base dashboard capability:
- For Supervisor: `SUPERVISOR_DASHBOARD_CAPABILITIES`
- For Aftersales: `AFTER_SALES_DASHBOARD_CAPABILITIES`

### Issue: Action buttons not appearing
**Solution:** User likely lacks the specific action capability. Superadmin should grant:
- For Dispatch: `SUPERVISOR_DISPATCH_CAPABILITIES`
- For Cases: `AFTER_SALES_CASE_CAPABILITIES`
- For Tracking: `SUPERVISOR_TRACKING_CAPABILITIES`
