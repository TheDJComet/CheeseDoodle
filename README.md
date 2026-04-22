# CheeseDoodle 🧀 - AI Job Application Agent

An automated job application agent that searches for jobs, scores them against your resume using Claude AI, and generates personalized cover letters. Features a Streamlit web UI for easy use.

## Features

- 📄 PDF resume upload via drag and drop
- 🔍 Job search via JSearch API
- 🤖 AI-powered job scoring (Claude)
- ✉️ Personalized cover letter generation
- 👀 Seen jobs tracking to avoid duplicates
- 🖥️ Streamlit web UI — no command line needed

## Setup

### Prerequisites

- Python 3.9+
- An Anthropic API key — [Get one here](https://console.anthropic.com/)
- A RapidAPI key with JSearch access — [Get one here](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)

### Installation

1. Clone the repository
2. Create and activate a virtual environment:
   py -m venv CheeseDoodle
   CheeseDoodle\Scripts\activate
3. Install dependencies:
   pip install pdfplumber anthropic playwright requests beautifulsoup4 streamlit pandas
   playwright install

## Usage

Run the Streamlit UI:
python -m streamlit run JobDoodle.py
Then in the app:

1. Enter your **Anthropic** and **JSearch** API keys in the sidebar
2. Upload your resume (PDF) via drag and drop
3. Enter job titles or keywords (comma-separated)
4. Set your preferred location and remote preference
5. Click **Find Jobs**

## Output

All generated files are saved to your home directory under `CheeseDoodle/`:
Cover_Letters/ # Generated cover letters (.txt)
job_cache/ # Cached job summaries
seen_jobs/
<--- seen_jobs.csv # Jobs already processed
You can view, download, and clear your seen jobs history directly in the sidebar.

## Notes

- JSearch free tier has a monthly request limit — recommend searching weekly to conserve quota
- Each user provides their own API keys — no shared credentials
- Cover letters are skipped if one already exists for that company

## Limitations

- Claude-based scoring works best with detailed job descriptions
- Complex ATS platforms (Greenhouse, Lever) not yet fully supported
- Remote filter depends on JSearch API support per listing

## Key things updated:

- Removed .env, ME.json, and RESUME_PATH setup instructions
- Added Streamlit UI usage instructions
- Added output directory structure
- Added seen jobs sidebar mention
- Removed old py job_agent.py usage and DRY_RUN references
- Updated dependencies list (added streamlit, pandas, removed python-dotenv)
