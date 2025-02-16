import os
import openai
import subprocess
import re
from textwrap import dedent

# Load OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_OPENAI = bool(OPENAI_API_KEY)  # Only use AI if API key is available

# Define log file paths
LOG_FILES = {
    "pytest": "pytest.log",
    "flake8": "flake8.log",
    "pylint": "pylint.log"
}

# Parse logs to extract error summaries
def extract_errors():
    error_summary = {}

    for tool, log_path in LOG_FILES.items():
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                log_content = f.read()

            if tool == "pytest":
                failed_tests = re.findall(r"=+ FAILURES =+\\n(.*?)(?==+)", log_content, re.S)
                if failed_tests:
                    error_summary['pytest'] = "Failures:\n" + failed_tests[0][:500]

            elif tool in ["flake8", "pylint"]:
                issues = [line for line in log_content.splitlines() if line.strip()]
                if issues:
                    error_summary[tool] = "\n".join(issues[:20])  # Limit to 20 errors

    return error_summary

# Submit logs + code to OpenAI for fixes
def get_openai_fix(error_summary):
    if not USE_OPENAI:
        return None

    # Prepare request payload
    logs = "\n\n".join([f"{tool}:\n{summary}" for tool, summary in error_summary.items()])
    prompt = dedent(f"""
    You are an AI that reviews Python CI/CD failures and suggests code fixes.
    Here are logs from pytest, flake8, and pylint:
    
    {logs}

    Provide fixes for the detected issues. Return only modified code snippets.
    """)

    # OpenAI API call
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )

    return response["choices"][0]["message"]["content"]

# Apply AI fixes
def apply_fixes(ai_fixes):
    if not ai_fixes:
        return

    # Apply fixes (write directly to affected files)
    for fix in ai_fixes.split("\n\n"):
        if "```python" in fix:
            fix = fix.split("```python")[1].split("```")[0].strip()

        file_path = fix.split("\n")[0].strip()  # Extract filename from first line
        modified_code = "\n".join(fix.split("\n")[1:])  # Remove filename

        # Write fixes to file
        with open(file_path, "w") as f:
            f.write(modified_code)

# Commit & create PR
def create_pr(error_summary):
    bot_name = os.getenv("GITHUB_ACTOR", "ci-bot")
    branch_name = f"ci-fix-auto-{os.getenv('GITHUB_RUN_ID', '1')}"

    # Configure git identity
    subprocess.run(["git", "config", "--local", "user.name", bot_name], check=True)
    subprocess.run(["git", "config", "--local", "user.email", f"{bot_name}@users.noreply.github.com"], check=True)

    # Create new branch
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)
    subprocess.run(["git", "add", "-A"], check=True)

    # **Check if there are any changes to commit**
    status = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if status.returncode == 0:
        print("No changes detected. Exiting without creating a PR.")
        exit(0)  # Exit script without error if no changes

    # Commit changes if they exist
    subprocess.run(["git", "commit", "-m", "Auto-fix CI issues [skip ci]"], check=True)
    subprocess.run(["git", "push", "origin", branch_name], check=True)

    # Assemble PR content
    pr_title = "🤖 Auto-fix for failing CI on main"
    pr_body = "## Automated Fixes for CI Failures\n"
    for tool, summary in error_summary.items():
        pr_body += f"### {tool.capitalize()} Output:\n```\n{summary}\n```\n\n"
    pr_body += "**Fixes generated automatically based on CI/CD logs. Please review before merging.**"

    # Create PR
    subprocess.run([
        "gh", "pr", "create",
        "--title", pr_title,
        "--body", pr_body,
        "--head", branch_name,
        "--base", "main",
        "--label", "ci-fix",
        "--assignee", "@me",
        "--draft"
    ], check=True)
