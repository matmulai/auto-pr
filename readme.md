# Auto-PR AI Code Fixer

![GitHub release (latest by date)](https://img.shields.io/github/v/release/yourusername/github-auto-pr-action)
![GitHub Marketplace](https://img.shields.io/badge/GitHub%20Marketplace-Auto--PR%20AI%20Code%20Fixer-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

Automatically fix failing tests and linting errors using OpenAI, then create pull requests with the fixes.

## 🌟 Features

- **AI-Powered Fixes**: Uses OpenAI to intelligently fix code errors
- **Automatic Pull Requests**: Creates PRs with fixes when tests or linting fail
- **Multiple Fix Attempts**: Tries multiple approaches if initial fixes don't work
- **Works with Many Languages**: Supports Python, JavaScript, TypeScript, and more
- **Customizable**: Adaptable to different testing and linting setups
- **Easy Integration**: Works with your existing test workflows

## 📋 How It Works

1. The action is triggered when a test workflow fails and the commit message contains "auto-pr"
2. It extracts error information from test and lint failures
3. The errors and code context are sent to OpenAI to generate fixes
4. Fixes are applied and verified by running tests again
5. If successful, a pull request is created with the changes

## 🔧 Setup Instructions

### Prerequisites

- An OpenAI API key (get one at [platform.openai.com](https://platform.openai.com))
- A GitHub repository with tests and/or linting

### Quick Start

Add this to your repository as `.github/workflows/auto-pr.yml`:

```yaml
name: Auto-PR Fixer

on:
  workflow_run:
    workflows: ["Tests"]  # Name of your test workflow
    types: [completed]
    branches: ["**"]

jobs:
  auto-fix:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'failure' && contains(github.event.workflow_run.head_commit.message, 'auto-pr') }}
    steps:
      - uses: actions/checkout@v3
        with:
          ref: ${{ github.event.workflow_run.head_branch }}
          
      - name: Auto-PR AI Code Fixer
        uses: yourusername/github-auto-pr-action@v1
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

### Setting Up Secrets

1. Go to your repository's Settings > Secrets and variables > Actions
2. Create a new repository secret:
   - Name: `OPENAI_API_KEY`
   - Value: Your OpenAI API key

## 🛠️ Usage Options

### Complete Configuration

```yaml
- name: Auto-PR AI Code Fixer
  uses: yourusername/github-auto-pr-action@v1
  with:
    # Required
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    
    # Optional - customize test and lint commands
    test-command: "pytest -v"
    lint-command: "pylint **/*.py --exit-zero"
    
    # Optional - fine-tune behavior
    max-attempts: 3
    openai-model: "gpt-3.5-turbo"
```

### Input Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `openai-api-key` | Yes | | Your OpenAI API key |
| `test-command` | No | `pytest` | Command to run tests |
| `lint-command` | No | `pylint **/*.py --exit-zero` | Command to run linting |
| `max-attempts` | No | `3` | Maximum number of fix attempts per file |
| `openai-model` | No | `gpt-3.5-turbo` | OpenAI model to use |

## 💡 Examples

### Using with Python Project

```yaml
- name: Auto-PR AI Code Fixer
  uses: yourusername/github-auto-pr-action@v1
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    test-command: "pytest"
    lint-command: "pylint **/*.py --exit-zero"
```

### Using with JavaScript/Node.js Project

```yaml
- name: Auto-PR AI Code Fixer
  uses: yourusername/github-auto-pr-action@v1
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    test-command: "npm test"
    lint-command: "eslint **/*.js"
```

### Using with Advanced Settings

```yaml
- name: Auto-PR AI Code Fixer
  uses: yourusername/github-auto-pr-action@v1
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    test-command: "python -m pytest tests/ -v"
    lint-command: "flake8 ."
    max-attempts: 5
    openai-model: "gpt-4"
```

## ⚠️ Limitations

- Fixes are limited by OpenAI model capabilities
- Complex bugs or architectural issues may not be fixable
- Requires well-structured tests that provide clear error messages
- The action needs appropriate permissions to create branches and pull requests

## 🔍 Troubleshooting

### Common Issues

**The action doesn't trigger:**
- Ensure your test workflow is properly named in the trigger
- Verify commit messages contain "auto-pr"
- Check workflow permissions

**OpenAI API errors:**
- Validate your API key
- Check OpenAI service status
- Ensure you have sufficient API credits

**No fixes are generated:**
- Make sure error messages are clear and detailed
- Check if your tests provide enough context for the AI
- Try increasing max-attempts

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Open a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- Built with [OpenAI API](https://openai.com/)
- Uses [create-pull-request](https://github.com/peter-evans/create-pull-request) action
- Inspired by the need to automate routine code fixes

---

Created with ❤️ by [Your Name](https://github.com/soodoku)

