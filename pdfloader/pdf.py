from docling.document_converter import DocumentConverter
import fitz  # PyMuPDF for hyperlink extraction
import re
from urllib.parse import urlparse

def pdf_to_text(pdf):
    """
    Args:
        pdf: path to PDF file or file-like object

    Returns:
        str: extracted text with hyperlinks preserved
    """
    # Extract text using docling
    converter = DocumentConverter()
    result = converter.convert(pdf)
    docling_text = result.document.export_to_markdown()

    # Now extract hyperlinks using PyMuPDF
    pdf_doc = fitz.open(pdf)
    all_uris = []
    
    for page in pdf_doc:
        for link in page.get_links():
            if link.get("uri"):
                all_uris.append(link["uri"])
    
    # Process URIs to create markdown links
    final_text = docling_text
    
    # Replace direct URIs in text
    for uri in all_uris:
        escaped_uri = re.escape(uri)
        final_text = re.sub(r'(?<!\[)' + escaped_uri + r'(?!\]\()', f'[{uri}]({uri})', final_text)
    
    # Find and link social media profiles (LinkedIn, GitHub)
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