import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from typing_extensions import TypedDict

from pdfloader.pdf import pdf_to_text
from graphs.prompts import ENHANCE_SYSTEM_PROMPT, ATS_OPTIMIZE_SYSTEM_PROMPT, ATS_SCORER_SYSTEM_PROMPT,LATEX_BUILDER_SYSTEM_PROMPT,CONDENSE_SYSTEM_PROMPT
from langgraph.graph import StateGraph, END

from pydanticmod.allmodels import ResumeData,ResumeState
from graphs.llm_client import call_llm, call_llm_json, LLMClientError
from graphs.config import MAX_PAGE_RETRIES





TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "resumetemplates"


def _load_template(has_experience: bool) -> tuple[str, str]:
    template_name = "exp.tex" if has_experience else "NOexp.tex"
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_name, template_path.read_text(encoding="utf-8")


def _serialize_list(items):
    result = []
    for item in (items or []):
        if hasattr(item, "model_dump"):
            result.append(item.model_dump())
        elif hasattr(item, "dict"):
            result.append(item.dict())
        elif isinstance(item, dict):
            result.append(item)
        else:
            result.append(str(item))
    return result


def normalize_node(state: ResumeState) -> dict:
    print("[Normalize] Processing resume data...")

    resume_data = state.get("resume_data")
    if not resume_data:
        raise ValueError("No resume data found in state")

    if isinstance(resume_data, dict):
        resume_obj = ResumeData(**resume_data)
    else:
        resume_obj = resume_data

    normalized = {
        "name": resume_obj.name.strip().title(),
        "title": resume_obj.title.strip(),
        "email": resume_obj.email.strip().lower(),
        "phone": resume_obj.phone.strip() if resume_obj.phone else None,
        "location": resume_obj.location.strip() if resume_obj.location else None,
        "linkedin_url": resume_obj.linkedin_url.strip() if resume_obj.linkedin_url else None,
        "github_url": resume_obj.github_url.strip() if resume_obj.github_url else None,
        "portfolio_url": resume_obj.portfolio_url.strip() if resume_obj.portfolio_url else None,
        "summary": resume_obj.summary.strip() if resume_obj.summary else None,
        "skills": [s.strip() for s in resume_obj.skills] if resume_obj.skills else [],
        "experience": _serialize_list(resume_obj.experience),
        "projects": _serialize_list(resume_obj.projects),
        "education": _serialize_list(resume_obj.education),
        "certifications": _serialize_list(resume_obj.certifications),
        "achievements": [a.strip() for a in resume_obj.achievements] if resume_obj.achievements else [],
        "additional_info": resume_obj.additional_info.strip() if resume_obj.additional_info else None,
    }

    has_experience = bool(normalized["experience"])
    template_name, template_content = _load_template(has_experience)

    print(f"[Normalize] {normalized['name']} — {normalized['title']}")
    print(f"[Normalize] Template: {template_name}")

    return {
        **state,
        "normalized_data": normalized,
        "selected_template": template_name,
        "template_content": template_content,
        "compilation_attempts": 0,
        "processing_steps": state.get("processing_steps", []) + ["normalized"],
        "errors": state.get("errors", []),
    }


def enhance_resume_node(state: ResumeState) -> dict:
    print("[Enhance] Calling LLM to enhance resume...")

    normalized = state.get("normalized_data", {})

    user_prompt = f"""Enhance this resume data. Return ONLY valid JSON.

CANDIDATE DATA:
{json.dumps(normalized, indent=2, default=str)}"""

    try:
        enhanced = call_llm_json(ENHANCE_SYSTEM_PROMPT, user_prompt, max_tokens=3500)
        state_errors = state.get("errors", [])
    except LLMClientError as e:
        print(f"[Enhance] LLM failed: {e}")
        enhanced = {
            "summary": normalized.get("summary", ""),
            "skills": {"technical": normalized.get("skills", []), "tools_platforms": [], "soft_skills": []},
            "experience": normalized.get("experience", []),
            "projects": normalized.get("projects", []),
            "achievements": normalized.get("achievements", []),
            "education": normalized.get("education", []),
            "certifications": normalized.get("certifications", []),
        }
        state_errors = state.get("errors", []) + [f"enhance LLM failed: {e}"]

    print("[Enhance] Done")

    return {
        **state,
        "enhanced_resume": enhanced,
        "processing_steps": state.get("processing_steps", []) + ["enhanced"],
        "errors": state_errors,
    }



