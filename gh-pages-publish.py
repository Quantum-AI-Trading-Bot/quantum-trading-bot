#!/usr/bin/env python3
"""
Simple Blog Publisher for GitHub Pages
Creates blog posts from markdown files
"""

import os
import sys
import re
from datetime import datetime
from pathlib import Path
from shutil import copy2

# Configuration
CONTENT_DIR = Path("blog/content")
POSTS_DIR = Path("blog/posts")
BLOG_INDEX = Path("blog/index.html")
TEMPLATE_POST = POSTS_DIR / "launch-announcement.html"


def parse_markdown(filepath):
    """Parse markdown with YAML frontmatter"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    frontmatter = {}
    body = content

    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            # Parse YAML
            for line in parts[1].strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    # Handle lists
                    if value.startswith('[') and value.endswith(']'):
                        try:
                            import json
                            frontmatter[key] = json.loads(value)
                        except:
                            frontmatter[key] = value
                    else:
                        frontmatter[key] = value
            body = parts[2].strip()

    return frontmatter, body


def slugify(title):
    """Create URL-safe slug"""
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


def markdown_to_html(md):
    """Convert markdown to HTML (basic)"""
    html = md

    # Headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold, italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Code
    html = re.sub(r'```(.+?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
    html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)

    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)

    # Line breaks to paragraphs
    lines = []
    in_para = False
    for line in html.split('\n'):
        line = line.strip()
        if not line:
            if in_para:
                lines.append('</p>')
                in_para = False
        elif line.startswith('<'):
            if in_para:
                lines.append('</p>')
                in_para = False
            lines.append(line)
        else:
            if not in_para:
                lines.append('<p>')
                in_para = True
            lines.append(line + ' ')
    if in_para:
        lines.append('</p>')

    html = '\n'.join(lines)

    return html


def create_post(frontmatter, body, slug):
    """Create HTML blog post"""
    with open(TEMPLATE_POST, 'r', encoding='utf-8') as f:
        template = f.read()

    title = frontmatter.get('title', 'Untitled')
    date = frontmatter.get('date', datetime.now().strftime('%B %d, %Y'))
    author = frontmatter.get('author', 'David Sanker')
    tags = frontmatter.get('tags', [])
    excerpt = frontmatter.get('excerpt', '')
    read_time = frontmatter.get('reading_time', '5 min')

    # Convert markdown body to HTML
    body_html = markdown_to_html(body)

    # Replace in template
    html = template
    html = re.sub(r'<title>.*?</title>', f'<title>{title} - Quantum AI Trading Bot Blog</title>', html)
    html = re.sub(r'<h1 class="article-title">.*?</h1>', f'<h1 class="article-title">{title}</h1>', html, flags=re.DOTALL)
    html = re.sub(r'📅.*?\)', f'📅 {date}', html)
    html = re.sub(r'⏱️.*?\)', f'⏱️ {read_time} read', html)
    html = re.sub(r'👤.*?\)', f'👤 {author}', html)

    # Tags
    if tags:
        tags_html = '\n            '.join([f'<span class="tag">{t}</span>' for t in tags])
        html = re.sub(
            r'<div class="article-tags">.*?</div>',
            f'<div class="article-tags">\n            {tags_html}\n        </div>',
            html,
            flags=re.DOTALL
        )

    # Body content
    html = re.sub(
        r'<div class="article-content">.*</div>',
        f'<div class="article-content">\n            {body_html}\n        </div>',
        html,
        flags=re.DOTALL
    )

    # Save
    output = POSTS_DIR / f"{slug}.html"
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)

    return output


def update_index(slug, frontmatter):
    """Update blog index with new post"""
    with open(BLOG_INDEX, 'r', encoding='utf-8') as f:
        index = f.read()

    title = frontmatter.get('title', 'Untitled')
    date = frontmatter.get('date', datetime.now().strftime('%B %d, %Y'))
    tags = frontmatter.get('tags', [])
    excerpt = frontmatter.get('excerpt', '')
    read_time = frontmatter.get('reading_time', '5 min')

    tags_html = '\n                '.join([f'<span class="tag">{t}</span>' for t in tags])

    card = f'''                <a href="posts/{slug}.html" class="post-card">
                    <h3>{title}</h3>
                    <div class="post-meta">{date} • {read_time} read</div>
                    <p class="post-excerpt">{excerpt}</p>
                    <div class="post-tags">
                        {tags_html}
                    </div>
                    <div class="read-more">Read More →</div>
                </a>'''

    # Find first post card and insert after it
    pattern = r'(<a href="posts/launch-announcement\.html" class="post-card">.*?</a>)'
    match = re.search(pattern, index, flags=re.DOTALL)
    if match:
        insert_pos = match.end()
        index = index[:insert_pos] + '\n' + card + index[insert_pos:]

    with open(BLOG_INDEX, 'w', encoding='utf-8') as f:
        f.write(index)


def main():
    """Main"""
    if len(sys.argv) < 2:
        print("Usage: python publish.py <markdown-file>")
        print("\nExample:")
        print("  python publish.py blog/content/my-post.md")
        return

    md_file = sys.argv[1]

    if not os.path.exists(md_file):
        print(f"❌ File not found: {md_file}")
        return

    print(f"📝 Publishing: {md_file}")

    # Parse
    fm, body = parse_markdown(md_file)
    title = fm.get('title', 'untitled')
    slug = slugify(title)

    print(f"   Slug: {slug}")

    # Create post
    output = create_post(fm, body, slug)
    print(f"   ✅ Created: {output}")

    # Update index
    update_index(slug, fm)
    print(f"   ✅ Updated index")

    print(f"\n🎉 Post published!")
    print(f"\n   To commit:")
    print(f"   git add blog/posts/{slug}.html blog/index.html")
    print(f"   git commit -m 'blog: add {title}'")
    print(f"   git push origin gh-pages")


if __name__ == "__main__":
    main()
