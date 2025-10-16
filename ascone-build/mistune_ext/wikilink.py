import typing
import mistune
import mistune.core
import mistune.inline_parser

def parse_wikilink(
        inline: mistune.inline_parser.InlineParser,
        m: typing.Match[str],
        state: mistune.core.InlineState
    ) -> int:
    """Parse wikilink syntax [[page title]] or [[page title|display text]]"""

    page_title = m.group('page').strip()
    display_text = m.group('display')

    # Use display text if provided, otherwise use page title
    if display_text is not None:
        text = display_text.strip()
    else:
        text = page_title

    # Create a wikilink token
    state.append_token({
        "type": "wikilink",
        "children": [{"type": "text", "raw": text}],
        "attrs": {
            "page": page_title,
            "display": text
        }
    })

    return m.end()

def render_wikilink_html(
        renderer: mistune.core.BaseRenderer,
        children: str,
        page: str,
        display: str
    ) -> str:
    """Render wikilink as HTML anchor tag"""

    url_page = page.replace(' ', '_')
    return f'<a href="/{url_page}.html" class="wikilink">{children}</a>'

def plugin(
        md: mistune.Markdown
    ) -> None:
    """Plugin function to add wikilink support to mistune"""

    # Use named groups
    WIKILINK_PATTERN = r'\[\[(?P<page>[^|\]]+)(?:\|(?P<display>[^\]]+))?\]\]'
    md.inline.register("wikilink", WIKILINK_PATTERN, parse_wikilink, before="link")

    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("wikilink", render_wikilink_html)
