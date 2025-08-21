import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'react-toastify';
import { useDropzone } from 'react-dropzone';
import { FiUpload, FiMail, FiSend, FiCopy, FiTarget, FiDownload, FiLinkedin, FiTrash2, FiBriefcase } from 'react-icons/fi';
import { emailService } from '../services/api';
import { TailSpin } from 'react-loader-spinner';
import sessionCache from '../utils/sessionCache';

const CACHE_KEY = 'ColdEmailGenerator';

const ColdEmailGenerator = () => {
  const [loading, setLoading] = useState(false);
  const [generatedEmail, setGeneratedEmail] = useState(null);
  const [resumeText, setResumeText] = useState('');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [valuePropositions, setValuePropositions] = useState([]);
  const [showLinkedInField, setShowLinkedInField] = useState(false);
  const [showJobPostingField, setShowJobPostingField] = useState(false);

  const { register, handleSubmit, formState: { errors }, setValue, watch, reset } = useForm();

  // Watch form values for caching
  const watchedValues = watch();

  // Load cached data on component mount
  useEffect(() => {
    const cached = sessionCache.get(CACHE_KEY);
    if (cached && Object.keys(cached).length > 0) {
      // Restore form values
      Object.keys(cached).forEach(key => {
        if (key !== 'timestamp' && key !== 'generatedEmail') {
          setValue(key, cached[key]);
        }
      });
      
      // Restore other state
      if (cached.resumeText) setResumeText(cached.resumeText);
      if (cached.showLinkedInField) setShowLinkedInField(cached.showLinkedInField);
      if (cached.showJobPostingField) setShowJobPostingField(cached.showJobPostingField);
      if (cached.generatedEmail) setGeneratedEmail(cached.generatedEmail);
      if (cached.valuePropositions) setValuePropositions(cached.valuePropositions);
      
      toast.info('Restored previous session data');
    }
  }, [setValue]);

  // Save to cache whenever form values change
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      sessionCache.set(CACHE_KEY, {
        ...watchedValues,
        resumeText,
        showLinkedInField,
        showJobPostingField,
        generatedEmail,
        valuePropositions
      });
    }, 500); // Debounce for 500ms

    return () => clearTimeout(timeoutId);
  }, [watchedValues, resumeText, showLinkedInField, showJobPostingField, generatedEmail, valuePropositions]);

  const clearCache = () => {
    sessionCache.clear(CACHE_KEY);
    reset();
    setResumeText('');
    setUploadedFile(null);
    setGeneratedEmail(null);
    setValuePropositions([]);
    setShowLinkedInField(false);
    setShowJobPostingField(false);
    toast.success('Session data cleared');
  };

  const onDrop = async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      setUploadedFile(file);
      setLoading(true);
      try {
        const result = await emailService.parseResume(file);
        if (result.success) {
          setResumeText(result.text_content);
          setValue('user_resume_text', result.text_content);
          toast.success('Resume parsed successfully!');
        } else {
          toast.error(result.error_message || 'Failed to parse resume');
        }
      } catch (error) {
        toast.error('Error parsing resume: ' + error.message);
      } finally {
        setLoading(false);
      }
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc']
    },
    maxFiles: 1
  });

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      // Include optional URLs only if the fields are shown and have values
      const requestData = {
        ...data,
        sender_linkedin_url: showLinkedInField ? data.sender_linkedin_url : null,
        job_posting_url: showJobPostingField ? data.job_posting_url : null
      };
      
      const response = await emailService.generateEmail(requestData);
      setGeneratedEmail(response);
      setValuePropositions(response.value_propositions || []);
      toast.success('Email generated successfully!');
    } catch (error) {
      toast.error('Failed to generate email: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };
  
  const formatEmailForCopy = (email) => {
    // Extract plain text from HTML
    let plainText = email.body;
    plainText = plainText.replace(/<br\s*\/?>/gi, '\n');
    plainText = plainText.replace(/<\/p>/gi, '\n\n');
    plainText = plainText.replace(/<\/div>/gi, '\n');
    plainText = plainText.replace(/<[^>]*>/g, '');
    plainText = plainText.replace(/\n{3,}/g, '\n\n');
    plainText = plainText.trim();
    
    return `Subject: ${email.subject}\n\n${plainText}`;
  };

  const downloadEmail = () => {
    if (!generatedEmail) return;
    
    const content = formatEmailForCopy(generatedEmail);
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'cold-email.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Email downloaded!');
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Cold Email Generator</h1>
            <p className="text-gray-600">Generate personalized cold emails that convert</p>
          </div>
          <button
            onClick={clearCache}
            className="flex items-center px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            title="Clear all cached form data"
          >
            <FiTrash2 className="mr-2" />
            Clear Session
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Input Form */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <FiMail className="mr-2 text-primary-600" />
            Email Details
          </h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Resume Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Resume/CV Upload
              </label>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                  isDragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-primary-400'
                }`}
              >
                <input {...getInputProps()} />
                <FiUpload className="mx-auto text-4xl text-gray-400 mb-2" />
                {uploadedFile ? (
                  <p className="text-sm text-gray-600">
                    Uploaded: {uploadedFile.name}
                  </p>
                ) : (
                  <p className="text-sm text-gray-600">
                    {isDragActive
                      ? 'Drop the file here...'
                      : 'Drag & drop your resume here, or click to select'}
                  </p>
                )}
              </div>
              {resumeText && (
                <textarea
                  {...register('user_resume_text', { required: 'Resume text is required' })}
                  className="mt-2 input-field h-20"
                  placeholder="Resume text will appear here..."
                  value={resumeText}
                  onChange={(e) => setResumeText(e.target.value)}
                />
              )}
              {errors.user_resume_text && (
                <p className="text-red-500 text-xs mt-1">{errors.user_resume_text.message}</p>
              )}
            </div>

            {/* Recipient Details */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Recipient Name
                </label>
                <input
                  {...register('recipient_name', { required: 'Recipient name is required' })}
                  className="input-field"
                  placeholder="John Smith"
                />
                {errors.recipient_name && (
                  <p className="text-red-500 text-xs mt-1">{errors.recipient_name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Recipient Role
                </label>
                <input
                  {...register('recipient_role', { required: 'Recipient role is required' })}
                  className="input-field"
                  placeholder="Hiring Manager"
                />
                {errors.recipient_role && (
                  <p className="text-red-500 text-xs mt-1">{errors.recipient_role.message}</p>
                )}
              </div>
            </div>

            {/* Sender's LinkedIn Profile Toggle */}
            <div className="bg-blue-50 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <FiLinkedin className="text-blue-600 mr-2" />
                  <span className="text-sm font-medium text-gray-700">
                    Add Your LinkedIn Profile URL (Optional)
                  </span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={showLinkedInField}
                    onChange={(e) => setShowLinkedInField(e.target.checked)}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
              
              {showLinkedInField && (
                <div className="mt-3 animate-slide-up">
                  <input
                    {...register('sender_linkedin_url')}
                    className="input-field"
                    placeholder="https://www.linkedin.com/in/your-username"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Adds credibility by showcasing your professional background to the recipient
                  </p>
                </div>
              )}
            </div>

            {/* Job Posting URL Toggle */}
            <div className="bg-indigo-50 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <FiBriefcase className="text-indigo-600 mr-2" />
                  <span className="text-sm font-medium text-gray-700">
                    Add Job Posting URL (Optional)
                  </span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={showJobPostingField}
                    onChange={(e) => setShowJobPostingField(e.target.checked)}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
              
              {showJobPostingField && (
                <div className="mt-3 animate-slide-up">
                  <input
                    {...register('job_posting_url')}
                    className="input-field"
                    placeholder="https://www.linkedin.com/jobs/view/123456789"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Provide the job posting URL to tailor your email specifically to the job requirements, skills, and qualifications
                  </p>
                </div>
              )}
            </div>

            {/* Company Website */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Company Website URL
              </label>
              <input
                {...register('company_website_url', { 
                  required: 'Company website is required',
                  pattern: {
                    value: /^https?:\/\/.+/,
                    message: 'Please enter a valid URL'
                  }
                })}
                className="input-field"
                placeholder="https://example.com"
              />
              {errors.company_website_url && (
                <p className="text-red-500 text-xs mt-1">{errors.company_website_url.message}</p>
              )}
            </div>

            {/* Tone and Goal */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Tone
                </label>
                <select
                  {...register('company_tone', { required: 'Please select a tone' })}
                  className="input-field"
                >
                  <option value="">Select tone...</option>
                  <option value="professional">Professional</option>
                  <option value="friendly">Friendly</option>
                  <option value="casual">Casual</option>
                  <option value="formal">Formal</option>
                  <option value="enthusiastic">Enthusiastic</option>
                </select>
                {errors.company_tone && (
                  <p className="text-red-500 text-xs mt-1">{errors.company_tone.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Goal
                </label>
                <input
                  {...register('email_goal', { required: 'Email goal is required' })}
                  className="input-field"
                  placeholder="Schedule a meeting"
                />
                {errors.email_goal && (
                  <p className="text-red-500 text-xs mt-1">{errors.email_goal.message}</p>
                )}
              </div>
            </div>

            {/* Pain Point */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Pain Point to Address (Optional)
              </label>
              <textarea
                {...register('pain_point')}
                className="input-field h-20"
                placeholder="Specific challenge or need to address..."
              />
            </div>

            {/* Sender Details */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Your Name
                </label>
                <input
                  {...register('sender_name', { required: 'Your name is required' })}
                  className="input-field"
                  placeholder="Jane Doe"
                />
                {errors.sender_name && (
                  <p className="text-red-500 text-xs mt-1">{errors.sender_name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Your Email
                </label>
                <input
                  type="email"
                  {...register('sender_email', {
                    required: 'Your email is required',
                    pattern: {
                      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                      message: 'Invalid email address'
                    }
                  })}
                  className="input-field"
                  placeholder="jane@example.com"
                />
                {errors.sender_email && (
                  <p className="text-red-500 text-xs mt-1">{errors.sender_email.message}</p>
                )}
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary flex items-center justify-center"
            >
              {loading ? (
                <TailSpin height="20" width="20" color="white" />
              ) : (
                <>
                  <FiSend className="mr-2" />
                  Generate Cold Email
                </>
              )}
            </button>
          </form>
        </div>

        {/* Generated Email */}
        <div className="space-y-6">
          {generatedEmail ? (
            <>
              {/* Email Preview */}
              <div className="card">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold">Generated Email</h3>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => copyToClipboard(formatEmailForCopy(generatedEmail))}
                      className="p-2 text-gray-600 hover:text-primary-600 transition-colors"
                      title="Copy to clipboard"
                    >
                      <FiCopy />
                    </button>
                    <button
                      onClick={downloadEmail}
                      className="p-2 text-gray-600 hover:text-primary-600 transition-colors"
                      title="Download email"
                    >
                      <FiDownload />
                    </button>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="mb-3">
                    <span className="text-sm font-medium text-gray-600">Subject:</span>
                    <p className="font-semibold text-gray-900">{generatedEmail.subject}</p>
                  </div>

                  <div>
                    <span className="text-sm font-medium text-gray-600">Body:</span>
                    <div className="mt-2 text-gray-800">
                      {(() => {
                        // Extract plain text from HTML email body
                        let plainText = generatedEmail.body;
                        
                        // Remove HTML tags but keep line breaks
                        plainText = plainText.replace(/<br\s*\/?>/gi, '\n');
                        plainText = plainText.replace(/<\/p>/gi, '\n\n');
                        plainText = plainText.replace(/<\/div>/gi, '\n');
                        plainText = plainText.replace(/<[^>]*>/g, '');
                        
                        // Clean up excessive whitespace
                        plainText = plainText.replace(/\n{3,}/g, '\n\n');
                        plainText = plainText.trim();
                        
                        // Split into paragraphs for better formatting
                        const paragraphs = plainText.split('\n\n').filter(p => p.trim());
                        
                        return (
                          <div className="space-y-3">
                            {paragraphs.map((paragraph, index) => (
                              <p key={index} className="leading-relaxed">
                                {paragraph.trim()}
                              </p>
                            ))}
                          </div>
                        );
                      })()}
                    </div>
                  </div>
                </div>

                {/* Tracking Info */}
                <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-800">
                    📊 This email includes a tracking pixel to monitor open rates
                  </p>
                  {showLinkedInField && watchedValues?.sender_linkedin_url && (
                    <p className="text-xs text-blue-700 mt-1">
                      ✓ Enhanced with your LinkedIn profile for added credibility
                    </p>
                  )}
                  {showJobPostingField && watchedValues?.job_posting_url && (
                    <p className="text-xs text-blue-700 mt-1">
                      ✓ Tailored specifically to match the job posting requirements
                    </p>
                  )}
                </div>
              </div>

              {/* Value Propositions */}
              {valuePropositions.length > 0 && (
                <div className="card">
                  <h3 className="text-lg font-semibold mb-3 flex items-center">
                    <FiTarget className="mr-2 text-primary-600" />
                    Value Propositions
                  </h3>
                  <ul className="space-y-2">
                    {valuePropositions.map((prop, index) => (
                      <li key={index} className="flex items-start">
                        <span className="text-primary-600 mr-2">•</span>
                        <span className="text-gray-700">{prop}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Tone Analysis */}
              {generatedEmail.tone_analysis && (
                <div className="card">
                  <h3 className="text-lg font-semibold mb-3">Tone Analysis</h3>
                  <div className="space-y-3">
                    {(() => {
                      // Parse tone analysis into structured format
                      const analysis = generatedEmail.tone_analysis;
                      const sections = analysis.split(/\d+\.\s+/).filter(s => s.trim());
                      
                      if (sections.length > 1) {
                        return sections.map((section, index) => {
                          const [title, ...content] = section.split(':');
                          return (
                            <div key={index} className="border-l-4 border-primary-500 pl-4">
                              <h4 className="font-medium text-gray-800 mb-1">
                                {index + 1}. {title ? title.trim() : section.split('.')[0]}
                              </h4>
                              {content.length > 0 && (
                                <p className="text-gray-600 text-sm">
                                  {content.join(':').trim()}
                                </p>
                              )}
                            </div>
                          );
                        });
                      } else {
                        // Fallback for unstructured analysis
                        return (
                          <div className="bg-gray-50 rounded-lg p-3">
                            <p className="text-gray-700">{analysis}</p>
                          </div>
                        );
                      }
                    })()}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="card text-center py-12">
              <FiMail className="mx-auto text-6xl text-gray-300 mb-4" />
              <p className="text-gray-500">
                Fill in the details to generate your personalized cold email
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ColdEmailGenerator;