# TalentScan

AI-powered resume screening and candidate search platform built for the Application Support Engineer assessment.

## Features

- Upload multiple PDF and DOCX resumes
- Extract resume text automatically
- Extract contact information using regex
- PII scrubbing before AI processing
- Gemini AI-powered candidate analysis
- Skills extraction
- Experience estimation
- Location detection
- Search and filter candidates
- Candidate profile management
- SQLite database storage
- Recruiter dashboard

## Tech Stack

- Python
- Streamlit
- SQLite
- Gemini 1.5 Flash

## Security

Before sending resume content to Gemini:
- Email addresses are removed
- Phone numbers are removed
- LinkedIn URLs are removed
- GitHub URLs are removed

This ensures AI only receives professional qualifications and not personal contact information.

## Run Locally

```bash
pip install -r requirements.txt
python -m streamlit run app.py
