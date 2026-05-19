import os
import re
import json
import time
from groq import Groq
from app.core.config import settings

# ---------------------------------------------------------------------------
# File filtering configuration
# ---------------------------------------------------------------------------

# Extensions for FULL LLM analysis (actual source code)
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java",
    ".go", ".rb", ".php", ".cs", ".cpp", ".c", ".h",
}

# Extensions / filenames for PATTERN-BASED scanning only (config / secrets)
# These are NOT sent to the LLM — they consume quota without adding much value
# since the regex scanner already handles them very well.
CONFIG_EXTENSIONS = {
    ".cfg", ".config", ".ini",
    ".yaml", ".yml", ".toml", ".properties",
}

# Filenames (exact basename) that are always pattern-scanned
SENSITIVE_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.staging",
    ".env.test",
}

# Directories to skip while walking the repo
EXCLUDED_DIRS = {
    ".git", "node_modules", "build", "dist",
    "__pycache__", ".venv", "venv",
    # NOTE: ".env" is intentionally NOT here — it is a file, not a directory.
}

MAX_CHUNK_SIZE = 3500   # characters per LLM call
GROQ_MODEL = "llama-3.3-70b-versatile"

# Seconds to wait between LLM calls to avoid Groq rate-limiting
LLM_CALL_DELAY = 0.5

# ---------------------------------------------------------------------------
# Regex patterns for deterministic secret detection
# ---------------------------------------------------------------------------

