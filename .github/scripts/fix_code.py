#!/usr/bin/env python3
"""
Script to fix code issues using OpenAI.
"""
import os
import json
import re
import subprocess
import requests

def get_file_content(file_path):
    """Read and return file content."""
    with open(file_path, 'r') as f:
        return f.read()

def write_file_content(file_path, content):
    """Write content to file."""
    with open(file_path, 'w') as f:
        f.write(content)

def get_file_type(file_path):
    """Determine file type based on extension."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ['.py']:
        return 'Python'
    elif ext in ['.js', '.jsx', '.ts', '.tsx']:
        return 'JavaScript/TypeScript'
    elif ext in ['.java']:
        return 'Java'
    elif ext in ['.rb']:
        return 'Ruby'
    elif ext in ['.go']:
        return 'Go'
    elif ext in ['.php']:
        return 'PHP'
    elif ext in ['.c', '.cpp', '.h', '.hpp']:
        return 'C/C++'
    elif ext in ['.cs']:
        return 'C#'
    elif ext in ['.html', '.htm']:
        return 'HTML'
    elif ext in ['.css', '.scss', '.sass', '.less']:
        return 'CSS'
    else:
        return 'Unknown'

def get_errors_for_file(file_path):
    """Extract errors for a specific file from environment variables."""
    try:
        # Run pylint and pytest to get errors for this file
        lint_errors = run_lint_for_file(file_path)
        test_errors = run_tests_for_file(file_path)
        
        all_errors = lint_errors + test_errors
        return all_errors
    except Exception as e:
        print(f"Error getting errors for {file_path}: {e}")
        return []

def run_lint_for_file(file_path):
    """Run linting for a specific file and return errors."""
    errors = []
    try:
        result = subprocess.run(
            ["pylint", file_path, "--exit-zero", "--output-format=text"], 
            capture_output=True, 
            text=True,
            check=False
        )
        
        # Parse pylint output
        lint_errors = re.findall(r'([^:]+):(\d+):(\d+): ([A-Z]\d+): (.+)', result.stdout)
        for match in lint_errors:
            _, line, col, code, message = match
            errors.append(f"Lint error {code} at line {line}: {message}")
    except Exception as e:
        print(f"Error running pylint for {file_path}: {e}")
    
    return errors

def run_tests_for_file(file_path):
    """Run tests that might be affected by this file and return errors."""
    errors = []
    try:
        # Determine if this is a module file or test file
        is_test_file = 'test_' in os.path.basename(file_path) or '/tests/' in file_path
        
        if is_test_file:
            # If it's a test file, just run that test
            test_path = file_path
        else:
            # If it's a module file, try to find corresponding test files
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            test_path = f"tests/test_{module_name}.py"
            if not os.path.exists(test_path):
                # If no direct test file, run all tests
                test_path = "tests/"
        
        # Run pytest on the identified test path
        result = subprocess.run(
            ["python", "-m", "pytest", test_path, "-v"], 
            capture_output=True, 
            text=True,
            check=False
        )
        
        # Parse pytest output for errors
        if "FAILURES" in result.stdout:
            # Extract failed test information
            failed_tests = re.findall(r"(FAILED\s+[^\n]+)", result.stdout)
            error_messages = re.findall(r"E\s+([^\n]+)", result.stdout)
            
            # Match errors to this file
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Add relevant test failures
            for test in failed_tests:
                if module_name in test or is_test_file:
                    errors.append(f"Test failure: {test}")
            
            # Add error messages for context
            if errors and error_messages:
                errors.extend([f"Error message: {msg}" for msg in error_messages[:5]])  # Limit to first 5 messages
    except Exception as e:
        print(f"Error running tests for {file_path}: {e}")
    
    return errors

def fix_file_with_openai(file_path, file_content, errors, file_type, attempt):
    """Use OpenAI to fix errors in the file."""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables")
    
    # Construct the prompt
    error_text = "\n".join(errors)
    
    prompt = f"""You are an expert {file_type} developer. I need your help fixing errors in a file.

