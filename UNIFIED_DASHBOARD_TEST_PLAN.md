# Unified Operations Dashboard - Test Plan & Verification Guide

## Current Implementation Status

✅ **Completed:**
- [x] Created `SharedOperationsDashboard.jsx` component
- [x] Implemented role detection (supervisor vs follow_up)
- [x] Added capability checking for all actions
- [x] Configured routes:
  - `/admin/operations-dashboard` - Superadmin access to shared dashboard
  - `/supervisor/dashboard` - Uses SharedOperationsDashboard with role detection
  - `/follow-up/dashboard` - Uses SharedOperationsDashboard with role detection
- [x] Added "Operations Dashboard" to admin sidebar menu
- [x] Created RBAC documentation

⏳ **Next Steps (Testing Required):**
- [ ] Test supervisor dashboard with full capabilities
- [ ] Test aftersales dashboard with full capabilities
- [ ] Test permission restrictions
- [ ] Test superadmin access to operations dashboard
- [ ] Verify data isolation

---

## Test Accounts

**Available test users:**
```
Admin:      admin1 / admin123
Superadmin: (if superadmin account exists)
Supervisor: supervisor1 / supervisor123
Technician: technician1 / tech123
Client:     client1 / client123
Follow-up:  (if follow_up account exists)
```

---

## Test Scenarios

### Test 1: Supervisor Dashboard - Full Access

**Objective:** Verify supervisor with all capabilities sees complete dashboard

**Setup:**
1. Ensure `supervisor1` has these capabilities:
   - `SUPERVISOR_DASHBOARD_CAPABILITIES`
   - `SUPERVISOR_DISPATCH_CAPABILITIES`
   - `SUPERVISOR_TICKETS_CAPABILITIES`
   - `SUPERVISOR_TRACKING_CAPABILITIES`
   - `SUPERVISOR_USER_ACCESS_CAPABILITIES`

**Steps:**
```
1. Login as supervisor1 / supervisor123
2. Navigate to /supervisor/dashboard
3. Verify page loads without errors
4. Check the following appear:
   ✓ Team Size card (total technicians)
   ✓ Availability Status card
   ✓ Open Tickets card
   ✓ Overdue Tickets card
   ✓ Quick Navigation grid with buttons:
     - Dispatch Board
     - Service Tickets
     - Live Map
     - Staff Access Control
   ✓ Top Performers section
   ✓ Recent Tickets list
```

**Expected Result:**
- All metrics load with actual data
- All action buttons are visible and clickable
- No permission warnings appear
- Navigation to each section works

**Verification Commands:**
```
# In browser console:
console.log(user.role) // Should show: 'supervisor'
console.log(user.capabilities) // Should have all SUPERVISOR_* capabilities
```

---

### Test 2: Supervisor Dashboard - Restricted Access

**Objective:** Verify permission warnings when supervisor lacks capabilities

**Setup:**
1. Using Admin panel, grant `supervisor1` ONLY:
   - `SUPERVISOR_DASHBOARD_CAPABILITIES` (view only, no actions)

2. Remove all other supervisor capabilities:
   - ~~SUPERVISOR_DISPATCH_CAPABILITIES~~
   - ~~SUPERVISOR_TICKETS_CAPABILITIES~~
   - ~~SUPERVISOR_TRACKING_CAPABILITIES~~
   - ~~SUPERVISOR_USER_ACCESS_CAPABILITIES~~

**Steps:**
```
1. Logout supervisor1
2. Remove all action capabilities via /admin/user-management
3. Login as supervisor1 again
4. Navigate to /supervisor/dashboard
5. Verify:
   ✓ Metrics appear (Team Size, etc.)
   ✓ Quick Navigation grid is empty
   ✓ Permission warning shows: "No actions available. Your access is restricted by your superadmin."
   ✓ Top Performers and Recent Tickets still display
```

**Expected Result:**
- Dashboard is read-only
- No action buttons visible
- Clear message explaining restrictions
- Data still visible but non-interactive

---

### Test 3: Aftersales Dashboard - Full Access

**Objective:** Verify aftersales with full capabilities sees complete dashboard

**Setup:**
1. Create or update follow_up user with:
   - `AFTER_SALES_DASHBOARD_CAPABILITIES`
   - `AFTER_SALES_CASE_CAPABILITIES`

2. Or if testing via admin panel, navigate to `/follow-up/dashboard`