SECRET_PATTERNS = [
    (r'(?i)(password|passwd|pwd)\s*[=:]\s*(?!your[_-]|placeholder|changeme|example|<|xxx)(\S+)',
     "Hardcoded password detected"),
    (r'(?i)(secret[_-]?key|secret)\s*[=:]\s*(?!your[_-]|placeholder|changeme|example|<|xxx)(\S+)',
     "Hardcoded secret key detected"),
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*(?!your[_-]|placeholder|changeme|example|<|xxx)(\S+)',
     "Hardcoded API key detected"),
    (r'(?i)(access[_-]?token|auth[_-]?token|token)\s*[=:]\s*(?!your[_-]|placeholder|changeme|example|<|xxx)(\S+)',
     "Hardcoded token detected"),
    (r'(?i)(database[_-]?url|db[_-]?url|connection[_-]?string)\s*[=:]\s*(postgres|mysql|mongodb|redis|sqlite)\S+',
     "Database connection string with credentials"),
    (r'AKIA[0-9A-Z]{16}', "Hardcoded AWS Access Key ID"),
    (r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*\S+', "Hardcoded AWS Secret Access Key"),
    (r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', "Private key material found in source"),
    (r'(?i)(password|secret|token|key)\s*=\s*["\'](?!your[_-]|placeholder|changeme|example|<)(.{6,})["\']',
     "Hardcoded credential in source code"),
    (r'https?://[^:@\s]+:[^@\s]+@', "URL with embedded credentials"),
]


def detect_secrets_by_pattern(filename: str, content: str) -> list[dict]:
    """
    Deterministic regex-based secret scanner.
    Runs on ALL files (source code + config/env files).
    Returns a list of issue dicts.
    """
    issues = []
    lines = content.splitlines()

    for line_num, line in enumerate(lines, start=1):
        for pattern, description in SECRET_PATTERNS:
            if re.search(pattern, line):
                issues.append({
                    "file": filename,
                    "line": line_num,
                    "severity": "High",
                    "description": f"{description} (line {line_num})",
                    "fix": (
                        "Remove the hardcoded credential from source code. "
                        "Use environment variables or a secrets manager (e.g., AWS Secrets Manager, "
                        "HashiCorp Vault, or a .env file that is listed in .gitignore) instead."
                    ),
                })
                break  # One issue per line is enough

    return issues


# ---------------------------------------------------------------------------
# File collection — clearly separates code files from config files
# ---------------------------------------------------------------------------

def filter_files(repo_path: str) -> tuple[list[dict], list[dict]]:
    """
    Walk repo and return two separate lists:
    - code_files: sent to the LLM for deep analysis
    - config_files: pattern-scanned only (env, yaml, ini, etc.)
    """
    code_files: list[dict] = []
    config_files: list[dict] = []
    seen: set[str] = set()

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for fname in files:
            full_path = os.path.join(root, fname)
            if full_path in seen:
                continue
            seen.add(full_path)

            ext = os.path.splitext(fname)[1].lower()
            basename = fname.lower()
            rel_path = os.path.relpath(full_path, repo_path)
            entry = {"path": full_path, "rel": rel_path}

            if ext in CODE_EXTENSIONS:
                code_files.append(entry)
            elif ext in CONFIG_EXTENSIONS or basename in SENSITIVE_FILENAMES:
                config_files.append(entry)

    return code_files, config_files


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_file(content: str, max_size: int = MAX_CHUNK_SIZE) -> list[str]:
    """Split file content into chunks that fit within LLM token limit."""
    lines = content.splitlines(keepends=True)
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0

    for line in lines:
        if current_size + len(line) > max_size and current:
            chunks.append("".join(current))
            current = []
            current_size = 0
        current.append(line)
        current_size += len(line)

    if current:
        chunks.append("".join(current))

    return chunks if chunks else [""]


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior software engineer and security expert performing a thorough code review.
Analyze the provided code and identify ALL issues including:

SECURITY (highest priority):
- Hardcoded secrets: passwords, API keys, tokens, private keys, OAuth secrets, JWT secrets
- SQL injection, XSS, CSRF, command injection, path traversal
- Insecure use of cryptography (MD5, SHA1, weak keys, no hashing for passwords)
- Missing authentication or authorization checks
- Insecure direct object references
- Sensitive data exposed in logs or error messages
- Use of deprecated or vulnerable dependencies/functions

CODE QUALITY & BUGS:
- Logic bugs and off-by-one errors
- Unhandled exceptions or missing error handling
- Race conditions or concurrency issues
- Memory leaks or resource leaks (unclosed files, connections)
- Code smells, duplication, poor naming
- Performance anti-patterns (N+1 queries, inefficient loops)
- Missing input validation

Respond ONLY with a valid JSON array. Each item must have exactly these fields:
{
  "file": "<filename>",
  "line": <integer line number>,
  "severity": "High" | "Medium" | "Low",
  "description": "<clear description of the issue>",
  "fix": "<specific actionable fix suggestion>"
}

Severity guide:
- High: credentials, injection vulnerabilities, authentication bypass, data exposure
- Medium: missing validation, improper error handling, insecure patterns
- Low: code quality, style, minor performance issues

If no issues are found, return an empty array: []
Do not include any explanations or markdown outside the JSON array."""


# ---------------------------------------------------------------------------
# LLM analysis — with retry and backoff for rate limits
# ---------------------------------------------------------------------------

def analyze_chunk(filename: str, chunk: str, start_line: int, client: Groq,
                  retries: int = 3) -> list[dict]:
    """Send one code chunk to Groq and parse the response. Retries on rate limit."""
    user_message = f"File: {filename}\nStarting at line: {start_line}\n\n```\n{chunk}\n```"

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,
                max_tokens=2048,
            )

            raw = response.choices[0].message.content.strip()

            # Extract JSON array from response (handles markdown code blocks)
            json_match = re.search(r'\[.*\]', raw, re.DOTALL)
            if not json_match:
                print(f"[LLM] No JSON array found in response for {filename}")
                return []

            issues = json.loads(json_match.group())
            if not isinstance(issues, list):
                return []

            # Normalize fields
            normalized = []
            for item in issues:
                if not isinstance(item, dict):
                    continue
                normalized.append({
                    "file": item.get("file", filename),
                    "line": (int(item.get("line", start_line))
                             if str(item.get("line", "")).isdigit()
                             else start_line),
                    "severity": (item.get("severity", "Medium")
                                 if item.get("severity") in ("High", "Medium", "Low")
                                 else "Medium"),
                    "description": str(item.get("description", "Issue detected")),
                    "fix": str(item.get("fix", "Review this code section")),
                })
            return normalized

        except Exception as e:
            err_str = str(e).lower()
            if "rate" in err_str or "429" in err_str or "limit" in err_str:
                wait = 5 * (attempt + 1)   # 5s, 10s, 15s
                print(f"[LLM] Rate limit hit for {filename}, waiting {wait}s (attempt {attempt + 1}/{retries})")
                time.sleep(wait)
            else:
                print(f"[LLM] Error analyzing chunk from {filename}: {e}")
                return []

    print(f"[LLM] Giving up on {filename} after {retries} retries")
    return []


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_llm_analysis(repo_path: str) -> tuple[dict, list[dict]]:
    """
    Main entry point:
    1. Collect two sets of files: code files (LLM) and config/env files (pattern only)
    2. Pattern-scan ALL files for hardcoded secrets
    3. LLM-analyse only SOURCE CODE files for deep bug/security review
    4. Deduplicate and aggregate results
    """
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set. Please add it to your .env file.")

    client = Groq(api_key=api_key)

    code_files, config_files = filter_files(repo_path)
    all_files = code_files + config_files
    all_issues: list[dict] = []

    print(f"[Scanner] Found {len(code_files)} source files and {len(config_files)} config/env files")

    # --- Step 1: Pattern-based secret scan on ALL files ---
    for file_info in all_files:
        try:
            with open(file_info["path"], "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue

        if not content.strip():
            continue

        file_info["_content"] = content   # cache so we don't re-read below
        pattern_issues = detect_secrets_by_pattern(file_info["rel"], content)
        if pattern_issues:
            print(f"[Pattern] {file_info['rel']}: {len(pattern_issues)} issue(s)")
        all_issues.extend(pattern_issues)

    # --- Step 2: LLM deep analysis on SOURCE CODE files only ---
    for file_info in code_files:
        rel_path = file_info["rel"]
        content = file_info.get("_content")

        if content is None:
            try:
                with open(file_info["path"], "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

        if not content.strip():
            continue

        chunks = chunk_file(content)
        line_offset = 1
        file_issue_count = 0

        for chunk in chunks:
            # Small delay between calls to stay under Groq's rate limit
            time.sleep(LLM_CALL_DELAY)

            llm_issues = analyze_chunk(rel_path, chunk, line_offset, client)
            all_issues.extend(llm_issues)
            file_issue_count += len(llm_issues)
            line_offset += chunk.count("\n") + 1

        print(f"[LLM] {rel_path}: {file_issue_count} issue(s)")

    # --- Step 3: Deduplicate ---
    seen_keys: set[tuple] = set()
    deduplicated: list[dict] = []
    for issue in all_issues:
        key = (issue["file"], issue["line"], issue["severity"])
        if key not in seen_keys:
            seen_keys.add(key)
            deduplicated.append(issue)

    # --- Step 4: Build summary ---
    high = sum(1 for i in deduplicated if i["severity"] == "High")
    medium = sum(1 for i in deduplicated if i["severity"] == "Medium")
    low = sum(1 for i in deduplicated if i["severity"] == "Low")

    summary = {
        "total_issues": len(deduplicated),
        "high": high,
        "medium": medium,
        "low": low,
        "files_scanned": len(all_files),
    }

    print(f"[Scanner] Done. {len(deduplicated)} total issues ({high} High, {medium} Medium, {low} Low)")

    return summary, deduplicated
