#!/usr/bin/env python3
"""
Test script for the Excel upload workflow
"""

import requests
import pandas as pd
from datetime import datetime
import json

# API base URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test if the API is running"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False

def create_sample_excel():
    """Create a sample Excel file for testing"""
    sample_data = {
        'author_name': [
            'Sarah Chen',
            'Sarah Chen',
            'Sarah Chen',
            'Michael Roberts',
            'Michael Roberts',
            'Emma Johnson',
            'Emma Johnson'
        ],
        'post_content': [
            """Just shipped a major feature after 3 months of development! 🚀

The key lesson? User feedback is EVERYTHING. We pivoted twice based on early beta testing, and the final product is 10x better than our original vision.

Don't build in isolation. Talk to your users early and often.

What's your approach to gathering user feedback during development?""",
            
            """The best engineers I know aren't the ones who write the most code.

They're the ones who:
→ Ask the right questions
→ Solve the right problems
→ Write code that others can understand
→ Delete more code than they add

Technical skills get you in the door. Problem-solving keeps you in the room.""",
            
            """Unpopular opinion: Most startups don't need microservices.

You need:
• A monolith that works
• Clear boundaries in your code
• Good deployment practices
• Monitoring that actually helps

Scale when you have the problem, not when you think you might have it.""",
            
            """After 15 years in sales, here's what I've learned:

People don't buy products. They buy better versions of themselves.

Your job isn't to sell features. It's to paint a picture of their success.

Focus on transformation, not transaction. The rest follows naturally.

#Sales #B2BSales #SalesStrategy""",
            
            """Closed a $2M deal today. Here's the email that started it all:

"Hi [Name], noticed you're scaling your team by 50% this quarter. Three similar companies using our solution reduced onboarding time by 40%. Worth a quick chat?"

62 words. No fluff. Just value.

Sometimes less really is more. 💼""",
            
            """Your network is your net worth? Maybe.

But your knowledge is your real currency.

Invest in learning. The ROI is infinite. 📚

What skill are you learning this quarter?""",
            
            """Leadership isn't about having all the answers.

It's about:
• Asking better questions
• Creating psychological safety
• Empowering others to shine
• Taking responsibility when things go wrong
• Sharing credit when things go right

The best leaders make everyone around them better. 🌟"""
        ],
        'post_summary': [
            'Product launch announcement with lessons learned',
            'Engineering philosophy and soft skills',
            'Technical architecture opinion',
            'Sales philosophy and mindset',
            'Deal closing success story',
            'Personal development and learning',
            'Leadership principles and team building'
        ],
        'post_date': [
            '2024-01-15', '2024-01-10', '2024-01-05',
            '2024-01-12', '2024-01-08',
            '2024-01-14', '2024-01-09'
        ],
        'engagement_metrics': [
            '1250 likes, 89 comments',
            '2100 likes, 156 comments',
            '3500 likes, 234 comments',
            '890 likes, 67 comments',
            '1560 likes, 98 comments',
            '450 likes, 23 comments',
            '1890 likes, 123 comments'
        ]
    }
    
    df = pd.DataFrame(sample_data)
    filename = 'sample_author_styles.xlsx'
    df.to_excel(filename, index=False)
    print(f"✅ Created sample Excel file: {filename}")
    return filename

def test_upload_excel(filename):
    """Test uploading the Excel file"""
    try:
        with open(filename, 'rb') as f:
            files = {'file': (filename, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            response = requests.post(f"{BASE_URL}/api/upload-author-styles", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Excel uploaded successfully")
            print(f"   - Authors processed: {data.get('authors_processed', 'N/A')}")
            print(f"   - Posts imported: {data.get('posts_imported', 'N/A')}")
            return True
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def test_get_authors():
    """Test fetching all authors"""
    try:
        response = requests.get(f"{BASE_URL}/api/author-styles")
        if response.status_code == 200:
            authors = response.json()
            print(f"✅ Retrieved {len(authors)} authors:")
            for author in authors:
                print(f"   - {author['author_name']}: {author['post_count']} posts")
            return authors
        else:
            print(f"❌ Failed to get authors: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting authors: {e}")
        return []

def test_generate_post_with_custom_author(author_name):
    """Test generating a LinkedIn post with custom author style"""
    try:
        payload = {
            "topic": "The importance of continuous learning in tech",
            "industry": "Technology",
            "target_audience": "Software engineers and tech professionals",
            "post_goal": "Drive Engagement",
            "influencer_style": "custom",
            "custom_author_name": author_name,
            "hashtags_count": 5
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-post", json=payload)
        
        if response.status_code == 200:
            post = response.json()
            print(f"✅ Generated post in {author_name}'s style:")
            print(f"   Preview: {post['content'][:150]}...")
            print(f"   Character count: {len(post['content'])}")
            return True
        else:
            print(f"❌ Failed to generate post: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error generating post: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Excel Upload Workflow for Author Styles")
    print("=" * 60)
    
    # Check API health
    if not test_health_check():
        print("\n⚠️  Please make sure the backend is running:")
        print("   cd backend && uvicorn app.main:app --reload")
        return
    
    print("\n" + "-" * 40)
    print("Step 1: Creating sample Excel file")
    print("-" * 40)
    filename = create_sample_excel()
    
    print("\n" + "-" * 40)
    print("Step 2: Uploading Excel file")
    print("-" * 40)
    if not test_upload_excel(filename):
        return
    
    print("\n" + "-" * 40)
    print("Step 3: Retrieving uploaded authors")
    print("-" * 40)
    authors = test_get_authors()
    
    if authors:
        print("\n" + "-" * 40)
        print("Step 4: Generating post with custom style")
        print("-" * 40)
        # Test with the first author
        test_generate_post_with_custom_author(authors[0]['author_name'])
    
    print("\n" + "=" * 60)
    print("✅ Workflow test completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start the frontend: cd frontend && npm start")
    print("2. Navigate to http://localhost:3000/author-styles")
    print("3. Upload your own Excel file with author posts")
    print("4. Go to LinkedIn Post Generator and select 'Custom Author'")
    print("5. Choose from your uploaded authors to emulate their style")

if __name__ == "__main__":
    main()