**Steps:**
```
1. Login as follow_up user (or aftersales account)
2. Navigate to /follow-up/dashboard
3. Verify:
   ✓ Different metrics than supervisor:
     - Total Cases
     - Open Cases
     - Overdue Cases
     - Due This Week
   ✓ Quick Navigation shows "All Cases" button
   ✓ Recent Cases list appears
   ✓ No supervisor-specific items (dispatch, tracking)
```

**Expected Result:**
- Aftersales-specific metrics display
- Only "All Cases" action available
- No permission warnings
- Clicking "All Cases" navigates to cases page

---

### Test 4: Superadmin Operations Dashboard

**Objective:** Verify superadmin can access shared dashboard from admin panel

**Setup:**
Login as superadmin or admin account

**Steps:**
```
1. Navigate to /admin/dashboard
2. Find "Operations Dashboard" in sidebar under Operations section
3. Click "Operations Dashboard"
4. Verify:
   ✓ Navigate to /admin/operations-dashboard
   ✓ Page loads with operational metrics
   ✓ Can access and view dashboard data
   ✓ All features visible and accessible
```

**Expected Result:**
- Navigation works smoothly
- Page renders without errors
- Dashboard displays operational data

---

### Test 5: Permission Updates Propagate

**Objective:** Verify permission changes take immediate effect after refresh

**Setup:**
1. Login as supervisor1 with restricted access (Test 2)
2. Test shows "No actions available" message

**Steps:**
```
1. Keep supervisor1 logged in
2. Open another browser/incognito and login as admin
3. Navigate to /admin/user-management
4. Find supervisor1 in the list
5. Click "Manage Access"
6. Add SUPERVISOR_DISPATCH_CAPABILITIES
7. Save changes
8. Return to original tab with supervisor1
9. Refresh the /supervisor/dashboard page
10. Verify:
    ✓ Dispatch Board button now appears
    ✓ Permission warning is gone
    ✓ New capability immediately available
```

**Expected Result:**
- Changes reflected after page refresh
- No need to logout/login
- Permissions update dynamically

---

### Test 6: Role Isolation

**Objective:** Verify supervisor cannot access aftersales data

**Setup:**
Two users logged in - supervisor and follow_up

**Steps:**
```
1. Login to two different tabs:
   - Tab 1: supervisor1
   - Tab 2: follow_up user (or test account)

2. In Tab 1 (Supervisor):
   Navigate to /supervisor/dashboard
   Verify: See ticket/dispatch metrics, Dispatch Board button

3. In Tab 2 (Aftersales):
   Navigate to /follow-up/dashboard
   Verify: See case metrics, All Cases button

4. In Tab 1, try to access /follow-up/dashboard directly
   Verify: Permission denied or redirects to supervisor dashboard

5. In Tab 2, try to access /supervisor/dashboard directly
   Verify: Permission denied or redirects to follow_up dashboard
```

**Expected Result:**
- Each role sees only their appropriate dashboard
- Cross-role access is blocked
- Route protection enforces role separation

---

### Test 7: Capability Granularity

**Objective:** Verify individual capability restrictions work correctly

**Setup:**
Grant supervisor1 these capabilities:
- `SUPERVISOR_DASHBOARD_CAPABILITIES`
- `SUPERVISOR_DISPATCH_CAPABILITIES` ✓
- ~~SUPERVISOR_TICKETS_CAPABILITIES~~
- ~~SUPERVISOR_TRACKING_CAPABILITIES~~
- ~~SUPERVISOR_USER_ACCESS_CAPABILITIES~~

**Steps:**
```
1. Login as supervisor1
2. Navigate to /supervisor/dashboard
3. Verify:
   ✓ Dispatch Board button visible and clickable
   ✓ Service Tickets button not visible
   ✓ Live Map button not visible
   ✓ Staff Access Control button not visible
   ✓ Only 1 button in Quick Navigation grid
```

**Expected Result:**
- Exactly matching capability grants
- Unused buttons don't appear
- No "disabled" state showing for missing capabilities
- Clean UI with only authorized actions

---

## Automated Test Script

Save as `test_shared_dashboard.py` in root:

