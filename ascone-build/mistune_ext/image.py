import typing
import mistune
import mistune.core
import mistune.inline_parser

def parse_image(
        inline: mistune.inline_parser.InlineParser,
        m: typing.Match[str],
        state: mistune.core.InlineState
    ) -> int:
    """Parse image syntax ![desc](url) ![[url|desc]]"""

    img_a   = m.group('img_a')
    img_b   = m.group('img_b')
    is_wiki = m.group('img_is_wiki')

    url  = img_a if is_wiki else img_b
    desc = img_b if is_wiki else img_a

    # Create a image token
    state.append_token({
        "type": "image",
        "attrs": {
            "url": url,
            "text": desc if desc else url,
        }
    })

    return m.end()

def render_image_html(
        renderer: mistune.core.BaseRenderer,
        text: str,
        **attrs: str,
        # display: str
    ) -> str:
    """Render image as HTML img tag"""

    url = attrs['href']

    url = url.replace(' ', '_')
    return f'<img src="/{url}" alt=""></a>'

def plugin(
        md: mistune.Markdown
    ) -> None:
    """Plugin function to add image support to mistune"""

    # Use named groups
    IMAGE_PATTERN = r'!\[(?P<img_is_wiki>\[)?(?P<img_a>(?(img_is_wiki)[^|\]]|[^\]])*)(?(img_is_wiki)(?P<img_has_wiki_desc>\|)?|\]\()(?P<img_b>[^\]]*)(?(img_is_wiki)\]\]|\))'
    md.inline.register("image", IMAGE_PATTERN, parse_image, before="link")

    # if md.renderer and md.renderer.NAME == "html":
    #     md.renderer.register("image", render_image_html)
