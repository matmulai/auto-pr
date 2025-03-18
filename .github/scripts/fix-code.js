const { Octokit } = require('@octokit/rest');
const axios = require('axios');
const fs = require('fs');
const { execSync } = require('child_process');
const path = require('path');

// Initialize GitHub client
const octokit = new Octokit({
  auth: process.env.GITHUB_TOKEN
});

// Parse environment variables
const [owner, repo] = process.env.REPO.split('/');
const commitSha = process.env.COMMIT_SHA;
const lintErrors = JSON.parse(process.env.LINT_ERRORS || '{}');
const testErrors = JSON.parse(process.env.TEST_ERRORS || '{}');
const affectedFiles = JSON.parse(process.env.AFFECTED_FILES || '[]');
const maxAttempts = parseInt(process.env.MAX_ATTEMPTS || '3');

// Keep track of original errors for reporting
const originalErrors = {
  lint: lintErrors,
  test: testErrors
};

// Main function to fix code issues
async function fixCode() {
  try {
    console.log('Starting auto-fix process...');
    console.log(`Affected files: ${JSON.stringify(affectedFiles)}`);
    console.log(`Lint errors: ${JSON.stringify(lintErrors)}`);
    console.log(`Test errors: ${JSON.stringify(testErrors)}`);
    
    let success = false;
    let changesLog = [];
    let verificationResults = '';
    
    // Combine all files that need fixing
    const filesToFix = new Set([
      ...Object.keys(lintErrors),
      ...Object.keys(testErrors)
    ].filter(file => file !== '_general'));
    
    // If we have general test errors with no specific files, try to identify files from affected files
    if (testErrors['_general'] && affectedFiles.length > 0) {
      affectedFiles.forEach(file => filesToFix.add(file));
    }
    
    console.log(`Files to fix: ${JSON.stringify([...filesToFix])}`);
    
    for (const filePath of filesToFix) {
      if (!fs.existsSync(filePath)) {
        console.log(`File ${filePath} does not exist, skipping.`);
        continue;
      }
      
      const fileContent = fs.readFileSync(filePath, 'utf8');
      const fileExtension = path.extname(filePath);
      
      // Determine file type based on extension
      let fileType;
      if (['.js', '.jsx', '.ts', '.tsx'].includes(fileExtension)) {
        fileType = 'JavaScript/TypeScript';
      } else if (['.py'].includes(fileExtension)) {
        fileType = 'Python';
      } else if (['.java'].includes(fileExtension)) {
        fileType = 'Java';
      } else if (['.rb'].includes(fileExtension)) {
        fileType = 'Ruby';
      } else if (['.go'].includes(fileExtension)) {
        fileType = 'Go';
      } else if (['.php'].includes(fileExtension)) {
        fileType = 'PHP';
      } else if (['.c', '.cpp', '.h', '.hpp'].includes(fileExtension)) {
        fileType = 'C/C++';
      } else if (['.cs'].includes(fileExtension)) {
        fileType = 'C#';
      } else if (['.html', '.htm'].includes(fileExtension)) {
        fileType = 'HTML';
      } else if (['.css', '.scss', '.sass', '.less'].includes(fileExtension)) {
        fileType = 'CSS';
      } else {
        fileType = 'Unknown';
      }
      
      const fileErrors = [];
      
      // Collect lint errors for this file
      if (lintErrors[filePath]) {
        fileErrors.push(...lintErrors[filePath].map(err => 
          `Lint error at line ${err.line}${err.column ? `, column ${err.column}` : ''}: ${err.message}`
        ));
      }
      
      // Collect test errors for this file
      if (testErrors[filePath]) {
        fileErrors.push(...testErrors[filePath].map(err => 
          `Test error: ${err.message} - ${err.details}`
        ));
      }
      
      // If there are general test errors, include them for all files we're fixing
      if (testErrors['_general']) {
        fileErrors.push(...testErrors['_general'].map(err => 
          `General test error that might relate to this file: ${err.message}`
        ));
      }
      
      if (fileErrors.length === 0) {
        console.log(`No specific errors found for ${filePath}, skipping.`);
        continue;
      }
      
      console.log(`Attempting to fix ${filePath}...`);
      
      let fixed = false;
      let attemptsMade = 0;
      let currentFileContent = fileContent;
      
      while (!fixed && attemptsMade < maxAttempts) {
        attemptsMade++;
        console.log(`Attempt ${attemptsMade}/${maxAttempts} for ${filePath}`);
        
        try {
          // Get fix suggestions from OpenAI
          const fixedContent = await getFixFromOpenAI(currentFileContent, fileErrors, fileType, filePath, attemptsMade);
          
          if (!fixedContent || fixedContent === currentFileContent) {
            console.log('No changes suggested or OpenAI returned the same content');
            if (attemptsMade === maxAttempts) {
              console.log(`Maximum attempts reached for ${filePath} without success`);
            }
            continue;
          }
          
          // Save the fixed content
          fs.writeFileSync(filePath, fixedContent);
          console.log(`Updated ${filePath} with suggested fixes`);
          
          // Commit the changes
          try {
            execSync(`git add "${filePath}"`);
            execSync(`git commit -m "fix: Auto-fix attempt ${attemptsMade} for ${filePath}"`);
            console.log(`Committed changes for ${filePath}`);
            
            // Log the changes
            const diff = execSync(`git diff HEAD~1 HEAD -- "${filePath}"`).toString();
            changesLog.push(`## Changes to ${filePath} (Attempt ${attemptsMade})\n\`\`\`diff\n${diff}\n\`\`\``);
            
            // Verify the changes by running relevant checks
            const verificationResult = await verifyFix(filePath, fileType);
            console.log(`Verification result: ${JSON.stringify(verificationResult)}`);
            
            if (verificationResult.success) {
              console.log(`Fix for ${filePath} was successful!`);
              fixed = true;
              success = true;
              verificationResults += `\n### ${filePath} - ✅ Fixed successfully\n${verificationResult.details}\n`;
            } else {
              console.log(`Fix for ${filePath} did not resolve all issues, trying again...`);
              // Update current content for next attempt
              currentFileContent = fixedContent;
              // Update file errors based on verification result
              if (verificationResult.errors && verificationResult.errors.length > 0) {
                fileErrors.length = 0; // Clear previous errors
                fileErrors.push(...verificationResult.errors);
              }
              verificationResults += `\n### ${filePath} - ❌ Attempt ${attemptsMade} failed\n${verificationResult.details}\n`;
            }
          } catch (commitError) {
            console.error(`Error committing changes: ${commitError}`);
            verificationResults += `\n### ${filePath} - ❌ Error committing changes\n${commitError}\n`;
          }
        } catch (error) {
          console.error(`Error fixing ${filePath}: ${error}`);
          verificationResults += `\n### ${filePath} - ❌ Error in fix attempt ${attemptsMade}\n${error}\n`;
        }
      }
      
      if (!fixed) {
        console.log(`Could not fix ${filePath} after ${maxAttempts} attempts`);
      }
    }
    
    // Set the outputs
    console.log(`::set-output name=success::${success}`);
    console.log(`::set-output name=original-errors::${JSON.stringify(originalErrors)}`);
    console.log(`::set-output name=changes-made::${changesLog.join('\n\n')}`);
    console.log(`::set-output name=verification-results::${verificationResults}`);
    
    if (success) {
      console.log('Successfully fixed at least one file!');
      process.exit(0);
    } else {
      console.log('Failed to fix any files.');
      process.exit(1);
    }
  } catch (error) {
    console.error('Error in fixCode function:', error);
    process.exit(1);
  }
}

