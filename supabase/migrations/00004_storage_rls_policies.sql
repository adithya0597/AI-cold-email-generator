-- Migration: 00004_storage_rls_policies
-- Description: Add Row-Level Security policies to Supabase Storage for per-user file isolation
-- Date: 2026-02-01

-- Enable RLS on storage.objects (may already be enabled by Supabase)
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to upload files to their own folder only
-- Folder structure: {bucket}/{user_id}/{filename}
CREATE POLICY "Users can upload own files"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'resumes'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow authenticated users to read their own files only
CREATE POLICY "Users can read own files"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'resumes'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow authenticated users to update their own files only
CREATE POLICY "Users can update own files"
ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id = 'resumes'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow authenticated users to delete their own files only
CREATE POLICY "Users can delete own files"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'resumes'
    AND (storage.foldername(name))[1] = auth.uid()::text
);
