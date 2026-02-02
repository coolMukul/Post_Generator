# UI Changelog

## Phase 2 - Ingest Page Updates (2026-02-02)

### Fixed Ingest Page (`app/ingest/page.tsx`)

Updated the ingest page to work correctly with the Phase 2 API implementation.

#### Changes Made:

1. **API Endpoint Corrections**
   - Changed from `http://localhost:3101` to `http://localhost:3000` (matching .env.example)
   - Updated endpoint from `/documents/submit-url` to `/pdf/process`
   - Updated job status endpoint from `/queue/jobs/{jobId}` to `/jobs/{jobId}`

2. **Request/Response Format Updates**
   - Removed `projectKey` parameter (not in API schema)
   - Updated response handling to use API format:
     - `job_id` instead of `jobId`
     - `status` instead of `state`
     - Added `created_at` display
     - Added `message` support

3. **Job Status Updates**
   - Updated TypeScript interfaces to match API schemas
   - Fixed status value mapping:
     - `pending` (was `waiting`)
     - `in_progress` (was `active`)
     - `success` (was `completed`)
     - `failed` (unchanged)
   - Updated status icons and colors accordingly
   - Fixed job result display to show `result.chunks_processed` and `result.document_id`

4. **File Upload**
   - Disabled file upload mode (not yet implemented in API)
   - Added visual indicator showing "Coming Soon"
   - Shows error message if user attempts to use file upload

5. **User Experience Improvements**
   - Added API endpoint information section
   - Shows clearer job status with timestamps
   - Better error message handling (uses `error` field from API)
   - Added helpful note about API server port

#### Testing

To test the ingest page:

1. Ensure API server is running on port 3000
2. Navigate to http://localhost:3001/ingest (or your UI port)
3. Submit a PDF URL (e.g., arXiv paper URL)
4. Watch the real-time job status updates
5. Verify successful completion with document ID

#### API Compatibility

The UI is now compatible with:
- API endpoints defined in `packages/api/src/routes/pdf.routes.ts`
- Job schemas defined in `packages/api/src/types/schemas.ts`
- Job status responses from `packages/api/src/routes/job.routes.ts`
