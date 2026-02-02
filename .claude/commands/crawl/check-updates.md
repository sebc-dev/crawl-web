---
description: Check if documentation sources need updates
---

# Check Documentation Updates

You are helping the user check if their crawled documentation needs to be updated.

## Steps to follow

### 1. List Available Sources

First, run the following command to see available sources:

```bash
.venv/bin/python3 crawl.py --list
```

Show the user the list of available sources.

### 2. Ask Which Source to Check

Use `AskUserQuestion` to ask the user which source they want to check. Include the sources found in step 1 as options.

### 3. Ask Check Type

Use `AskUserQuestion` to ask what type of check to perform:

**Option 1: Local Check (Recommended for quick check)**
- Compares local output files against the saved crawl state
- Detects if files were manually modified since the last crawl
- Fast - no network requests needed
- Command: `.venv/bin/python3 crawl.py <source> --check`

**Option 2: Remote Check (Full verification)**
- Re-crawls all pages from the remote server
- Compares new content with saved state using content hashes
- Detects new, changed, or removed pages on the remote site
- Slower - requires full re-crawl
- Command: `.venv/bin/python3 crawl.py <source> --check-remote`

**Option 3: Both**
- Run local check first, then remote check
- Most thorough verification

### 4. Run the Check

Execute the appropriate command(s) based on user selection.

### 5. Interpret Results

After running the check, explain the results to the user:

**For Local Check (`--check`):**
- **unchanged**: File matches the crawl state (no local modifications)
- **modified**: File was modified locally since last crawl
- **missing**: File exists in state but not on disk
- **new_local_file**: File exists on disk but not in crawl state

**For Remote Check (`--check-remote`):**
- **unchanged**: Remote content matches saved state
- **changed**: Remote content has changed (needs re-crawl)
- **new**: New page discovered (wasn't in last crawl)
- **removed**: Page no longer exists on remote

### 6. Suggest Next Actions

Based on the results, suggest appropriate actions:

- **If remote changes detected**:
  ```bash
  .venv/bin/python3 crawl.py <source>  # Full re-crawl to update
  ```

- **If local modifications detected**:
  - Ask if they want to preserve local changes or overwrite with remote
  - If overwrite: `.venv/bin/python3 crawl.py <source>`
  - If preserve: backup files first, then decide

- **If new pages found**:
  - Consider adding patterns to `include_patterns` in config.yaml
  - Re-run discovery: `.venv/bin/python3 crawl.py <source> --discover-only`

- **If pages removed**:
  - May indicate URL structure changes
  - Review `seed_urls` and `include_patterns` in config.yaml

### 7. Summary Report

Provide a clear summary:
- Total pages checked
- Pages unchanged
- Pages needing attention (changed/new/removed)
- Recommended action

## Example Output Format

```
📊 Update Check Report for {source_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Last crawl: {date}

Local Status:
  ✓ {n} files unchanged
  ⚠ {n} files modified locally
  ✗ {n} files missing

Remote Status:
  ✓ {n} pages unchanged
  ⚠ {n} pages changed
  + {n} new pages
  - {n} pages removed

Recommendation: {action}
```
