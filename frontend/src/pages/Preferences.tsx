/**
 * Preferences page -- multi-step preference wizard controller.
 *
 * Steps: 0=JobType, 1=Location, 2=Salary, 3=DealBreakers, 4=H1B, 5=Autonomy, 6=Summary
 *
 * Uses usePreferenceStore (Zustand) for persistent step state.
 * Each step saves to backend via PATCH /api/v1/preferences/{section}.
 * Final submit calls PUT /api/v1/preferences with full data.
 */

import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { useApiClient } from '../services/api';
import { usePreferenceStore } from '../hooks/useOnboarding';
import { useAnalytics } from '../hooks/useAnalytics';
import WizardShell from '../components/shared/WizardShell';
import JobTypeStep from '../components/preferences/JobTypeStep';
import LocationStep from '../components/preferences/LocationStep';
import SalaryStep from '../components/preferences/SalaryStep';
import DealBreakerStep from '../components/preferences/DealBreakerStep';
import H1BStep from '../components/preferences/H1BStep';
import AutonomyStep from '../components/preferences/AutonomyStep';
import SummaryStep from '../components/preferences/SummaryStep';
import type { FullPreferences } from '../types/preferences';
import type {
  JobTypeFormData,
  LocationFormData,
  SalaryFormData,
  DealBreakerFormData,
  H1BFormData,
  AutonomyFormData,
} from '../types/preferences';

const STEP_LABELS = ['Job Type', 'Location', 'Salary', 'Deal-Breakers', 'Visa', 'Autonomy', 'Summary'];
const TOTAL_STEPS = 7;

// Map step index to API section name
const SECTION_MAP: Record<number, string> = {
  0: 'job_type',
  1: 'location',
  2: 'salary',
  3: 'deal_breakers',
  4: 'h1b',
  5: 'autonomy',
};