```python
#!/usr/bin/env python
import os
import django
import subprocess
from django.contrib.auth import authenticate

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings')
django.setup()

def test_dashboard_access():
    """Test dashboard access for different roles"""
    
    test_cases = [
        {
            'username': 'supervisor1',
            'password': 'supervisor123',
            'role': 'supervisor',
            'expected_dashboards': ['/supervisor/dashboard', '/admin/operations-dashboard'],
            'forbidden_dashboards': ['/follow-up/dashboard', '/admin/analytics']
        },
        {
            'username': 'technician1',
            'password': 'tech123',
            'role': 'technician',
            'expected_dashboards': ['/technician/dashboard'],
            'forbidden_dashboards': ['/supervisor/dashboard', '/follow-up/dashboard', '/admin/dashboard']
        }
    ]
    
    for test_case in test_cases:
        user = authenticate(
            username=test_case['username'],
            password=test_case['password']
        )
        
        if user:
            print(f"✓ {test_case['username']} authenticated successfully")
            print(f"  Role: {user.role}")
            print(f"  Capabilities: {user.capabilities}")
        else:
            print(f"✗ {test_case['username']} failed to authenticate")

if __name__ == '__main__':
    test_dashboard_access()
```

Run with:
```bash
cd backend
python ../test_shared_dashboard.py
```

---

## Manual Testing Checklist

- [ ] **Test 1:** Supervisor full access works
  - [ ] Metrics display correctly
  - [ ] All 4 buttons visible
  - [ ] Buttons are clickable
  - [ ] No errors in console

- [ ] **Test 2:** Supervisor restricted access shows message
  - [ ] Permission warning appears
  - [ ] Metrics still visible
  - [ ] No action buttons
  - [ ] Message is clear

- [ ] **Test 3:** Aftersales full access works
  - [ ] Different metrics than supervisor
  - [ ] "All Cases" button visible
  - [ ] Recent cases list appears
  - [ ] No dispatcher/tracker items

- [ ] **Test 4:** Superadmin can access operations dashboard
  - [ ] Link appears in sidebar
  - [ ] Navigation works
  - [ ] Page renders

- [ ] **Test 5:** Permission updates propagate
  - [ ] Changes visible after refresh
  - [ ] No logout needed
  - [ ] Buttons appear/disappear correctly

- [ ] **Test 6:** Role isolation enforced
  - [ ] Supervisor can't see aftersales data
  - [ ] Aftersales can't see supervisor data
  - [ ] Cross-role access blocked

- [ ] **Test 7:** Capabilities are granular
  - [ ] Individual capabilities restrict correctly
  - [ ] Only authorized buttons show
  - [ ] No disabled state UI

---

## Troubleshooting

### Issue: Dashboard shows 404 error

**Solution:**
1. Verify `SharedOperationsDashboard.jsx` exists at `frontend/src/pages/shared/SharedOperationsDashboard.jsx`
2. Check import in App.jsx: `const SharedOperationsDashboard = lazy(() => import('./pages/shared/SharedOperationsDashboard'));`
3. Verify routes in App.jsx reference SharedOperationsDashboard

### Issue: Permission warning appears when shouldn't

**Solution:**
1. Run SQL to check user capabilities:
   ```sql
   SELECT * FROM users_user WHERE username = 'supervisor1';
   SELECT * FROM users_capabilitygroup WHERE user_id = (SELECT id FROM users_user WHERE username = 'supervisor1');
   ```
2. Check `hasAnyCapability()` function in `rbac.js`
3. Verify `SUPERVISOR_DISPATCH_CAPABILITIES` constant is exported

### Issue: Buttons not clickable

**Solution:**
1. Check browser console for errors
2. Verify `setDestinationPath()` function exists
3. Check navigation route exists in App.jsx

### Issue: Metrics show as "Loading..." or don't load

**Solution:**
1. Check backend API: `GET /api/dashboard-stats/?dashboard_type=supervisor`
2. Verify `fetchDashboardStats()` in `api.js`
3. Check browser Network tab for failed requests
4. Verify backend returns the correct dashboardType parameter

### Issue: Wrong role display (supervisor seeing aftersales content)

**Solution:**
1. Check `user.role` in browser DevTools
2. Verify `isSupervisor` and `isAftersales` conditions in component
3. Ensure `user?.role` is correctly set from AuthContext
4. Check backend returns correct role in auth response

---

## Performance Monitoring

After testing, verify:

1. **Page Load Time:** Dashboard should load in < 2 seconds
2. **Data Load Time:** Stats should appear within 1 second of page load
3. **Memory Usage:** No memory leaks when navigating between dashboards
4. **API Calls:** Only 1 call to `/api/dashboard-stats/` per page load

---

## Success Criteria

All tests pass when:
- ✅ Supervisor and Aftersales see identical layout
- ✅ Each sees only their role's data
- ✅ Capabilities restrict actions correctly
- ✅ Permission warnings appear when appropriate
- ✅ No console errors
- ✅ Navigation works smoothly
- ✅ Superadmin can access shared dashboard from admin panel
- ✅ Role changes propagate after refresh
- ✅ No cross-role data leakage
