import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
from io import BytesIO
from dotenv import load_dotenv

# Import our backend modules
import database as db
import parser
import gemini_client

# Load environment variables
load_dotenv()

# Initialize Database on app load
db.init_db()

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="TalentScan - AI Resume Parser & Recruiter Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics and premium styling
st.markdown("""
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Title Gradient */
    .title-gradient {
        background: linear-gradient(90deg, #4A00E0 0%, #8E2DE2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    
    .subtitle-text {
        color: #6c757d;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Card Container */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 1rem;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.05);
    }
    
    /* Badge styling */
    .skill-badge {
        display: inline-block;
        background-color: #EBF8FF;
        color: #2B6CB0;
        font-weight: 500;
        font-size: 0.85rem;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        border: 1px solid #BEE3F8;
    }
    
    .contact-badge {
        display: inline-block;
        background-color: #F7FAFC;
        color: #4A5568;
        font-weight: 500;
        font-size: 0.9rem;
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        border: 1px solid #E2E8F0;
    }
    
    /* Terminal logs container */
    .log-container {
        background-color: #1A202C;
        color: #48BB78;
        font-family: 'Courier New', monospace;
        padding: 1rem;
        border-radius: 8px;
        max-height: 250px;
        overflow-y: auto;
        font-size: 0.85rem;
        border: 1px solid #2D3748;
        margin-bottom: 1rem;
    }
    
    .log-entry {
        margin-bottom: 0.25rem;
        white-space: pre-wrap;
    }
    
    .log-error {
        color: #F56565;
    }
    
    .log-warning {
        color: #ECC94B;
    }
    
    .log-info {
        color: #4299E1;
    }
    
    /* Empty State */
    .empty-state {
        text-align: center;
        padding: 3rem 1.5rem;
        background-color: #F7FAFC;
        border: 2px dashed #E2E8F0;
        border-radius: 12px;
        margin: 2rem 0;
    }
    .empty-state h3 {
        color: #4A5568;
        margin-bottom: 0.5rem;
    }
    .empty-state p {
        color: #718096;
        margin-bottom: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR CONFIGURATION -----------------
st.sidebar.markdown("## 🔍 TalentScan Admin")

# API Key handling
api_key_env = os.getenv("GEMINI_API_KEY", "")
api_key_input = st.sidebar.text_input(
    "Gemini API Key", 
    type="password",
    value=st.session_state.get("gemini_key", api_key_env),
    help="Enter your Google Gemini API key here. It will override any environment variable."
)

if api_key_input:
    st.session_state["gemini_key"] = api_key_input
else:
    if not api_key_env:
        st.sidebar.warning("⚠️ Gemini API key is missing. Add it to .env or paste it here to enable parsing.")

# Navigation options
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation", 
    ["📊 Dashboard", "📤 Upload Resumes", "🔍 Search & Filter", "👤 Candidate Profiles"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='font-size: 0.8rem; color: #718096;'>
    <b>Talentscan v1.0.0</b><br/>
    Local database storage: SQLite<br/>
    AI Model: Gemini 1.5 Flash
    </div>
    """, 
    unsafe_allow_html=True
)

# Helper function to get current active API key
def get_active_api_key():
    return st.session_state.get("gemini_key", "") or os.getenv("GEMINI_API_KEY", "")

