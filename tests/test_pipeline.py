# test_pipeline.py
from utils.configs import Exa_API, Groq_API, Gemini_API
from utils.system_prompts import Info_Refiner_Prompt, Report_Generator_Prompt
from agents.web_extractor import main_we
from agents.info_refiner import main_ir
from agents.report_generator import main_rg

q = "How AI Works?"
print("→ Web...")
content, sources = main_we(q, Exa_API)
print(f"→ {len(sources)} sources")

print("→ Refine...")
refined = main_ir(content, q, Info_Refiner_Prompt, Groq_API)

print("→ Report...")
report = main_rg(Gemini_API, refined, Report_Generator_Prompt, q, sources)
print(report)