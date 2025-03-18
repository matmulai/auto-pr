# Auto-PR GitHub Action

This GitHub Action automatically fixes code issues and creates pull requests when errors are detected in your linting or testing workflows.

## How It Works

1. When you commit with the message containing `auto-pr`, this action is triggered
2. It waits for your existing lint and test actions to complete
3. If any errors are found, it uses OpenAI to suggest fixes
4. It creates a new branch, attempts the fixes, and verifies if they work
5. If successful, it creates a pull request with the fixed code

## Setup Instructions

### 1. Create the Required Directory Structure

First, set up the necessary files in your repository:

```bash
mkdir -p .github/workflows
mkdir -p .github/scripts
```

### 2. Add the GitHub Action Workflow

Create the file `.github/workflows/auto-pr.yml` with the content from the provided workflow file.

### 3. Add the Supporting Scripts

Add the two JavaScript files to the scripts directory:
- `.github/scripts/wait-for-actions.js`
- `.github/scripts/fix-code.js`

### 4. Configure OpenAI API Key

Add your OpenAI API key as a secret in your GitHub repository:

1. Go to your repository's Settings
2. Click on "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Name: `OPENAI_API_KEY`

