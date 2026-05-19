from app.services.llm_service import run_llm_analysis

def analyze_repository(repo_path: str):
    """Run real AI-powered analysis on the cloned repository."""
    return run_llm_analysis(repo_path)