// Function to get fix suggestions from OpenAI
async function getFixFromOpenAI(fileContent, errors, fileType, filePath, attempt) {
  try {
    console.log(`Requesting OpenAI fix for ${filePath} (Attempt ${attempt})`);
    
    const errorText = errors.join('\n');
    
    // Construct a prompt for the OpenAI API
    const prompt = `You are an expert ${fileType} developer. I need your help fixing errors in a file.

File Path: ${filePath}
File Type: ${fileType}
Attempt: ${attempt}/${maxAttempts}

The file has the following errors:
${errorText}

Here is the current content of the file:
\`\`\`
${fileContent}
\`\`\`

Please provide ONLY the fixed version of the file with no explanation. Your response should be the complete file content that resolves the errors.`;

    const response = await axios.post(
      'https://api.openai.com/v1/chat/completions',
      {
        model: 'gpt-3.5-turbo',
        messages: [{
          role: 'user',
          content: prompt
        }],
        temperature: 0.2,
        max_tokens: 4096
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`
        }
      }
    );
    
    if (response.data && response.data.choices && response.data.choices.length > 0) {
      let fixedContent = response.data.choices[0].message.content;
      
      // Strip out markdown code blocks if present
      if (fixedContent.includes('```')) {
        const codeBlockMatch = fixedContent.match(/```(?:\w+)?\n([\s\S]+?)```/);
        if (codeBlockMatch && codeBlockMatch[1]) {
          fixedContent = codeBlockMatch[1];
        } else {
          // Try another pattern
          const lines = fixedContent.split('\n');
          const startIdx = lines.findIndex(line => line.startsWith('```'));
          const endIdx = lines.slice(startIdx + 1).findIndex(line => line.startsWith('```')) + startIdx + 1;
          
          if (startIdx !== -1 && endIdx !== -1) {
            fixedContent = lines.slice(startIdx + 1, endIdx).join('\n');
          }
        }
      }
      
      return fixedContent;
    } else {
      console.error('Unexpected response format from OpenAI');
      return null;
    }
  } catch (error) {
    console.error('Error getting fix from OpenAI:', error.response?.data || error.message);
    return null;
  }
}

