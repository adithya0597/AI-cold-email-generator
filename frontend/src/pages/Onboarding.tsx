/**
 * Onboarding page -- multi-step controller for the onboarding flow.
 *
 * Steps:
 *   0 = ResumeUpload (upload resume or LinkedIn URL)
 *   1 = ProfileReview (review and edit extracted profile)
 *   2 = BriefingPreview ("magic moment" preview)
 *
 * Uses useOnboardingStore (Zustand) for persistent step state.
 * Calls backend APIs via useApiClient for profile extraction and confirmation.
 */

import { useEffect, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useApiClient } from '../services/api';
import { useOnboardingStore } from '../hooks/useOnboarding';
import { useAnalytics } from '../hooks/useAnalytics';
import WizardShell from '../components/shared/WizardShell';
import ResumeUpload from '../components/onboarding/ResumeUpload';
import ProfileReview from '../components/onboarding/ProfileReview';
import BriefingPreview from '../components/onboarding/BriefingPreview';
import type { ExtractedProfile, ProfileConfirmRequest, OnboardingStatusResponse } from '../types/onboarding';

const STEP_LABELS = ['Upload Resume', 'Review Profile', 'First Look'];

export default function Onboarding() {
  const navigate = useNavigate();
  const apiClient = useApiClient();
  const { track } = useAnalytics();
  const [isConfirming, setIsConfirming] = useState(false);

  const {
    currentStep,
    profileData,
    completedSteps,
    setStep,
    nextStep,
    prevStep,
    setProfileData,
    markStepComplete,
  } = useOnboardingStore();

  // ---- Check onboarding status on mount ----
  const { data: statusData } = useQuery<OnboardingStatusResponse>({
    queryKey: ['onboarding-status'],
    queryFn: async () => {
      const res = await apiClient.get('/api/v1/onboarding/status');
      return res.data;
    },
    retry: 1,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (!statusData) return;

    const status = statusData.onboarding_status;

    if (status === 'complete') {
      navigate('/dashboard', { replace: true });
      return;
    }

    if (status === 'preferences_pending') {
      navigate('/preferences', { replace: true });
      return;
    }

    if (status === 'profile_complete') {
      // Skip to briefing preview
      setStep(2);
      return;
    }

    // Track onboarding_started only on first visit
    if (status === 'not_started') {
      track('onboarding_started');
    }
  }, [statusData]);

  // ---- Profile confirmation mutation ----
  const confirmProfileMutation = useMutation({
    mutationFn: async (profile: ProfileConfirmRequest) => {
      const res = await apiClient.put('/api/v1/onboarding/profile/confirm', profile);
      return res.data;
    },
  });

  // ---- Step handlers ----

  const handleProfileExtracted = useCallback(
    (profile: ExtractedProfile) => {
      setProfileData(profile);
      markStepComplete(0);
      nextStep();
    },
    [setProfileData, markStepComplete, nextStep]
  );

  const handleProfileConfirm = useCallback(
    async (profile: ProfileConfirmRequest) => {
      setIsConfirming(true);
      try {
        await confirmProfileMutation.mutateAsync(profile);
        markStepComplete(1);
        nextStep();
      } catch {
        // Error is handled by the mutation state; ProfileReview can show a toast
      } finally {
        setIsConfirming(false);
      }
    },
    [confirmProfileMutation, markStepComplete, nextStep]
  );

  const handleBriefingContinue = useCallback(() => {
    markStepComplete(2);
    navigate('/preferences');
  }, [markStepComplete, navigate]);

  // ---- Render current step ----

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return <ResumeUpload onProfileExtracted={handleProfileExtracted} />;

      case 1:
        if (!profileData) {
          // If somehow we're on step 1 without profile data, go back
          setStep(0);
          return null;
        }
        return (
          <ProfileReview
            initialProfile={profileData as ExtractedProfile}
            onConfirm={handleProfileConfirm}
            onBack={() => prevStep()}
          />
        );

      case 2:
        return (
          <BriefingPreview
            userName={profileData?.name || statusData?.display_name || 'there'}
            onContinue={handleBriefingContinue}
          />
        );

      default:
        setStep(0);
        return null;
    }
  };

  // For the WizardShell: we only show its nav buttons on step 2 (BriefingPreview manages its own)
  // Steps 0 and 1 have their own navigation (upload triggers next, ProfileReview has back/confirm)
  // We still render the WizardShell for the step indicator at the top
  const completedStepsSet = new Set(completedSteps);

  return (
    <div className="py-4">
      <WizardShell
        currentStep={currentStep}
        totalSteps={3}
        stepLabels={STEP_LABELS}
        completedSteps={completedStepsSet}
        // Don't show WizardShell nav buttons -- each step component handles its own navigation
      >
        {isConfirming ? (
          <div className="flex flex-col items-center justify-center py-16">
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
            <p className="mt-4 text-lg font-medium text-indigo-700">Saving your profile...</p>
          </div>
        ) : (
          renderStep()
        )}
      </WizardShell>
    </div>
  );
}
