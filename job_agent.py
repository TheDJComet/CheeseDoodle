#automated job application agent using Claude for job search, scoring, cover letter generation, and Playwright for application submission. It extracts resume text, searches for jobs, scores them based on fit, generates personalized cover letters, and automates the application process by analyzing job application pages and performing the necessary actions.
import base64
import json
import random
import requests # type: ignore
import pdfplumber # type: ignore
import os
from dotenv import load_dotenv # type: ignore
import csv
import anthropic # type: ignore
from playwright.sync_api import sync_playwright # type: ignore
from urllib.parse import urlencode
import time
from bs4 import BeautifulSoup  # type: ignore
import re

load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")
job_api_key = os.getenv("JSEARCH_API_KEY")
client = anthropic.Anthropic(api_key=api_key)
resume = os.getenv("RESUME_PATH")
search_query = ["Software Engineer", "Frontend Developer", "Backend Developer", "Full Stack Developer", "DevOps Engineer", "Cybersecurity Analyst", "Game Developer"]
locations = ["United States"]
job_type = ["remote", "onsite", "hybrid"]
min_salary = 60000
DRY_RUN = True


def extract_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return None

def extract_resume_text(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        pages = [page.extract_text() for page in pdf.pages]
    return "\n".join(filter(None, pages))


def search_jobs():
    jobs = []
    for query in search_query:
        for page_num in range(1,4):  # Get first 3 pages of results
            url = "https://jsearch.p.rapidapi.com/search"
            
            headers = {
                "X-RapidAPI-Key": job_api_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
            }
            
            params = {
                "query": f"{query} in United States",
                "num_pages": "1",
                "date_posted": "month",
                "remote_jobs_only": "false",
                "employment_types": "FULLTIME",
                "job_requirements": "no_experience,under_3_years_experience"
            }
            
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            #print(f"API response for '{query}': {data.get('status')} - {len(data.get('data', []))} jobs")
            #print(f"Full response: {data}")
            for job in data.get("data", []):
                if not job.get("job_apply_is_direct"):
                    continue
                jobs.append({
                    "title": job.get("job_title"),
                    "company": job.get("employer_name"),
                    "location": job.get("job_city"),
                    "link": job.get("job_apply_link"),
                    "description": job.get("job_description")
                })
    return jobs

def score_job(resume_text: str):
    jobs = search_jobs()
    print(f"Jobs found: {len(jobs)}")
    scored_jobs = []
    seen_urls = load_seen_jobs()
    print(f"Seen URLs loaded: {len(seen_urls)}")
    new_urls = []

    # Build one big string with all jobs
    jobs_text = ""
    for i, job in enumerate(jobs):
        if job.get("link") in seen_urls:
            continue
        jobs_text += f"""
Job {i+1}:
Title: {job.get('title')}
Company: {job.get('company')}
Location: {job.get('location')}
Link: {job.get('link')}
Description: {job.get('description')}
---
"""
        new_urls.append(job.get("link"))

    if not jobs_text:
        print("No new jobs to score.")
        return []
    
    # ONE Claude call for all jobs
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[{"role": "user", "content": f"""The following resume may be in a jumbled two-column format.
Interpret it as best you can, then score each job 1-10 based on fit.
Return JSON only:
[{{"job_number": 1, "score": 8, "reason": "..."}}]

Resume:
{resume_text}

Jobs:
{jobs_text}"""}]
    )
    
    import json
    print(response.content[0].text)
    scores = json.loads(response.content[0].text)

    for url in new_urls:
        save_seen_job(url)

    for i, score_data in enumerate(scores):
        job = jobs[i]
        job["score"] = score_data["score"]
        job["reason"] = score_data["reason"]
        scored_jobs.append(job)

    scored_jobs = [x for x in scored_jobs if x["score"] >= 6]
    
    return scored_jobs

