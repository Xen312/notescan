# Local Handwritten Notes to Typed PDF Converter (`note2pdf`)

A simplified local tool that uses the **Groq Vision API** to convert handwritten lecture notes (including mathematical, physical, and chemical notations) into clean, formatted Markdown files and print-ready PDFs.

---

## Technical Pipeline Overview

```text
[Input Target File]
       │ (PDF, single JPG/PNG, or folder of image pages)
       ▼
[Input Loader]
       │ (Analyzes input and compiles page execution queue)
       ▼
[PDF Converter]
       │ (Splits PDF files into high-resolution images via PyMuPDF)
       ▼
[Groq Vision Backend]
       │ (Sends image directly to Groq Vision API. Outputs Markdown.)
       ▼
[Markdown Cleaner]
       │ (Cleans layout syntax and validates unclosed blocks)
       ▼
[PDF Renderer]
       └─► (Converts Markdown to HTML, compiles LaTeX math using MathJax,
            and exports a printable vector PDF using Playwright)"# notescan" 
