/**
 * ResumeUpload -- drag-and-drop resume upload with LinkedIn URL secondary input.
 *
 * Primary: PDF/DOCX drag-and-drop via react-dropzone (max 10MB).
 * Secondary: LinkedIn URL text input with validation and 15-second timeout.
 *
 * Stories: 1-1 (LinkedIn URL), 1-2 (Resume Upload), 1-5 (Error/Loading states)
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { useApiClient } from '../../services/api';
import { useAnalytics } from '../../hooks/useAnalytics';
import type { ExtractedProfile } from '../../types/onboarding';

interface ResumeUploadProps {
  onProfileExtracted: (profile: ExtractedProfile) => void;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
};
const LINKEDIN_TIMEOUT_MS = 15_000;

export default function ResumeUpload({ onProfileExtracted }: ResumeUploadProps) {
  const apiClient = useApiClient();
  const { track } = useAnalytics();

  const [isUploading, setIsUploading] = useState(false);
  const [isExtractingLinkedIn, setIsExtractingLinkedIn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [linkedInUrl, setLinkedInUrl] = useState('');
  const [linkedInTimedOut, setLinkedInTimedOut] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  // ---- Resume Upload ----

  const onDrop = useCallback(
    async (acceptedFiles: File[], rejectedFiles: unknown[]) => {
      setError(null);
      setLinkedInTimedOut(false);

      if (rejectedFiles && (rejectedFiles as Array<unknown>).length > 0) {
        setError('Please upload a PDF or DOCX file under 10MB.');
        return;
      }

      const file = acceptedFiles[0];
      if (!file) return;

      setSelectedFile(file);
      track('profile_extraction_method_chosen', { method: 'resume' });
      await uploadResume(file);
    },
    [apiClient, track]
  );

  const uploadResume = async (file: File) => {
    setIsUploading(true);
    setUploadProgress(0);
    setError(null);

    track('resume_uploaded', { file_type: file.name.split('.').pop(), file_size: file.size });

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await apiClient.post('/api/v1/onboarding/resume/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            setUploadProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
          }
        },
      });

      track('profile_extraction_completed', { method: 'resume' });
      onProfileExtracted(response.data);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const detail = axiosError?.response?.data?.detail;
      const message =
        detail || 'Something went wrong while processing your resume. Please try again.';
      setError(message);
      track('profile_extraction_failed', { method: 'resume', error: message });
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_FILE_SIZE,
    maxFiles: 1,
    disabled: isUploading || isExtractingLinkedIn,
  });

  // ---- LinkedIn URL ----

  const isValidLinkedInUrl = (url: string): boolean => {
    return url.includes('linkedin.com/in/');
  };

  const handleLinkedInSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLinkedInTimedOut(false);

    if (!linkedInUrl.trim()) {
      setError('Please enter a LinkedIn profile URL.');
      return;
    }

    if (!isValidLinkedInUrl(linkedInUrl)) {
      setError('Please enter a valid LinkedIn profile URL (e.g., linkedin.com/in/yourname).');
      return;
    }

    track('profile_extraction_method_chosen', { method: 'linkedin' });
    setIsExtractingLinkedIn(true);

    // Set a 15-second timeout
    timeoutRef.current = setTimeout(() => {
      setLinkedInTimedOut(true);
    }, LINKEDIN_TIMEOUT_MS);

    try {
      const response = await apiClient.post('/api/v1/onboarding/linkedin/extract', {
        url: linkedInUrl,
      });

      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      track('profile_extraction_completed', { method: 'linkedin' });
      onProfileExtracted(response.data);
    } catch (err: unknown) {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const detail = axiosError?.response?.data?.detail;
      setError(
        detail ||
          "We couldn't access that profile. Try uploading your resume instead."
      );
      track('profile_extraction_failed', { method: 'linkedin', error: detail || 'unknown' });
    } finally {
      setIsExtractingLinkedIn(false);
    }
  };

  // ---- Loading / Timeout States ----

  if (isUploading) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border-2 border-indigo-200 bg-indigo-50 p-12 text-center">
        <div className="mb-4">
          <svg
            className="mx-auto h-12 w-12 animate-spin text-indigo-500"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        </div>
        <p className="text-lg font-medium text-indigo-700">Your agent is reading your resume...</p>
        <p className="mt-1 text-sm text-indigo-500">This usually takes 10-30 seconds</p>
        {uploadProgress > 0 && uploadProgress < 100 && (
          <div className="mt-4 w-64">
            <div className="h-2 rounded-full bg-indigo-200">
              <div
                className="h-2 rounded-full bg-indigo-600 transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-indigo-400">Uploading... {uploadProgress}%</p>
          </div>
        )}
      </div>
    );
  }

  if (isExtractingLinkedIn) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border-2 border-indigo-200 bg-indigo-50 p-12 text-center">
        <div className="mb-4">
          <svg
            className="mx-auto h-12 w-12 animate-spin text-indigo-500"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        </div>
        <p className="text-lg font-medium text-indigo-700">Your agent is reading your profile...</p>
        <p className="mt-1 text-sm text-indigo-500">This usually takes a few seconds</p>
        {linkedInTimedOut && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-medium text-amber-800">
              This is taking longer than expected.
            </p>
            <p className="mt-1 text-sm text-amber-600">
              Try uploading your resume instead for faster results.
            </p>
            <button
              type="button"
              onClick={() => {
                setIsExtractingLinkedIn(false);
                setLinkedInTimedOut(false);
                if (timeoutRef.current) clearTimeout(timeoutRef.current);
              }}
              className="mt-2 text-sm font-medium text-indigo-600 hover:text-indigo-500"
            >
              Cancel and upload resume
            </button>
          </div>
        )}
      </div>
    );
  }

  // ---- Main Upload UI ----

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900">Let's get to know you</h2>
        <p className="mt-2 text-gray-600">
          Upload your resume so your agent can learn about your experience and skills.
        </p>
      </div>

      {/* Error display */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex">
            <svg className="h-5 w-5 flex-shrink-0 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <p className="ml-3 text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Drag-and-drop upload zone */}
      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors sm:p-12 ${
          isDragActive
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-gray-300 bg-white hover:border-indigo-400 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-indigo-100">
          <svg className="h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
        </div>

        {selectedFile ? (
          <>
            <p className="text-lg font-medium text-gray-900">{selectedFile.name}</p>
            <p className="mt-1 text-sm text-gray-500">
              {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB
            </p>
            <p className="mt-2 text-sm text-indigo-600">Click or drop a different file to replace</p>
          </>
        ) : (
          <>
            {isDragActive ? (
              <p className="text-lg font-medium text-indigo-600">Drop your resume here</p>
            ) : (
              <>
                <p className="text-lg font-medium text-gray-900">
                  Drag and drop your resume here
                </p>
                <p className="mt-1 text-sm text-gray-500">
                  or <span className="text-indigo-600 font-medium">browse files</span>
                </p>
              </>
            )}
            <p className="mt-3 text-xs text-gray-400">PDF or DOCX, up to 10MB</p>
          </>
        )}
      </div>

      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-200" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-gradient-to-br from-blue-50 to-indigo-100 px-4 text-gray-500">
            or
          </span>
        </div>
      </div>

      {/* LinkedIn URL input */}
      <form onSubmit={handleLinkedInSubmit} className="space-y-3">
        <label htmlFor="linkedin-url" className="block text-sm font-medium text-gray-700">
          Paste your LinkedIn profile URL
        </label>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <svg className="h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path d="M16.338 16.338H13.67V12.16c0-.995-.017-2.277-1.387-2.277-1.39 0-1.601 1.086-1.601 2.207v4.248H8.014V8h2.559v1.174h.037c.356-.675 1.227-1.387 2.526-1.387 2.703 0 3.203 1.778 3.203 4.092v4.459zM5.005 6.575a1.548 1.548 0 11-.003-3.096 1.548 1.548 0 01.003 3.096zm1.336 9.763H3.667V8h2.674v8.338zM17.668 1H2.328C1.595 1 1 1.581 1 2.298v15.403C1 18.418 1.595 19 2.328 19h15.34c.734 0 1.332-.582 1.332-1.299V2.298C19 1.581 18.402 1 17.668 1z" />
              </svg>
            </div>
            <input
              type="url"
              id="linkedin-url"
              value={linkedInUrl}
              onChange={(e) => setLinkedInUrl(e.target.value)}
              placeholder="https://linkedin.com/in/yourname"
              className="block w-full rounded-lg border border-gray-300 py-2.5 pl-10 pr-3 text-sm placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <button
            type="submit"
            disabled={!linkedInUrl.trim()}
            className={`inline-flex items-center rounded-lg px-4 py-2.5 text-sm font-medium text-white shadow-sm ${
              linkedInUrl.trim()
                ? 'bg-indigo-600 hover:bg-indigo-700'
                : 'cursor-not-allowed bg-indigo-300'
            }`}
          >
            Extract
          </button>
        </div>
        <p className="text-xs text-gray-400">
          We'll try to extract your profile info. If it doesn't work, upload your resume instead.
        </p>
      </form>
    </div>
  );
}
