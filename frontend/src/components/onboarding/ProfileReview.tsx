/**
 * ProfileReview -- displays extracted profile data with inline editing.
 *
 * Users can edit name, headline, phone, skills, experience, and education
 * before confirming. Requires name + at least 1 work experience.
 *
 * Story 1-3: Profile Confirmation
 * Story 1-5: Empty state when extraction yielded limited data
 */

import React, { useEffect, useMemo } from 'react';
import { useForm, useFieldArray, Controller } from 'react-hook-form';
import { useAnalytics } from '../../hooks/useAnalytics';
import type { ExtractedProfile, ProfileConfirmRequest, WorkExperience, Education } from '../../types/onboarding';
import EmptyState from '../shared/EmptyState';

interface ProfileReviewProps {
  initialProfile: ExtractedProfile;
  onConfirm: (profile: ProfileConfirmRequest) => void;
  onBack: () => void;
}

interface ProfileFormData {
  name: string;
  headline: string;
  phone: string;
  skills: string[];
  experience: WorkExperience[];
  education: Education[];
}

function SkillTagInput({
  skills,
  onChange,
}: {
  skills: string[];
  onChange: (skills: string[]) => void;
}) {
  const [input, setInput] = React.useState('');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const trimmed = input.trim();
      if (trimmed && !skills.includes(trimmed)) {
        onChange([...skills, trimmed]);
      }
      setInput('');
    } else if (e.key === 'Backspace' && !input && skills.length > 0) {
      onChange(skills.slice(0, -1));
    }
  };

  const removeSkill = (index: number) => {
    onChange(skills.filter((_, i) => i !== index));
  };

  return (
    <div className="rounded-lg border border-gray-300 p-2 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500">
      <div className="flex flex-wrap gap-1.5">
        {skills.map((skill, index) => (
          <span
            key={`${skill}-${index}`}
            className="inline-flex items-center rounded-full bg-indigo-100 px-2.5 py-0.5 text-sm text-indigo-700"
          >
            {skill}
            <button
              type="button"
              onClick={() => removeSkill(index)}
              className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full text-indigo-500 hover:bg-indigo-200 hover:text-indigo-700"
            >
              <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </span>
        ))}
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={skills.length === 0 ? 'Type a skill and press Enter' : 'Add more...'}
          className="min-w-[120px] flex-1 border-none p-1 text-sm focus:outline-none focus:ring-0"
        />
      </div>
    </div>
  );
}

