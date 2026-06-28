import os
import json
import google.generativeai as genai

def analyze_resume_with_gemini(scrubbed_text, api_key=None):
    """
    Sends the scrubbed resume text to Gemini 1.5 Flash to extract candidate details.
    
    Parameters:
        scrubbed_text (str): Resume text with name, email, and phone redacted.
        api_key (str): Optional. Gemini API key. If not provided, resolves from environment.
        
    Returns:
        dict: A dictionary containing 'skills' (list), 'years_of_experience' (float),
              'location' (str), and 'summary' (str).
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("Gemini API key is not configured. Please set the GEMINI_API_KEY environment variable or provide it in the sidebar.")
        
    genai.configure(api_key=key)
    
    # We use gemini-1.5-flash as it is fast, highly capable, and has native JSON output support
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
You are an expert technical recruiter analyzing a candidate's resume for a talent screening application.
All PII (Names, Emails, and Phone Numbers) have been redacted and replaced with placeholders like [REDACTED_NAME], [REDACTED_EMAIL], and [REDACTED_PHONE].
Focus entirely on the professional qualifications. Do not try to reconstruct the contact details.

Analyze the resume and extract:
1. "skills": A list of technical and soft skills. Normalize and clean the names. For example:
   - "react.js", "react js", "reactjs" -> "React"
   - "python3", "py", "python programming" -> "Python"
   - "nodejs", "node js", "node" -> "Node.js"
   - "postgres", "postgresql", "mysql" -> "SQL"
   - "machine learning", "ml", "deep learning" -> "Machine Learning"
2. "years_of_experience": Estimate the total years of professional experience as a number (integer or float). 
   - Be conservative: exclude school projects or short courses.
   - For students or fresh graduates with no full-time job experience, return 0.0.
3. "location": The candidate's city and country or state (e.g. "Seattle, WA", "Bangalore, India", "Remote"). If not found, return "Unknown".
4. "summary": A professional, 2-3 sentence summary of the candidate's profile, highlighting their core strengths, key projects, and career level. Do not include their name or contact details.

You MUST respond strictly with a valid JSON object matching the schema below. Do not wrap your response in markdown code blocks.
{{
    "skills": ["Skill1", "Skill2", ...],
    "years_of_experience": 4.5,
    "location": "City, State/Country",
    "summary": "Professional summary here..."
}}

Scrubbed Resume Text:
{scrubbed_text}
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        raw_text = response.text.strip()
        print("Gemini Response:")
        print(raw_text)
        data = json.loads(raw_text)

        # Handle Gemini returning a list
        if isinstance(data, list):
           if len(data) > 0:
               data = data[0]
           else:
               data = {}
        
        # Clean and validate output structure
        skills = data.get("skills", [])
        if not isinstance(skills, list):
            skills = []
        skills = [str(s).strip() for s in skills if s]
        
        # Skill normalization/deduplication post-processing
        normalized_skills = []
        seen = set()
        for s in skills:
            # Basic title case normalization
            norm = s.strip()
            # De-duplicate case-insensitively
            if norm.lower() not in seen:
                seen.add(norm.lower())
                normalized_skills.append(norm)
                
        try:
            years = float(data.get("years_of_experience", 0.0))
        except (ValueError, TypeError):
            years = 0.0
            
        location = str(data.get("location", "Unknown")).strip()
        summary = str(data.get("summary", "No profile summary generated.")).strip()
        
        return {
            "skills": normalized_skills,
            "years_of_experience": years,
            "location": location,
            "summary": summary
        }
    except Exception as e:
        raise RuntimeError(f"Gemini API processing failed: {str(e)}")
