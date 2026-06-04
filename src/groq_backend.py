import base64
import logging
import time
from pathlib import Path
from groq import Groq
from src.config import Config

logger = logging.getLogger("Note2PDF.GroqBackend")

SYSTEM_PROMPT = """You are an expert academic transcriptionist and document compiler.
Convert the provided handwritten note page image into clean, highly readable, structured Markdown.

Analyze the image closely and follow these strict rules:
1. STRUCTURE:
   - Identify and organize headings using proper levels (#, ##, ###).
   - Format bullet lists (-), numbered lists (1.), and blockquotes cleanly.
   - Maintain structural order, indentation, and paragraph divisions.

2. ACADEMIC SYMBOLS & NOTATIONS:
   - MATHEMATICS: Output standard LaTeX for mathematical expressions. Use double dollar signs ($$) for block equations, and single dollar signs ($) for inline equations. Handle integrals, differentials, limits, matrices, vectors, summations, and derivations precisely.
   - PHYSICS: Keep symbols, units, exponents, and derivation workflows consistent and clear.
   - CHEMISTRY: Use proper LaTeX syntax or clean chemical formulas for compounds, reactions, symbols, subscripts/superscripts, and charges.
   - COMPUTER SCIENCE: Write code snippets or pseudocode block outputs in appropriate markdown code fences (e.g., ```python) and preserve indentation.

3. DIAGRAMS, FLOWCHARTS & DRAWINGS:
   - If you detect any hand-drawn diagrams, flowcharts, block diagrams, sequence charts, or structural hierarchies, transcribe them into standard **Mermaid.js** syntax enclosed in a markdown code fence starting with ```mermaid.
   - **CRITICAL MERMAID RULE**: Do NOT use LaTeX math delimiters (like `$`) or LaTeX backslashes (like `\\lambda`) inside Mermaid nodes or edge labels. Instead, use simple plain text and standard Unicode characters (such as `λ` instead of `\\lambda`, `t1` instead of `t_1`, `t - t1` instead of `t - t_1`). This is because the Mermaid parser does not support LaTeX and will crash if it encounters raw LaTeX inside diagrams. Keep all diagram text simple and clean.
   - Always wrap node labels and edge labels inside double quotes `""` to prevent parsing crashes.
     - For example:
       ```mermaid
       graph TD
           A["Start"] --> B{{"Inventory Level"}}
           B -->| "Demand Rate λ" | C["Inventory Depletion"]
       ```
   - For simple geometric illustrations or plots, represent them as raw inline **SVG** elements where practical.
   - For highly complex sketches that cannot be converted to code, write a clear, structured text description wrapped inside a blockquote (e.g. `> [Diagram: <detailed description>]`).

4. DATA TABLES:
   - Convert structural grid/table lists into standard Markdown tables.

5. HANDWRITING INTERPRETATION & HONESTY:
   - Do NOT invent, summarize, rewrite, or paraphrase text or equations if they are not present.
   - Do NOT try to fill in blank or erased areas.
   - If a word, symbol, or equation is completely illegible or cut off, output the placeholder label: "[unclear]".
   - Do not include conversational remarks, pleasantries, or preamble blocks. Return ONLY the converted Markdown.
"""

class GroqBackend:
    def __init__(self):
        if not Config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing from the configuration (.env file).")
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        self.model_name = Config.GROQ_VISION_MODEL
        logger.info(f"Initialized Groq Vision Backend (Model: {self.model_name})")

    def extract_markdown(self, image_path: Path) -> str:
        """Encodes the image to Base64 and transcribes it via the Groq Vision model with robust retries."""
        logger.info(f"Preparing image for Groq Vision: {image_path.name}")
        
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            raise IOError(f"Could not read image file {image_path.name}: {e}")

        ext = image_path.suffix.lower()
        mime_type = "image/png" if ext == ".png" else "image/jpeg"

        max_retries = 3
        retry_delay = 5  # Base delay in seconds

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Sending vision request to Groq (Attempt {attempt}/{max_retries})...")
                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text", 
                                    "text": SYSTEM_PROMPT
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=0.1,
                    max_tokens=4096
                )
                output = completion.choices[0].message.content
                return output if output else ""
            except Exception as e:
                logger.warning(f"Groq API call failed on attempt {attempt}: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("All retry attempts to Groq Vision API have been exhausted.")
                    raise RuntimeError(f"Groq Vision API execution failed: {e}")