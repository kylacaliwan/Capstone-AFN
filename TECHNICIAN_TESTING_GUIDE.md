# Quick Testing Guide - Technician Improvements

## Login Credentials
- **Username**: tech1
- **Password**: tech123456
- **Role**: Technician
- **Assigned Tickets**: 10, 11 (both from client3, AC Service)

---

## Test Scenario 1: Complete Job With Proof Images

### Workflow
```
1. Open browser and login as tech1
2. Navigate to "My Jobs"
3. Find ticket #10 or #11 (should show "Not Started")
4. Click "Start Job" button
5. Job status changes to "In Progress"
6. Now can click "Complete Job (with proof)"
```

### Expected Result
- Completion modal appears
- File upload section visible
- "At least one proof image is required" warning shown
- Submit button disabled until images added

### Steps to Complete
```
1. Upload 1-2 test images (screenshot, photo, any image file)
2. Add optional work notes: "AC unit serviced and tested successfully"
3. Click "Complete Job with Proof"
4. See success message
5. Job status changes to "Completed"
```

---

## Test Scenario 2: View Proof Images in History

### Workflow
```
1. After completing job as tech1
2. Navigate to "Job History"
3. Find the completed job
4. Should see "COMPLETED" badge
5. Should see new button: "View Proof Images (2)"
```

### Expected Result
- "View Proof Images" button visible (showing image count)
- Clicking opens full-screen image gallery
- Shows all uploaded images in grid
- Work notes displayed below gallery

### Verification
```
1. Click "View Proof Images" button
2. Modal opens with image gallery
3. See all 1-2 images in grid
4. See work notes: "AC unit serviced and tested successfully"
5. Hover over images to see counter overlay
6. Close modal by clicking "Close" button
```

---

## Test Scenario 3: Map Navigation & Routing

### Workflow
```
1. From "My Jobs", click job details
2. Click "Open Navigation" for a job
3. Map loads with route from your location to job
```

### Expected Results
- Blue polyline shows complete route
- Red marker shows job location
- Blue marker shows your location
- Distance and time estimates visible
- Turn-by-turn directions listed below map

### Map Features to Verify
```
1. ✓ Polyline starts from current location (blue marker)
2. ✓ Polyline ends at job location (red marker)
3. ✓ No disappearing or straight-line artifacts
4. ✓ Map properly zoomed to show entire route
5. ✓ Click "Recalculate Route" - should refresh smoothly
6. ✓ Green overlay appears as you progress (if simulating movement)
```

### Arrival & Completion Check
```
1. In navigation view, look for "Mark Arrived" button
2. If near job location (50m radius), button becomes:
   ✓ "Arrived at site" (green badge)
3. With arrival confirmed + proof images:
   ✓ Can complete job with proof
4. Without arrival:
   ✓ Cannot mark job as completed
```

---

## Test Scenario 4: Complete Workflow (End-to-End)

### Full User Journey
```
Phase 1: Assignment
├─ Login as tech1
├─ Navigate to "My Jobs"
├─ Find ticket #10 (AC Service for client3)
└─ Status: "Not Started"

Phase 2: Start Work
├─ Click "Start Job"
├─ Confirm status change to "In Progress"
├─ (Optional) Click "Open Navigation" to see route
└─ Close navigation after reviewing route

Phase 3: Complete Work
├─ Click "Complete Job (with proof)"
├─ Modal opens with image upload
├─ Upload 1-2 test images
├─ Add work notes (optional)
├─ Click "Complete Job with Proof"
└─ Confirm: Success message + status "Completed"

Phase 4: Verify History
├─ Navigate to "Job History"
├─ Find completed ticket #10
├─ See "COMPLETED" badge with date
├─ Click "View Proof Images (2)"
├─ Gallery shows uploaded images
├─ See work notes section
└─ Close gallery
```

### Success Criteria ✓
- Job status progresses: Not Started → In Progress → Completed
- Proof images required and stored
- Images viewable in history
- Map route displayed correctly
- No errors in browser console

---

## Test Scenario 5: Image Upload Validation

### Test Valid Upload
```
✓ Upload 1 image → "Complete Job" button ENABLED
✓ Upload 2-3 images → Button stays ENABLED
✓ See preview grid of uploaded images
✓ See × button to remove individual images
```

### Test Invalid Upload
```
✗ No images selected → "Complete Job" button DISABLED
✗ Try to submit without images → Error message shown:
   "At least one proof image is required to complete the job."
✗ Button remains disabled until image added
```

### Test Image Removal
```
1. Upload 3 images
2. Click × button on second image
3. Image removed from preview
4. Grid updates to show 2 remaining
5. Button still enabled (1+ images present)
6. Remove all images
7. Warning appears: "At least one proof image is required"
8. Button becomes disabled
```

---

## Test Scenario 6: Map Rendering Issues - Verification

