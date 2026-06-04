import re
import logging
from pathlib import Path
import markdown
from playwright.sync_api import sync_playwright

logger = logging.getLogger("Note2PDF.Renderer")

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Processed Academic Notes</title>
  
  <!-- MathJax Configuration for LaTeX Rendering -->
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['$', '$'], ['\\(', '\\)']],
        displayMath: [['$$', '$$'], ['\\[', '\\]']],
        processEscapes: true,
        processEnvironments: true
      }},
      options: {{
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
      }},
      svg: {{ fontCache: 'global' }}
    }};
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

  <!-- Highlight.js for Syntax Highlighting -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.8.0/styles/github.min.css">
  <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.8.0/highlight.min.js"></script>
  <script>hljs.highlightAll();</script>

  <!-- Load Mermaid.js for Diagram Rendering -->
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    document.addEventListener("DOMContentLoaded", function() {{
      // Initialize Mermaid with loose security to allow math and HTML rendering in SVG labels
      mermaid.initialize({{ 
        startOnLoad: true, 
        theme: 'default',
        securityLevel: 'loose'
      }});
      
      // Give Mermaid a brief moment to compile the visual SVG diagrams,
      // then trigger MathJax to parse and typeset the LaTeX formulas inside the SVG nodes!
      setTimeout(function() {{
        if (window.MathJax && window.MathJax.typesetPromise) {{
          window.MathJax.typesetPromise();
        }}
      }}, 1000);
    }});
  </script>

  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 820px;
      margin: 0 auto;
      padding: 30px;
    }}
    h1, h2, h3, h4 {{
      color: #111;
      font-weight: 600;
      margin-top: 1.5em;
      margin-bottom: 0.5em;
      page-break-after: avoid;
    }}
    h1 {{
      font-size: 2em;
      border-bottom: 2px solid #eaecef;
      padding-bottom: 0.3em;
    }}
    h2 {{
      font-size: 1.5em;
      border-bottom: 1px solid #eaecef;
      padding-bottom: 0.3em;
    }}
    p {{
      margin-top: 0;
      margin-bottom: 1em;
    }}
    code {{
      font-family: Consolas, "Liberation Mono", Menlo, Courier, monospace;
      background-color: rgba(27, 31, 35, 0.05);
      padding: 0.2em 0.4em;
      border-radius: 3px;
      font-size: 85%;
    }}
    pre {{
      background-color: #f6f8fa;
      padding: 16px;
      border-radius: 6px;
      overflow-x: auto;
    }}
    pre code {{
      background-color: transparent;
      padding: 0;
      font-size: 90%;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin-bottom: 1.5em;
    }}
    th, td {{
      padding: 8px 12px;
      border: 1px solid #dfe2e5;
    }}
    th {{
      background-color: #f6f8fa;
      font-weight: 600;
    }}
    tr:nth-child(even) {{
      background-color: #f8f9fa;
    }}
    blockquote {{
      margin: 0 0 1em 0;
      padding: 0 1em;
      color: #6a737d;
      border-left: 0.25em solid #dfe2e5;
    }}
    .mermaid {{
      display: flex;
      justify-content: center;
      margin: 20px 0;
    }}
    .page-break {{
      page-break-before: always;
    }}
    @media print {{
      body {{
        padding: 0;
        font-size: 11pt;
      }}
      pre {{
        background-color: #f6f8fa !important;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }}
    }}
  </style>
</head>
<body>
  {body_content}
</body>
</html>
"""

class PDFRenderer:
    @staticmethod
    def _preprocess_mermaid(md_text: str) -> str:
        """Finds all fenced markdown code blocks for mermaid, sanitizes math delimiters, and escapes backslashes."""
        pattern = re.compile(r"```mermaid\s*\n([\s\S]*?)\n```", re.IGNORECASE)
        
        def replace_block(match):
            content = match.group(1)
            
            # Helper to clean math/LaTeX delimiters out of Mermaid labels to prevent parser crashes
            def clean_label_text(label: str) -> str:
                # Remove dollar signs
                label = label.replace("$", "")
                # Replace common Greek letters with Unicode equivalents
                label = label.replace("\\lambda", "λ")
                label = label.replace("\\alpha", "α")
                label = label.replace("\\beta", "β")
                label = label.replace("\\theta", "θ")
                label = label.replace("\\pi", "π")
                label = label.replace("\\sigma", "σ")
                label = label.replace("\\omega", "ω")
                label = label.replace("\\delta", "δ")
                label = label.replace("\\epsilon", "ε")
                label = label.replace("\\gamma", "γ")
                # Remove any leftover backslashes
                label = label.replace("\\", "")
                return label.strip()
            
            # Failsafe 1: Convert unquoted edge labels inside pipes |...| into standard quoted connections
            # Matches standard connection arrows (e.g., -->, ---, ==>, -.->)
            edge_pattern = re.compile(r"([\-\.\=\>]+)\|([^\"\|\n\r]+)\|")
            
            def escape_edge_label(edge_match):
                arrow = edge_match.group(1).strip()
                label = edge_match.group(2)
                cleaned_label = clean_label_text(label)
                
                # Safely translate raw connection syntax to Mermaid's standard quoted edge label format
                if arrow == "-->":
                    return f'-- "{cleaned_label}" -->'
                elif arrow == "==>":
                    return f'== "{cleaned_label}" ==>'
                elif arrow == "-.->":
                    return f'-. "{cleaned_label}" .->'
                else:
                    return f'-- "{cleaned_label}" -->'
                
            fixed_content = edge_pattern.sub(escape_edge_label, content)
            
            # Failsafe 2: Auto-wrap ALL unquoted node labels inside double quotes and clean them
            # Matches square brackets [] and round parentheses () to prevent syntax errors
            node_pattern = re.compile(r"([a-zA-Z0-9_\-]+)([\[\(])([^\"\]\)\n\r]+)([\]\)])")
            
            def escape_node_label(node_match):
                node_id = node_match.group(1)
                open_shape = node_match.group(2)
                label = node_match.group(3)
                close_shape = node_match.group(4)
                cleaned_label = clean_label_text(label)
                return f'{node_id}{open_shape}"{cleaned_label}"{close_shape}'
                
            fixed_content = node_pattern.sub(escape_node_label, fixed_content)
            
            # Inject local Mermaid configuration block to force loose HTML and default themes
            config_header = "%%{init: {'theme': 'default', 'securityLevel': 'loose'}}%%\n"
            if not fixed_content.strip().startswith("%%"):
                fixed_content = config_header + fixed_content
                
            # Direct CLI Print block for real-time validation
            print(f"\n--- DEBUG: PREPROCESSED MERMAID DIAGRAM ---\n{fixed_content}\n-------------------------------------------\n")
            logger.info(f"Preprocessed Mermaid Block:\n{fixed_content}")
            
            return f'<div class="mermaid">\n{fixed_content}\n</div>'
            
        return pattern.sub(replace_block, md_text)

    @staticmethod
    def build(markdown_text: str, output_pdf_path: Path, temp_dir: Path) -> None:
        """Converts Markdown containing MathJax LaTeX formulas and Mermaid diagrams into a styled PDF file."""
        logger.info("Preprocessing Mermaid diagram fences in Markdown...")
        preprocessed_md = PDFRenderer._preprocess_mermaid(markdown_text)
        
        logger.info("Converting Markdown contents into HTML...")
        body_html = markdown.markdown(
            preprocessed_md,
            extensions=['extra', 'codehilite', 'tables', 'fenced_code']
        )
        
        # Double escaped format matches correctly on template dictionary replace
        final_html = HTML_TEMPLATE.format(body_content=body_html)
        
        temp_html_file = temp_dir / "index.html"
        temp_html_file.write_text(final_html, encoding="utf-8")
        logger.debug(f"Saved temporary HTML compilation wrapper to: {temp_html_file.name}")

        logger.info("Initializing Playwright background renderer...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"file:///{temp_html_file.resolve().as_posix()}")
                
                # Allow CDN assets for MathJax, HighlightJS, and Mermaid to finish loading and rendering
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3500)  # Safe delay buffer for rendering complex math equations and diagrams
                
                page.pdf(
                    path=str(output_pdf_path),
                    format="A4",
                    print_background=True,
                    margin={
                        "top": "20mm",
                        "bottom": "20mm",
                        "left": "20mm",
                        "right": "20mm"
                    }
                )
                browser.close()
                
            logger.info(f"Successfully generated PDF file output: {output_pdf_path.name}")
        except Exception as e:
            logger.error(f"Playwright failed to render document output: {e}")
            raise RuntimeError(f"Could not render final PDF layout: {e}")