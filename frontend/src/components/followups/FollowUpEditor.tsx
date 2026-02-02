/**
 * FollowUpEditor — modal editor for follow-up email drafts.
 *
 * Allows editing subject and body, then saving, sending, or copying.
 */

import { useState } from 'react';
import type { FollowupSuggestion } from '../../services/followups';
import {
  useUpdateDraft,
  useSendFollowup,
  useCopyFollowup,
} from '../../services/followups';

interface FollowUpEditorProps {
  suggestion: FollowupSuggestion;
  onClose: () => void;
}

export default function FollowUpEditor({ suggestion, onClose }: FollowUpEditorProps) {
  const [subject, setSubject] = useState(suggestion.draft_subject ?? '');
  const [body, setBody] = useState(suggestion.draft_body ?? '');
  const [toast, setToast] = useState<string | null>(null);

  const updateDraft = useUpdateDraft();
  const sendFollowup = useSendFollowup();
  const copyFollowup = useCopyFollowup();

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const handleSave = () => {
    updateDraft.mutate(
      {
        suggestionId: suggestion.id,
        updates: { draft_subject: subject, draft_body: body },
      },
      {
        onSuccess: () => showToast('Draft saved'),
        onError: () => showToast('Failed to save draft'),
      },
    );
  };

  const handleSend = () => {
    sendFollowup.mutate(
      { suggestionId: suggestion.id },
      {
        onSuccess: () => {
          showToast('Follow-up sent');
          onClose();
        },
        onError: () => showToast('Failed to send'),
      },
    );
  };

  const handleCopy = () => {
    copyFollowup.mutate(
      { suggestionId: suggestion.id, subject, body },
      {
        onSuccess: () => {
          showToast('Copied to clipboard & marked as sent');
          onClose();
        },
        onError: () => showToast('Failed to copy'),
      },
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      data-testid="followup-editor-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4" data-testid="followup-editor">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Edit Follow-up Draft</h2>
            <p className="text-sm text-gray-500">
              {suggestion.company} — {suggestion.job_title}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl"
            data-testid="followup-editor-close"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          <div>
            <label htmlFor="draft-subject" className="block text-sm font-medium text-gray-700 mb-1">
              Subject
            </label>
            <input
              id="draft-subject"
              type="text"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              data-testid="draft-subject-input"
            />
          </div>
          <div>
            <label htmlFor="draft-body" className="block text-sm font-medium text-gray-700 mb-1">
              Body
            </label>
            <textarea
              id="draft-body"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500"
              rows={10}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              data-testid="draft-body-input"
            />
          </div>
        </div>

        {/* Toast */}
        {toast && (
          <div
            className="mx-6 mb-2 px-3 py-2 text-sm rounded bg-blue-50 text-blue-700"
            data-testid="editor-toast"
          >
            {toast}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-gray-200">
          <button
            type="button"
            className="px-4 py-2 text-sm font-medium rounded bg-gray-100 text-gray-700 hover:bg-gray-200"
            onClick={handleSave}
            data-testid="editor-save-btn"
          >
            Save Draft
          </button>
          <button
            type="button"
            className="px-4 py-2 text-sm font-medium rounded bg-gray-100 text-gray-700 hover:bg-gray-200"
            onClick={handleCopy}
            data-testid="editor-copy-btn"
          >
            Copy to Clipboard
          </button>
          <button
            type="button"
            className="px-4 py-2 text-sm font-medium rounded bg-green-600 text-white hover:bg-green-700"
            onClick={handleSend}
            data-testid="editor-send-btn"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
