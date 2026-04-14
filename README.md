# CheeseDoodle - AI Job Application Agent

An automated job application agent that searches for jobs, scores them against your resume using Claude AI, generates personalized cover letters, and automates the application process using Playwright.

## Features

- PDF resume parsing
- Job search via JSearch API
- AI-powered job scoring (Claude)
- Automated browser-based application submission
- Cover letter generation on demand
- Seen jobs tracking to avoid duplicates
- Daily scheduling via Windows Task Scheduler

## Setup

### Prerequisites

- Python 3.9+
- A Anthropic API key
- A RapidAPI key with JSearch access

### Installation

1. Clone the repository
2. Create and activate a virtual environment:
   py -m venv CheeseDoodle
   CheeseDoodle\Scripts\activate
3. Install dependencies:
   pip install pdfplumber python-dotenv anthropic playwright requests beautifulsoup4
   playwright install

### Configuration

Create a `.env` file in the project root:
ANTHROPIC_API_KEY=your_key_here
JSEARCH_API_KEY=your_key_here
RESUME_PATH=path_to_your_resume.pdf

Create a `ME.json` file with your personal info:

```json
{
  "first_name": "",
  "last_name": "",
  "email": "",
  "phone": "",
  "address": {
    "street": "",
    "city": "",
    "state": "",
    "zip": ""
  },
  "linkedin": "",
  "work_authorized": true,
  "years_of_experience": 0
}
```

## Usage

py job_agent.py

Set `DRY_RUN = True` in `job_agent.py` to test without submitting real applications.

## Notes

- JSearch free tier has a monthly request limit
- Recommend running search weekly and apply daily to conserve API quota
- Bot detection may prevent automation on some job sites

## V1 Limitations

- Claude-based apply loop works best on simple direct application pages
- Complex ATS platforms (Greenhouse, Lever) not yet fully supported
- Some pages may require manual intervention
