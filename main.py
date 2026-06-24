from dotenv import load_dotenv
load_dotenv(override=True)
# Reload trigger for gemini-flash-lite-latest


import os
import tempfile
import json
import base64
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
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

app = FastAPI()


def _run_pipeline(resume_dict: dict) -> dict:
    result = process_resume_with_graph(resume_dict)
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
        print("⚠️ DATABASE_URL not set, skipping Neon DB insert.")
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
        print(f"✅ Saved {name} to leaderboard.")
    except Exception as e:
        print(f"❌ Failed to insert into Neon DB: {e}")

def upload_to_cloudinary(file_path: str) -> str:
    if not os.getenv("CLOUDINARY_URL"):
        print("⚠️ CLOUDINARY_URL not set, skipping Cloudinary upload.")
        return ""
    try:
        upload_result = cloudinary.uploader.upload(
            file_path,
            resource_type="raw",       # "raw" preserves the file as-is with correct Content-Type
            format="pdf",              # ensure .pdf extension on the URL
            type="upload",
            access_mode="public",
            use_filename=True,
            unique_filename=True,
        )
        print("✅ Uploaded to Cloudinary:", upload_result.get("secure_url"))
        return upload_result.get("secure_url", "")
    except Exception as e:
        print(f"❌ Failed to upload to Cloudinary: {e}")
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
        result = _run_pipeline(resume_dict)
        candidate_name = resume_dict.get("name", "resume").replace(" ", "_").lower()
        score = result.get("ats_score", 0)

        # Upload generated PDF to Cloudinary
        pdf_url = ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as gen_temp:
            gen_temp.write(result["pdf_bytes"])
            gen_temp_path = gen_temp.name
        try:
            pdf_url = upload_to_cloudinary(gen_temp_path)
        finally:
            os.unlink(gen_temp_path)

        # Save to Neon DB
        if pdf_url:
            save_to_leaderboard(candidate_name, score, pdf_url)

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
async def process_pdf(file: UploadFile = File(...)):
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

    pdf_url = upload_to_cloudinary(temp_file_path)
    os.unlink(temp_file_path)

    candidate_name = file.filename.split('.')[0] if file.filename else "Unknown"
    if pdf_url:
        save_to_leaderboard(candidate_name, score, pdf_url)

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
        cur.execute("SELECT id, name, ats_score, pdf_url FROM leaderboard ORDER BY ats_score DESC LIMIT 50")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"success": True, "leaderboard": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch leaderboard: {str(e)}")


