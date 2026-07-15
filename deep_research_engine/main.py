import sys
from deep_research_engine.config import config, OutputFormat
from deep_research_engine.research_loop import run_research
from deep_research_engine.html_renderer import render_html
from deep_research_engine.pdf_exporter import export_to_pdf

def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = input("Enter your research goal: ")

    if not prompt.strip():
        print("Research goal cannot be empty. Exiting.")
        return

    # Run the main research loop
    state = run_research(prompt)
    
    if not state.is_complete:
        print("Research failed to complete successfully.")
        return

    # Output paths
    html_out = f"{config.OUTPUT_DIR}/report.html"
    pdf_out = f"{config.OUTPUT_DIR}/report.pdf"

    # Ensure output directory exists
    import os
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    # Export formats
    generated_html = ""
    if config.OUTPUT_FORMAT in [OutputFormat.HTML, OutputFormat.BOTH]:
        generated_html = render_html(state.synthesis, state.findings, html_out)

    if config.OUTPUT_FORMAT in [OutputFormat.PDF, OutputFormat.BOTH]:
        # If HTML wasn't generated yet, we need it to create the PDF
        if not generated_html:
            generated_html = render_html(state.synthesis, state.findings, html_out)
        export_to_pdf(generated_html, pdf_out)

if __name__ == "__main__":
    main()
