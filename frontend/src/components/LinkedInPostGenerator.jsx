import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'react-toastify';
import { FiLinkedin, FiHash, FiTrendingUp, FiUsers, FiCopy, FiEye, FiImage, FiLink } from 'react-icons/fi';
import { linkedInService } from '../services/api';
import { TailSpin } from 'react-loader-spinner';
import axios from 'axios';
import sessionCache from '../utils/sessionCache';

const INFLUENCER_STYLES = [
  { value: 'Gary Vaynerchuk', label: 'Gary Vaynerchuk', description: 'Direct, energetic, motivational' },
  { value: 'Simon Sinek', label: 'Simon Sinek', description: 'Thoughtful, philosophical, purpose-driven' },
  { value: 'Brené Brown', label: 'Brené Brown', description: 'Vulnerable, authentic, research-based' },
  { value: 'Neil Patel', label: 'Neil Patel', description: 'Data-driven, tactical, actionable' },
  { value: 'Arianna Huffington', label: 'Arianna Huffington', description: 'Wellness-focused, balanced' },
  { value: 'Adam Grant', label: 'Adam Grant', description: 'Research-backed, organizational psychology' },
  { value: 'custom', label: 'Custom Author', description: 'Emulate any author\'s style' }
];

const POST_GOALS = [
  { value: 'Drive Engagement', label: 'Drive Engagement', icon: FiTrendingUp },
  { value: 'Generate Leads', label: 'Generate Leads', icon: FiUsers },
  { value: 'Build Thought Leadership', label: 'Build Thought Leadership', icon: FiEye }
];

const COLD_EMAIL_CACHE_KEY = 'ColdEmailGenerator';
const LINKEDIN_CACHE_KEY = 'LinkedInPostGenerator';

