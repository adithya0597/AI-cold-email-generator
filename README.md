# AI Content Generation Suite

A production-ready web application for generating personalized cold emails and LinkedIn posts using advanced AI capabilities.

## Features

### Cold Email Generator
- Resume parsing (PDF/DOCX)
- Company website research via web scraping
- Job posting integration for targeted outreach
- Personalized value propositions using Josh Braun's 4T methodology
- Multiple tone options

### LinkedIn Post Generator  
- Multiple writing styles (Gary Vaynerchuk, Simon Sinek, etc.)
- Topic-specific trending hashtags
- Reference URL integration (up to 3 sources)
- Optional AI image generation
- Engagement optimization

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- OpenAI or Anthropic API key (optional)

### Backend Setup

```bash
# Clone repository
git clone <repository-url>
cd AI-cold-email-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your_key_here"  # Or use .env file

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
# Install dependencies
cd frontend
npm install

# Start development server
npm start
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── models.py            # Pydantic models
│   │   ├── core/                # Core utilities
│   │   ├── services/            # Business logic
│   │   └── monitoring/          # Alerts and metrics
│   └── tests/                   # Test suite
│
└── frontend/
    ├── src/
    │   ├── components/          # React components
    │   └── services/            # API services
    └── public/                  # Static assets
```

## API Endpoints

### Email Generation
- `POST /api/generate-email` - Generate cold email
- `POST /api/parse-resume` - Parse resume file

### LinkedIn Posts
- `POST /api/generate-post` - Generate LinkedIn post

### Utilities
- `GET /health` - Health check
- `POST /api/scrape-url` - Scrape website

## Environment Variables

```env
# Required
OPENAI_API_KEY=your_key_here

# Optional
ANTHROPIC_API_KEY=your_anthropic_key
SERP_API_KEY=your_search_api_key
TRACKING_BASE_URL=http://localhost:8000/api/track
```

## Testing

```bash
# Run tests
pytest backend/tests/ -v

# With coverage
pytest backend/tests/ --cov=app --cov-report=html
```

## License

MIT

## Support

For issues or questions, please open an issue on GitHub.