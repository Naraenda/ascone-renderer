import typing
import mistune
import mistune.core
import mistune.inline_parser

def parse_image(
        inline: mistune.inline_parser.InlineParser,
        m: typing.Match[str],
        state: mistune.core.InlineState
    ) -> int:
    """Parse image syntax ![description](url)"""

    url = m.group('url').strip()
    description = m.group('description')

    # Create a image token
    state.append_token({
        "type": "image",
        "children": [{"type": "text", "raw": description}] if description else None,
        "attrs": {
            "url": url,
            "description": description if description else ""
        }
    })

    return m.end()

def render_wikilink_html(
        renderer: mistune.core.BaseRenderer,
        children: str,
        url: str,
        description: str
    ) -> str:
    """Render image as HTML img tag"""

    # TODO: add image description maybe as child tag? idfk
    url = url.replace(' ', '_')
    return f'<img src="/{url}" alt="{description}"></a>'

def plugin(
        md: mistune.Markdown
    ) -> None:
    """Plugin function to add image support to mistune"""

    # Use named groups
    IMAGE_PATTERN = r'!\[(?P<description>[^|\]]+)\]\((?P<url>[^\]]+)\)'
    md.inline.register("image", IMAGE_PATTERN, parse_image, before="link")

    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("image", render_wikilink_html)