def load_seen_jobs():
    seen_urls = set()
    if os.path.exists("seen_jobs.csv"):
        with open("seen_jobs.csv", "r") as f:
            reader = csv.reader(f)
            for row in reader:
                seen_urls.add(row[0])
    else:
        with open("seen_jobs.csv", "w") as f:
            writer = csv.writer(f)
    return seen_urls

def save_seen_job(job_url: str):
    with open("seen_jobs.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([job_url])

def load_personal_info():
    with open("ME.json", "r") as f:
        return json.load(f)

personal_info = load_personal_info()

def generate_cover_letter(job,resume_text):
    job_description = job.get("description", "")
    company = job.get("company", "")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[{"role": "user", "content": f"""Generate a personalized cover letter for the following job description, using the provided resume text and personal information. Highlight relevant skills and experiences that match the job requirements.
Job Description:
{job_description}
Resume Text:
{resume_text}
Personal Information:
{json.dumps(personal_info)}"""}]

    )
    print(response.content[0].text)
    cover_letter = response.content[0].text.strip()

    with open(f"cover_letter_{company}.txt", "w") as f:
        f.write(cover_letter)

    return f"cover_letter_{company}.txt"


def apply_to_job(job, personal_info,resume_text):
    resume_path = resume
    cover_letter_path = None  # Not generated yet
    applied = False
    skipped = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(job["link"])
        page.wait_for_load_state("networkidle")
        max_steps = 10
        steps = 0
        while steps < max_steps:
            steps += 1
            time.sleep(2)  
            html_content = page.inner_html("body")  # Get the entire page HTML
            soup = BeautifulSoup(html_content, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            clean_html = str(soup)[:40000]
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": f"""Analyze this HTML of a job application page.
                    What is the next single action to take to apply for this job?
                    Personal info: {json.dumps(personal_info)}
                    Resume path: {resume_path}
                    If you cannot determine the next action or the page requires login/CAPTCHA,
                    return: {{"action": "skip", "selector": "", "value": ""}}
                    Return JSON only: {{"action": "click" or "type" or "upload" or "submit",
                        "selector": "CSS selector for the element",
                        "value": "text or file path if applicable"}}

                        HTML:
                        {clean_html}"""}]
             )
            
            print(response.content[0].text)
            try:
            
                action_data = extract_json(response.content[0].text)
                if action_data is None:
                    print("Could not extract JSON, skipping")
                    continue
            except json.JSONDecodeError:
                print("Claude returned non-JSON, skipping this step")
                print("Response was:", response.content[0].text[:200])
                continue

            action = action_data.get("action")
            selector = action_data.get("selector")
            value = action_data.get("value")
            skip = action_data.get("skip")

            if action == "upload" and "cover" in action_data.get("value", "").lower():
                if cover_letter_path is None:
                    cover_letter_path = generate_cover_letter(job, resume_text)
                action_data["value"] = cover_letter_path

            if action == "click":
                page.click(selector)
            elif action == "type":
                page.fill(selector, value)
            elif action == "upload":
                page.set_input_files(selector, value)
            elif action == "skip":
                skipped = True
                print("Skipping this job application due to complexity or login requirement.")
                break
            elif action == "submit":
                if DRY_RUN:
                    print(f"DRY RUN: Would have submitted to {job['company']}")
                    applied = True
                    break
                else:
                    page.click(selector)
                    page.wait_for_timeout(2000)
                    applied = True
                    break

        browser.close()
    return "applied" if applied else "skipped"

def main():
    resume_text = extract_resume_text(resume)
    print(f"Extracted resume text length: {len(resume_text)} characters")
    scored_jobs = score_job(resume_text)
    applications_attempted = 0
    applications_skipped = 0

    for job in scored_jobs:
        result = apply_to_job(job, personal_info, resume_text)
        if result == "applied":
            applications_attempted += 1
        else:
            applications_skipped += 1


    print(f"Jobs scored 6+: {len(scored_jobs)}")
    print(f"Applications attempted: {applications_attempted}")
    print(f"Applications skipped: {applications_skipped}")

if __name__ == "__main__":
    main()