def ats_optimize_node(state: ResumeState) -> dict:
    print("[ATS Optimize] Calling LLM...")

    normalized = state.get("normalized_data", {})
    enhanced = state.get("enhanced_resume", {})

    user_prompt = f"""Optimize for ONE-PAGE ATS format. Return ONLY valid JSON.

CANDIDATE:
Name: {normalized.get('name', '')}
Title: {normalized.get('title', '')}
Email: {normalized.get('email', '')}
Phone: {normalized.get('phone', '')}
Location: {normalized.get('location', '')}
LinkedIn: {normalized.get('linkedin_url', '')}
GitHub: {normalized.get('github_url', '')}
Portfolio: {normalized.get('portfolio_url', '')}

ENHANCED DATA:
{json.dumps(enhanced, indent=2, default=str)}"""

    try:
        optimized = call_llm_json(ATS_OPTIMIZE_SYSTEM_PROMPT, user_prompt, max_tokens=3500)
        state_errors = state.get("errors", [])
    except LLMClientError as e:
        print(f"[ATS Optimize] LLM failed: {e}")
        optimized = {
            "name": normalized.get("name", ""),
            "title": normalized.get("title", ""),
            "contact": {
                "email": normalized.get("email", ""),
                "phone": normalized.get("phone", ""),
                "location": normalized.get("location", ""),
                "linkedin": normalized.get("linkedin_url", ""),
                "github": normalized.get("github_url", ""),
                "portfolio": normalized.get("portfolio_url", ""),
            },
            "summary": enhanced.get("summary", "")[:200],
            "skills": enhanced.get("skills", {}),
            "experience": enhanced.get("experience", [])[:3],
            "projects": enhanced.get("projects", [])[:2],
            "education": enhanced.get("education", [])[:2],
            "certifications": enhanced.get("certifications", [])[:3],
            "achievements": enhanced.get("achievements", [])[:4],
        }
        state_errors = state.get("errors", []) + [f"ats_optimize LLM failed: {e}"]

    print("[ATS Optimize] Done")

    return {
        **state,
        "ats_optimized_data": optimized,
        "processing_steps": state.get("processing_steps", []) + ["ats_optimized"],
        "errors": state_errors,
    }


def latex_builder_node(state: ResumeState) -> dict:
    print("[LaTeX Builder] Calling LLM to generate LaTeX...")

    optimized = state.get("ats_optimized_data", {})
    template_content = state.get("template_content", "")
    template_name = state.get("selected_template", "exp.tex")

    user_prompt = f"""Fill the following LaTeX template with this candidate's data.
Keep EVERY LaTeX command, package, and spacing value EXACTLY as-is.
ONLY replace the human content (name, contact, summary, skills, experience, projects, education, certs, achievements).
The result MUST be exactly 1 page. Trim content if needed.
Output ONLY raw LaTeX.

TEMPLATE FILE ({template_name}) — USE THIS EXACT SKELETON:
---
{template_content}
---

CANDIDATE DATA TO INSERT:
{json.dumps(optimized, indent=2, default=str)}"""

    try:
        latex = call_llm(LATEX_BUILDER_SYSTEM_PROMPT, user_prompt, max_tokens=4096)
    except LLMClientError as e:
        print(f"[LaTeX Builder] LLM failed: {e}")
        return {
            **state,
            "latex_content": "",
            "processing_steps": state.get("processing_steps", []) + ["latex_failed"],
            "errors": state.get("errors", []) + [f"latex_builder LLM failed: {e}"],
        }

    latex = latex.strip()
    if latex.startswith("```"):
        first_nl = latex.index("\n")
        latex = latex[first_nl + 1:]
    if latex.endswith("```"):
        latex = latex[:-3].strip()

    print(f"[LaTeX Builder] Generated {len(latex)} chars")

    return {
        **state,
        "latex_content": latex,
        "processing_steps": state.get("processing_steps", []) + ["latex_generated"],
        "errors": state.get("errors", []),
    }


