-- Allow a Group Learning Task to reference a user-hosted Google Drive video.
-- The application stores only the HTTPS share URL; the video remains in the owner's Drive.
ALTER TABLE public.group_learning_tasks
  ADD COLUMN IF NOT EXISTS video_url VARCHAR(2048) NULL;

-- The table already has RLS enabled and direct Data API privileges revoked.
-- FastAPI continues to access it through the configured server-side database role.
