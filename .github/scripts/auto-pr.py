import os
import subprocess
import re
from textwrap import dedent

# Paths to log files (created by the GitHub Action steps)
LOG_FILES = {
    "pytest": "pytest.log",
    "flake8": "flake8.log",
    "pylint": "pylint.log"
}

# Collect errors and warnings from logs
error_summary = {}
for tool, log_path in LOG_FILES.items():
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            log_content = f.read()
        # Filter relevant lines
        if tool == "pytest":
            # Capture summary of failures and first lines of error messages
            failed_tests = re.findall(r"=+ FAILURES =+\\n(.*?)(?==+)", log_content, re.S)
            # If any failures, take a snippet of each
            if failed_tests:
                error_summary['pytest'] = "Failures:\n" + "\n\n".join(
                    [failed_tests[0][:500]]  # include first 500 chars of first failure (truncate if long)
                )
                # Note: Could capture multiple failures if needed
        elif tool == "flake8":
            # Collect flake8 error lines
            issues = [line for line in log_content.splitlines() if line.strip() and not line.startswith("==")]
            if issues:
                error_summary['flake8'] = "\n".join(issues[:20])  # include at most 20 issues to avoid huge output
        elif tool == "pylint":
            # Collect Pylint warnings/errors (skip summary footer)
            lines = [l for l in log_content.splitlines() if l.strip() and not l.startswith(("********", "Your code", "pylint"))]
            if lines:
                error_summary['pylint'] = "\n".join(lines[:20])  # include first 20 lines of pylint output

# If nothing to fix (no errors collected), exit
if not error_summary:
    print("No errors to fix detected. Exiting.")
    exit(0)

# 1. Apply automatic fixes to the codebase
# a) Use autopep8 to fix formatting issues (PEP8 style errors) across the repository
subprocess.run(["autopep8", "--in-place", "--aggressive", "--aggressive", "--recursive", "."], check=False)
# b) Use autoflake to remove unused imports and variables (safe removal)
subprocess.run(["autoflake", "--in-place", "--remove-all-unused-imports", "--remove-unused-variables", "--recursive", "."], check=False)

# (Optional) You could run isort or black as additional formatters if desired:
# subprocess.run(["isort", "."], check=False)
# subprocess.run(["black", "."], check=False)

# 2. Configure git identity for the bot commit
bot_name = os.getenv("GITHUB_ACTOR", "ci-bot")
subprocess.run(["git", "config", "--local", "user.name", bot_name], check=True)
subprocess.run(["git", "config", "--local", "user.email", f"{bot_name}@users.noreply.github.com"], check=True)

# 3. Create a new branch for the fixes
branch_name = "ci-fix-auto-{0}".format(os.getenv("GITHUB_RUN_ID", "1"))
subprocess.run(["git", "checkout", "-b", branch_name], check=True)

# 4. Commit the changes (if any)
subprocess.run(["git", "add", "-A"], check=True)
# Use a generic commit message, include [skip ci] to avoid re-running CI on the fix branch
commit_msg = "Auto-fix CI issues [skip ci]"
result = subprocess.run(["git", "diff", "--cached", "--quiet"])
if result.returncode != 0:  # there are changes staged
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
else:
    print("No changes to commit after auto-fix. Exiting.")
    # Nothing changed by autopep8/autoflake, so exit to avoid creating an empty PR
    exit(0)

# 5. Push the new branch to origin
repo = os.getenv("GITHUB_REPOSITORY")  # e.g. user/repo
if repo:
    remote_branch = f"origin {branch_name}"
else:
    remote_branch = branch_name
subprocess.run(["git", "push", "origin", branch_name], check=True)

# 6. Assemble the PR title and body
pr_title = "🤖 Auto-fix for failing CI on main"
pr_body = "# Automated fixes for CI failures\n"
pr_body += "This PR was created automatically because CI on `main` failed. The following issues were identified and fixed:\n\n"
for tool, summary in error_summary.items():
    pr_body += f"## {tool.capitalize()} Output:\n```\n{summary}\n```\n\n"
pr_body += "_*Logs have been truncated for brevity. Please review the changes and merge if they look correct.*_"

# 7. Create a Pull Request using GitHub CLI
subprocess.run([
    "gh", "pr", "create",
    "--title", pr_title,
    "--body", pr_body,
    "--head", branch_name,
    "--base", "main",
    "--label", "ci-fix",
    "--assignee", "@me",   # assign to the person who triggered or maintainers can adjust
    "--draft"             # create as a draft PR to avoid auto-merging
], check=True)
