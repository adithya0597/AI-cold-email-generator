import React, { useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-toastify';
import { FiUpload, FiDownload, FiTrash2, FiSearch, FiUser, FiEye } from 'react-icons/fi';
import { TailSpin } from 'react-loader-spinner';
import axios from 'axios';

const AuthorStylesManager = () => {
  const [loading, setLoading] = useState(false);
  const [authors, setAuthors] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAuthor, setSelectedAuthor] = useState(null);
  const [authorDetails, setAuthorDetails] = useState(null);
  const [showUploadGuide, setShowUploadGuide] = useState(false);

  useEffect(() => {
    fetchAuthors();
  }, []);

  const fetchAuthors = async () => {
    try {
      const response = await axios.get('/api/author-styles');
      setAuthors(response.data);
    } catch (error) {
      toast.error('Failed to fetch authors: ' + error.message);
    }
  };

  const onDrop = async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      setLoading(true);
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await axios.post('/api/upload-author-styles', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });

        if (response.data.success) {
          toast.success(response.data.message);
          fetchAuthors(); // Refresh the list
        } else {
          toast.error(response.data.error || 'Failed to process file');
        }
      } catch (error) {
        toast.error('Error uploading file: ' + error.message);
      } finally {
        setLoading(false);
      }
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    maxFiles: 1
  });

  const deleteAuthor = async (authorId, authorName) => {
    if (window.confirm(`Are you sure you want to delete ${authorName}'s style?`)) {
      try {
        await axios.delete(`/api/author-styles/${authorId}`);
        toast.success('Author style deleted successfully');
        fetchAuthors();
      } catch (error) {
        toast.error('Failed to delete author: ' + error.message);
      }
    }
  };

  const viewAuthorDetails = async (authorName) => {
    try {
      const response = await axios.get(`/api/author-styles/${encodeURIComponent(authorName)}`);
      setAuthorDetails(response.data);
      setSelectedAuthor(authorName);
    } catch (error) {
      toast.error('Failed to fetch author details: ' + error.message);
    }
  };

  const exportDatabase = async () => {
    try {
      const response = await axios.get('/api/export-author-styles', {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'author_styles_export.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Database exported successfully');
    } catch (error) {
      toast.error('Failed to export database: ' + error.message);
    }
  };

  const searchAuthors = async () => {
    if (!searchQuery.trim()) {
      fetchAuthors();
      return;
    }

    try {
      const response = await axios.get(`/api/author-styles/search/${encodeURIComponent(searchQuery)}`);
      setAuthors(response.data);
    } catch (error) {
      toast.error('Search failed: ' + error.message);
    }
  };

  const filteredAuthors = authors.filter(author =>
    author.author_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    author.style_summary.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Author Styles Manager</h1>
        <p className="text-gray-600">Upload and manage LinkedIn author posts for style emulation</p>
      </div>

      {/* Upload Section */}
      <div className="card mb-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Upload Author Posts</h2>
          <button
            onClick={() => setShowUploadGuide(!showUploadGuide)}
            className="text-primary-600 hover:text-primary-700 text-sm"
          >
            {showUploadGuide ? 'Hide Guide' : 'Show Format Guide'}
          </button>
        </div>

        {showUploadGuide && (
          <div className="mb-4 p-4 bg-blue-50 rounded-lg">
            <h3 className="font-semibold text-blue-900 mb-2">Excel File Format</h3>
            <p className="text-sm text-blue-800 mb-2">Required columns:</p>
            <ul className="text-sm text-blue-700 space-y-1 ml-4">
              <li>• <strong>author_name</strong>: Name of the author</li>
              <li>• <strong>post_content</strong>: Full text of the LinkedIn post</li>
              <li>• <strong>post_summary</strong>: Brief description of post type/style</li>
            </ul>
            <p className="text-sm text-blue-800 mt-2">Optional columns:</p>
            <ul className="text-sm text-blue-700 space-y-1 ml-4">
              <li>• <strong>post_link</strong>: LinkedIn post URL</li>
              <li>• <strong>post_date</strong>: Date of the post</li>
              <li>• <strong>engagement_metrics</strong>: Likes, comments, shares</li>
            </ul>
          </div>
        )}

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-primary-400'
          }`}
        >
          <input {...getInputProps()} />
          {loading ? (
            <TailSpin height="40" width="40" color="#3B82F6" wrapperClass="justify-center" />
          ) : (
            <>
              <FiUpload className="mx-auto text-5xl text-gray-400 mb-3" />
              <p className="text-gray-600 mb-1">
                {isDragActive
                  ? 'Drop the Excel file here...'
                  : 'Drag & drop an Excel file here, or click to select'}
              </p>
              <p className="text-xs text-gray-500">Supports .xlsx and .xls files</p>
            </>
          )}
        </div>

        <div className="mt-4 flex justify-end">
          <button
            onClick={exportDatabase}
            className="flex items-center px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <FiDownload className="mr-2" />
            Export Database
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="card mb-6">
        <div className="flex space-x-2">
          <div className="flex-1 relative">
            <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && searchAuthors()}
              className="input-field pl-10"
              placeholder="Search authors by name or style..."
            />
          </div>
          <button
            onClick={searchAuthors}
            className="btn-primary"
          >
            Search
          </button>
        </div>
      </div>

      {/* Authors Table */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Uploaded Authors ({filteredAuthors.length})</h2>
        
        {filteredAuthors.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <FiUser className="mx-auto text-5xl mb-3" />
            <p>No authors uploaded yet</p>
            <p className="text-sm mt-1">Upload an Excel file to get started</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Author
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Posts
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Style Summary
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Sample
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredAuthors.map((author) => (
                  <tr key={author.author_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <FiUser className="text-gray-400 mr-2" />
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {author.author_name}
                          </div>
                          <div className="text-xs text-gray-500">
                            Added: {new Date(author.created_at).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
                        {author.post_count} posts
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-gray-600 max-w-xs truncate">
                        {author.style_summary}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-xs text-gray-500 max-w-xs truncate">
                        {author.sample_post}
                      </p>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => viewAuthorDetails(author.author_name)}
                          className="text-primary-600 hover:text-primary-900"
                          title="View details"
                        >
                          <FiEye />
                        </button>
                        <button
                          onClick={() => deleteAuthor(author.author_id, author.author_name)}
                          className="text-red-600 hover:text-red-900"
                          title="Delete"
                        >
                          <FiTrash2 />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Author Details Modal */}
      {selectedAuthor && authorDetails && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-lg bg-white">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold">{selectedAuthor}'s Posts</h3>
              <button
                onClick={() => {
                  setSelectedAuthor(null);
                  setAuthorDetails(null);
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            
            <div className="mb-4">
              <p className="text-sm text-gray-600">
                <strong>Total Posts:</strong> {authorDetails.post_count}
              </p>
              <p className="text-sm text-gray-600">
                <strong>Style:</strong> {authorDetails.style_summary}
              </p>
            </div>

            <div className="max-h-96 overflow-y-auto space-y-4">
              {authorDetails.posts.map((post) => (
                <div key={post.post_id} className="border rounded-lg p-4 bg-gray-50">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="text-sm font-medium text-gray-700">
                        {post.summary}
                      </p>
                      {post.date && (
                        <p className="text-xs text-gray-500">
                          {new Date(post.date).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    <div className="text-xs text-gray-500">
                      {post.word_count} words • {post.character_count} chars
                    </div>
                  </div>
                  
                  <div className="text-sm text-gray-800 whitespace-pre-wrap line-clamp-4">
                    {post.content}
                  </div>
                  
                  {post.engagement && (
                    <div className="mt-2 flex space-x-3 text-xs text-gray-500">
                      {post.engagement.likes && <span>👍 {post.engagement.likes}</span>}
                      {post.engagement.comments && <span>💬 {post.engagement.comments}</span>}
                      {post.engagement.shares && <span>🔄 {post.engagement.shares}</span>}
                    </div>
                  )}
                  
                  {post.link && (
                    <a
                      href={post.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary-600 hover:underline mt-2 inline-block"
                    >
                      View on LinkedIn →
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuthorStylesManager;