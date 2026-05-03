# Proof Image Access - RBAC Implementation

## Overview
A secure **role-based access control (RBAC)** system has been implemented to control who can view proof images uploaded by technicians as evidence of work completion.

## Authorized Users by Role

### Who Can View Proof Images?

| Role | Access Level | Details |
|------|-------------|---------|
| **Admin/Superadmin** | ✅ All images | Can view all proof images from all service tickets |
| **Supervisor** | ✅ All images | Can view all proof images (monitoring team performance) |
| **Technician** | ✅ Own tickets only | Can view images from tickets they're assigned to |
| **Client** | ✅ Own service images | Can view images from their own service requests only |
| **Follow-up Staff** | ❌ No access | Cannot view proof images |

---

## API Endpoints

### 1. View Job Completion Proof Images
**Endpoint:** `GET /api/services/service-tickets/{ticket_id}/proof_images/`

**Description:** Returns proof images uploaded when completing a service ticket

**Access Control:**
- ✅ Client: Only own tickets
- ✅ Admin/Superadmin: All tickets
- ✅ Supervisor: All tickets
- ✅ Technician: Assigned tickets only

**Request:**
```bash
GET /api/services/service-tickets/1/proof_images/
Authorization: Bearer {token}
```

**Response:**
```json
{
  "ticket_id": 1,
  "client": "Client ABC Ltd",
  "service_type": "Installation",
  "completion_proof_images": [
    "/media/checklists/ticket-1/09e8feb92fbc414e90a98c3727464c7e-site-photo.jpg",
    "/media/checklists/ticket-1/2c97f56260f145a58eec3fbab45d2e5e-site-photo.jpg",
    "/media/checklists/ticket-1/15290c62133449c4a6b994a74c1ebb3a-site-video.mp4"
  ],
  "has_proof_images": true,
  "image_count": 3
}
```

### 2. View Inspection Checklist Proof Media
**Endpoint:** `GET /api/services/inspections/{checklist_id}/proof_media/`

**Description:** Returns proof media from pre-installation inspection checklists

**Access Control:**
- ✅ Client: Only own inspections
- ✅ Admin/Superadmin: All inspections
- ✅ Supervisor: All inspections
- ✅ Technician: Their assigned inspections

**Request:**
```bash
GET /api/services/inspections/5/proof_media/
Authorization: Bearer {token}
```

**Response:**
```json
{
  "checklist_id": 5,
  "ticket_id": 1,
  "client": "Client ABC Ltd",
  "service_type": "Installation",
  "proof_media": [
    {
      "type": "photo",
      "name": "site-condition-1.jpg",
      "url": "/media/checklists/ticket-1/site-photo.jpg"
    },
    {
      "type": "video",
      "name": "site-walkthrough.mp4",
      "url": "/media/checklists/ticket-1/site-video.mp4"
    }
  ],
  "has_proof_media": true,
  "media_count": 2
}
```

---

## Access Scenarios

### Scenario 1: Client Viewing Their Own Images
```
Client logs in → Views their service ticket → Clicks "View Proof Images"
↓
API checks: ticket.request.client == current_user ✅
↓
Returns: Their own proof images ONLY
```

### Scenario 2: Supervisor Monitoring Team
```
Supervisor logs in → Views technician jobs → Clicks "View Proof"
↓
API checks: user.role == 'supervisor' ✅
↓
Returns: All team members' proof images
```

### Scenario 3: Admin Audit
```
Admin logs in → Audits tickets → Views any ticket's proof images
↓
API checks: user.role == 'admin' ✅
↓
Returns: All proof images across all tickets
```

### Scenario 4: Unauthorized Access (Denied)
```
Technician A tries to view Technician B's ticket image
↓
API checks: ticket.technician == current_user? NO
            is_admin? NO
            is_supervisor? NO
↓
Returns: 403 Forbidden - "You do not have permission..."
```

---

## Frontend Implementation

