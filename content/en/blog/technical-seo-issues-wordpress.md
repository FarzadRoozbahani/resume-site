---
title: 5 Technical SEO Issues That Quietly Kill WordPress Rankings
date: 2026-08-29
excerpt: WordPress makes it easy to publish and just as easy to accumulate crawl and indexing problems nobody notices until traffic drops.
---

WordPress is friendly to write in and unfriendly to leave unattended. Most of the technical SEO problems I see on client sites aren't dramatic — no plugin crashed, nothing looks broken in the browser. They just quietly waste crawl budget and confuse search engines about which page should actually rank. Here are the five I check first on every new site.

## 1. Tag and category archives competing with your real content

WordPress generates an archive page for every tag and category by default. On a blog with loose tagging habits, that can mean dozens of thin, near-duplicate pages indexed alongside your actual articles — all fighting each other for the same keywords. Decide early whether tag archives earn their place in the index. If they don't add unique value, `noindex` them in your SEO plugin rather than leaving them to compete with pages that matter.

## 2. Canonical tags that point to the wrong place

This one is sneaky because it's invisible until you check `view-source`. Page builders, some caching plugins, and multilingual setups can all quietly rewrite or duplicate canonical tags — sending Google to index the wrong URL, or splitting ranking signals between `http`/`https`, `www`/non-`www`, or a staging URL that never got cleaned up. Crawl the site with a tool like Screaming Frog after any theme or plugin change and check that every canonical tag actually points to itself, not somewhere else.

## 3. A sitemap that isn't wired up properly

A sitemap doesn't help if it isn't in `robots.txt`, isn't submitted in Search Console, or lists URLs that 404. I've seen sites running for years with a sitemap plugin installed and no one having ever pointed Google at it. Check Search Console's Sitemaps report for errors — not just whether it says "Success," but whether the *indexed* count roughly matches the *submitted* count.

## 4. Crawl budget wasted on pages that shouldn't be crawled

Author archives on a single-author blog, `?replytocom` comment-reply URLs, internal search result pages, feed URLs — none of these need to be crawled, and on a large site they can genuinely compete with your real pages for crawl budget. A few lines in `robots.txt` fix most of it:

```
Disallow: /?replytocom=
Disallow: /?s=
Disallow: /author/
```

## 5. Redirect chains from old migrations

Every domain migration, HTTP-to-HTTPS switch, or URL structure change that didn't get cleaned up leaves a redirect behind. Individually harmless — but stack three or four of them on the same URL and you're burning crawl budget and diluting link equity on every single request. Run a redirect-chain check after any migration and flatten anything more than one hop.

None of these require touching code most of the time — they need someone willing to actually crawl the site, read the reports, and fix what they find instead of assuming the SEO plugin is handling it. That's most of the job.