### Before vs After Analysis

**BEFORE Fixes (Issues)**
- Route shows as straight line
- Doesn't start from technician location
- Polyline disappears/flickers
- Map doesn't show full route

**AFTER Fixes (Expected)**
```
✓ Blue polyline shows full curved route
✓ Route starts from blue marker (current location)
✓ Route ends at red marker (job location)
✓ Green overlay shows traveled portion
✓ Map zoomed to show entire route
✓ No flickering when GPS updates
✓ Smoothly updates when button clicked
```

### Technical Verification
```
1. Open Developer Tools (F12)
2. Go to "Sources" tab
3. Set breakpoint in route rendering
4. Verify routeCoords array has correct coordinates
5. Check that polyline positions include start + all waypoints + end
6. Confirm bounds calculation includes all three points
```

---

## Browser Console Checks

Open Developer Tools (F12) and check for:

### No Errors Expected ✓
```
✓ No red errors in console
✓ No CORS errors
✓ No undefined variable errors
✓ No 404 API errors
```

### API Calls Expected ✓
```
POST /api/technician/jobs/{id}/status/ 
  → Update job to "in_progress" status
  → Update job to "completed" status with proof images

GET /api/technician/jobs/
  → Fetch all jobs for technician

GET /api/technician/history/
  → Fetch job history

POST /api/navigation/route/
  → Calculate route from current to job location
```

---

## Troubleshooting

### Issue: "Complete Job (with proof)" button not appearing
**Solution**: 
1. Hard refresh browser (Ctrl+Shift+R)
2. Check job status is "In Progress"
3. Check browser console for errors
4. Verify jobId in URL matches displayed job

### Issue: Images not uploading
**Solution**:
1. Check file is valid image format (JPG, PNG, etc.)
2. Check file size under 5MB
3. Check browser permissions for file access
4. Check network tab in DevTools for upload errors

### Issue: Map route not showing
**Solution**:
1. Check internet connection (OpenStreetMap API needs access)
2. Check job has valid coordinates in database
3. Hard refresh page
4. Check browser console for JavaScript errors
5. Try "Recalculate Route" button

### Issue: Cannot mark as completed
**Solution**:
1. Upload at least 1 proof image
2. Confirm "In Progress" status (not "Not Started")
3. Check arrival confirmation (if required by system)
4. Try hard refresh if button appears disabled
5. Check for validation errors in browser console

### Issue: Proof images not showing in history
**Solution**:
1. Confirm job is marked "Completed"
2. Hard refresh page (Ctrl+Shift+R)
3. Check network tab - verify API response includes images
4. Look for browser console JSON parsing errors
5. Verify images were uploaded with completion

---

## Performance Tips

### For Testing with Many Images
```
1. Keep images under 1MB each
2. Test with 1-2 images first
3. Then test with 3-5 images
4. Monitor browser performance (DevTools)
5. Check memory usage doesn't spike
```

### For Testing Navigation
```
1. Ensure good GPS signal for accuracy
2. Grant location permissions in browser
3. Use Chrome DevTools to simulate location
4. Clear cache between tests
5. Use incognito mode to avoid cache issues
```

---

## Expected Performance

| Task | Expected Time |
|------|--------------|
| Start job | < 1 second |
| Complete with 2 images | 2-3 seconds |
| Load history | 1-2 seconds |
| View proof images | < 1 second |
| Map route calculation | 3-5 seconds |
| Route recalculate | 2-3 seconds |

---

## Sign-Off Verification

After testing all scenarios:

- [ ] Job status transitions work (Not Started → In Progress → Completed)
- [ ] Image upload required and enforced
- [ ] Proof images viewable in history
- [ ] Map route displays without artifacts
- [ ] Green overlay shows progress on route
- [ ] Arrival detection working (if enabled)
- [ ] No console errors or warnings
- [ ] API calls successful (check Network tab)
- [ ] Database stores proof images correctly
- [ ] Performance acceptable (under 5 seconds per operation)

✅ **All tests passing** = Ready for production deployment

---

## Additional Notes

### Test Data Available
- **Technician**: tech1 / tech123456
- **Tickets**: #10, #11 (both pre-assigned to tech1)
- **Client**: client3
- **Service Type**: AC Service - Installation

### Backend Server Status
```
✓ Running on http://localhost:8000
✓ All migrations applied
✓ Database ready
✓ API endpoints accessible
```

### Next Steps After Testing
1. Deploy to staging environment
2. Run automated API tests
3. Performance load testing (100+ concurrent users)
4. Cross-browser compatibility testing
5. Mobile device testing
6. Deploy to production

---

**Last Updated**: April 14, 2026
**Test Environment**: Windows 10, Chrome Browser
**Backend**: Django 4.2.29
**Database**: SQLite (dev), PostgreSQL (production)