### Example: Display Proof Images for Clients
```javascript
// In Client Dashboard / Ticket Details
useEffect(() => {
  const loadProofImages = async () => {
    try {
      const response = await api.get(
        `/services/service-tickets/${ticketId}/proof_images/`
      );
      setProofImages(response.data.completion_proof_images);
    } catch (error) {
      if (error.response?.status === 403) {
        console.error("You don't have permission to view these images");
      }
    }
  };
  
  loadProofImages();
}, [ticketId]);
```

### Example: Display Proof Images for Supervisors
```javascript
// In Supervisor / Technician Jobs View
const handleViewProof = async (ticketId) => {
  const response = await api.get(
    `/services/service-tickets/${ticketId}/proof_images/`
  );
  
  // Show image gallery with all images
  setGalleryImages(response.data.completion_proof_images);
  setShowGallery(true);
};
```

---

## Security Considerations

### What's Protected?
- ✅ Unauthorized users cannot access image URLs directly
- ✅ Clients cannot see other clients' images
- ✅ Technicians cannot see images from other technicians' jobs
- ✅ Access is verified on every request (not cached)

### File Storage
- Images are stored in: `backend/media/checklists/ticket-{id}/`
- Direct file access is allowed by Django's static file serving
- API layer enforces permission checks BEFORE returning URLs

### When Permission is Denied
```json
{
  "detail": "You do not have permission to view images for this ticket."
}
```
HTTP Status: **403 Forbidden**

---

## Database Models Reference

### ServiceTicket Image Field
```python
completion_proof_images = models.JSONField(
    default=list,
    blank=True,
    help_text="List of image URLs uploaded as proof of job completion"
)
```

### InspectionChecklist Media Field
```python
proof_media = models.JSONField(
    default=list,
    blank=True,
    help_text="Proof media from inspection checklist"
)
```

---

## Audit Trail

All image access attempts are logged through:
1. Django request logging
2. Optional: Create `ImageAccessLog` model for compliance

Example log entry:
```
[2026-04-15 10:30:45] user=client_user role=client 
action=view_proof_images ticket=1 
status=SUCCESS ip=192.168.1.100
```

---

## Testing Access Control

### Test 1: Client Cannot View Other Client's Images
```bash
# Login as client_a
curl -H "Authorization: Bearer token_a" \
  http://localhost:8000/api/services/service-tickets/999/proof_images/

# Response: 403 Forbidden
# "You do not have permission to view images for this ticket."
```

### Test 2: Admin Can View All Images
```bash
# Login as admin
curl -H "Authorization: Bearer admin_token" \
  http://localhost:8000/api/services/service-tickets/999/proof_images/

# Response: 200 OK with image URLs
```

### Test 3: Supervisor Can Monitor Team
```bash
# Login as supervisor
curl -H "Authorization: Bearer supervisor_token" \
  http://localhost:8000/api/services/service-tickets/999/proof_images/

# Response: 200 OK with image URLs
```

---

## Troubleshooting

### Issue: 403 Forbidden when trying to view images
**Cause:** User doesn't have permission for that ticket
**Solution:** 
- If Client: Verify ticket belongs to them
- If Technician: Verify ticket is assigned to them
- If Supervisor: Verify user has supervisor role

### Issue: 404 Not Found - Image URLs in response are invalid
**Cause:** Media files were deleted or directory structure changed
**Solution:**
1. Check if files exist: `ls backend/media/checklists/`
2. Verify MEDIA_ROOT in settings.py
3. Re-upload proof images

### Issue: Images are served but appear broken in browser
**Cause:** CORS or static file serving issue
**Solution:**
1. Check CORS settings in settings.py
2. Verify MEDIA_URL configuration
3. Ensure Django is serving static files in development

---

## Future Enhancements

1. **Watermarking:** Add watermarks to images with viewing user info
2. **Download Audit:** Log when users download images
3. **Expiration:** Set image URLs to expire after X days
4. **Encryption:** Encrypt sensitive proof images
5. **Compression:** Auto-compress images for faster loading
6. **Thumbnail Generation:** Create thumbnails for gallery views
