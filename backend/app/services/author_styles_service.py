"""
Author styles service for managing Excel-based author post database
"""

import pandas as pd
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import io

logger = logging.getLogger(__name__)


class AuthorStylesService:
    """Service for managing author styles from Excel uploads"""
    
    def __init__(self):
        # In production, use a database. For MVP, store in memory
        self.author_styles_db = {}
        self.required_columns = ['author_name', 'post_content', 'post_summary']
        self.optional_columns = ['post_link', 'post_date', 'engagement_metrics']
    
    async def process_excel_upload(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Process uploaded Excel file containing author posts
        
        Args:
            file_content: Excel file content as bytes
            filename: Original filename
            
        Returns:
            Processing result with statistics
        """
        try:
            # Read Excel file
            df = pd.read_excel(io.BytesIO(file_content))
            
            # Validate columns
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                return {
                    "success": False,
                    "error": f"Missing required columns: {', '.join(missing_columns)}",
                    "required_columns": self.required_columns
                }
            
            # Process each row
            processed_count = 0
            skipped_count = 0
            authors_added = set()
            
            for index, row in df.iterrows():
                try:
                    # Skip rows with missing required data
                    if pd.isna(row['author_name']) or pd.isna(row['post_content']):
                        skipped_count += 1
                        continue
                    
                    # Create author entry
                    author_id = str(uuid.uuid4())
                    author_name = str(row['author_name']).strip()
                    
                    # Initialize or update author in database
                    if author_name not in self.author_styles_db:
                        self.author_styles_db[author_name] = {
                            "author_id": author_id,
                            "author_name": author_name,
                            "posts": [],
                            "created_at": datetime.utcnow().isoformat(),
                            "post_count": 0,
                            "style_summary": ""
                        }
                    
                    # Add post to author's collection
                    post_entry = {
                        "post_id": str(uuid.uuid4()),
                        "content": str(row['post_content']),
                        "summary": str(row.get('post_summary', 'No summary provided')),
                        "link": str(row.get('post_link', '')) if pd.notna(row.get('post_link')) else None,
                        "date": self._parse_date(row.get('post_date')) if 'post_date' in row else None,
                        "engagement": self._parse_engagement(row.get('engagement_metrics')) if 'engagement_metrics' in row else None,
                        "word_count": len(str(row['post_content']).split()),
                        "character_count": len(str(row['post_content']))
                    }
                    
                    self.author_styles_db[author_name]["posts"].append(post_entry)
                    self.author_styles_db[author_name]["post_count"] += 1
                    
                    # Update style summary based on all posts
                    self._update_author_style_summary(author_name)
                    
                    authors_added.add(author_name)
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row {index}: {str(e)}")
                    skipped_count += 1
            
            return {
                "success": True,
                "processed_count": processed_count,
                "skipped_count": skipped_count,
                "authors_added": list(authors_added),
                "total_authors": len(self.author_styles_db),
                "message": f"Successfully processed {processed_count} posts from {len(authors_added)} authors"
            }
            
        except Exception as e:
            logger.error(f"Error processing Excel file: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to process Excel file. Please check the format."
            }
    
    def _parse_date(self, date_value) -> Optional[str]:
        """Parse date from various formats"""
        if pd.isna(date_value):
            return None
        
        try:
            if isinstance(date_value, str):
                return date_value
            elif hasattr(date_value, 'isoformat'):
                return date_value.isoformat()
            else:
                return str(date_value)
        except:
            return None
    
    def _parse_engagement(self, engagement_value) -> Optional[Dict[str, int]]:
        """Parse engagement metrics from string or dict"""
        if pd.isna(engagement_value):
            return None
        
        try:
            if isinstance(engagement_value, dict):
                return engagement_value
            elif isinstance(engagement_value, str):
                # Try to parse JSON
                if '{' in engagement_value:
                    return json.loads(engagement_value)
                # Try to parse simple format like "100 likes, 20 comments"
                metrics = {}
                parts = engagement_value.lower().split(',')
                for part in parts:
                    if 'like' in part:
                        metrics['likes'] = int(''.join(filter(str.isdigit, part)))
                    elif 'comment' in part:
                        metrics['comments'] = int(''.join(filter(str.isdigit, part)))
                    elif 'share' in part:
                        metrics['shares'] = int(''.join(filter(str.isdigit, part)))
                    elif 'view' in part:
                        metrics['views'] = int(''.join(filter(str.isdigit, part)))
                return metrics if metrics else None
        except:
            return None
    
    def _update_author_style_summary(self, author_name: str):
        """Generate a summary of the author's writing style based on their posts"""
        if author_name not in self.author_styles_db:
            return
        
        author_data = self.author_styles_db[author_name]
        posts = author_data["posts"]
        
        if not posts:
            return
        
        # Analyze post characteristics
        avg_word_count = sum(p["word_count"] for p in posts) / len(posts)
        avg_char_count = sum(p["character_count"] for p in posts) / len(posts)
        
        # Check for common patterns
        has_emojis = any('🔥' in p["content"] or '💡' in p["content"] or '🚀' in p["content"] for p in posts)
        has_questions = sum(1 for p in posts if '?' in p["content"]) / len(posts) > 0.5
        has_lists = sum(1 for p in posts if '\n•' in p["content"] or '\n-' in p["content"] or '1.' in p["content"]) / len(posts) > 0.3
        
        # Generate style summary
        style_elements = []
        
        if avg_word_count < 100:
            style_elements.append("concise")
        elif avg_word_count > 200:
            style_elements.append("detailed")
        
        if has_emojis:
            style_elements.append("uses emojis")
        
        if has_questions:
            style_elements.append("engages with questions")
        
        if has_lists:
            style_elements.append("structured with lists")
        
        # Analyze post summaries for themes
        summaries = [p["summary"].lower() for p in posts if p["summary"]]
        common_themes = []
        
        theme_keywords = {
            "leadership": ["leader", "leadership", "manage", "team"],
            "innovation": ["innovation", "innovative", "disrupt", "new"],
            "growth": ["growth", "scale", "expand", "develop"],
            "insights": ["insight", "lesson", "learn", "tip"],
            "storytelling": ["story", "experience", "journey", "personal"]
        }
        
        for theme, keywords in theme_keywords.items():
            if any(any(keyword in summary for keyword in keywords) for summary in summaries):
                common_themes.append(theme)
        
        # Combine into summary
        style_summary = f"Writing style: {', '.join(style_elements[:3])}. "
        if common_themes:
            style_summary += f"Common themes: {', '.join(common_themes[:3])}. "
        style_summary += f"Average post length: {int(avg_word_count)} words."
        
        author_data["style_summary"] = style_summary
    
    async def get_all_author_styles(self) -> List[Dict[str, Any]]:
        """
        Get all author styles from the database
        
        Returns:
            List of author style summaries
        """
        authors = []
        for author_name, data in self.author_styles_db.items():
            authors.append({
                "author_id": data["author_id"],
                "author_name": author_name,
                "post_count": data["post_count"],
                "style_summary": data["style_summary"],
                "created_at": data["created_at"],
                "sample_post": data["posts"][0]["content"][:200] + "..." if data["posts"] else None
            })
        
        return sorted(authors, key=lambda x: x["post_count"], reverse=True)
    
    async def get_author_posts(self, author_name: str) -> Optional[Dict[str, Any]]:
        """
        Get all posts for a specific author
        
        Args:
            author_name: Name of the author
            
        Returns:
            Author data with all posts
        """
        if author_name in self.author_styles_db:
            return self.author_styles_db[author_name]
        return None
    
    async def get_sample_posts_for_style(self, author_name: str, count: int = 3) -> List[str]:
        """
        Get sample posts for training style emulation
        
        Args:
            author_name: Name of the author
            count: Number of samples to return
            
        Returns:
            List of post contents
        """
        if author_name not in self.author_styles_db:
            return []
        
        posts = self.author_styles_db[author_name]["posts"]
        
        # Sort by engagement if available, otherwise random selection
        sorted_posts = posts
        if any(p.get("engagement") for p in posts):
            sorted_posts = sorted(posts, 
                                key=lambda p: sum(p.get("engagement", {}).values()) if p.get("engagement") else 0,
                                reverse=True)
        
        return [p["content"] for p in sorted_posts[:count]]
    
    async def delete_author_style(self, author_id: str) -> bool:
        """
        Delete an author style from the database
        
        Args:
            author_id: ID of the author to delete
            
        Returns:
            Success status
        """
        for author_name, data in list(self.author_styles_db.items()):
            if data["author_id"] == author_id:
                del self.author_styles_db[author_name]
                logger.info(f"Deleted author style: {author_name}")
                return True
        return False
    
    async def search_authors(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for authors by name or style
        
        Args:
            query: Search query
            
        Returns:
            List of matching authors
        """
        query_lower = query.lower()
        results = []
        
        for author_name, data in self.author_styles_db.items():
            if (query_lower in author_name.lower() or 
                query_lower in data.get("style_summary", "").lower()):
                results.append({
                    "author_id": data["author_id"],
                    "author_name": author_name,
                    "post_count": data["post_count"],
                    "style_summary": data["style_summary"]
                })
        
        return results
    
    def export_author_database(self) -> bytes:
        """
        Export the author database as Excel file
        
        Returns:
            Excel file as bytes
        """
        all_posts = []
        
        for author_name, data in self.author_styles_db.items():
            for post in data["posts"]:
                all_posts.append({
                    "author_name": author_name,
                    "post_content": post["content"],
                    "post_summary": post["summary"],
                    "post_link": post.get("link", ""),
                    "post_date": post.get("date", ""),
                    "word_count": post["word_count"],
                    "character_count": post["character_count"]
                })
        
        df = pd.DataFrame(all_posts)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Author Posts', index=False)
        
        output.seek(0)
        return output.read()