import re
from pypdf import PdfReader
import docx

# Email regex
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

# Phone number regex matching common formats (including international, spaces, dashes, parentheses)
# Matches numbers like: +1 (123) 456-7890, 123-456-7890, +91 9876543210, etc.
PHONE_REGEX = re.compile(
    r'(?:\+\d{1,3}[-.\s]?)?'          # Optional country code
    r'(?:\(?\d{2,5}\)?[-.\s]?)'       # Area code (2-5 digits, optional parentheses)
    r'\d{3,5}'                        # Subscriber prefix
    r'[-.\s]?'                        # separator
    r'\d{3,5}'                        # subscriber line number
)

def extract_text_from_pdf(file_bytes):
    """Extracts raw text from a PDF file using pypdf."""
    reader = PdfReader(file_bytes)
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"
    return text

def extract_text_from_docx(file_bytes):
    """Extracts raw text from a DOCX file using python-docx."""
    doc = docx.Document(file_bytes)
    text = []
    for para in doc.paragraphs:
        text.append(para.text)
    return "\n".join(text)

def parse_resume_text(text, filename=""):
    """
    Parses resume raw text to extract email, phone, and name before AI processing.
    Returns: (name, email, phone, scrubbed_text)
    """
    # 1. Extract Email
    emails = EMAIL_REGEX.findall(text)
    email = emails[0].strip() if emails else ""

    # 2. Extract Phone
    phones = PHONE_REGEX.findall(text)
    # Filter out false positives (e.g. date ranges like 2018-2022, or postal codes, or digits without enough length)
    valid_phones = []
    for p in phones:
        # Count digits
        digits = re.sub(r'\D', '', p)
        # Avoid matches that look like years (e.g. 2018-2022) or are too short
        if 8 <= len(digits) <= 15:
            # Check it's not a range like 2015-2019
            if not ("201" in p or "202" in p and "-" in p):
                valid_phones.append(p.strip())
                
    phone = valid_phones[0] if valid_phones else ""

    # 3. Extract Name Heuristics
    name = extract_name_heuristic(text, filename)

    # 4. Scrub PII
    scrubbed_text = scrub_pii(text, name, email, phone)

    return name, email, phone, scrubbed_text

def extract_name_heuristic(text, filename=""):
    """
    Extracts name from the first few lines of the text using casing patterns.
    Falls back to formatted filename if no name is found.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    exclude_keywords = {
        "resume", "curriculum", "vitae", "cv", "page", "summary", "profile", "contact", 
        "email", "phone", "portfolio", "github", "linkedin", "address", "education",
        "experience", "skills", "objective", "about", "me", "hobbies", "languages"
    }
    
    for line in lines[:8]:  # Scan top 8 non-empty lines
        # Clean special chars but preserve spaces
        clean_line = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        words = clean_line.split()
        
        # Name is likely 2-4 words, and starts with Capital letters
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
            # Check if any word is a common heading keyword or email domain
            if not any(kw in clean_line.lower() for kw in exclude_keywords):
                return clean_line
                
    # Fallback to filename formatting
    if filename:
        # Remove extension
        name_part = filename.rsplit('.', 1)[0]
        # Replace underscores, hyphens, and common terms
        name_part = re.sub(r'(_|-|resume|cv|parsed|docx|pdf)', ' ', name_part, flags=re.IGNORECASE)
        # Title case and clean whitespace
        name_part = ' '.join(name_part.split()).strip()
        if name_part:
            return name_part.title()
            
    return "Unknown Candidate"

def scrub_pii(text, name, email, phone):
    """
    Scrubs contact details from the raw text, replacing them with placeholders.
    """
    scrubbed = text
    
    # 1. Scrub Email
    if email:
        email_esc = re.escape(email)
        scrubbed = re.sub(email_esc, "[REDACTED_EMAIL]", scrubbed, flags=re.IGNORECASE)
        
    # 2. Scrub Phone
    if phone:
        phone_esc = re.escape(phone)
        scrubbed = re.sub(phone_esc, "[REDACTED_PHONE]", scrubbed, flags=re.IGNORECASE)
        
    # 3. Scrub Name (Full Name and component parts)
    if name and name != "Unknown Candidate":
        name_esc = re.escape(name)
        scrubbed = re.sub(name_esc, "[REDACTED_NAME]", scrubbed, flags=re.IGNORECASE)
        
        # Also scrub individual name parts (e.g. first and last name)
        name_parts = [p.strip() for p in name.split() if len(p.strip()) > 2]
        common_exclusions = {
            "resume", "curriculum", "vitae", "manager", "engineer", "developer", "lead", 
            "senior", "project", "university", "college", "school", "data", "analyst",
            "associate", "director", "consultant", "intern"
        }
        for part in name_parts:
            if part.lower() not in common_exclusions:
                part_esc = re.escape(part)
                # Word boundary matches to avoid scrubbing parts of other words
                scrubbed = re.sub(rf'\b{part_esc}\b', "[REDACTED_NAME]", scrubbed, flags=re.IGNORECASE)
                
    return scrubbed
