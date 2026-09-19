---
title: Hello, World
date: 2026-09-19
excerpt: The blog is live. This is a placeholder post — edit or delete it and add your own.
---

This is the first post on the blog. It exists to show the format a post file needs — replace this text with real content, or delete this file entirely once you have your own first post.

## How to add a new post

1. Create a new Markdown file under `content/en/blog/` (and `content/fa/blog/` for the Persian version, if you're writing both).
2. Give it frontmatter at the top: `title`, `date` (YYYY-MM-DD), and `excerpt`.
3. Write the body below the frontmatter using plain Markdown — paragraphs, `**bold**`, `*italic*`, `# / ## / ###` headings, `- ` bullet lists, and `[link text](https://example.com)` links.
4. Run `python3 build.py` from the project root.
5. Commit and push. GitHub Pages serves whatever `build.py` generated.

The filename becomes the post's URL slug, so `hello-world.md` publishes at `/en/blog/hello-world/`.
