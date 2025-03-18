const { Octokit } = require('@octokit/rest');
const fs = require('fs');

// Initialize GitHub client
const octokit = new Octokit({
  auth: process.env.GITHUB_TOKEN
});

const [owner, repo] = process.env.REPO.split('/');
const commitSha = process.env.COMMIT_SHA;

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForActions() {
  console.log(`Waiting for actions to complete for commit ${commitSha}...`);
  
  let allCompleted = false;
  let attempts = 0;
  const maxAttempts = 30; // 15 minutes max wait time (30 attempts * 30 seconds)
  
  let lintChecks = [];
  let testChecks = [];
  
  // List of relevant check names (customize based on your project)
  const lintCheckNames = ['lint', 'eslint', 'prettier', 'stylelint'];
  const testCheckNames = ['test', 'jest', 'mocha', 'cypress'];
  
  while (!allCompleted && attempts < maxAttempts) {
    try {
      // Get check runs for the commit
      const checkRuns = await octokit.checks.listForRef({
        owner,
        repo,
        ref: commitSha,
      });
      
      // Filter for relevant checks
      lintChecks = checkRuns.data.check_runs.filter(check => 
        lintCheckNames.some(name => check.name.toLowerCase().includes(name)) && 
        check.status === 'completed'
      );
      
      testChecks = checkRuns.data.check_runs.filter(check => 
        testCheckNames.some(name => check.name.toLowerCase().includes(name)) && 
        check.status === 'completed'
      );
      
      // Check if at least one relevant check of each type has completed
      const hasCompletedLintCheck = lintChecks.length > 0;
      const hasCompletedTestCheck = testChecks.length > 0;
      
      if (hasCompletedLintCheck && hasCompletedTestCheck) {
        allCompleted = true;
        console.log('All relevant checks have completed.');
      } else {
        attempts++;
        console.log(`Waiting for checks to complete... Attempt ${attempts}/${maxAttempts}`);
        await sleep(30000); // Wait 30 seconds before checking again
      }
    } catch (error) {
      console.error('Error checking workflow status:', error);
      attempts++;
      await sleep(30000);
    }
  }
  
  if (!allCompleted) {
    console.log('Timed out waiting for actions to complete.');
    process.exit(1);
  }
  
  // Process the results
  const lintErrors = {};
  const testErrors = {};
  const affectedFiles = new Set();
  
  // Extract lint errors
  for (const check of lintChecks) {
    if (check.conclusion === 'failure') {
      const annotations = await getAnnotationsForCheck(check.id);
      annotations.forEach(annotation => {
        if (!lintErrors[annotation.path]) {
          lintErrors[annotation.path] = [];
        }
        lintErrors[annotation.path].push({
          message: annotation.message,
          line: annotation.start_line || annotation.line,
          column: annotation.start_column
        });
        affectedFiles.add(annotation.path);
      });
    }
  }
  
  // Extract test errors
  for (const check of testChecks) {
    if (check.conclusion === 'failure') {
      try {
        // Get the full output of the failed test
        const details = await octokit.checks.get({
          owner,
          repo,
          check_run_id: check.id
        });
        
        // Extract file paths from test error messages - this will need to be adapted for your test framework
        // This is a simple example that might need to be extended based on your test output format
        const output = details.data.output.text || '';
        
        // Simple parsing - adjust the regex based on your test framework's output
        const errorMatches = output.match(/Error at .*?:\d+/g) || [];
        const failMatches = output.match(/Failed at .*?:\d+/g) || [];
        const allMatches = [...errorMatches, ...failMatches];
        
        allMatches.forEach(match => {
          const filePath = match.replace(/Error at |Failed at /, '').split(':')[0];
          if (filePath && filePath.includes('.')) {  // Basic check to ensure it's a file
            if (!testErrors[filePath]) {
              testErrors[filePath] = [];
            }
            testErrors[filePath].push({
              message: `Test failure in ${filePath}`,
              details: match
            });
            affectedFiles.add(filePath);
          }
        });
        
        // If we couldn't extract specific files, store the entire output under a general key
        if (Object.keys(testErrors).length === 0 && output.includes('fail')) {
          testErrors['_general'] = [{
            message: 'Test failures detected',
            details: output
          }];
        }
      } catch (error) {
        console.error('Error getting test details:', error);
      }
    }
  }
  
  // Output the results as GitHub outputs
  console.log(`::set-output name=lint-errors::${JSON.stringify(lintErrors)}`);
  console.log(`::set-output name=test-errors::${JSON.stringify(testErrors)}`);
  console.log(`::set-output name=affected-files::${JSON.stringify([...affectedFiles])}`);
}

async function getAnnotationsForCheck(checkId) {
  try {
    const response = await octokit.checks.listAnnotations({
      owner,
      repo,
      check_run_id: checkId
    });
    return response.data;
  } catch (error) {
    console.error('Error getting annotations:', error);
    return [];
  }
}

// Run the main function
waitForActions().catch(error => {
  console.error('Error in waitForActions:', error);
  process.exit(1);
});