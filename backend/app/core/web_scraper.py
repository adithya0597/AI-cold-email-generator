"""
Web scraping service for extracting content from websites
"""

import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
import logging
import asyncio
from urllib.parse import urlparse, urljoin
import re

from ..models import WebScrapingResult

logger = logging.getLogger(__name__)


class WebScraper:
    """Service for scraping and parsing web content"""
    
    def __init__(self):
        self.timeout = 10  # Reduced from 30 seconds for faster response
        self.max_retries = 2  # Reduced from 3 for faster failure
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def scrape_website(self, url: str) -> WebScrapingResult:
        """
        Scrape content from a website
        
        Args:
            url: The URL to scrape
            
        Returns:
            WebScrapingResult with extracted content
        """
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return WebScrapingResult(
                    url=url,
                    success=False,
                    error_message="Invalid URL format"
                )
            
            # Fetch the webpage
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await self._fetch_with_retry(client, url)
                
                if response is None:
                    return WebScrapingResult(
                        url=url,
                        success=False,
                        error_message="Failed to fetch webpage after retries"
                    )
                
                # Parse HTML content
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract text content
                text_content = self._extract_text_content(soup)
                
                # Extract metadata
                metadata = self._extract_metadata(soup, url)
                
                # Clean and process text
                cleaned_text = self._clean_text(text_content)
                
                return WebScrapingResult(
                    url=url,
                    success=True,
                    content=cleaned_text,
                    metadata=metadata
                )
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return WebScrapingResult(
                url=url,
                success=False,
                error_message=str(e)
            )
    
    async def _fetch_with_retry(self, client: httpx.AsyncClient, url: str) -> Optional[httpx.Response]:
        """
        Fetch URL with retry logic
        """
        for attempt in range(self.max_retries):
            try:
                response = await client.get(url, headers=self.headers, follow_redirects=True)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error {e.response.status_code} for {url}, attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return None
            except Exception as e:
                logger.warning(f"Error fetching {url}, attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries - 1:
                    return None
            
            # Wait before retry
            await asyncio.sleep(2 ** attempt)
        
        return None
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main text content from HTML
        """
        # Remove script and style elements
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        # Try to find main content areas
        main_content = None
        
        # Look for common content containers
        content_selectors = [
            'main',
            'article',
            '[role="main"]',
            '#content',
            '.content',
            '#main',
            '.main'
        ]
        
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # If no main content found, use body
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Extract text
        text = main_content.get_text(separator='\n', strip=True)
        
        # Also extract important elements that might be outside main content
        # Extract company mission/vision if available
        mission_elements = soup.find_all(text=re.compile(r'(mission|vision|values|about)', re.I))
        mission_text = ' '.join([elem.parent.get_text(strip=True) for elem in mission_elements[:3]])
        
        # Extract key services/products
        services_elements = soup.find_all(text=re.compile(r'(services|products|solutions)', re.I))
        services_text = ' '.join([elem.parent.get_text(strip=True) for elem in services_elements[:3]])
        
        # Combine all text
        combined_text = f"{text}\n\nMission/Vision: {mission_text}\n\nServices/Products: {services_text}"
        
        return combined_text
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract metadata from the webpage
        """
        metadata = {
            'url': url,
            'domain': urlparse(url).netloc
        }
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            metadata['description'] = meta_desc.get('content', '')
        
        # Extract Open Graph data
        og_title = soup.find('meta', property='og:title')
        if og_title:
            metadata['og_title'] = og_title.get('content', '')
        
        og_description = soup.find('meta', property='og:description')
        if og_description:
            metadata['og_description'] = og_description.get('content', '')
        
        # Extract company name from various sources
        company_name = None
        
        # Try JSON-LD structured data
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                import json
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    company_name = data.get('name') or data.get('organizationName')
            except:
                pass
        
        # Try meta tags
        if not company_name:
            org_meta = soup.find('meta', attrs={'name': 'organization'})
            if org_meta:
                company_name = org_meta.get('content', '')
        
        if company_name:
            metadata['company_name'] = company_name
        
        # Extract contact information if available
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, soup.get_text())
        if emails:
            metadata['contact_emails'] = list(set(emails))[:3]  # Limit to 3 emails
        
        # Extract social media links
        social_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if any(social in href for social in ['linkedin.com', 'twitter.com', 'facebook.com']):
                social_links.append(href)
        
        if social_links:
            metadata['social_media'] = list(set(social_links))[:5]  # Limit to 5 links
        
        return metadata
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-\(\)\:\;\"\'\/]', '', text)
        
        # Remove very short lines (likely navigation items)
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if len(line.strip()) > 20]
        
        # Join lines back
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Limit text length to avoid token limits and speed up processing
        max_chars = 3000  # Reduced from 10000 for faster processing
        if len(cleaned_text) > max_chars:
            # Try to cut at a sentence boundary
            sentences = cleaned_text[:max_chars].split('.')
            cleaned_text = '.'.join(sentences[:-1]) + '.'
        
        return cleaned_text
    
    async def scrape_multiple_pages(self, base_url: str, max_pages: int = 3) -> List[WebScrapingResult]:
        """
        Scrape multiple pages from a website
        
        Args:
            base_url: The base URL to start from
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of WebScrapingResult objects
        """
        results = []
        visited_urls = set()
        to_visit = [base_url]
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while to_visit and len(results) < max_pages:
                url = to_visit.pop(0)
                
                if url in visited_urls:
                    continue
                
                visited_urls.add(url)
                
                # Scrape the page
                result = await self.scrape_website(url)
                results.append(result)
                
                if result.success:
                    # Extract links from the page
                    try:
                        response = await client.get(url, headers=self.headers)
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Find relevant internal links
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            full_url = urljoin(url, href)
                            
                            # Only add internal links
                            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                                # Prioritize about, services, products pages
                                if any(keyword in href.lower() for keyword in ['about', 'service', 'product', 'solution']):
                                    if full_url not in visited_urls and full_url not in to_visit:
                                        to_visit.insert(0, full_url)  # Add to front of queue
                                elif len(to_visit) < max_pages * 2:  # Limit queue size
                                    if full_url not in visited_urls and full_url not in to_visit:
                                        to_visit.append(full_url)
                    except Exception as e:
                        logger.warning(f"Error extracting links from {url}: {str(e)}")
        
        return results