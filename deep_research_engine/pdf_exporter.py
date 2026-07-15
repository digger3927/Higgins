import os
from typing import Optional

def export_to_pdf(html_path: str, pdf_path: str = "report.pdf") -> bool:
    """
    Ingests an HTML file and exports a high-resolution, multi-page PDF using weasyprint.
    """
    if not os.path.exists(html_path):
        print(f"Error: HTML file {html_path} does not exist.")
        return False

    try:
        from weasyprint import HTML, CSS
        # Using basic printing CSS properties to ensure clean page breaks
        print_css = CSS(string='''
            @page { size: A4; margin: 2cm; }
            h1, h2 { page-break-after: avoid; }
            table, img, .timeline { page-break-inside: avoid; }
        ''')
        
        HTML(html_path).write_pdf(pdf_path, stylesheets=[print_css])
        print(f"Successfully generated PDF at {pdf_path}")
        return True
    except ImportError:
        print("Error: weasyprint is not installed. Please install it using 'pip install weasyprint'.")
        return False
    except Exception as e:
        print(f"Error generating PDF from HTML: {e}")
        return False
