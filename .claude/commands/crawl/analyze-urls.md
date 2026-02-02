---
description: Analyze a documentation URL to get an optimal list of pages to crawl
---

# Analyze Documentation URLs

You are helping the user define their crawling needs to get an optimal list of URLs.

## Steps to follow

### 1. Get User Input

Use `AskUserQuestion` to gather the necessary information:

**Question 1: Documentation URL**
Ask the user to provide the base URL of the documentation they want to analyze.
- Example: "https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API"
- Free text input expected

**Question 2: Scope/Depth**
Ask what level of coverage they need:
- **Single page only** - Just the URL provided, no linked pages
- **Section** - The page and its direct sub-pages (one level deep)
- **Full documentation** - All pages under this URL path (recursive)

**Question 3: Content Focus (optional)**
Ask if they want to focus on specific types of content:
- **All content** - Everything found
- **API references** - Focus on interfaces, methods, properties
- **Guides/Tutorials** - Focus on how-to content
- **Examples** - Focus on code examples and demos

### 2. Validate the URL

Before proceeding, validate that the URL is accessible:

```bash
curl -sI "<user-provided-url>" | head -5
```

If the URL returns an error, ask the user to verify and provide a corrected URL.

### 3. Delegate to the URL Analyzer Agent

Once you have all the information, use the Task tool to launch the `url-analyzer` agent with the following prompt structure:

```
Analyze the following documentation URL and return an optimal list of pages:

**Target URL:** <url>
**Scope:** <single-page|section|full>
**Content Focus:** <all|api-references|guides|examples>

Crawl the pages, analyze their content, and return the URLs grouped by category.
```

### 4. Present Results

After the agent returns, present the results to the user:
- Show the categorized URL list
- Indicate the total number of pages found
- Suggest next steps (e.g., create a source config with `/crawl:create-source` or run a direct crawl)

## Example Interaction

```
User: /crawl:analyze-urls

Claude: What documentation URL would you like to analyze?
User: https://developer.mozilla.org/en-US/docs/Web/CSS/animation

Claude: What level of coverage do you need?
User: Section

Claude: What type of content are you interested in?
User: All content

Claude: I'll analyze this documentation section. [Launches url-analyzer agent]

[Agent returns grouped URLs]

Claude: Found 24 pages organized in 4 categories:
- Overview (3 pages)
- Properties (15 pages)
- Guides (4 pages)
- Examples (2 pages)

Would you like me to create a source configuration for these URLs?
```
