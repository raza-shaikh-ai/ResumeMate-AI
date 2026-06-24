from dotenv import load_dotenv
load_dotenv(override=True)


import os
import tempfile
import json
import base64
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import cloudinary
import cloudinary.uploader
import cloudinary.api
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, Response
from typing import Optional, Union
from pydanticmod.allmodels import ResumeData
from pdfloader.pdf import pdf_to_text
from graphs.nodes import process_resume_with_graph, ATS_SCORER_SYSTEM_PROMPT
from graphs.llm_client import call_llm_json, LLMClientError

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static/resumes", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


def _run_pipeline(resume_dict: dict, pdf_text: Optional[str] = None) -> dict:
    result = process_resume_with_graph(resume_dict, pdf_text)
    if not result.get("success") or not result.get("pdf_bytes"):
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Resume generation failed",
                "errors": result.get("errors", []),
                "processing_steps": result.get("processing_steps", []),
            }
        )
    return result

def save_to_leaderboard(name: str, ats_score: int, pdf_url: str):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set, skipping Neon DB insert.")
        return
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        record_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO leaderboard (id, name, ats_score, pdf_url) VALUES (%s, %s, %s, %s)",
            (record_id, name, ats_score, pdf_url)
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f"Saved {name} to leaderboard.")
    except Exception as e:
        print(f"Failed to insert into Neon DB: {e}")

def upload_to_cloudinary(file_path: str) -> str:
    if not os.getenv("CLOUDINARY_URL"):
        print("CLOUDINARY_URL not set, skipping Cloudinary upload.")
        return ""
    try:
        upload_result = cloudinary.uploader.upload(
            file_path,
            resource_type="raw",
            format="pdf",
            type="upload",
            access_mode="public",
            use_filename=True,
            unique_filename=True,
        )
        print("Uploaded to Cloudinary:", upload_result.get("secure_url"))
        return upload_result.get("secure_url", "")
    except Exception as e:
        print(f"Failed to upload to Cloudinary: {e}")
        return ""


@app.post("/process-resume")
async def process_resume(
    file: Optional[Union[UploadFile, str]] = File(None),
    data: Optional[str] = Form(None)
):
    pdfdata = None
    resume_dict = None

    if file and isinstance(file, UploadFile) and file.filename:
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        try:
            pdfdata = pdf_to_text(temp_file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")
        finally:
            os.unlink(temp_file_path)

    if data:
        try:
            data_dict = json.loads(data)
            resume_obj = ResumeData(**data_dict)
            resume_dict = resume_obj.model_dump()
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=422, detail=f"Invalid JSON data: {str(e)}")

    if resume_dict:
        result = _run_pipeline(resume_dict, pdfdata)
        candidate_name = resume_dict.get("name", "resume").replace(" ", "_").lower()
        db_name = resume_dict.get("name", "John Doe").strip()
        score = result.get("ats_score", 0)

        local_filename = f"{uuid.uuid4()}.pdf"
        local_path = os.path.join("static", "resumes", local_filename)
        with open(local_path, "wb") as f:
            f.write(result["pdf_bytes"])
        
        pdf_url = f"/static/resumes/{local_filename}"

        try:
            upload_to_cloudinary(local_path)
        except Exception as e:
            print(f"Cloudinary fallback upload failed: {e}")

        save_to_leaderboard(db_name, score, pdf_url)

        metadata = {
            "success": True,
            "ats_score": score,
            "ats_feedback": result.get("ats_feedback", {}),
            "page_count": result.get("page_count", 0),
            "filename": f"{candidate_name}_resume.pdf",
            "pdf_url": pdf_url,
            "processing_steps": result.get("processing_steps", []),
            "errors": result.get("errors", []),
        }

        return Response(
            content=result["pdf_bytes"],
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{candidate_name}_resume.pdf"',
                "X-Metadata": json.dumps(metadata),
                "Access-Control-Expose-Headers": "Content-Disposition, X-Metadata"
            }
        )

    return {"pdfdata": pdfdata, "message": "No structured resume data provided. Send JSON in 'data' field."}

@app.post("/process-pdf")
async def process_pdf(
    file: UploadFile = File(...),
    candidate_name: Optional[str] = Form(None)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(content)
        temp_file_path = temp_file.name
        
    try:
        pdf_text = pdf_to_text(temp_file_path)
    except Exception as e:
        os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")

    user_prompt = f"""Score this resume for ATS compatibility. Return ONLY valid JSON.

RESUME TEXT:
{pdf_text}"""

    try:
        feedback = call_llm_json(ATS_SCORER_SYSTEM_PROMPT, user_prompt, max_tokens=2048)
        score = feedback.get("score", 0)
    except LLMClientError as e:
        os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=f"LLM scoring failed: {str(e)}")

    local_filename = f"{uuid.uuid4()}.pdf"
    local_path = os.path.join("static", "resumes", local_filename)
    with open(local_path, "wb") as f:
        f.write(content)
    
    pdf_url = f"/static/resumes/{local_filename}"

    try:
        upload_to_cloudinary(local_path)
    except Exception as e:
        print(f"Cloudinary fallback upload failed: {e}")
        
    os.unlink(temp_file_path)

    db_name = candidate_name.strip() if (candidate_name and candidate_name.strip()) else (file.filename.split('.')[0] if file.filename else "Unknown")
    save_to_leaderboard(db_name, score, pdf_url)

    return {
        "success": True,
        "ats_score": score,
        "ats_feedback": feedback,
        "pdf_url": pdf_url
    }

@app.get("/leaderboard")
async def get_leaderboard():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured.")
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT id, name, ats_score, pdf_url FROM ("
            "  SELECT DISTINCT ON (LOWER(name)) id, name, ats_score, pdf_url "
            "  FROM leaderboard "
            "  ORDER BY LOWER(name), ats_score DESC"
            ") subquery ORDER BY ats_score DESC LIMIT 50"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"success": True, "leaderboard": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch leaderboard: {str(e)}")


LAST_KNOWN_VISITORS = 1
LAST_FETCH_TIME = 0.0


@app.get("/visitors")
async def get_visitors():
    global LAST_KNOWN_VISITORS, LAST_FETCH_TIME
    import time
    current_time = time.time()
    if current_time - LAST_FETCH_TIME < 15:
        return {"success": True, "visitors": LAST_KNOWN_VISITORS}
    load_dotenv(override=True)
    project_id = os.getenv("POSTHOG_PROJECT_ID", "")
    api_key = os.getenv("POSTHOG_API_KEY", "")
    if not api_key:
        return {"success": False, "visitors": LAST_KNOWN_VISITORS, "error": "POSTHOG_API_KEY not set"}
    try:
        url = f"https://us.posthog.com/api/projects/{project_id}/query"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "query": {
                "kind": "HogQLQuery",
                "query": f"SELECT count(distinct person_id) FROM events WHERE event = '$pageview' /* {uuid.uuid4().hex} */"
            }
        }
        r = requests.post(url, headers=headers, json=data, timeout=10)
        if r.status_code == 200:
            res = r.json()
            count = res.get("results", [[LAST_KNOWN_VISITORS]])[0][0]
            if isinstance(count, (int, float)):
                LAST_KNOWN_VISITORS = int(count)
                LAST_FETCH_TIME = current_time
            return {"success": True, "visitors": LAST_KNOWN_VISITORS}
        else:
            return {"success": True, "visitors": LAST_KNOWN_VISITORS}
    except Exception:
        return {"success": True, "visitors": LAST_KNOWN_VISITORS}


