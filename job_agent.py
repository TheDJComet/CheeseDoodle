import base64
import json
import random
import requests # type: ignore
import pdfplumber # type: ignore
import os
import csv
import anthropic # type: ignore
from playwright.sync_api import sync_playwright # type: ignore
from urllib.parse import urlencode
import time
from bs4 import BeautifulSoup  # type: ignore
import re
from pathlib import Path





CACHE_DIR = Path.home() / "CheeseDoodle" / "job_cache"
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

# -----------------------------
# UTILS
# -----------------------------
def chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

def safe_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = re.sub(r'\s+', "_", name)
    return name[:100]

def extract_json(text):
    try:
        return json.loads(text)
    except:
        pass

    # Try to extract JSON array
    match = re.search(r'\[\s*{.*?}\s*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    # Try to fix common issues
    try:
        cleaned = text.strip()

        # remove leading text before [
        cleaned = cleaned[cleaned.find('['):]

        # remove trailing text after ]
        cleaned = cleaned[:cleaned.rfind(']')+1]

        return json.loads(cleaned)
    except:
        return None
    

    
#------------------------------
# SAVE AND LOAD
#------------------------------
def load_seen_jobs():
    seen = set()
    file_path = Path.home() / "CheeseDoodle" / "seen_jobs" / "seen_jobs.csv"
    if file_path.exists():
        with open(file_path, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                seen.add(row[0])
    return seen

def save_seen_job(job_url):
    base_dir = Path.home() / "CheeseDoodle" / "seen_jobs"
    file_path = base_dir / "seen_jobs.csv"
        

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([job_url])


# -----------------------------
# RESUME
# -----------------------------
def extract_resume_text(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        pages = [page.extract_text() for page in pdf.pages]
    return "\n".join(filter(None, pages))

def summarize_resume(resume_text,client):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""
Summarize this resume into structured JSON:
- skills
- technologies
- experience highlights
- projects
- education

Be concise and optimized for job applications.

Resume:
{resume_text}
"""
        }]
    )
    return response.content[0].text.strip()

# -----------------------------
# JOB SEARCH
# -----------------------------
def search_jobs(user_queries, location="United States", remote=False, job_api_key=None):
    jobs = []
    for query in user_queries:
        print(f"Searching for '{query}' jobs...")
        for page_num in range(1, 3):  # Get first 2 pages of results
            url = "https://jsearch.p.rapidapi.com/search"

            headers = {
                "X-RapidAPI-Key": job_api_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
            }

            params = {
                "query": f"{query} in {location}",
                "num_pages": "1",
                "date_posted": "month",
                "employment_types": "FULLTIME",
            }

            if remote:
                params["remote"] = "true"

            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            for job in data.get("data", []):
                jobs.append({
                    "title": job.get("job_title"),
                    "company": job.get("employer_name"),
                    "location": job.get("job_city"),
                    "link": job.get("job_apply_link"),
                    "description": job.get("job_description")
                })

    unique_jobs = {job['link']: job for job in jobs}.values()
    print(f"Found {len(unique_jobs)} unique jobs.")
    return list(unique_jobs)

# -----------------------------
# JOB SUMMARIZATION + CACHE
# -----------------------------
def get_job_cache_path(job):
    name = safe_filename(job.get("company", "unknown") + "_" + job.get("title", "role"))
    return CACHE_DIR / f"{name}.txt"

def summarize_job(job):
    cache_path = get_job_cache_path(job)

    if cache_path.exists():
        with open(cache_path, "r") as f:
            return f.read()

    description = BeautifulSoup(job.get("description", ""), "html.parser").get_text()

    trimmed = description[:1500]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""
Summarize this job into:
- key responsibilities
- required skills
- preferred skills

Job:
{trimmed}
"""
        }]
    )

    summary = response.content[0].text.strip()

    with cache_path.open("w", encoding="utf-8") as f:
        f.write(summary)

    return summary

# -----------------------------
# SCORING JOBS
# -----------------------------
def score_jobs(resume_summary,jobs,client):
    seen_jobs = load_seen_jobs()
    filtered_jobs = [job for job in jobs if job.get("link") not in seen_jobs]
    all_scored_jobs = []

    CHUNK_SIZE = 8  # sweet spot (5–10 works well)

    for chunk_index, job_chunk in enumerate(chunk_list(filtered_jobs, CHUNK_SIZE)):
        print(f"Scoring chunk {chunk_index + 1}...")

        jobs_text = ""
        for i, job in enumerate(job_chunk):
            jobs_text += f"""
Job {i+1}:
Title: {job['title']}
Company: {job['company']}
Description: {job['description'][:800]}
---
"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": f"""
You are a JSON API.

Return ONLY valid JSON.
No explanations. No text outside JSON.

Format:
[
  {{"job_number": 1, "score": 7, "reason": "short reason"}}
]

Rules:
- Output MUST start with [
- Output MUST end with ]
- No trailing commas

Candidate:
{resume_summary}

Jobs:
{jobs_text}
"""
            }]
        )

        raw = response.content[0].text
        scores = extract_json(raw)

        if not scores:
            print("Failed chunk. Raw output:")
            print(raw[:500])
            continue

        # map scores back to jobs
        for i, score_data in enumerate(scores):
            if i >= len(job_chunk):
                continue

            job = job_chunk[i]
            job["score"] = score_data.get("score", 0)
            job["reason"] = score_data.get("reason", "")
            all_scored_jobs.append(job)
            save_seen_job(job.get("link"))
            

    # sort + take top
    all_scored_jobs = sorted(all_scored_jobs, key=lambda x: x["score"], reverse=True)

    return all_scored_jobs[:5]


# -----------------------------
# COVER LETTER
# -----------------------------
def generate_cover_letter(job, resume_summary,client):
    job_summary = summarize_job(job,client)
    job_url = job.get("link", "N/A")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"""
Write a concise (under 300 words) cover letter.

Candidate:
{resume_summary}

Job:
{job_summary}

Job URL:
{job_url}

Make it tailored, professional, and direct.
"""
        }]
    )

    cover_letter = response.content[0].text.strip()

    company = safe_filename(job.get("company", "unknown"))

    filename = f"cover_letter_{company}.txt"
    
    base_dir = Path.home() / "CheeseDoodle" / "Cover_Letters"
    file_path = base_dir / filename
    if file_path.exists():
        print (f"⚠️ {filename} already exists. Skipping save.")
        return filename

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as f:
        f.write(cover_letter)

    return filename

# -----------------------------
# MAIN
# -----------------------------
def run_agent(uploaded_file,user_queries, location="United States", remote=False,anthropic_key=None, jsearch_key=None):
    client = anthropic.Anthropic(api_key=anthropic_key)
    resume_text = extract_resume_text(uploaded_file)
    resume_summary = summarize_resume(resume_text, client)
    jobs = search_jobs(user_queries, location, remote, jsearch_key)
    top_jobs = score_jobs(resume_summary, jobs, client)

    results = []

    for job in top_jobs:
        cover_letter_file = generate_cover_letter(job, resume_summary, client)
        results.append({
            "job_title": job.get("title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "link": job.get("link"),
            "score": job.get("score"),
            "reason": job.get("reason"),
            "description": job.get("description"),
            "cover_letter_file": cover_letter_file
        })

    return results
