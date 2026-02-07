import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'react-toastify';
import {
  FiLinkedin,
  FiHash,
  FiTrendingUp,
  FiUsers,
  FiCopy,
  FiEye,
  FiImage,
  FiLink,
  FiClock,
  FiTrash2,
  FiChevronRight,
  FiBookOpen,
  FiAward,
  FiMessageSquare,
  FiStar,
  FiZap,
  FiFileText,
} from 'react-icons/fi';
import { useApiClient } from '../services/api';
import { TailSpin } from 'react-loader-spinner';
import DOMPurify from 'dompurify';
import sessionCache from '../utils/sessionCache';
import { useAnalytics } from '../hooks/useAnalytics';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface InfluencerStyle {
  value: string;
  label: string;
  description: string;
}

interface PostGoalOption {
  value: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface UploadedAuthor {
  author_id: string;
  author_name: string;
  post_count: number;
}

interface GeneratedPost {
  post_id: string;
  content: string;
  hook: string;
  body: string;
  call_to_action: string;
  hashtags: string[];
  estimated_reading_time: number;
  style_analysis?: string;
  image_url?: string;
  image_type?: string;
  image_prompt?: string;
  image_relevance_score?: number;
}

interface PostFormData {
  topic: string;
  industry: string;
  target_audience: string;
  post_goal: string;
  influencer_style: string;
  custom_author_name?: string;
}

interface PostTemplate {
  id: string;
  name: string;
  description: string;
  defaultTopic: string;
  suggestedStyle: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface HistoryEntry {
  id: string;
  timestamp: number;
  preview: string;
  style: string;
  template?: string;
  post: GeneratedPost;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const INFLUENCER_STYLES: InfluencerStyle[] = [
  { value: 'Gary Vaynerchuk', label: 'Gary Vaynerchuk', description: 'Direct, energetic, motivational' },
  { value: 'Simon Sinek', label: 'Simon Sinek', description: 'Thoughtful, philosophical, purpose-driven' },
  { value: 'Bren\u00e9 Brown', label: 'Bren\u00e9 Brown', description: 'Vulnerable, authentic, research-based' },
  { value: 'Neil Patel', label: 'Neil Patel', description: 'Data-driven, tactical, actionable' },
  { value: 'Arianna Huffington', label: 'Arianna Huffington', description: 'Wellness-focused, balanced' },
  { value: 'Adam Grant', label: 'Adam Grant', description: 'Research-backed, organizational psychology' },
  { value: 'custom', label: 'Custom Author', description: "Emulate any author's style" },
];

const POST_GOALS: PostGoalOption[] = [
  { value: 'Drive Engagement', label: 'Drive Engagement', icon: FiTrendingUp },
  { value: 'Generate Leads', label: 'Generate Leads', icon: FiUsers },
  { value: 'Build Thought Leadership', label: 'Build Thought Leadership', icon: FiEye },
];

const TEMPLATES: PostTemplate[] = [
  {
    id: 'job-update',
    name: 'Job Update',
    description: 'Share a career transition, new role, or milestone',
    defaultTopic: 'Excited to share my latest career move',
    suggestedStyle: 'Gary Vaynerchuk',
    icon: FiZap,
  },
  {
    id: 'industry-insight',
    name: 'Industry Insight',
    description: 'Share trends, data, or analysis from your field',
    defaultTopic: `Key trends shaping our industry in ${new Date().getFullYear()}`,
    suggestedStyle: 'Neil Patel',
    icon: FiTrendingUp,
  },
  {
    id: 'career-advice',
    name: 'Career Advice',
    description: 'Offer tips and lessons from your professional journey',
    defaultTopic: 'Lessons I wish I knew earlier in my career',
    suggestedStyle: 'Adam Grant',
    icon: FiBookOpen,
  },
  {
    id: 'achievement',
    name: 'Achievement',
    description: 'Celebrate a win, launch, or project completion',
    defaultTopic: 'Proud to announce a major milestone',
    suggestedStyle: 'Arianna Huffington',
    icon: FiAward,
  },
  {
    id: 'networking',
    name: 'Networking',
    description: 'Connect with your audience and spark conversations',
    defaultTopic: 'The power of building genuine professional relationships',
    suggestedStyle: 'Bren\u00e9 Brown',
    icon: FiMessageSquare,
  },
  {
    id: 'thought-leadership',
    name: 'Thought Leadership',
    description: 'Share a bold perspective or framework',
    defaultTopic: 'A contrarian take on a popular industry belief',
    suggestedStyle: 'Simon Sinek',
    icon: FiStar,
  },
];

const COLD_EMAIL_CACHE_KEY = 'ColdEmailGenerator';
const LINKEDIN_CACHE_KEY = 'LinkedInPostGenerator';
const HISTORY_STORAGE_KEY = 'linkedin_post_history';
const MAX_HISTORY_SIZE = 50;

// ---------------------------------------------------------------------------
// History helpers
// ---------------------------------------------------------------------------

function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as HistoryEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveHistory(entries: HistoryEntry[]): void {
  try {
    const capped = entries.slice(0, MAX_HISTORY_SIZE);
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(capped));
  } catch {
    // Storage full - silently ignore
  }
}

// ---------------------------------------------------------------------------
// Sanitize helper -- strips HTML tags from server-generated content to
// avoid XSS when rendering post previews. Only <strong> tags (from our
// own markdown-to-bold conversion) are preserved.
// ---------------------------------------------------------------------------
function sanitizePostLine(raw: string): string {
  const text = raw.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  return DOMPurify.sanitize(text, { ALLOWED_TAGS: ['strong'], ALLOWED_ATTR: [] });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const LinkedInPostGenerator: React.FC = () => {
  const { track } = useAnalytics();
  const apiClient = useApiClient();

  // Form / generation state
  const [loading, setLoading] = useState(false);
  const [generatedPost, setGeneratedPost] = useState<GeneratedPost | null>(null);
  const [showCustomAuthor, setShowCustomAuthor] = useState(false);
  const [characterCount, setCharacterCount] = useState(0);
  const [uploadedAuthors, setUploadedAuthors] = useState<UploadedAuthor[]>([]);
  const [selectedUploadedAuthor, setSelectedUploadedAuthor] = useState('');
  const [generateImage, setGenerateImage] = useState(false);
  const [referenceUrls, setReferenceUrls] = useState<string[]>(['']);

  // Template state
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

  // History state
  const [activeTab, setActiveTab] = useState<'compose' | 'history'>('compose');
  const [history, setHistory] = useState<HistoryEntry[]>(loadHistory);
  const [viewingHistoryPost, setViewingHistoryPost] = useState<HistoryEntry | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
  } = useForm<PostFormData>();

  const watchedStyle = watch('influencer_style');

  // -----------------------------------------------------------------------
  // Load cold email cross-fill and cached data
  // -----------------------------------------------------------------------
  useEffect(() => {
    const coldEmailData = sessionCache.get(COLD_EMAIL_CACHE_KEY) as Record<string, string | undefined>;
    if (coldEmailData) {
      if (coldEmailData.company_tone) {
        const toneToStyle: Record<string, string> = {
          professional: 'Adam Grant',
          friendly: 'Gary Vaynerchuk',
          casual: 'Bren\u00e9 Brown',
          formal: 'Simon Sinek',
          enthusiastic: 'Gary Vaynerchuk',
        };
        setValue('influencer_style', toneToStyle[coldEmailData.company_tone] || 'professional');
      }
      if (coldEmailData.pain_point) {
        setValue('topic', coldEmailData.pain_point);
      }
      if (coldEmailData.recipient_role) {
        setValue('target_audience', `${coldEmailData.recipient_role}s and decision makers`);
      }
    }

    const linkedInData = sessionCache.get(LINKEDIN_CACHE_KEY) as Record<string, unknown>;
    if (linkedInData) {
      Object.keys(linkedInData).forEach((key) => {
        if (key !== 'timestamp' && key !== 'generatedPost' && key !== 'referenceUrls') {
          setValue(key as keyof PostFormData, linkedInData[key] as string);
        }
      });
      if (linkedInData.generatedPost) setGeneratedPost(linkedInData.generatedPost as GeneratedPost);
      if (linkedInData.generateImage !== undefined) setGenerateImage(linkedInData.generateImage as boolean);
      if (linkedInData.referenceUrls) setReferenceUrls(linkedInData.referenceUrls as string[]);
    }
  }, [setValue]);

  // Watch influencer style changes
  useEffect(() => {
    setShowCustomAuthor(watchedStyle === 'custom');
    if (watchedStyle === 'custom') {
      fetchUploadedAuthors();
    }
    if (watchedStyle) {
      track('linkedin_style_selected', { style: watchedStyle });
    }
  }, [watchedStyle]);

  // Debounced session cache save
  const watchedValues = watch(['topic', 'industry', 'target_audience', 'influencer_style', 'post_goal']);
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      const [topic, industry, target_audience, influencer_style, post_goal] = watchedValues;
      sessionCache.set(LINKEDIN_CACHE_KEY, {
        topic,
        industry,
        target_audience,
        influencer_style,
        post_goal,
        generatedPost,
        generateImage,
        referenceUrls,
      });
    }, 500);
    return () => clearTimeout(timeoutId);
  }, [watchedValues, generatedPost, generateImage, referenceUrls]);

  // -----------------------------------------------------------------------
  // Fetchers
  // -----------------------------------------------------------------------
  const fetchUploadedAuthors = async () => {
    try {
      const response = await apiClient.get('/api/author-styles');
      setUploadedAuthors(response.data);
    } catch (error) {
      console.error('Failed to fetch uploaded authors:', error);
    }
  };

  // -----------------------------------------------------------------------
  // Template selection
  // -----------------------------------------------------------------------
  const handleTemplateSelect = useCallback(
    (template: PostTemplate) => {
      setSelectedTemplate(template.id);
      setValue('topic', template.defaultTopic);
      setValue('influencer_style', template.suggestedStyle);
      setShowCustomAuthor(template.suggestedStyle === 'custom');

      track('linkedin_template_selected', {
        template: template.id,
        style: template.suggestedStyle,
      });
    },
    [setValue, track],
  );

  const clearTemplate = useCallback(() => {
    setSelectedTemplate(null);
    setValue('topic', '');
    setValue('influencer_style', '');
  }, [setValue]);

  // -----------------------------------------------------------------------
  // Form submission
  // -----------------------------------------------------------------------
  const isSubmitting = useRef(false);
  const onSubmit = async (data: PostFormData) => {
    if (isSubmitting.current) return;
    isSubmitting.current = true;
    setLoading(true);
    try {
      if (data.influencer_style === 'custom' && !data.custom_author_name) {
        toast.error('Please provide a custom author name');
        setLoading(false);
        return;
      }

      const validUrls = referenceUrls.filter((url) => url.trim() !== '');

      const invalidUrl = validUrls.find((url) => !url.startsWith('http://') && !url.startsWith('https://'));
      if (invalidUrl) {
        toast.error('Reference URLs must start with http:// or https://');
        return;
      }

      const requestData = {
        ...data,
        generate_image: generateImage,
        reference_urls: validUrls,
      };

      const response = await apiClient.post('/api/generate-post', requestData);
      const postData = response.data as GeneratedPost;
      setGeneratedPost(postData);
      setCharacterCount(postData.content.length);
      toast.success('LinkedIn post generated successfully!');

      // Save to history
      const entry: HistoryEntry = {
        id: postData.post_id || crypto.randomUUID(),
        timestamp: Date.now(),
        preview: postData.content.slice(0, 120),
        style: data.influencer_style === 'custom' ? data.custom_author_name || 'Custom' : data.influencer_style,
        template: selectedTemplate || undefined,
        post: postData,
      };
      setHistory((prev) => {
        const updated = [entry, ...prev];
        saveHistory(updated);
        return updated.slice(0, MAX_HISTORY_SIZE);
      });

      track('linkedin_post_generated', {
        style: data.influencer_style,
        template: selectedTemplate,
        has_references: validUrls.length > 0,
        has_image: generateImage,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      toast.error('Failed to generate post: ' + message);
    } finally {
      setLoading(false);
      isSubmitting.current = false;
    }
  };

  // -----------------------------------------------------------------------
  // Clipboard
  // -----------------------------------------------------------------------
  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success('Copied to clipboard!');
      track('linkedin_post_copied', {
        style: watchedStyle,
        template: selectedTemplate,
      });
    } catch {
      toast.error('Failed to copy to clipboard');
    }
  };

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------
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

  const deleteHistoryEntry = (id: string) => {
    setHistory((prev) => {
      const updated = prev.filter((e) => e.id !== id);
      saveHistory(updated);
      return updated;
    });
    if (viewingHistoryPost?.id === id) setViewingHistoryPost(null);
  };

  const formatDate = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  // -----------------------------------------------------------------------
  // Render: Template selector
  // -----------------------------------------------------------------------
  const renderTemplates = () => (
    <div className="mb-6">
      <h3 className="text-sm font-medium text-gray-700 mb-3">Start with a template or blank post</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {/* Blank post */}
        <button
          type="button"
          onClick={clearTemplate}
          className={`flex flex-col items-center p-3 rounded-lg border-2 transition-colors text-center ${
            selectedTemplate === null
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
          }`}
        >
          <FiFileText className="text-xl mb-1 text-gray-500" aria-hidden="true" />
          <span className="text-xs font-medium">Blank Post</span>
        </button>

        {TEMPLATES.map((tpl) => {
          const Icon = tpl.icon;
          return (
            <button
              key={tpl.id}
              type="button"
              onClick={() => handleTemplateSelect(tpl)}
              className={`flex flex-col items-center p-3 rounded-lg border-2 transition-colors text-center ${
                selectedTemplate === tpl.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <Icon className="text-xl mb-1 text-blue-600" aria-hidden="true" />
              <span className="text-xs font-medium">{tpl.name}</span>
              <span className="text-[10px] text-gray-500 leading-tight mt-0.5 hidden sm:block">{tpl.description}</span>
            </button>
          );
        })}
      </div>
    </div>
  );

  // -----------------------------------------------------------------------
  // Render: Post preview (shared between compose & history)
  // -----------------------------------------------------------------------
  const renderPostPreview = (post: GeneratedPost) => (
    <>
      {/* Post Preview */}
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Generated Post</h3>
          <div className="flex items-center space-x-4">
            <span className={`text-sm ${getCharacterCountColor()}`}>{post.content.length} characters</span>
            <button
              onClick={() => copyToClipboard(post.content)}
              className="p-2 text-gray-600 hover:text-primary-600 transition-colors"
              title="Copy to clipboard"
              aria-label="Copy post to clipboard"
            >
              <FiCopy aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* LinkedIn-style post preview */}
        <div className="border rounded-lg p-4 bg-white">
          <div className="flex items-start mb-3">
            <div className="w-12 h-12 bg-gradient-to-br from-primary-400 to-primary-600 rounded-full flex items-center justify-center text-white font-bold flex-shrink-0">
              YN
            </div>
            <div className="ml-3">
              <p className="font-semibold">Your Name</p>
              <p className="text-sm text-gray-500">Professional Title &bull; Now</p>
            </div>
          </div>

          <div className="text-gray-800 mb-3">
            {(() => {
              const postText = post.content.split('#')[0].trim();
              const lines = postText.split('\n');

              return lines.map((line, idx) => {
                const sanitized = sanitizePostLine(line);
                const isBullet = /^[\u2192\u25B8\u2022\u2713]/.test(line.trim());
                const isEmpty = line.trim() === '';

                if (isEmpty) {
                  return <div key={idx} className="h-2" />;
                }

                return (
                  <div
                    key={idx}
                    className={`${isBullet ? 'pl-4' : ''} ${idx > 0 && !isEmpty ? 'mt-1' : ''}`}
                    dangerouslySetInnerHTML={{ __html: sanitized }}
                  />
                );
              });
            })()}
          </div>

          {/* Generated Image Display */}
          {post.image_url && (
            <div className="mb-3">
              <div className="relative rounded-lg overflow-hidden">
                <img
                  src={post.image_url}
                  alt="Post visual"
                  className="w-full h-auto object-cover"
                  style={{ maxHeight: '400px' }}
                />
                {post.image_type && (
                  <div className="absolute top-2 left-2 bg-black bg-opacity-70 text-white px-2 py-1 rounded text-xs">
                    {post.image_type.toUpperCase()}
                  </div>
                )}
                {post.image_relevance_score != null && post.image_relevance_score >= 0.8 && (
                  <div className="absolute top-2 right-2 bg-green-500 text-white px-2 py-1 rounded text-xs">
                    Highly Relevant
                  </div>
                )}
              </div>
              {post.image_prompt && (
                <p className="text-xs text-gray-500 mt-1">Image: {post.image_prompt.substring(0, 100)}...</p>
              )}
            </div>
          )}

          {/* Engagement Preview */}
          <div className="border-t pt-3 flex items-center justify-between text-sm text-gray-500">
            <div className="flex space-x-4">
              <span>Like</span>
              <span>Comment</span>
              <span>Repost</span>
              <span>Send</span>
            </div>
          </div>
        </div>

        {/* Reading Time */}
        <div className="mt-3 text-sm text-gray-600">
          Estimated reading time: {post.estimated_reading_time} seconds
        </div>
      </div>

      {/* Post Components Breakdown */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Post Structure Analysis</h3>

        {/* Hook */}
        <div className="mb-4">
          <label className="text-sm font-medium text-gray-700">Hook:</label>
          <div className="mt-1 p-3 bg-blue-50 rounded-lg">
            <p className="text-gray-800">{post.hook}</p>
          </div>
        </div>

        {/* Body */}
        <div className="mb-4">
          <label className="text-sm font-medium text-gray-700">Body:</label>
          <div className="mt-1 p-3 bg-gray-50 rounded-lg">
            <p className="text-gray-800">{post.body}</p>
          </div>
        </div>

        {/* Call to Action */}
        <div className="mb-4">
          <label className="text-sm font-medium text-gray-700">Call to Action:</label>
          <div className="mt-1 p-3 bg-green-50 rounded-lg">
            <p className="text-gray-800">{post.call_to_action}</p>
          </div>
        </div>

        {/* Trending Hashtags Suggestions */}
        {post.hashtags && post.hashtags.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">Trending Hashtag Suggestions:</label>
              <span className="text-xs text-gray-500">Based on current LinkedIn trends</span>
            </div>
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-3">
              <div className="flex flex-wrap gap-2">
                {post.hashtags.map((tag, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      navigator.clipboard.writeText(tag);
                      toast.success(`Copied ${tag} to clipboard!`);
                    }}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-white border border-blue-200 text-blue-800 hover:bg-blue-100 transition-colors cursor-pointer"
                    title="Click to copy"
                  >
                    <FiHash className="mr-1" aria-hidden="true" />
                    {tag.replace('#', '')}
                    {index < 3 && <span className="ml-2 text-xs bg-red-500 text-white px-1 rounded">HOT</span>}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-600 mt-2">
                Click any hashtag to copy -- Use 5-7 for optimal reach -- Mix trending with niche tags
              </p>
            </div>
          </div>
        )}

        {/* Style Analysis */}
        {post.style_analysis && (
          <div className="mt-4 p-3 bg-purple-50 rounded-lg">
            <p className="text-sm font-medium text-purple-800 mb-1">Style Analysis:</p>
            <p className="text-sm text-purple-700">{post.style_analysis}</p>
          </div>
        )}
      </div>

      {/* Generated Image Details Card */}
      {post.image_url && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-3">Generated Visual Asset</h3>
          <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-4">
            <div className="mb-4">
              <img
                src={post.image_url}
                alt="Generated visual for LinkedIn post"
                className="w-full rounded-lg shadow-lg"
                style={{ maxHeight: '500px', objectFit: 'contain' }}
              />
            </div>

            <div className="bg-white rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Visual Type:</span>
                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                  {post.image_type
                    ? post.image_type.charAt(0).toUpperCase() + post.image_type.slice(1)
                    : 'Illustration'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Relevance Score:</span>
                <div className="flex items-center">
                  <div className="w-32 bg-gray-200 rounded-full h-2 mr-2">
                    <div
                      className={`h-2 rounded-full ${
                        (post.image_relevance_score ?? 0.7) >= 0.8
                          ? 'bg-green-500'
                          : (post.image_relevance_score ?? 0.7) >= 0.6
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                      }`}
                      style={{ width: `${(post.image_relevance_score ?? 0.7) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">
                    {Math.round((post.image_relevance_score ?? 0.7) * 100)}%
                  </span>
                </div>
              </div>

              {post.image_prompt && (
                <div className="pt-2 border-t">
                  <p className="text-xs text-gray-600">
                    <strong>Generation Prompt:</strong> {post.image_prompt}
                  </p>
                </div>
              )}

              <div className="pt-2 flex justify-end">
                <a
                  href={post.image_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  Open in new tab
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );

  // -----------------------------------------------------------------------
  // Render: History tab
  // -----------------------------------------------------------------------
  const renderHistory = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* History list */}
      <div className="space-y-3">
        <h2 className="text-xl font-semibold mb-4 flex items-center">
          <FiClock className="mr-2 text-blue-600" aria-hidden="true" />
          Post History
          <span className="ml-2 text-sm text-gray-400 font-normal">({history.length})</span>
        </h2>
        {history.length === 0 ? (
          <div className="card text-center py-12">
            <FiClock className="mx-auto text-5xl text-gray-300 mb-4" aria-hidden="true" />
            <p className="text-gray-500">No posts generated yet. Create your first post!</p>
          </div>
        ) : (
          history.map((entry) => (
            <div
              key={entry.id}
              className={`card cursor-pointer hover:ring-2 hover:ring-blue-200 transition-all ${
                viewingHistoryPost?.id === entry.id ? 'ring-2 ring-blue-500' : ''
              }`}
              onClick={() => setViewingHistoryPost(entry)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1 min-w-0 mr-3">
                  <p className="text-sm text-gray-800 truncate">{entry.preview}...</p>
                  <div className="flex flex-wrap items-center mt-2 gap-2">
                    <span className="text-xs text-gray-500">{formatDate(entry.timestamp)}</span>
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">{entry.style}</span>
                    {entry.template && (
                      <span className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded-full">
                        {TEMPLATES.find((t) => t.id === entry.template)?.name || entry.template}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-2 flex-shrink-0">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      copyToClipboard(entry.post.content);
                    }}
                    className="p-1.5 text-gray-400 hover:text-blue-600 transition-colors"
                    title="Copy post"
                    aria-label="Copy post to clipboard"
                  >
                    <FiCopy className="w-4 h-4" aria-hidden="true" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteHistoryEntry(entry.id);
                    }}
                    className="p-1.5 text-gray-400 hover:text-red-600 transition-colors"
                    title="Delete"
                    aria-label="Delete post from history"
                  >
                    <FiTrash2 className="w-4 h-4" aria-hidden="true" />
                  </button>
                  <FiChevronRight className="w-4 h-4 text-gray-300" aria-hidden="true" />
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* History detail */}
      <div className="space-y-6">
        {viewingHistoryPost ? (
          renderPostPreview(viewingHistoryPost.post)
        ) : (
          <div className="card text-center py-12">
            <FiEye className="mx-auto text-5xl text-gray-300 mb-4" aria-hidden="true" />
            <p className="text-gray-500">Select a post from the history to preview</p>
          </div>
        )}
      </div>
    </div>
  );

  // -----------------------------------------------------------------------
  // Main render
  // -----------------------------------------------------------------------
  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">LinkedIn Post Generator</h1>
            <p className="text-gray-600">Create engaging LinkedIn posts that drive results</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {/* Tabs */}
            <div className="flex rounded-lg border border-gray-300 overflow-hidden">
              <button
                onClick={() => setActiveTab('compose')}
                className={`px-3 sm:px-4 py-2 min-h-[44px] text-sm font-medium transition-colors ${
                  activeTab === 'compose' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                <FiLinkedin className="inline mr-1.5 -mt-0.5" aria-hidden="true" />
                Compose
              </button>
              <button
                onClick={() => setActiveTab('history')}
                className={`px-3 sm:px-4 py-2 min-h-[44px] text-sm font-medium transition-colors ${
                  activeTab === 'history' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                <FiClock className="inline mr-1.5 -mt-0.5" aria-hidden="true" />
                History
                {history.length > 0 && (
                  <span className="ml-1.5 bg-gray-200 text-gray-700 text-xs px-1.5 py-0.5 rounded-full">
                    {history.length}
                  </span>
                )}
              </button>
            </div>
            <button
              onClick={clearCache}
              className="flex items-center px-3 sm:px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm"
              title="Clear all cached data"
            >
              Clear Session
            </button>
          </div>
        </div>
      </div>

      {activeTab === 'history' ? (
        renderHistory()
      ) : (
        <>
          {/* Template Library */}
          {renderTemplates()}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Input Form */}
            <div className="card">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <FiLinkedin className="mr-2 text-blue-600" aria-hidden="true" />
                Post Configuration
              </h2>

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                {/* Topic */}
                <div>
                  <label htmlFor="linkedin-topic" className="block text-sm font-medium text-gray-700 mb-1">Post Topic</label>
                  <input
                    id="linkedin-topic"
                    {...register('topic', { required: 'Topic is required' })}
                    className="input-field"
                    placeholder="The future of AI in business"
                    maxLength={500}
                  />
                  {errors.topic && <p className="text-red-500 text-xs mt-1">{errors.topic.message}</p>}
                </div>

                {/* Industry */}
                <div>
                  <label htmlFor="linkedin-industry" className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
                  <input
                    id="linkedin-industry"
                    {...register('industry', { required: 'Industry is required' })}
                    className="input-field"
                    placeholder="Technology, Finance, Healthcare..."
                    maxLength={200}
                  />
                  {errors.industry && <p className="text-red-500 text-xs mt-1">{errors.industry.message}</p>}
                </div>

                {/* Target Audience */}
                <div>
                  <label htmlFor="linkedin-audience" className="block text-sm font-medium text-gray-700 mb-1">Target Audience</label>
                  <input
                    id="linkedin-audience"
                    {...register('target_audience', { required: 'Target audience is required' })}
                    className="input-field"
                    placeholder="Tech leaders, entrepreneurs, marketing professionals..."
                    maxLength={200}
                  />
                  {errors.target_audience && (
                    <p className="text-red-500 text-xs mt-1">{errors.target_audience.message}</p>
                  )}
                </div>

                {/* Post Goal */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Post Goal</label>
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
                          <Icon className="mr-2 text-primary-600" aria-hidden="true" />
                          <span className="font-medium">{goal.label}</span>
                        </label>
                      );
                    })}
                  </div>
                  {errors.post_goal && <p className="text-red-500 text-xs mt-1">{errors.post_goal.message}</p>}
                </div>

                {/* Writing Style */}
                <div>
                  <label htmlFor="linkedin-style" className="block text-sm font-medium text-gray-700 mb-2">Writing Style</label>
                  <select
                    id="linkedin-style"
                    {...register('influencer_style', { required: 'Please select a style' })}
                    className="input-field mb-2"
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
                        <label htmlFor="linkedin-custom-author" className="block text-sm font-medium text-gray-700 mb-1">
                          Or Enter Any Author Name
                        </label>
                        <input
                          id="linkedin-custom-author"
                          className="input-field"
                          placeholder="Enter author name to emulate (e.g., Satya Nadella)"
                          value={selectedUploadedAuthor}
                          onChange={(e) => {
                            setSelectedUploadedAuthor(e.target.value);
                            setValue('custom_author_name', e.target.value);
                          }}
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          {selectedUploadedAuthor &&
                          uploadedAuthors.find((a) => a.author_name === selectedUploadedAuthor)
                            ? `Using uploaded samples for ${selectedUploadedAuthor}`
                            : "We'll analyze and emulate this author's writing style"}
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
                          Upload more author samples
                        </a>
                      </div>
                    </div>
                  )}
                </div>

                {/* Reference URLs (Optional) */}
                <div className="bg-indigo-50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center">
                      <FiLink className="text-indigo-600 mr-2" aria-hidden="true" />
                      <span className="text-sm font-medium text-gray-700">Reference URLs (Up to 3)</span>
                    </div>
                    {referenceUrls.length < 3 && (
                      <button
                        type="button"
                        onClick={() => setReferenceUrls([...referenceUrls, ''])}
                        className="text-sm text-indigo-600 hover:text-indigo-800 font-medium min-h-[44px]"
                      >
                        + Add URL
                      </button>
                    )}
                  </div>

                  {referenceUrls.map((url, index) => (
                    <div key={index} className="flex items-center space-x-2 mb-2">
                      <input
                        id={`linkedin-url-${index}`}
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
                          className="text-red-500 hover:text-red-700 min-w-[44px] min-h-[44px] flex items-center justify-center"
                          title="Remove URL"
                          aria-label={`Remove reference URL ${index + 1}`}
                        >
                          x
                        </button>
                      )}
                    </div>
                  ))}

                  <p className="text-xs text-gray-600 mt-1">
                    Provide URLs to articles or content pieces to use as reference. The AI will analyze and incorporate
                    insights from these sources while maintaining your chosen style.
                  </p>
                </div>

                {/* Image Generation Toggle */}
                <div className="bg-purple-50 rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <FiImage className="text-purple-600 mr-2" aria-hidden="true" />
                      <span className="text-sm font-medium text-gray-700">Generate AI Image (Optional)</span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        checked={generateImage}
                        onChange={(e) => setGenerateImage(e.target.checked)}
                        aria-label="Generate AI Image"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                    </label>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    {generateImage
                      ? 'AI will generate a relevant image (infographic, chart, or illustration) for your post'
                      : 'Post will be text-only for faster generation'}
                  </p>
                </div>

                {/* Submit Button */}
                <button type="submit" disabled={loading} className="w-full btn-primary py-3 flex items-center justify-center">
                  {loading ? (
                    <TailSpin height="20" width="20" color="white" />
                  ) : (
                    <>
                      <FiLinkedin className="mr-2" aria-hidden="true" />
                      Generate LinkedIn Post
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Generated Post */}
            <div className="space-y-6" aria-live="polite">
              {generatedPost ? (
                renderPostPreview(generatedPost)
              ) : (
                !loading && (
                  <div className="card text-center py-12">
                    <FiLinkedin className="mx-auto text-6xl text-gray-300 mb-4" aria-hidden="true" />
                    <p className="text-gray-500">Configure your post settings to generate engaging LinkedIn content</p>
                  </div>
                )
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default LinkedInPostGenerator;
