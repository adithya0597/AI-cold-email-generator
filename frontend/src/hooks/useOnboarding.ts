/**
 * Zustand stores for onboarding and preference wizard state.
 *
 * Both stores use the `persist` middleware to survive page refreshes.
 * Arrays are used instead of Sets because Sets don't serialize to JSON.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ExtractedProfile } from '../types/onboarding';
import type { FullPreferences } from '../types/preferences';

// ============================================================
// Onboarding Store
// ============================================================

interface OnboardingState {
  currentStep: number;
  totalSteps: number;
  profileData: Partial<ExtractedProfile> | null;
  completedSteps: number[];

  // Actions
  setStep: (step: number) => void;
  nextStep: () => void;
  prevStep: () => void;
  setProfileData: (data: Partial<ExtractedProfile>) => void;
  markStepComplete: (step: number) => void;
  reset: () => void;
}

const ONBOARDING_INITIAL: Pick<
  OnboardingState,
  'currentStep' | 'totalSteps' | 'profileData' | 'completedSteps'
> = {
  currentStep: 0,
  totalSteps: 3,
  profileData: null,
  completedSteps: [],
};

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set, get) => ({
      ...ONBOARDING_INITIAL,

      setStep: (step) => set({ currentStep: step }),

      nextStep: () => {
        const { currentStep, totalSteps } = get();
        if (currentStep < totalSteps - 1) {
          set({ currentStep: currentStep + 1 });
        }
      },

      prevStep: () => {
        const { currentStep } = get();
        if (currentStep > 0) {
          set({ currentStep: currentStep - 1 });
        }
      },

      setProfileData: (data) => set({ profileData: data }),

      markStepComplete: (step) => {
        const { completedSteps } = get();
        if (!completedSteps.includes(step)) {
          set({ completedSteps: [...completedSteps, step] });
        }
      },

      reset: () => set(ONBOARDING_INITIAL),
    }),
    {
      name: 'jobpilot-onboarding',
    }
  )
);

// ============================================================
// Preference Store
// ============================================================

const DEFAULT_PREFERENCES: Partial<FullPreferences> = {};

interface PreferenceState {
  currentStep: number;
  preferencesData: Partial<FullPreferences>;
  completedSteps: number[];

  // Actions
  setStep: (step: number) => void;
  nextStep: () => void;
  prevStep: () => void;
  updateSection: <K extends keyof FullPreferences>(
    section: K,
    data: FullPreferences[K]
  ) => void;
  markStepComplete: (step: number) => void;
  setPreferencesData: (data: Partial<FullPreferences>) => void;
  reset: () => void;
}

const PREFERENCE_INITIAL: Pick<
  PreferenceState,
  'currentStep' | 'preferencesData' | 'completedSteps'
> = {
  currentStep: 0,
  preferencesData: DEFAULT_PREFERENCES,
  completedSteps: [],
};

export const usePreferenceStore = create<PreferenceState>()(
  persist(
    (set, get) => ({
      ...PREFERENCE_INITIAL,

      setStep: (step) => set({ currentStep: step }),

      nextStep: () => {
        const { currentStep } = get();
        set({ currentStep: currentStep + 1 });
      },

      prevStep: () => {
        const { currentStep } = get();
        if (currentStep > 0) {
          set({ currentStep: currentStep - 1 });
        }
      },

      updateSection: (section, data) => {
        const { preferencesData } = get();
        set({
          preferencesData: {
            ...preferencesData,
            [section]: data,
          },
        });
      },

      markStepComplete: (step) => {
        const { completedSteps } = get();
        if (!completedSteps.includes(step)) {
          set({ completedSteps: [...completedSteps, step] });
        }
      },

      setPreferencesData: (data) => set({ preferencesData: data }),

      reset: () => set(PREFERENCE_INITIAL),
    }),
    {
      name: 'jobpilot-preferences',
    }
  )
);
