import re
import logging

logger = logging.getLogger("Note2PDF.MarkdownCleaner")

class MarkdownCleaner:
    @staticmethod
    def run(raw_text: str) -> str:
        """Cleans syntax boundaries, balances unclosed code blocks, and normalizes LaTeX math notations."""
        if not raw_text:
            return ""

        cleaned = raw_text.strip()

        # 1. Strip surrounding markdown code block markers if the LLM wrapped its entire response
        cleaned = re.sub(r"^```markdown\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned)
        cleaned = cleaned.strip()

        # 2. Balance unclosed code blocks to prevent layout leakage across page boundaries
        # Count '```' occurrences. An odd count means a code block was left open.
        backtick_count = cleaned.count("```")
        if backtick_count % 2 != 0:
            logger.warning(
                "Detected unclosed code block in page extraction. "
                "Appending closing backticks to preserve Markdown validity."
            )
            cleaned += "\n```"

        # 3. Unify bracketed math delimiters to standard LaTeX $ tags
        cleaned = re.sub(r"\\\[", "$$", cleaned)
        cleaned = re.sub(r"\\\]", "$$", cleaned)
        cleaned = re.sub(r"\\\(", "$", cleaned)
        cleaned = re.sub(r"\\\)", "$", cleaned)

        # 4. Standardize spacing
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        logger.debug("Markdown cleaning and normalization completed.")
        return cleaned