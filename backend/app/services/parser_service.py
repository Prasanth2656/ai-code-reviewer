def extract_repo_info(repo_url: str):
    parts = repo_url.rstrip("/").split("/")
    developer = parts[-2]
    repository = parts[-1]
    return developer, repository