export default function Preferences() {
  const navigate = useNavigate();
  const apiClient = useApiClient();
  const { track } = useAnalytics();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    currentStep,
    preferencesData,
    completedSteps,
    setStep,
    nextStep,
    prevStep,
    updateSection,
    markStepComplete,
    setPreferencesData,
    reset,
  } = usePreferenceStore();

  // Load existing preferences on mount
  const { data: existingPrefs } = useQuery<Partial<FullPreferences>>({
    queryKey: ['preferences'],
    queryFn: async () => {
      const res = await apiClient.get('/api/v1/preferences');
      return res.data;
    },
    retry: 1,
    staleTime: 30_000,
  });

  // Seed store from server data if store is empty
  useEffect(() => {
    if (existingPrefs && Object.keys(preferencesData).length === 0) {
      setPreferencesData(existingPrefs);
    }
  }, [existingPrefs]);

  // Track wizard started
  useEffect(() => {
    track('preference_wizard_started');
  }, []);

  // Save a single section to the backend
  const saveSection = useCallback(
    async (section: string, data: Record<string, unknown>) => {
      try {
        await apiClient.patch(`/api/v1/preferences/${section}`, data);
      } catch {
        // Non-blocking -- Zustand has local state as fallback
      }
    },
    [apiClient]
  );

  // Step handlers
  const handleJobTypeSubmit = useCallback(
    async (data: JobTypeFormData) => {
      updateSection('job_type', data);
      markStepComplete(0);
      track('preference_step_completed', { step_name: 'job_type', step_number: 0 });
      await saveSection('job_type', data);
      nextStep();
    },
    [updateSection, markStepComplete, nextStep, saveSection, track]
  );

  const handleLocationSubmit = useCallback(
    async (data: LocationFormData) => {
      updateSection('location', data);
      markStepComplete(1);
      track('preference_step_completed', { step_name: 'location', step_number: 1 });
      await saveSection('location', data);
      nextStep();
    },
    [updateSection, markStepComplete, nextStep, saveSection, track]
  );

  const handleSalarySubmit = useCallback(
    async (data: SalaryFormData) => {
      updateSection('salary', data);
      markStepComplete(2);
      track('preference_step_completed', { step_name: 'salary', step_number: 2 });
      await saveSection('salary', data);
      nextStep();
    },
    [updateSection, markStepComplete, nextStep, saveSection, track]
  );

  const handleDealBreakerSubmit = useCallback(
    async (data: DealBreakerFormData) => {
      updateSection('deal_breakers', data);
      markStepComplete(3);
      track('preference_step_completed', { step_name: 'deal_breakers', step_number: 3 });
      await saveSection('deal_breakers', data);
      nextStep();
    },
    [updateSection, markStepComplete, nextStep, saveSection, track]
  );

  const handleH1BSubmit = useCallback(
    async (data: H1BFormData) => {
      updateSection('h1b', data);
      markStepComplete(4);
      track('preference_step_completed', { step_name: 'h1b', step_number: 4 });
      await saveSection('h1b', data);
      nextStep();
    },
    [updateSection, markStepComplete, nextStep, saveSection, track]
  );

  const handleAutonomySubmit = useCallback(
    async (data: AutonomyFormData) => {
      updateSection('autonomy', data);
      markStepComplete(5);
      track('preference_step_completed', { step_name: 'autonomy', step_number: 5 });
      await saveSection('autonomy', data);
      nextStep();
    },
    [updateSection, markStepComplete, nextStep, saveSection, track]
  );

  const handleSkip = useCallback(
    (stepIndex: number, stepName: string) => {
      track('preference_step_skipped', { step_name: stepName, step_number: stepIndex });
      nextStep();
    },
    [nextStep, track]
  );

  const handleConfirm = useCallback(async () => {
    setIsSubmitting(true);
    try {
      await apiClient.put('/api/v1/preferences', preferencesData);
      track('preferences_confirmed');
      track('onboarding_completed');
      reset();
      toast.success('Your agent is now active! Check back tomorrow for your first briefing.');
      navigate('/dashboard', { replace: true });
    } catch {
      toast.error('Something went wrong. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }, [apiClient, preferencesData, navigate, track, reset]);

  const handleEditFromSummary = useCallback(
    (stepIndex: number) => {
      setStep(stepIndex);
    },
    [setStep]
  );

  // Render current step
  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return (
          <JobTypeStep
            defaultValues={preferencesData.job_type}
            onSubmit={handleJobTypeSubmit}
            onSkip={() => handleSkip(0, 'job_type')}
          />
        );
      case 1:
        return (
          <LocationStep
            defaultValues={preferencesData.location}
            onSubmit={handleLocationSubmit}
            onBack={() => prevStep()}
            onSkip={() => handleSkip(1, 'location')}
          />
        );
      case 2:
        return (
          <SalaryStep
            defaultValues={preferencesData.salary}
            onSubmit={handleSalarySubmit}
            onBack={() => prevStep()}
            onSkip={() => handleSkip(2, 'salary')}
          />
        );
      case 3:
        return (
          <DealBreakerStep
            defaultValues={preferencesData.deal_breakers}
            onSubmit={handleDealBreakerSubmit}
            onBack={() => prevStep()}
            onSkip={() => handleSkip(3, 'deal_breakers')}
          />
        );
      case 4:
        return (
          <H1BStep
            defaultValues={preferencesData.h1b}
            onSubmit={handleH1BSubmit}
            onBack={() => prevStep()}
            onSkip={() => handleSkip(4, 'h1b')}
          />
        );
      case 5:
        return (
          <AutonomyStep
            defaultValues={preferencesData.autonomy}
            onSubmit={handleAutonomySubmit}
            onBack={() => prevStep()}
            onSkip={() => handleSkip(5, 'autonomy')}
          />
        );
      case 6:
        return (
          <SummaryStep
            preferences={preferencesData}
            completedSteps={completedSteps}
            onEdit={handleEditFromSummary}
            onConfirm={handleConfirm}
            onBack={() => prevStep()}
            isSubmitting={isSubmitting}
          />
        );
      default:
        setStep(0);
        return null;
    }
  };

  const completedStepsSet = new Set(completedSteps);

  return (
    <div className="py-4">
      <WizardShell
        currentStep={currentStep}
        totalSteps={TOTAL_STEPS}
        stepLabels={STEP_LABELS}
        completedSteps={completedStepsSet}
        // Steps manage their own navigation buttons
      >
        {renderStep()}
      </WizardShell>
    </div>
  );
}
