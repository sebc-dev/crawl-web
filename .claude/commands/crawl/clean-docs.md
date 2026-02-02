---
description: Clean and improve crawled documentation quality
---

# Clean Crawled Documentation

You are helping the user clean and improve the quality of their crawled documentation. This workflow uses specialized agents for analysis and implementation.

## Steps to follow

### 1. Select Source to Clean

First, list available sources and check which have been crawled:

```bash
.venv/bin/python3 crawl.py --list
```

```bash
ls -d sources/*/output 2>/dev/null
```

If multiple sources exist, use `AskUserQuestion` to ask which source the user wants to clean.

### 2. Launch the Cleaning Analyzer Agent

Use the `Task` tool to launch the `cleaning-analyzer` agent:

```
Analyze the crawled documentation for source "{source_name}" to identify noise patterns and cleaning opportunities.

Source directory: sources/{source_name}/
Output directory: sources/{source_name}/output/

Provide a detailed report of issues found and recommended cleaning rules.
```

Wait for the agent to complete and present the analysis report to the user.

### 3. Confirm Issues to Address

Use `AskUserQuestion` to confirm which issues the user wants to address from the analysis report.

### 4. Launch the Cleaning Implementer Agent

Use the `Task` tool to launch the `cleaning-implementer` agent:

```
Implement cleaning rules for source "{source_name}" based on the analysis report.

Issues to address:
{list of confirmed issues from user}

Source cleaner: sources/{source_name}/cleaner.py
Base cleaner: crawl4ai_toolkit/cleaner.py

Create or update the cleaner module with the necessary methods.
```

Wait for the agent to complete the implementation.

### 5. Re-crawl to Apply Changes

Ask the user if they want to re-crawl to apply the cleaning changes:

```bash
.venv/bin/python3 crawl.py {source_name}
```

### 6. Verify Results

After re-crawling, read a sample file to verify the cleaning worked:

```bash
head -50 sources/{source_name}/output/{sample_file}.md
```

Use `AskUserQuestion` to ask if the user is satisfied or wants further refinement.

### 7. Iterate if Needed

If the user wants more cleaning:
- Go back to step 2 for additional analysis, or
- Go back to step 4 to add more cleaning rules

### 8. Final Summary

Once satisfied, provide a summary:

```
Documentation Cleaning Complete for {source_name}

Cleaning rules implemented:
  - {rule_1}
  - {rule_2}
  - ...

Files processed: {n}
Output directory: sources/{source_name}/output/
```