export default function ProfileReview({
  initialProfile,
  onConfirm,
  onBack,
}: ProfileReviewProps) {
  const { track } = useAnalytics();

  // Track when profile review is shown
  useEffect(() => {
    track('profile_review_started', {
      fields_populated: countPopulatedFields(initialProfile),
    });
  }, []);

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<ProfileFormData>({
    defaultValues: {
      name: initialProfile.name || '',
      headline: initialProfile.headline || '',
      phone: initialProfile.phone || '',
      skills: initialProfile.skills || [],
      experience: initialProfile.experience.length > 0
        ? initialProfile.experience
        : [{ company: '', title: '', startDate: null, endDate: null, description: null }],
      education: initialProfile.education || [],
    },
  });

  const {
    fields: experienceFields,
    append: appendExperience,
    remove: removeExperience,
  } = useFieldArray({ control, name: 'experience' });

  const {
    fields: educationFields,
    append: appendEducation,
    remove: removeEducation,
  } = useFieldArray({ control, name: 'education' });

  const watchedData = watch();

  // Determine if extraction yielded limited data
  const fieldsPopulated = useMemo(
    () => countPopulatedFields(initialProfile),
    [initialProfile]
  );
  const isLimitedExtraction = fieldsPopulated < 3;

  const onSubmit = (data: ProfileFormData) => {
    // Count how many fields were edited from initial
    const editedCount = countEditedFields(initialProfile, data);

    track('profile_confirmed', { fields_edited_count: editedCount });

    onConfirm({
      name: data.name,
      headline: data.headline || null,
      phone: data.phone || null,
      skills: data.skills,
      experience: data.experience.map((exp) => ({
        company: exp.company,
        title: exp.title,
        start_date: exp.startDate,
        end_date: exp.endDate,
        description: exp.description,
      })),
      education: data.education.map((edu) => ({
        institution: edu.institution,
        degree: edu.degree,
        field: edu.field,
        graduation_year: edu.graduationYear,
      })),
      extraction_source: 'resume',
    });
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900">Review your profile</h2>
        <p className="mt-2 text-gray-600">
          We extracted this from your resume. Make any corrections before continuing.
        </p>
      </div>

      {isLimitedExtraction && (
        <EmptyState
          icon={
            <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          }
          title="We found some info!"
          description="Help your agent by adding more details below. The more complete your profile, the better your job matches will be."
        />
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Info */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Basic Information</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                Full Name <span className="text-red-500">*</span>
              </label>
              <input
                {...register('name', { required: 'Name is required' })}
                id="name"
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              {errors.name && (
                <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>
              )}
            </div>
            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-gray-700">
                Phone
              </label>
              <input
                {...register('phone')}
                id="phone"
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="headline" className="block text-sm font-medium text-gray-700">
                Professional Headline
              </label>
              <input
                {...register('headline')}
                id="headline"
                placeholder="e.g., Senior Software Engineer at Google"
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>
        </div>

        {/* Skills */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Skills</h3>
          <Controller
            control={control}
            name="skills"
            render={({ field }) => (
              <SkillTagInput skills={field.value} onChange={field.onChange} />
            )}
          />
          <p className="mt-1.5 text-xs text-gray-400">
            Type a skill and press Enter to add it
          </p>
        </div>

        {/* Experience */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              Work Experience <span className="text-red-500">*</span>
            </h3>
            <button
              type="button"
              onClick={() =>
                appendExperience({
                  company: '',
                  title: '',
                  startDate: null,
                  endDate: null,
                  description: null,
                })
              }
              className="inline-flex items-center rounded-md border border-indigo-300 bg-white px-3 py-1.5 text-xs font-medium text-indigo-600 hover:bg-indigo-50"
            >
              <svg className="mr-1 h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              Add Experience
            </button>
          </div>

          {errors.experience?.root && (
            <p className="mb-3 text-xs text-red-500">{errors.experience.root.message}</p>
          )}

          <div className="space-y-4">
            {experienceFields.map((field, index) => (
              <div
                key={field.id}
                className="relative rounded-lg border border-gray-100 bg-gray-50 p-4"
              >
                {experienceFields.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeExperience(index)}
                    className="absolute right-2 top-2 rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-red-500"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-medium text-gray-600">Company</label>
                    <input
                      {...register(`experience.${index}.company`, {
                        required: 'Company is required',
                      })}
                      className="mt-1 block w-full rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600">Title</label>
                    <input
                      {...register(`experience.${index}.title`, {
                        required: 'Title is required',
                      })}
                      className="mt-1 block w-full rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600">Start Date</label>
                    <input
                      {...register(`experience.${index}.startDate`)}
                      placeholder="e.g., Jan 2020"
                      className="mt-1 block w-full rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600">End Date</label>
                    <input
                      {...register(`experience.${index}.endDate`)}
                      placeholder="e.g., Present"
                      className="mt-1 block w-full rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-medium text-gray-600">Description</label>
                    <textarea
                      {...register(`experience.${index}.description`)}
                      rows={2}
                      className="mt-1 block w-full rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Education */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Education</h3>
            <button
              type="button"
              onClick={() =>
                appendEducation({
                  institution: '',
                  degree: null,
                  field: null,
                  graduationYear: null,
                })
              }
              className="inline-flex items-center rounded-md border border-indigo-300 bg-white px-3 py-1.5 text-xs font-medium text-indigo-600 hover:bg-indigo-50"
            >
              <svg className="mr-1 h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              Add Education
            </button>
          </div>

          {educationFields.length === 0 ? (
            <p className="text-sm text-gray-400 italic">
              No education entries found. Add one if you'd like.
            </p>
          ) : (
            <div className="space-y-4">
              {educationFields.map((field, index) => (
                <div
                  key={field.id}
                  className="relative rounded-lg border border-gray-100 bg-gray-50 p-4"
                >
                  <button
                    type="button"
                    onClick={() => removeEducation(index)}
                    className="absolute right-2 top-2 rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-red-500"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <label className="block text-xs font-medium text-gray-600">Institution</label>
                      <input
                        {...register(`education.${index}.institution`, {
                          required: 'Institution is required',
                        })}
                        className="mt-1 block w-full rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600">Degree</label>
                      <input
                        {...register(`education.${index}.degree`)}
                        className="mt-1 block w-full rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600">Field of Study</label>
                      <input
                        {...register(`education.${index}.field`)}
                        className="mt-1 block w-full rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600">Graduation Year</label>
                      <input
                        {...register(`education.${index}.graduationYear`)}
                        placeholder="e.g., 2020"
                        className="mt-1 block w-full rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center justify-between border-t border-gray-200 pt-6">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
          >
            <svg className="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
            Back
          </button>
          <button
            type="submit"
            disabled={
              !watchedData.name?.trim() ||
              !watchedData.experience?.some(
                (exp) => exp.company?.trim() && exp.title?.trim()
              )
            }
            className={`inline-flex items-center rounded-md px-6 py-2 text-sm font-medium text-white shadow-sm ${
              watchedData.name?.trim() &&
              watchedData.experience?.some((exp) => exp.company?.trim() && exp.title?.trim())
                ? 'bg-indigo-600 hover:bg-indigo-700'
                : 'cursor-not-allowed bg-indigo-300'
            }`}
          >
            Confirm Profile
            <svg className="ml-2 h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
}

// ---- Helpers ----

function countPopulatedFields(profile: ExtractedProfile): number {
  let count = 0;
  if (profile.name) count++;
  if (profile.headline) count++;
  if (profile.phone) count++;
  if (profile.skills.length > 0) count++;
  if (profile.experience.length > 0) count++;
  if (profile.education.length > 0) count++;
  if (profile.email) count++;
  return count;
}

function countEditedFields(
  original: ExtractedProfile,
  edited: ProfileFormData
): number {
  let count = 0;
  if (original.name !== edited.name) count++;
  if ((original.headline || '') !== edited.headline) count++;
  if ((original.phone || '') !== edited.phone) count++;
  if (JSON.stringify(original.skills) !== JSON.stringify(edited.skills)) count++;
  if (JSON.stringify(original.experience) !== JSON.stringify(edited.experience)) count++;
  if (JSON.stringify(original.education) !== JSON.stringify(edited.education)) count++;
  return count;
}