def pdf_compiler_node(state: ResumeState) -> dict:
    print("[PDF Compiler] Compiling LaTeX to PDF...")

    latex_content = state.get("latex_content", "")
    if not latex_content:
        print("[PDF Compiler] No LaTeX content")
        return {
            **state,
            "pdf_bytes": b"",
            "page_count": 0,
            "compilation_attempts": state.get("compilation_attempts", 0) + 1,
            "processing_steps": state.get("processing_steps", []) + ["pdf_compile_skipped"],
            "errors": state.get("errors", []) + ["No LaTeX content to compile"],
        }

    attempts = state.get("compilation_attempts", 0) + 1

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        pdf_path = os.path.join(tmpdir, "resume.pdf")

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_content)

        try:
            for _ in range(2):
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

            if not os.path.exists(pdf_path):
                log_path = os.path.join(tmpdir, "resume.log")
                log_content = ""
                if os.path.exists(log_path):
                    with open(log_path, "r") as lf:
                        log_content = lf.read()[-2000:]
                print(f"[PDF Compiler] pdflatex failed.\n{log_content}")
                return {
                    **state,
                    "pdf_bytes": b"",
                    "page_count": 0,
                    "compilation_attempts": attempts,
                    "processing_steps": state.get("processing_steps", []) + ["pdf_compile_failed"],
                    "errors": state.get("errors", []) + [f"pdflatex failed (attempt {attempts})"],
                }

            with open(pdf_path, "rb") as pf:
                pdf_bytes = pf.read()

            try:
                import fitz
                pdf_doc = fitz.open(pdf_path)
                page_count = len(pdf_doc)
                pdf_doc.close()
            except ImportError:
                page_count = max(1, len(pdf_bytes) // 50000)
                print("[PDF Compiler] PyMuPDF not available, estimated page count")

        except subprocess.TimeoutExpired:
            print("[PDF Compiler] pdflatex timed out")
            return {
                **state,
                "pdf_bytes": b"",
                "page_count": 0,
                "compilation_attempts": attempts,
                "processing_steps": state.get("processing_steps", []) + ["pdf_compile_timeout"],
                "errors": state.get("errors", []) + [f"pdflatex timed out (attempt {attempts})"],
            }
        except FileNotFoundError:
            print("[PDF Compiler] pdflatex not found — install TeX Live or MiKTeX")
            return {
                **state,
                "pdf_bytes": b"",
                "page_count": 0,
                "compilation_attempts": attempts,
                "processing_steps": state.get("processing_steps", []) + ["pdflatex_not_found"],
                "errors": state.get("errors", []) + ["pdflatex not found on system"],
            }

    print(f"[PDF Compiler] {len(pdf_bytes)} bytes, {page_count} page(s) (attempt {attempts})")

    return {
        **state,
        "pdf_bytes": pdf_bytes,
        "page_count": page_count,
        "compilation_attempts": attempts,
        "processing_steps": state.get("processing_steps", []) + [f"pdf_compiled_attempt_{attempts}"],
        "errors": state.get("errors", []),
    }



def condense_resume_node(state: ResumeState) -> dict:
    attempts = state.get("compilation_attempts", 0)
    page_count = state.get("page_count", "?")
    print(f"[Condense] {page_count} pages — condensing (attempt {attempts})...")

    latex = state.get("latex_content", "")

    if attempts > MAX_PAGE_RETRIES:
        urgency = f"""CRITICAL: This is attempt {attempts}. Previous condensation attempts FAILED to reach 1 page.
You MUST be DRASTICALLY more aggressive:
- Cut each experience to MAX 2 bullet points
- Cut projects to MAX 1-2 lines each
- Remove achievements section entirely if needed
- Remove certifications if needed to fit
- Use \\vspace{{-Xpt}} aggressively to reclaim space
- The result MUST be 1 page. There is NO alternative."""
    else:
        urgency = f"Attempt {attempts} of {MAX_PAGE_RETRIES}. Be more aggressive with each attempt."

    user_prompt = f"""This LaTeX resume compiles to {page_count} page(s).
It MUST fit on exactly ONE page. Output ONLY raw LaTeX.

{urgency}

CURRENT LATEX:
{latex}"""

    try:
        condensed = call_llm(CONDENSE_SYSTEM_PROMPT, user_prompt, max_tokens=4096)
    except LLMClientError as e:
        print(f"[Condense] LLM failed: {e}")
        return {
            **state,
            "processing_steps": state.get("processing_steps", []) + ["condense_failed"],
            "errors": state.get("errors", []) + [f"condense LLM failed: {e}"],
        }

    condensed = condensed.strip()
    if condensed.startswith("```"):
        first_nl = condensed.index("\n")
        condensed = condensed[first_nl + 1:]
    if condensed.endswith("```"):
        condensed = condensed[:-3].strip()

    print(f"[Condense] {len(latex)} → {len(condensed)} chars")

    return {
        **state,
        "latex_content": condensed,
        "processing_steps": state.get("processing_steps", []) + [f"condensed_attempt_{attempts}"],
        "errors": state.get("errors", []),
    }

def ats_scorer_node(state: ResumeState) -> dict:
    print("[ATS Scorer] Scoring resume...")

    pdf_bytes = state.get("pdf_bytes", b"")
    
    if not pdf_bytes:
        print("[ATS Scorer] No PDF bytes found. Falling back to LaTeX.")
        resume_content = state.get("latex_content", "")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            resume_content = pdf_to_text(tmp_path)
        except Exception as e:
            print(f"[ATS Scorer] PDF text extraction failed: {e}. Falling back to LaTeX.")
            resume_content = state.get("latex_content", "")
        finally:
            os.unlink(tmp_path)

    user_prompt = f"""Score this resume for ATS compatibility. Return ONLY valid JSON.

RESUME TEXT:
{resume_content}"""

    try:
        feedback = call_llm_json(ATS_SCORER_SYSTEM_PROMPT, user_prompt, max_tokens=2048)
        score = feedback.get("score", 0)
    except LLMClientError as e:
        print(f"[ATS Scorer] LLM failed: {e}")
        score = 0
        feedback = {
            "score": 0,
            "strengths": ["Unable to score — LLM call failed"],
            "improvements": [str(e)],
        }

    print(f"[ATS Scorer] Score: {score}/100")

    return {
        **state,
        "ats_score": score,
        "ats_feedback": feedback,
        "processing_steps": state.get("processing_steps", []) + ["ats_scored"],
        "errors": state.get("errors", []),
    }


HARD_CAP_RETRIES = MAX_PAGE_RETRIES + 2


def check_page_count(state: ResumeState) -> str:
    page_count = state.get("page_count", 0)
    attempts = state.get("compilation_attempts", 0)

    if page_count <= 1:
        print(f"[Router] {page_count} page(s) — proceeding to scoring")
        return "ats_scorer"

    if attempts >= HARD_CAP_RETRIES:
        print(f"[Router] FAILED: still {page_count} pages after {attempts} attempts — aborting")
        raise RuntimeError(
            f"Resume is {page_count} pages after {attempts} condensation attempts. "
            f"Could not fit to 1 page. Review content or template."
        )

    if attempts >= MAX_PAGE_RETRIES:
        print(f"[Router] {page_count} pages after {attempts} attempts — aggressive condense")
    else:
        print(f"[Router] {page_count} pages — condensing (attempt {attempts}/{MAX_PAGE_RETRIES})")

    return "condense"


def create_resume_processing_graph() -> StateGraph:
    workflow = StateGraph(ResumeState)

    workflow.add_node("normalize", normalize_node)
    workflow.add_node("enhance", enhance_resume_node)
    workflow.add_node("ats_optimize", ats_optimize_node)
    workflow.add_node("latex_builder", latex_builder_node)
    workflow.add_node("pdf_compiler", pdf_compiler_node)
    workflow.add_node("condense", condense_resume_node)
    workflow.add_node("ats_scorer", ats_scorer_node)

    workflow.set_entry_point("normalize")
    workflow.add_edge("normalize", "enhance")
    workflow.add_edge("enhance", "ats_optimize")
    workflow.add_edge("ats_optimize", "latex_builder")
    workflow.add_edge("latex_builder", "pdf_compiler")

    workflow.add_conditional_edges(
        "pdf_compiler",
        check_page_count,
        {
            "ats_scorer": "ats_scorer",
            "condense": "condense",
        },
    )

    workflow.add_edge("condense", "pdf_compiler")
    workflow.add_edge("ats_scorer", END)

    return workflow


resume_processing_graph = create_resume_processing_graph().compile()


def process_resume_with_graph(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    print("Starting resume processing pipeline...")

    initial_state: ResumeState = {
        "resume_data": resume_data,
        "processing_steps": [],
        "errors": [],
        "compilation_attempts": 0,
    }

    try:
        result = resume_processing_graph.invoke(initial_state)

        response = {
            "success": True,
            "pdf_bytes": result.get("pdf_bytes", b""),
            "latex_content": result.get("latex_content", ""),
            "ats_score": result.get("ats_score", 0),
            "ats_feedback": result.get("ats_feedback", {}),
            "page_count": result.get("page_count", 0),
            "optimized_data": result.get("ats_optimized_data", {}),
            "processing_steps": result.get("processing_steps", []),
            "errors": result.get("errors", []),
        }

        print(f"Done — {result.get('page_count', '?')} page(s), ATS: {result.get('ats_score', '?')}/100")
        return response

    except Exception as e:
        print(f"Pipeline failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "processing_steps": initial_state.get("processing_steps", []),
            "errors": initial_state.get("errors", []) + [str(e)],
        }
