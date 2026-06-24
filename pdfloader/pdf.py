from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption
from docling.datamodel.base_models import InputFormat
import fitz
import re
from urllib.parse import urlparse


def _extract_text_pymupdf(pdf: str) -> str:

    doc = fitz.open(pdf)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages)


def pdf_to_text(pdf):
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False

    docling_text = ""
    try:
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        result = converter.convert(pdf)
        docling_text = result.document.export_to_markdown() or ""
    except Exception as e:
        print(f"Docling conversion failed: {e}")

    # Fallback to PyMuPDF if Docling output is empty, too short, or just a layout placeholder
    clean_docling = docling_text.strip().replace("<!-- image -->", "").strip()
    if not clean_docling or len(clean_docling) < 50:
        print("Docling text is empty or too short. Falling back to PyMuPDF.")
        docling_text = _extract_text_pymupdf(pdf)

    pdf_doc = fitz.open(pdf)
    all_uris = []

    for page in pdf_doc:
        for link in page.get_links():
            if link.get("uri"):
                all_uris.append(link["uri"])

    final_text = docling_text

    for uri in all_uris:
        escaped_uri = re.escape(uri)
        final_text = re.sub(r'(?<!\[)' + escaped_uri + r'(?!\]\()', f'[{uri}]({uri})', final_text)

    linkedin_uri = None
    github_uri = None
    for uri in all_uris:
        parsed = urlparse(uri)
        if "linkedin.com" in parsed.netloc:
            linkedin_uri = uri
        if "github.com" in parsed.netloc:
            github_uri = uri

    if linkedin_uri:
        final_text = re.sub(r'LinkedIn: ([^\s|]+)', f'LinkedIn: [\\1]({linkedin_uri})', final_text)

    if github_uri:
        final_text = re.sub(r'GitHub: ([^\s|]+)', f'GitHub: [\\1]({github_uri})', final_text)

    return final_text