# ----------------- PAGE 1: DASHBOARD -----------------
if page == "📊 Dashboard":
    st.markdown("<h1 class='title-gradient'>Recruiter Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle-text'>Real-time resume analytics and candidate processing overview</p>", unsafe_allow_html=True)
    
    stats = db.get_dashboard_stats()
    
    if stats["total_candidates"] == 0:
        st.markdown(
            """
            <div class='empty-state'>
                <h3>No Candidates Found</h3>
                <p>Upload candidate resumes in the "Upload Resumes" section to populate this dashboard.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        # Show recent logs if any exist (even if DB candidates are deleted, logs might stay)
        logs = db.get_processing_logs(limit=10)
        if logs:
            st.subheader("Recent Processing Logs")
            st.dataframe(pd.DataFrame(logs), use_container_width=True)
    else:
        # Metrics Row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <p style='color: #718096; font-size: 0.9rem; margin-bottom: 0.2rem; font-weight: 500;'>TOTAL CANDIDATES</p>
                    <h2 style='color: #2D3748; font-size: 2.2rem; margin: 0; font-weight: 700;'>{stats["total_candidates"]}</h2>
                </div>
                """, 
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <p style='color: #718096; font-size: 0.9rem; margin-bottom: 0.2rem; font-weight: 500;'>AVG EXPERIENCE</p>
                    <h2 style='color: #2D3748; font-size: 2.2rem; margin: 0; font-weight: 700;'>{stats["avg_experience"]} Years</h2>
                </div>
                """, 
                unsafe_allow_html=True
            )
        with col3:
            # Calculate total unique skills
            unique_skills_count = len(stats["top_skills"])
            st.markdown(
                f"""
                <div class='metric-card'>
                    <p style='color: #718096; font-size: 0.9rem; margin-bottom: 0.2rem; font-weight: 500;'>UNIQUE SKILLS EXTRACTED</p>
                    <h2 style='color: #2D3748; font-size: 2.2rem; margin: 0; font-weight: 700;'>{unique_skills_count}</h2>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        st.markdown("---")
        
        # Charts Row
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("Top Extracted Skills")
            if stats["top_skills"]:
                # Convert top skills to DataFrame
                skills_df = pd.DataFrame(stats["top_skills"][:10], columns=["Skill", "Count"])
                fig_skills = px.bar(
                    skills_df, 
                    x="Count", 
                    y="Skill", 
                    orientation="h",
                    color="Count",
                    color_continuous_scale="Viridis",
                    labels={"Skill": "Skill Name", "Count": "Number of Candidates"},
                    template="plotly_white"
                )
                fig_skills.update_layout(yaxis={'categoryorder':'total ascending'}, height=350, margin=dict(l=0, r=0, t=10, b=10))
                st.plotly_chart(fig_skills, use_container_width=True)
            else:
                st.info("Not enough skills data to plot charts.")
                
        with chart_col2:
            st.subheader("Experience Distribution")
            candidates = db.get_all_candidates()
            if candidates:
                exp_df = pd.DataFrame([{"Name": c["name"], "Experience": c["years_of_experience"]} for c in candidates])
                fig_exp = px.histogram(
                    exp_df, 
                    x="Experience", 
                    nbins=10,
                    color_discrete_sequence=["#8E2DE2"],
                    labels={"Experience": "Years of Experience", "count": "Count"},
                    template="plotly_white"
                )
                fig_exp.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=10))
                st.plotly_chart(fig_exp, use_container_width=True)
            else:
                st.info("Not enough experience data to plot charts.")
                
        # Recent Processing Logs Table
        st.markdown("---")
        st.subheader("Recent Resume Processing Logs")
        logs = db.get_processing_logs(limit=8)
        if logs:
            logs_df = pd.DataFrame(logs)
            # Reorder and format columns
            logs_df = logs_df[["timestamp", "filename", "status", "message"]]
            logs_df.columns = ["Timestamp", "Filename", "Status", "Log Message"]
            
            # Colored status highlights
            def color_status(val):
                color = '#C6F6D5' if val == 'SUCCESS' else '#FED7D7'
                text_color = '#22543D' if val == 'SUCCESS' else '#742A2A'
                return f'background-color: {color}; color: {text_color}; font-weight: bold;'
                
            st.dataframe(
                logs_df.style.map(color_status, subset=["Status"]),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No processing logs recorded yet.")

# ----------------- PAGE 2: UPLOAD RESUMES -----------------
elif page == "📤 Upload Resumes":
    st.markdown("<h1 class='title-gradient'>Upload Resumes</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle-text'>Drag and drop multiple PDF or DOCX resumes to process them securely</p>", unsafe_allow_html=True)
    
    # Check key before processing
    active_key = get_active_api_key()
    if not active_key:
        st.error("⚠️ Gemini API Key is required to analyze resumes. Please configure it in the sidebar.")
        
    uploaded_files = st.file_uploader(
        "Select Resume Files (PDF, DOCX)",
        type=["pdf", "docx"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.markdown("### Processing Queue")
        
        # Action button to trigger processing
        process_btn = st.button("Start Processing Resumes", type="primary", disabled=not active_key)
        
        if process_btn:
            total_files = len(uploaded_files)
            progress_bar = st.progress(0)
            
            # Logs visualization panel
            log_placeholder = st.empty()
            logs_html = []
            
            def append_log(message, type="info"):
                timestamp = pd.Timestamp.now().strftime("%H:%M:%S")
                if type == "error":
                    color_class = "log-error"
                    prefix = "[ERROR]"
                elif type == "warning":
                    color_class = "log-warning"
                    prefix = "[WARN] "
                elif type == "success":
                    color_class = "log-success"
                    prefix = "[SUCCESS]"
                else:
                    color_class = "log-info"
                    prefix = "[INFO] "
                    
                logs_html.append(f"<div class='log-entry {color_class}'>{timestamp} {prefix} {message}</div>")
                
                # Render to screen
                full_html = f"<div class='log-container'>{''.join(logs_html)}</div>"
                log_placeholder.markdown(full_html, unsafe_allow_html=True)

            success_count = 0
            fail_count = 0
            
            append_log(f"Starting batch process of {total_files} file(s)...")
            
            for index, file in enumerate(uploaded_files):
                filename = file.name
                append_log(f"--- Processing [{index+1}/{total_files}]: {filename} ---")
                
                try:
                    # 1. Read File Text
                    file_bytes = file.read()
                    file_ext = filename.split('.')[-1].lower()
                    
                    if file_ext == 'pdf':
                        append_log(f"Extracting text from PDF...")
                        raw_text = parser.extract_text_from_pdf(BytesIO(file_bytes))
                    elif file_ext == 'docx':
                        append_log(f"Extracting text from DOCX...")
                        raw_text = parser.extract_text_from_docx(BytesIO(file_bytes))
                    else:
                        raise ValueError(f"Unsupported file format: {file_ext}")
                        
                    if not raw_text.strip():
                        raise ValueError("No text could be extracted from the document.")
                        
                    append_log(f"Raw text extracted ({len(raw_text)} chars).")
                    
                    # 2. Extract Contact Details and Scrub PII
                    append_log(f"Extracting contact details (Pre-AI extraction)...")
                    name, email, phone, scrubbed_text = parser.parse_resume_text(raw_text, filename)
                    
                    append_log(f"Extracted Name: '{name}' | Email: '{email or 'Not Found'}' | Phone: '{phone or 'Not Found'}'", "success")
                    append_log(f"Scrubbing contact details from text (PII protection active)...")
                    
                    # 3. Process with Gemini API
                    append_log(f"Calling Gemini API to analyze scrubbed resume...")
                    analysis = gemini_client.analyze_resume_with_gemini(scrubbed_text, api_key=active_key)
                    
                    # 4. Insert into database
                    append_log(f"Saving candidate profile separately from contact details in DB...")
                    db.insert_candidate(
                        name=name,
                        email=email,
                        phone=phone,
                        location=analysis["location"],
                        years_of_experience=analysis["years_of_experience"],
                        summary=analysis["summary"],
                        skills=analysis["skills"],
                        original_filename=filename
                    )
                    
                    # 5. Log processing success
                    db.insert_processing_log(filename, "SUCCESS", f"Candidate '{name}' parsed and saved.")
                    append_log(f"Successfully processed and stored candidate {name}!", "success")
                    success_count += 1
                    
                except Exception as e:
                    error_msg = str(e)
                    append_log(f"Failed to process {filename}. Error: {error_msg}", "error")
                    db.insert_processing_log(filename, "ERROR", error_msg)
                    fail_count += 1
                    
                # Update progress bar
                progress_bar.progress((index + 1) / total_files)
                
            append_log("=========================================")
            append_log(f"Batch completed: {success_count} succeeded, {fail_count} failed.", "success" if fail_count == 0 else "warning")
            
            # Show success toast or warn toast
            if success_count > 0:
                st.toast(f"Successfully imported {success_count} resumes!", icon="✅")
            if fail_count > 0:
                st.toast(f"Failed to import {fail_count} resumes. Check logs.", icon="⚠️")

# ----------------- PAGE 3: SEARCH & FILTER -----------------
elif page == "🔍 Search & Filter":
    st.markdown("<h1 class='title-gradient'>Candidate Search & Filters</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle-text'>Search the candidate database case-insensitively using advanced filters</p>", unsafe_allow_html=True)
    
    # Retrieve all candidates to establish options for multiselects and basic data
    all_candidates = db.get_all_candidates()
    
    if not all_candidates:
        st.markdown(
            """
            <div class='empty-state'>
                <h3>No Candidates Available</h3>
                <p>The database is currently empty. Please upload resumes to start searching.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        # Build Filter Pane in UI
        st.markdown("### Search Filters")
        col_search1, col_search2, col_search3, col_search4 = st.columns(4)
        
        with col_search1:
            name_filter = st.text_input("Name Keyword", placeholder="e.g. John")
        with col_search2:
            skill_filter = st.text_input("Skill Keyword", placeholder="e.g. Python")
        with col_search3:
            location_filter = st.text_input("Location Keyword", placeholder="e.g. London")
        with col_search4:
            # Find max experience to scale slider
            max_exp = max([c["years_of_experience"] for c in all_candidates]) if all_candidates else 10.0
            max_exp = max(max_exp, 5.0)
            exp_filter = st.slider("Minimum Years of Experience", 0.0, float(max_exp), 0.0, step=0.5)
            
        # Run Search
        results = db.search_candidates(
            skill_query=skill_filter,
            min_experience=exp_filter,
            location_query=location_filter,
            name_query=name_filter
        )
        
        st.markdown("---")
        st.subheader(f"Search Results ({len(results)} matches)")
        
        if not results:
            st.markdown(
                """
                <div class='empty-state'>
                    <h3>No Matches Found</h3>
                    <p>Try broadening your filter keywords or lowering the minimum experience limit.</p>
                </div>
                """, 
                unsafe_allow_html=True
            )
        else:
            # Format results for Dataframe display
            table_data = []
            for r in results:
                table_data.append({
                    "ID": r["id"],
                    "Name": r["name"],
                    "Email": r["email"],
                    "Phone": r["phone"],
                    "Location": r["location"],
                    "Years Exp": r["years_of_experience"],
                    "Skills": ", ".join(r["skills"][:6]) + ("..." if len(r["skills"]) > 6 else ""),
                    "Filename": r["original_filename"]
                })
                
            df_results = pd.DataFrame(table_data)
            
            st.dataframe(
                df_results,
                use_container_width=True,
                hide_index=True
            )
            
            # Export CSV Option
            st.markdown("### Export Results")
            # Build CSV content
            export_df = pd.DataFrame(results)
            # Reorder for friendly columns and expand skills list to comma-separated
            if not export_df.empty:
                export_df["skills"] = export_df["skills"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
                export_df = export_df.rename(columns={
                    "id": "Candidate ID",
                    "name": "Full Name",
                    "email": "Email Address",
                    "phone": "Phone Number",
                    "location": "Location",
                    "years_of_experience": "Years of Experience",
                    "summary": "Profile Summary",
                    "skills": "Skills List",
                    "original_filename": "Original Filename",
                    "created_at": "Parsed Date"
                })
                
                csv_data = export_df.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="📥 Export Candidate Data to CSV",
                    data=csv_data,
                    file_name="talentscan_candidates.csv",
                    mime="text/csv",
                    help="Click here to download the filtered candidates list as a CSV file."
                )

# ----------------- PAGE 4: CANDIDATE PROFILES -----------------
elif page == "👤 Candidate Profiles":
    st.markdown("<h1 class='title-gradient'>Candidate Detail Profiles</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle-text'>View and manage detailed information for individual candidates</p>", unsafe_allow_html=True)
    
    candidates = db.get_all_candidates()
    
    if not candidates:
        st.markdown(
            """
            <div class='empty-state'>
                <h3>No Profiles Available</h3>
                <p>Upload resumes to populate the candidate profiles.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        # Candidate Selector
        candidate_options = {f"{c['name']} (ID: {c['id']}) - {c['location']}": c['id'] for c in candidates}
        selected_option = st.selectbox("Select a Candidate", list(candidate_options.keys()))
        
        if selected_option:
            candidate_id = candidate_options[selected_option]
            c = db.get_candidate_by_id(candidate_id)
            
            if c:
                st.markdown("---")
                
                # Header Details
                header_col1, header_col2 = st.columns([3, 1])
                with header_col1:
                    st.markdown(f"<h2 style='margin:0;'>{c['name']}</h2>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#718096; font-size:1.1rem;'>📍 {c['location']}</p>", unsafe_allow_html=True)
                with header_col2:
                    # Professional delete button
                    if st.button("🗑️ Delete Candidate Profile", type="secondary"):
                        db.delete_candidate(c["id"])
                        st.toast(f"Candidate {c['name']} deleted successfully.", icon="🗑️")
                        st.rerun()
                        
                # Split content into Contact details and Professional summary
                col_left, col_right = st.columns([1, 2])
                
                with col_left:
                    st.markdown("### Contact Details")
                    
                    st.markdown(
                        f"""
                        <div class="metric-card" style="background-color: #F8FAFC;">
                            <p style="margin: 0 0 0.5rem 0;"><b>📧 Email Address:</b></p>
                            <p style="margin: 0 0 1rem 0; color: #2B6CB0; word-break: break-all;">{c['email'] or 'Not Extracted'}</p>
                            <p style="margin: 0 0 0.5rem 0;"><b>📞 Phone Number:</b></p>
                            <p style="margin: 0 0 1rem 0; color: #2B6CB0;">{c['phone'] or 'Not Extracted'}</p>
                            <p style="margin: 0 0 0.5rem 0;"><b>📁 Original File:</b></p>
                            <p style="margin: 0 0 1rem 0; color: #4A5568; font-size: 0.9rem;">{c['original_filename'] or 'N/A'}</p>
                            <p style="margin: 0 0 0.5rem 0;"><b>📅 Date Parsed:</b></p>
                            <p style="margin: 0; color: #718096; font-size: 0.9rem;">{c['created_at']}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Professional Info
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <p style="color: #718096; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.2rem;">EXPERIENCE LEVEL</p>
                            <h3 style="margin: 0; color: #2D3748;">{c['years_of_experience']} Years</h3>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                with col_right:
                    st.markdown("### Profile Summary")
                    st.info(c["summary"])
                    
                    st.markdown("### Normalized Skills")
                    if c["skills"]:
                        badges_html = "".join([f"<span class='skill-badge'>{s}</span>" for s in c["skills"]])
                        st.markdown(badges_html, unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='color:#718096; font-style:italic;'>No skills extracted</p>", unsafe_allow_html=True)
                        
                    # Let the user review the PII scrubbed text version to prove compliance
                    st.markdown("---")
                    with st.expander("📄 View Scrubbed Resume Text (PII Protected)"):
                        st.markdown(
                            f"""
                            <div style="background-color: #F7FAFC; padding: 1rem; border-radius: 8px; border: 1px solid #E2E8F0; max-height: 400px; overflow-y: auto; white-space: pre-wrap; font-family: monospace; font-size: 0.85rem; color: #4A5568;">
{parser.scrub_pii(parser.scrub_pii(parser.scrub_pii(c['summary'] or '', c['name'], c['email'], c['phone']), c['name'], c['email'], c['phone']), c['name'], c['email'], c['phone'])}
...
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                        st.caption("Note: This is the raw text structure parsed from the document with privacy redaction tokens applied before Gemini API processing.")
