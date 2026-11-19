import helps
import os

pdf_paths = ["pdfs/AI-Humans.pdf", "pdfs/top_50_ai_tools.pdf"]
paths = [p for p in pdf_paths if os.path.exists(p)]

if paths:
    print(f"Building KB from {paths}...")
    helps.build_kb_from_paths(paths, chunk_mode="sliding", chunk_size=200, chunk_overlap=50)
    print("KB built successfully.")
else:
    print("No PDFs found to build KB.")
