import os
import tempfile
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import Optional
from pydanticmod.allmodels import ResumeData
from dotenv import load_dotenv
from pdfloader.pdf import pdf_to_text

load_dotenv()
app = FastAPI()


@app.post("/process-resume")
async def process_resume(
    file: Optional[UploadFile] = File(None),
    data: Optional[str] = None
):
    pdfdata = None
    extra_data = None

    # Extract text from PDF if file is provided
    if file:
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
    
    # Parse JSON data if provided using ResumeData Pydantic model
    if data:
        try:
            # Parse JSON string into dictionary first
            data_dict = json.loads(data)
            # Then create ResumeData object for validation
            extra_data = ResumeData(**data_dict)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=422, detail=f"Invalid JSON data: {str(e)}")
    
    return {
        "pdfdata": pdfdata,
        "extra_data": extra_data.dict() if extra_data else None
    }


@app.post("/process-pdf-only")
async def process_pdf_only(file: UploadFile = File(...)):
    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(content)
        temp_file_path = temp_file.name
    try:
        pdfdata = pdf_to_text(temp_file_path)
        return {
            "pdfdata": pdfdata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")
    finally:
        os.unlink(temp_file_path)