File Path: {file_path}
File Type: {file_type}
Attempt: {attempt}

The file has the following errors:
{error_text}

Here is the current content of the file:
```
{file_content}
```

Please provide ONLY the fixed version of the file with no explanation. Your response should be the complete file content that resolves the errors."""

    # Make the API request
    response = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        },
        json={
            'model': 'gpt-3.5-turbo',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.2,
            'max_tokens': 4096
        }
    )
    
    if response.status_code != 200:
        raise ValueError(f"OpenAI API request failed: {response.text}")
    
    # Extract the generated code
    result = response.json()
    if not result.get('choices') or not result['choices'][0].get('message'):
        raise ValueError("Unexpected response format from OpenAI")
    
    fixed_content = result['choices'][0]['message']['content']
    
    # Strip out markdown code blocks if present
    if '```' in fixed_content:
        match = re.search(r'```(?:\w+)?\n([\s\S]+?)\n```', fixed_content)
        if match:
            fixed_content = match.group(1)
    
    return fixed_content

def main():
    """Main function to fix code issues."""
    # Get affected files from environment
    affected_files_json = os.environ.get('ERROR_FILES')
    max_attempts = int(os.environ.get('MAX_ATTEMPTS', '3'))
    
    if affected_files_json:
        affected_files = json.loads(affected_files_json)
    else:
        # Fallback to checking Python files that most likely have issues
        affected_files = ["calculator/calculator.py", "tests/test_calculator.py"]
    
    changes_summary = []
    
    for file_path in affected_files:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
        
        print(f"Attempting to fix {file_path}...")
        original_content = get_file_content(file_path)
        file_type = get_file_type(file_path)
        
        # Get errors for this file
        errors = get_errors_for_file(file_path)
        if not errors:
            print(f"No errors found for {file_path}, skipping.")
            continue
        
        print(f"Found {len(errors)} errors in {file_path}")
        
        # Try to fix the file
        fixed = False
        current_content = original_content
        
        for attempt in range(1, max_attempts + 1):
            print(f"Fix attempt {attempt}/{max_attempts} for {file_path}")
            
            try:
                # Get fix from OpenAI
                fixed_content = fix_file_with_openai(
                    file_path, current_content, errors, file_type, attempt
                )
                
                if not fixed_content or fixed_content == current_content:
                    print("No changes suggested or same content returned")
                    continue
                
                # Write fixed content
                write_file_content(file_path, fixed_content)
                print(f"Updated {file_path} with suggested fixes")
                
                # Create unified diff for logging
                diff_process = subprocess.run(
                    ["git", "diff", "--unified=3", "--", file_path],
                    capture_output=True,
                    text=True,
                    check=True
                )
                diff = diff_process.stdout
                
                # Add to changes summary
                changes_summary.append(f"## Changes to {file_path} (Attempt {attempt})\n```diff\n{diff}\n```")
                
                # Commit the changes
                subprocess.run(["git", "add", file_path], check=True)
                subprocess.run(["git", "commit", "-m", f"fix: Auto-fix attempt {attempt} for {file_path}"], check=True)
                
                # Check if fixes worked
                new_errors = get_errors_for_file(file_path)
                if not new_errors:
                    print(f"Successfully fixed all errors in {file_path}!")
                    fixed = True
                    break
                else:
                    print(f"Still {len(new_errors)} errors after fix attempt {attempt}")
                    errors = new_errors
                    current_content = fixed_content
            except Exception as e:
                print(f"Error in fix attempt {attempt} for {file_path}: {e}")
        
        if not fixed:
            print(f"Could not fix all errors in {file_path} after {max_attempts} attempts")
    
    # Set GitHub Actions output
    with open(os.environ.get("GITHUB_OUTPUT", "output.txt"), "a") as f:
        changes_output = "\n\n".join(changes_summary)
        f.write(f"changes_summary<<EOF\n{changes_output}\nEOF\n")
    
    print("Completed fix attempts.")

if __name__ == "__main__":
    main()