const LinkedInPostGenerator = () => {
  const [loading, setLoading] = useState(false);
  const [generatedPost, setGeneratedPost] = useState(null);
  const [showCustomAuthor, setShowCustomAuthor] = useState(false);
  const [characterCount, setCharacterCount] = useState(0);
  const [uploadedAuthors, setUploadedAuthors] = useState([]);
  const [selectedUploadedAuthor, setSelectedUploadedAuthor] = useState('');
  const [generateImage, setGenerateImage] = useState(false);
  const [referenceUrls, setReferenceUrls] = useState(['']);

  const { register, handleSubmit, formState: { errors }, watch, setValue } = useForm();

  const watchedStyle = watch('influencer_style');

  // Load data from cold email generator if available
  useEffect(() => {
    const coldEmailData = sessionCache.get(COLD_EMAIL_CACHE_KEY);
    if (coldEmailData) {
      // Pre-fill relevant fields from cold email data
      if (coldEmailData.company_tone) {
        // Map email tone to LinkedIn style
        const toneToStyle = {
          'professional': 'Adam Grant',
          'friendly': 'Gary Vaynerchuk',
          'casual': 'Brené Brown',
          'formal': 'Simon Sinek',
          'enthusiastic': 'Gary Vaynerchuk'
        };
        setValue('influencer_style', toneToStyle[coldEmailData.company_tone] || 'professional');
      }
      
      // Use company/industry info if available
      if (coldEmailData.pain_point) {
        setValue('topic', coldEmailData.pain_point);
      }
      
      // Use sender info for target audience
      if (coldEmailData.recipient_role) {
        setValue('target_audience', `${coldEmailData.recipient_role}s and decision makers`);
      }
    }
    
    // Load LinkedIn-specific cached data
    const linkedInData = sessionCache.get(LINKEDIN_CACHE_KEY);
    if (linkedInData) {
      Object.keys(linkedInData).forEach(key => {
        if (key !== 'timestamp' && key !== 'generatedPost' && key !== 'referenceUrls') {
          setValue(key, linkedInData[key]);
        }
      });
      
      if (linkedInData.generatedPost) setGeneratedPost(linkedInData.generatedPost);
      if (linkedInData.generateImage !== undefined) setGenerateImage(linkedInData.generateImage);
      if (linkedInData.referenceUrls) setReferenceUrls(linkedInData.referenceUrls);
    }
  }, [setValue]);

  React.useEffect(() => {
    setShowCustomAuthor(watchedStyle === 'custom');
    fetchUploadedAuthors();
  }, [watchedStyle]);

  const fetchUploadedAuthors = async () => {
    try {
      const response = await axios.get('/api/author-styles');
      setUploadedAuthors(response.data);
    } catch (error) {
      console.error('Failed to fetch uploaded authors:', error);
    }
  };

  // Save form data to cache
  const watchedValues = watch();
  
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      sessionCache.set(LINKEDIN_CACHE_KEY, {
        ...watchedValues,
        generatedPost,
        generateImage,
        referenceUrls
      });
    }, 500); // Debounce for 500ms

    return () => clearTimeout(timeoutId);
  }, [watchedValues, generatedPost, generateImage, referenceUrls]);

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      // If custom style is selected but no author name provided, use the style as the author name
      if (data.influencer_style === 'custom' && !data.custom_author_name) {
        toast.error('Please provide a custom author name');
        setLoading(false);
        return;
      }

      // Filter out empty URLs
      const validUrls = referenceUrls.filter(url => url.trim() !== '');

      // Add generate_image flag and reference URLs to the request
      const requestData = {
        ...data,
        generate_image: generateImage,
        reference_urls: validUrls
      };

      const response = await linkedInService.generatePost(requestData);
      setGeneratedPost(response);
      setCharacterCount(response.content.length);
      toast.success('LinkedIn post generated successfully!');
    } catch (error) {
      toast.error('Failed to generate post: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  const getCharacterCountColor = () => {
    if (characterCount === 0) return 'text-gray-400';
    if (characterCount <= 1300) return 'text-green-600';
    if (characterCount <= 2000) return 'text-yellow-600';
    if (characterCount <= 3000) return 'text-orange-600';
    return 'text-red-600';
  };

  const clearCache = () => {
    sessionCache.clear(LINKEDIN_CACHE_KEY);
    window.location.reload();
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">LinkedIn Post Generator</h1>
            <p className="text-gray-600">Create engaging LinkedIn posts that drive results</p>
          </div>
          <button
            onClick={clearCache}
            className="flex items-center px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            title="Clear all cached data"
          >
            Clear Session
          </button>
        </div>
        
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Input Form */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <FiLinkedin className="mr-2 text-blue-600" />
            Post Configuration
          </h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Topic */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Post Topic
              </label>
              <input
                {...register('topic', { required: 'Topic is required' })}
                className="input-field"
                placeholder="The future of AI in business"
              />
              {errors.topic && (
                <p className="text-red-500 text-xs mt-1">{errors.topic.message}</p>
              )}
            </div>

            {/* Industry */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Industry
              </label>
              <input
                {...register('industry', { required: 'Industry is required' })}
                className="input-field"
                placeholder="Technology, Finance, Healthcare..."
              />
              {errors.industry && (
                <p className="text-red-500 text-xs mt-1">{errors.industry.message}</p>
              )}
            </div>

            {/* Target Audience */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Target Audience
              </label>
              <input
                {...register('target_audience', { required: 'Target audience is required' })}
                className="input-field"
                placeholder="Tech leaders, entrepreneurs, marketing professionals..."
              />
              {errors.target_audience && (
                <p className="text-red-500 text-xs mt-1">{errors.target_audience.message}</p>
              )}
            </div>

            {/* Post Goal */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Post Goal
              </label>
              <div className="grid grid-cols-1 gap-2">
                {POST_GOALS.map((goal) => {
                  const Icon = goal.icon;
                  return (
                    <label
                      key={goal.value}
                      className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors"
                    >
                      <input
                        type="radio"
                        {...register('post_goal', { required: 'Please select a goal' })}
                        value={goal.value}
                        className="mr-3"
                      />
                      <Icon className="mr-2 text-primary-600" />
                      <span className="font-medium">{goal.label}</span>
                    </label>
                  );
                })}
              </div>
              {errors.post_goal && (
                <p className="text-red-500 text-xs mt-1">{errors.post_goal.message}</p>
              )}
            </div>

            {/* Writing Style */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Writing Style
              </label>
              <select
                {...register('influencer_style', { required: 'Please select a style' })}
                className="input-field mb-2"
                onChange={(e) => {
                  const value = e.target.value;
                  setValue('influencer_style', value);
                  setShowCustomAuthor(value === 'custom');
                  if (value !== 'custom') {
                    setSelectedUploadedAuthor('');
                  }
                }}
              >
                <option value="">Select a style...</option>
                {INFLUENCER_STYLES.map((style) => (
                  <option key={style.value} value={style.value}>
                    {style.label} - {style.description}
                  </option>
                ))}
              </select>
              {errors.influencer_style && (
                <p className="text-red-500 text-xs mt-1">{errors.influencer_style.message}</p>
              )}

              {/* Custom Author Input */}
              {showCustomAuthor && (
                <div className="mt-2 animate-slide-up space-y-3">
                  {/* Uploaded Authors Dropdown */}
                  {uploadedAuthors.length > 0 && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Select from Uploaded Authors
                      </label>
                      <select
                        value={selectedUploadedAuthor}
                        onChange={(e) => {
                          setSelectedUploadedAuthor(e.target.value);
                          setValue('custom_author_name', e.target.value);
                        }}
                        className="input-field"
                      >
                        <option value="">-- Select an uploaded author --</option>
                        {uploadedAuthors.map((author) => (
                          <option key={author.author_id} value={author.author_name}>
                            {author.author_name} ({author.post_count} posts)
                          </option>
                        ))}
                      </select>
                      <p className="text-xs text-gray-500 mt-1">
                        These authors have been uploaded via Excel with actual post samples
                      </p>
                    </div>
                  )}
                  
                  {/* Manual Entry */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Or Enter Any Author Name
                    </label>
                    <input
                      {...register('custom_author_name')}
                      className="input-field"
                      placeholder="Enter author name to emulate (e.g., Satya Nadella)"
                      value={selectedUploadedAuthor}
                      onChange={(e) => {
                        setSelectedUploadedAuthor(e.target.value);
                      }}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      {selectedUploadedAuthor && uploadedAuthors.find(a => a.author_name === selectedUploadedAuthor)
                        ? `✓ Using uploaded samples for ${selectedUploadedAuthor}`
                        : 'We\'ll analyze and emulate this author\'s writing style'}
                    </p>
                  </div>
                  
                  {/* Link to Author Styles Manager */}
                  <div className="text-xs">
                    <a 
                      href="/author-styles" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:underline"
                    >
                      → Upload more author samples
                    </a>
                  </div>
                </div>
              )}
            </div>

            {/* Reference URLs (Optional) */}
            <div className="bg-indigo-50 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  <FiLink className="text-indigo-600 mr-2" />
                  <span className="text-sm font-medium text-gray-700">
                    Reference URLs (Up to 3)
                  </span>
                </div>
                {referenceUrls.length < 3 && (
                  <button
                    type="button"
                    onClick={() => setReferenceUrls([...referenceUrls, ''])}
                    className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                  >
                    + Add URL
                  </button>
                )}
              </div>
              
              {referenceUrls.map((url, index) => (
                <div key={index} className="flex items-center space-x-2 mb-2">
                  <input
                    value={url}
                    onChange={(e) => {
                      const newUrls = [...referenceUrls];
                      newUrls[index] = e.target.value;
                      setReferenceUrls(newUrls);
                    }}
                    className="input-field flex-1"
                    placeholder={`https://example.com/article-${index + 1}`}
                  />
                  {referenceUrls.length > 1 && (
                    <button
                      type="button"
                      onClick={() => {
                        const newUrls = referenceUrls.filter((_, i) => i !== index);
                        setReferenceUrls(newUrls);
                      }}
                      className="text-red-500 hover:text-red-700 px-2 py-1"
                      title="Remove URL"
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
              
              <p className="text-xs text-gray-600 mt-1">
                Provide URLs to articles or content pieces to use as reference. The AI will analyze and incorporate insights from these sources while maintaining your chosen style.
              </p>
            </div>

            {/* Image Generation Toggle */}
            <div className="bg-purple-50 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <FiImage className="text-purple-600 mr-2" />
                  <span className="text-sm font-medium text-gray-700">
                    Generate AI Image (Optional)
                  </span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={generateImage}
                    onChange={(e) => setGenerateImage(e.target.checked)}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                </label>
              </div>
              <p className="text-xs text-gray-600 mt-1">
                {generateImage 
                  ? "AI will generate a relevant image (infographic, chart, or illustration) for your post"
                  : "Post will be text-only for faster generation"}
              </p>
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
                  <FiLinkedin className="mr-2" />
                  Generate LinkedIn Post
                </>
              )}
            </button>
          </form>
        </div>

        {/* Generated Post */}
        <div className="space-y-6">
          {generatedPost && (
            <>
              {/* Post Preview */}
              <div className="card">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold">Generated Post</h3>
                  <div className="flex items-center space-x-4">
                    <span className={`text-sm ${getCharacterCountColor()}`}>
                      {characterCount} characters
                    </span>
                    <button
                      onClick={() => copyToClipboard(generatedPost.content)}
                      className="p-2 text-gray-600 hover:text-primary-600 transition-colors"
                      title="Copy to clipboard"
                    >
                      <FiCopy />
                    </button>
                  </div>
                </div>

                {/* LinkedIn-style post preview */}
                <div className="border rounded-lg p-4 bg-white">
                  <div className="flex items-start mb-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-primary-400 to-primary-600 rounded-full flex items-center justify-center text-white font-bold">
                      YN
                    </div>
                    <div className="ml-3">
                      <p className="font-semibold">Your Name</p>
                      <p className="text-sm text-gray-500">Professional Title • Now</p>
                    </div>
                  </div>

                  <div className="text-gray-800 mb-3">
                    {(() => {
                      // Format the post content for better display
                      const postText = generatedPost.content.split('#')[0].trim();
                      const lines = postText.split('\n');
                      
                      return lines.map((line, idx) => {
                        // Process each line for formatting
                        let formatted = line;
                        
                        // Convert **bold** to actual bold
                        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                        
                        // Check for special formatting
                        const hasEmoji = /^[🔥💡🎯⚡🚀📊📈✓❌→▸•]/.test(line.trim());
                        const isBullet = /^[→▸•✓]/.test(line.trim());
                        const isEmpty = line.trim() === '';
                        
                        if (isEmpty) {
                          return <div key={idx} className="h-2" />;
                        }
                        
                        return (
                          <div 
                            key={idx}
                            className={`
                              ${hasEmoji ? 'font-medium text-gray-900' : ''}
                              ${isBullet ? 'pl-4' : ''}
                              ${idx > 0 && !isEmpty ? 'mt-1' : ''}
                            `}
                            dangerouslySetInnerHTML={{ __html: formatted }}
                          />
                        );
                      });
                    })()}
                  </div>
                  
                  {/* Generated Image Display */}
                  {generatedPost.image_url && (
                    <div className="mb-3">
                      <div className="relative rounded-lg overflow-hidden">
                        <img 
                          src={generatedPost.image_url} 
                          alt="Post visual"
                          className="w-full h-auto object-cover"
                          style={{ maxHeight: '400px' }}
                        />
                        {generatedPost.image_type && (
                          <div className="absolute top-2 left-2 bg-black bg-opacity-70 text-white px-2 py-1 rounded text-xs">
                            {generatedPost.image_type.toUpperCase()}
                          </div>
                        )}
                        {generatedPost.image_relevance_score && generatedPost.image_relevance_score >= 0.8 && (
                          <div className="absolute top-2 right-2 bg-green-500 text-white px-2 py-1 rounded text-xs">
                            ✓ Highly Relevant
                          </div>
                        )}
                      </div>
                      {generatedPost.image_prompt && (
                        <p className="text-xs text-gray-500 mt-1">
                          Image: {generatedPost.image_prompt.substring(0, 100)}...
                        </p>
                      )}
                    </div>
                  )}

                  {/* Engagement Preview */}
                  <div className="border-t pt-3 flex items-center justify-between text-sm text-gray-500">
                    <div className="flex space-x-4">
                      <span>👍 Like</span>
                      <span>💬 Comment</span>
                      <span>🔄 Repost</span>
                      <span>📤 Send</span>
                    </div>
                  </div>
                </div>

                {/* Reading Time */}
                <div className="mt-3 text-sm text-gray-600">
                  Estimated reading time: {generatedPost.estimated_reading_time} seconds
                </div>
              </div>

              {/* Post Components Breakdown */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Post Structure Analysis</h3>
                
                {/* Hook */}
                <div className="mb-4">
                  <label className="text-sm font-medium text-gray-700">Hook:</label>
                  <div className="mt-1 p-3 bg-blue-50 rounded-lg">
                    <p className="text-gray-800">{generatedPost.hook}</p>
                  </div>
                </div>

                {/* Body */}
                <div className="mb-4">
                  <label className="text-sm font-medium text-gray-700">Body:</label>
                  <div className="mt-1 p-3 bg-gray-50 rounded-lg">
                    <p className="text-gray-800">{generatedPost.body}</p>
                  </div>
                </div>

                {/* Call to Action */}
                <div className="mb-4">
                  <label className="text-sm font-medium text-gray-700">Call to Action:</label>
                  <div className="mt-1 p-3 bg-green-50 rounded-lg">
                    <p className="text-gray-800">{generatedPost.call_to_action}</p>
                  </div>
                </div>

                {/* Trending Hashtags Suggestions */}
                {generatedPost.hashtags && generatedPost.hashtags.length > 0 && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-gray-700">
                        🔥 Trending Hashtag Suggestions:
                      </label>
                      <span className="text-xs text-gray-500">
                        Based on current LinkedIn trends
                      </span>
                    </div>
                    <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-3">
                      <div className="flex flex-wrap gap-2">
                        {generatedPost.hashtags.map((tag, index) => (
                          <button
                            key={index}
                            onClick={() => {
                              navigator.clipboard.writeText(tag);
                              toast.success(`Copied ${tag} to clipboard!`);
                            }}
                            className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-white border border-blue-200 text-blue-800 hover:bg-blue-100 transition-colors cursor-pointer"
                            title="Click to copy"
                          >
                            <FiHash className="mr-1" />
                            {tag.replace('#', '')}
                            {index < 3 && (
                              <span className="ml-2 text-xs bg-red-500 text-white px-1 rounded">HOT</span>
                            )}
                          </button>
                        ))}
                      </div>
                      <p className="text-xs text-gray-600 mt-2">
                        💡 Click any hashtag to copy • Use 5-7 for optimal reach • Mix trending with niche tags
                      </p>
                    </div>
                  </div>
                )}

                {/* Style Analysis */}
                {generatedPost.style_analysis && (
                  <div className="mt-4 p-3 bg-purple-50 rounded-lg">
                    <p className="text-sm font-medium text-purple-800 mb-1">Style Analysis:</p>
                    <p className="text-sm text-purple-700">{generatedPost.style_analysis}</p>
                  </div>
                )}
              </div>
              
              {/* Generated Image Details Card */}
              {generatedPost.image_url && (
                <div className="card">
                  <h3 className="text-lg font-semibold mb-3">📸 Generated Visual Asset</h3>
                  <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-4">
                    <div className="mb-4">
                      <img 
                        src={generatedPost.image_url} 
                        alt="Generated visual for LinkedIn post"
                        className="w-full rounded-lg shadow-lg"
                        style={{ maxHeight: '500px', objectFit: 'contain' }}
                      />
                    </div>
                    
                    <div className="bg-white rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">Visual Type:</span>
                        <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                          {generatedPost.image_type ? generatedPost.image_type.charAt(0).toUpperCase() + generatedPost.image_type.slice(1) : 'Illustration'}
                        </span>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">Relevance Score:</span>
                        <div className="flex items-center">
                          <div className="w-32 bg-gray-200 rounded-full h-2 mr-2">
                            <div 
                              className={`h-2 rounded-full ${
                                generatedPost.image_relevance_score >= 0.8 
                                  ? 'bg-green-500' 
                                  : generatedPost.image_relevance_score >= 0.6
                                  ? 'bg-yellow-500'
                                  : 'bg-red-500'
                              }`}
                              style={{ width: `${(generatedPost.image_relevance_score || 0.7) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium">
                            {Math.round((generatedPost.image_relevance_score || 0.7) * 100)}%
                          </span>
                        </div>
                      </div>
                      
                      {generatedPost.image_prompt && (
                        <div className="pt-2 border-t">
                          <p className="text-xs text-gray-600">
                            <strong>Generation Prompt:</strong> {generatedPost.image_prompt}
                          </p>
                        </div>
                      )}
                      
                      <div className="pt-2 flex justify-end">
                        <a 
                          href={generatedPost.image_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                        >
                          Open in new tab →
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Empty State */}
          {!generatedPost && !loading && (
            <div className="card text-center py-12">
              <FiLinkedin className="mx-auto text-6xl text-gray-300 mb-4" />
              <p className="text-gray-500">
                Configure your post settings to generate engaging LinkedIn content
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LinkedInPostGenerator;