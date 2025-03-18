#!/usr/bin/env python3
"""
Script to extract error information from test logs.
"""
import os
import json
import glob
import re
import requests

def extract_pytest_errors():
    """Extract errors from pytest output."""
    errors = {}
    
    # Check if we have test logs in artifacts
    test_logs = glob.glob("artifacts/test-logs/*.log")
    if test_logs:
        for log_file in test_logs:
            with open(log_file, 'r') as f:
                content = f.read()
                parse_test_output(content, errors)
    else:
        # If no artifacts, run the tests to get fresh errors
        try:
            import subprocess
            result = subprocess.run(
                ["python", "-m", "pytest", "-v"], 
                capture_output=True, 
                text=True,
                check=False
            )
            parse_test_output(result.stdout + result.stderr, errors)
        except Exception as e:
            print(f"Error running tests: {e}")
    
    return errors

def extract_lint_errors():
    """Extract errors from pylint output."""
    errors = {}
    
    # Check if we have lint logs in artifacts
    lint_logs = glob.glob("artifacts/lint-logs/*.log")
    if lint_logs:
        for log_file in lint_logs:
            with open(log_file, 'r') as f:
                content = f.read()
                parse_lint_output(content, errors)
    else:
        # If no artifacts, run pylint to get fresh errors
        try:
            import subprocess
            result = subprocess.run(
                ["pylint", "calculator/", "tests/", "--exit-zero", "--output-format=text"], 
                capture_output=True, 
                text=True,
                check=False
            )
            parse_lint_output(result.stdout + result.stderr, errors)
        except Exception as e:
            print(f"Error running pylint: {e}")
    
    return errors

def parse_test_output(output, errors):
    """Parse pytest output to extract error information."""
    # Extract failed test information
    failed_tests = re.findall(r"(FAILED\s+[^\n]+)", output)
    error_messages = re.findall(r"E\s+([^\n]+)", output)
    
    # Extract file paths from error messages
    file_pattern = re.compile(r'([a-zA-Z0-9_/]+\.py)')
    
    for test in failed_tests:
        file_matches = file_pattern.findall(test)
        for file_path in file_matches:
            if file_path not in errors:
                errors[file_path] = []
            errors[file_path].append(f"Test failure: {test}")
    
    return errors

def parse_lint_output(output, errors):
    """Parse pylint output to extract error information."""
    # Match pylint error lines like: "calculator/calculator.py:5:0: W0611: Unused import random (unused-import)"
    lint_errors = re.findall(r'([^:]+):(\d+):(\d+): ([A-Z]\d+): (.+)', output)
    
    for match in lint_errors:
        file_path, line, col, code, message = match
        if file_path not in errors:
            errors[file_path] = []
        errors[file_path].append(f"Lint error {code} at {file_path}:{line}: {message}")
    
    return errors

def main():
    """Main function to extract and output errors."""
    # Combine test and lint errors
    all_errors = {}
    all_errors.update(extract_lint_errors())
    all_errors.update(extract_test_errors())
    
    # Output errors for use in GitHub Actions
    error_details = []
    for file_path, file_errors in all_errors.items():
        error_details.append(f"File: {file_path}")
        for error in file_errors:
            error_details.append(f"  - {error}")
    
    error_output = "\n".join(error_details)
    
    # Set GitHub Actions output
    with open(os.environ.get("GITHUB_OUTPUT", "output.txt"), "a") as f:
        f.write(f"error_details<<EOF\n{error_output}\nEOF\n")
    
    # Also set as environment variable
    with open(os.environ.get("GITHUB_ENV", "env.txt"), "a") as f:
        f.write(f"ERROR_FILES={json.dumps(list(all_errors.keys()))}\n")
    
    # Print for debugging
    print(f"Found errors in {len(all_errors)} files.")
    print(error_output)
    
    return all_errors

if __name__ == "__main__":
    main()