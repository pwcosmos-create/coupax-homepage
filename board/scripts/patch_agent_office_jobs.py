import os

FILE_PATH = r"C:\커셔\coupax홈페이지\board\scripts\agent_office_jobs.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# Import block to add
import_block = """
try:
    from agent_office_chief_dev_jobs import (
        job_chief_arch_review,
        job_chief_rag_crawler,
        job_chief_devops_monitor,
    )
except ImportError:
    job_chief_arch_review = lambda a: (True, "chief-dev jobs 미구현")
    job_chief_rag_crawler = lambda a: (True, "chief-dev jobs 미구현")
    job_chief_devops_monitor = lambda a: (True, "chief-dev jobs 미구현")
"""

# Dictionary entries to add
handler_entries = """
    "chief_arch_review": job_chief_arch_review,
    "chief_rag_crawler": job_chief_rag_crawler,
    "chief_devops_monitor": job_chief_devops_monitor,
"""

if "job_chief_arch_review" not in content:
    # Insert import block before JOB_HANDLERS
    content = content.replace("JOB_HANDLERS = {", import_block + "\n\nJOB_HANDLERS = {")
    
    # Insert handlers at the end of JOB_HANDLERS dictionary
    content = content.replace("}\n", handler_entries + "}\n", 1)

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(content)
print("agent_office_jobs.py patched successfully.")
