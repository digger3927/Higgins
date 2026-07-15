import os
import markdown
from typing import Dict, Any

def render_html(synthesis_markdown: str, findings: list, output_path: str = "report.html") -> str:
    """
    Renders the research synthesis and raw findings into a beautifully styled HTML document.
    """
    # Convert markdown to HTML
    html_content = markdown.markdown(synthesis_markdown, extensions=['tables', 'fenced_code'])
    
    # Generate findings timeline/table section
    findings_html = "<h2>Research Timeline & Sources</h2><ul>"
    for idx, f in enumerate(findings):
        findings_html += f"<li><strong>Iteration {idx+1} - Query: {f.get('query', 'N/A')}</strong><br/>{f.get('facts', '')}</li>"
    findings_html += "</ul>"

    # HTML template with embedded CSS
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Deep Research Report</title>
    <style>
        :root {{
            --bg-color: #f9fafb;
            --text-color: #1f2937;
            --accent-color: #2563eb;
            --border-color: #e5e7eb;
        }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--bg-color);
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }}
        h1, h2, h3, h4 {{
            color: #111827;
            margin-top: 2rem;
            margin-bottom: 1rem;
            font-weight: 700;
        }}
        h1 {{
            font-size: 2.5rem;
            border-bottom: 3px solid var(--accent-color);
            padding-bottom: 0.5rem;
            margin-bottom: 2rem;
        }}
        p {{
            margin-bottom: 1rem;
        }}
        a {{
            color: var(--accent-color);
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 2rem 0;
            background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 1rem;
            border: 1px solid var(--border-color);
            text-align: left;
        }}
        th {{
            background-color: #f3f4f6;
            font-weight: 600;
        }}
        .timeline {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-top: 3rem;
        }}
        @media print {{
            body {{
                background-color: white;
                max-width: 100%;
                padding: 0;
            }}
            .timeline {{
                box-shadow: none;
                border: 1px solid var(--border-color);
            }}
        }}
    </style>
</head>
<body>
    <h1>Deep Research Report</h1>
    <div class="content">
        {html_content}
    </div>
    <div class="timeline">
        {findings_html}
    </div>
</body>
</html>
"""
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_html)
        print(f"Successfully generated HTML report at {output_path}")
        return output_path
    except IOError as e:
        print(f"Error writing HTML file: {e}")
        return ""
