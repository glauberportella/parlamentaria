"""Telegram message formatter — converts Markdown to Telegram HTML.

The ADK agents generate responses in standard Markdown. Telegram's Bot API
supports a subset of HTML for rich formatting. This module bridges the gap
by converting Markdown syntax to Telegram-compatible HTML tags.

Supported conversions:
    **bold** / __bold__       → <b>bold</b>
    *italic* / _italic_       → <i>italic</i>
    ~~strikethrough~~         → <s>strikethrough</s>
    `inline code`             → <code>inline code</code>
    ```code blocks```         → <pre>code blocks</pre>
    [text](url)               → <a href="url">text</a>
    > blockquotes             → <blockquote>quote</blockquote>
    * / - / + list items      → • bullet items
    # headings                → <b>headings</b>
    --- horizontal rules      → ━━━ separator line
"""

from __future__ import annotations

import html
import re

# Telegram Bot API message size limit (characters).
TELEGRAM_MAX_MESSAGE_LENGTH = 4096


def markdown_to_telegram_html(text: str) -> str:
    """Convert standard Markdown to Telegram-compatible HTML.

    The conversion is done in phases to avoid conflicts between similar
    Markdown patterns (e.g. ``*`` for lists vs italics).

    Args:
        text: Markdown-formatted text from the agent.

    Returns:
        Telegram HTML-formatted text.
    """
    if not text:
        return text

    # ------------------------------------------------------------------
    # Phase 1 — Extract code blocks & inline code (protect from escaping)
    # ------------------------------------------------------------------
    placeholders: list[str] = []

    def _ph(replacement_html: str) -> str:
        """Store pre-built HTML and return a placeholder token."""
        idx = len(placeholders)
        placeholders.append(replacement_html)
        return f"\x00PH{idx}\x00"

    # Fenced code blocks: ```lang\n...\n```
    def _sub_code_block(m: re.Match) -> str:
        lang = m.group(1) or ""
        code = html.escape(m.group(2).strip())
        if lang:
            return _ph(
                f'<pre><code class="language-{html.escape(lang)}">'
                f"{code}</code></pre>"
            )
        return _ph(f"<pre>{code}</pre>")

    text = re.sub(
        r"```(\w*)\n?(.*?)```", _sub_code_block, text, flags=re.DOTALL
    )

    # Inline code: `code`
    def _sub_inline_code(m: re.Match) -> str:
        return _ph(f"<code>{html.escape(m.group(1))}</code>")

    text = re.sub(r"`([^`\n]+)`", _sub_inline_code, text)

    # ------------------------------------------------------------------
    # Phase 2 — Escape HTML entities in the remaining text
    # ------------------------------------------------------------------
    text = html.escape(text)

    # ------------------------------------------------------------------
    # Phase 3 — Convert Markdown patterns to Telegram HTML
    # ------------------------------------------------------------------

    # Headings: # Title  →  <b>Title</b>
    text = re.sub(
        r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE
    )

    # Horizontal rules: ---, ***, ___
    text = re.sub(
        r"^[\-\*_]{3,}\s*$", "━━━━━━━━━━━━━━━", text, flags=re.MULTILINE
    )

    # Unordered list items: *, -, + (with 1-4 trailing spaces) → bullet
    # Must run BEFORE bold/italic so the leading * is consumed first.
    text = re.sub(r"^\s*[\*\-\+]\s{1,4}", "  • ", text, flags=re.MULTILINE)

    # Bold: **text** and __text__  (must run before italic)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)

    # Italic: *text* and _text_
    # Negative look-behind/-ahead for word chars avoids matching
    # inside_variable_names or stray asterisks.
    text = re.sub(
        r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<i>\1</i>", text
    )
    text = re.sub(
        r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"<i>\1</i>", text
    )

    # Strikethrough: ~~text~~
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)

    # Links: [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text
    )

    # Blockquotes: > text  (after html.escape, > became &gt;)
    # Merge consecutive quote lines into a single <blockquote>.
    lines = text.split("\n")
    merged: list[str] = []
    quote_buf: list[str] = []

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("&gt;"):
            content = stripped[4:].lstrip()
            quote_buf.append(content)
        else:
            if quote_buf:
                merged.append(
                    "<blockquote>"
                    + "\n".join(quote_buf)
                    + "</blockquote>"
                )
                quote_buf = []
            merged.append(line)

    if quote_buf:
        merged.append(
            "<blockquote>" + "\n".join(quote_buf) + "</blockquote>"
        )

    text = "\n".join(merged)

    # ------------------------------------------------------------------
    # Phase 4 — Restore protected placeholders
    # ------------------------------------------------------------------
    for idx, ph_html in enumerate(placeholders):
        text = text.replace(f"\x00PH{idx}\x00", ph_html)

    # ------------------------------------------------------------------
    # Phase 5 — Clean-up
    # ------------------------------------------------------------------
    # Collapse 3+ consecutive blank lines into at most 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_message(
    text: str,
    max_length: int = TELEGRAM_MAX_MESSAGE_LENGTH,
) -> list[str]:
    """Split text into chunks that fit Telegram's message size limit.

    Split priority:
        1. Paragraph boundary (double newline)
        2. Line boundary (single newline)
        3. Word boundary (space)
        4. Hard cut at ``max_length`` (last resort)

    Args:
        text: Text to split.
        max_length: Maximum characters per chunk.

    Returns:
        List of text chunks, each within the size limit.
    """
    if not text:
        return []
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            stripped = remaining.strip()
            if stripped:
                chunks.append(stripped)
            break

        # Try split at paragraph boundary
        split_pos = remaining.rfind("\n\n", 0, max_length)

        # Try line boundary
        if split_pos <= 0:
            split_pos = remaining.rfind("\n", 0, max_length)

        # Try word boundary
        if split_pos <= 0:
            split_pos = remaining.rfind(" ", 0, max_length)

        # Hard cut
        if split_pos <= 0:
            split_pos = max_length

        chunk = remaining[:split_pos].rstrip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_pos:].lstrip("\n")

    return chunks


def format_agent_response(text: str) -> str:
    """Format an agent response for Telegram display.

    Convenience wrapper that converts Markdown to Telegram HTML.
    If conversion fails for any reason, returns the original text
    with HTML entities escaped so it is safe for ``ParseMode.HTML``.

    Args:
        text: Raw agent response in Markdown.

    Returns:
        Telegram HTML-formatted text.
    """
    if not text:
        return text
    try:
        return markdown_to_telegram_html(text)
    except Exception:
        # Safety net: escape HTML so the text is still safe to send.
        return html.escape(text)