// Function to verify if the fix resolves the issues
async function verifyFix(filePath, fileType) {
  try {
    console.log(`Verifying fix for ${filePath}`);
    
    // Determine the appropriate verification command based on file type
    let command = '';
    let useGenericLint = false;
    
    if (['.js', '.jsx'].includes(path.extname(filePath))) {
      if (fs.existsSync('package.json')) {
        const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
        if (packageJson.scripts) {
          if (packageJson.scripts.lint) {
            command = 'npm run lint';
          } else if (packageJson.scripts.eslint) {
            command = 'npm run eslint';
          } else {
            useGenericLint = true;
          }
        }
      }
      
      if (useGenericLint || !command) {
        if (fs.existsSync('.eslintrc') || fs.existsSync('.eslintrc.js') || fs.existsSync('.eslintrc.json')) {
          command = `npx eslint "${filePath}"`;
        }
      }
    } else if (['.ts', '.tsx'].includes(path.extname(filePath))) {
      if (fs.existsSync('package.json')) {
        const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
        if (packageJson.scripts && packageJson.scripts.lint) {
          command = 'npm run lint';
        } else {
          useGenericLint = true;
        }
      }
      
      if (useGenericLint || !command) {
        if (fs.existsSync('tsconfig.json')) {
          command = `npx tsc --noEmit`;
        }
      }
    } else if (path.extname(filePath) === '.py') {
      if (fs.existsSync('requirements.txt') || fs.existsSync('pyproject.toml')) {
        command = `python -m pylint "${filePath}"`;
      }
    }
    
    // If we couldn't determine a specific linting command, try running tests
    if (!command) {
      if (fs.existsSync('package.json')) {
        const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
        if (packageJson.scripts && packageJson.scripts.test) {
          command = 'npm test';
        }
      } else if (fs.existsSync('pytest.ini') || fs.existsSync('conftest.py')) {
        command = 'python -m pytest';
      } else if (fs.existsSync('build.gradle') || fs.existsSync('build.gradle.kts')) {
        command = './gradlew test';
      }
    }
    
    if (!command) {
      return {
        success: false,
        details: 'Could not determine appropriate verification command for this file type.',
        errors: []
      };
    }
    
    console.log(`Running verification command: ${command}`);
    
    try {
      const output = execSync(command, { stdio: 'pipe' }).toString();
      console.log(`Verification succeeded with output: ${output}`);
      
      return {
        success: true,
        details: `Command \`${command}\` executed successfully!\n\nOutput:\n${output || 'No output'}`
      };
    } catch (error) {
      console.log(`Verification failed with error: ${error.message}`);
      console.log(`Stderr: ${error.stderr?.toString() || 'No stderr'}`);
      console.log(`Stdout: ${error.stdout?.toString() || 'No stdout'}`);
      
      // Parse errors from the output
      const errorOutput = error.stderr?.toString() || error.stdout?.toString() || '';
      const parsedErrors = parseErrorOutput(errorOutput, filePath, fileType);
      
      return {
        success: false,
        details: `Command \`${command}\` failed!\n\nError:\n${errorOutput}`,
        errors: parsedErrors
      };
    }
  } catch (error) {
    console.error(`Error in verifyFix: ${error}`);
    return {
      success: false,
      details: `Exception during verification: ${error}`,
      errors: []
    };
  }
}

// Helper function to parse error output into a structured format
function parseErrorOutput(output, filePath, fileType) {
  try {
    const errors = [];
    const lines = output.split('\n');
    
    if (fileType === 'JavaScript/TypeScript') {
      // Parse ESLint-like errors
      for (const line of lines) {
        if (line.includes(filePath) && (line.includes('error') || line.includes('warning'))) {
          errors.push(line.trim());
        }
      }
    } else if (fileType === 'Python') {
      // Parse Pylint-like errors
      for (const line of lines) {
        if (line.includes(filePath) && (line.includes('E:') || line.includes('W:'))) {
          errors.push(line.trim());
        }
      }
    } else {
      // Generic error parsing - just include lines that mention the file path
      for (const line of lines) {
        if (line.includes(filePath)) {
          errors.push(line.trim());
        }
      }
    }
    
    // If we couldn't find specific errors mentioning the file, include some context
    if (errors.length === 0 && output.trim()) {
      const relevantLines = output.split('\n')
        .filter(line => line.trim() && (line.includes('error') || line.includes('fail')))
        .slice(0, 10); // Limit to 10 error lines
      
      errors.push(...relevantLines.map(line => line.trim()));
    }
    
    return errors;
  } catch (error) {
    console.error(`Error parsing error output: ${error}`);
    return [output.trim().substring(0, 500)]; // Return truncated output as a single error
  }
}

// Run the main function
fixCode().catch(error => {
  console.error('Uncaught error in fixCode:', error);
  process.exit(1);
});