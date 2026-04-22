import streamlit as st
import pandas as pd
from pathlib import Path
from job_agent import run_agent

st.set_page_config(page_title="Job Doodle 🧀", page_icon="🧀", layout="wide")


st.title("Job Doodle 🧀 Application Agent")

with st.sidebar:
    st.header("API KEYS")
    anthropic_key = st.text_input("Anthropic API Key:", type="password")
    jsearch_key = st.text_input("JSearch API Key:", type="password")
    st.markdown("[Get Anthropic Key](https://console.anthropic.com/)")
    st.markdown("[Get JSearch Key](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)")

    st.markdown("---")
    st.header("Seen Jobs")
    seen_jobs_path = Path.home() / "CheeseDoodle" / "Jobs" / "seen_jobs.csv"
    if seen_jobs_path.exists():
        df = pd.read_csv(seen_jobs_path, header=None,names=["Link","Title","Company", "Location"])
        st.write(f"Total jobs seen: **{len(df)}**")
        st.dataframe(df[["Link","Title","Company","Location"]], use_container_width = True)

        st.download_button(
            label="Download Seen Jobs CSV",
            data=df.to_csv(index=False),
            file_name="seen_jobs.csv",
            mime="text/csv"
        )

        if st.button("Clear Seen Jobs"):
            seen_jobs_path.unlink()
            st.success("Seen jobs cleared!")
            st.rerun()
        else:
            st.info("No seen jobs yet.")

        

uploaded_file = st.file_uploader("Upload your resume (PDF):", type=["pdf"])

job_input = st.text_input(
    "Enter job titles or keywords (comma-separated):",
    placeholder="For Example: Software Engineer, Frontend Developer, " \
    "Backend Developer, Full Stack Developer, DevOps Engineer, " \
    "Cybersecurity Analyst, Game Developer"
)
    
queries = [q.strip() for q in job_input.split(",") if q.strip()]


location = st.text_input("Preferred job location (optional):", placeholder="United States")
remote_option = st.selectbox("Remote work preference:", ["No Preference", "Remote Only", "On-site Only"])
remote = remote_option == "Remote Only"
if st.button("Find Jobs"):
    if not anthropic_key or not jsearch_key:
        st.error("Please enter both API keys in the sidebar.")
    elif not uploaded_file:
        st.error("Please upload your resume.")
    elif not job_input:
        st.error("Please enter at least one job title or keyword.")
    else:
        with st.spinner("Analyzing your resume and searching for jobs..."):
            try:
                results = run_agent(uploaded_file, queries, location or "United States", remote,anthropic_key=anthropic_key,jsearch_key=jsearch_key)
                if results:
                    st.success(f"Found {len(results)} matching jobs!")
                    for job in results:
                        st.subheader(f"{job['job_title']} at {job['company']}")
                        st.write(f"📍 Location: {job['location']}")
                        st.write(f"⭐ Match Score: {job.get('score', 'N/A')}/10")
                        st.write(f"💡 Why it fits: {job.get('reason', 'N/A')}")
                        st.write(f"📄 Cover Letter saved as: `{job.get('cover_letter_file', 'N/A')}`")
                        if job.get('description'):
                            st.write(f"📝 {job['description'][:200]}...")
                        st.markdown(f"[Apply Here ↗]({job['link']})")
                        st.markdown("---")
                else:
                    st.warning("No matching jobs found. Try adjusting your search criteria.")
            except Exception as e:
                st.error(f"An error occurred: {e}")