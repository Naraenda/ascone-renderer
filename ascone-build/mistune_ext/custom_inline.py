import typing
import mistune
import re

class InlineDecorator:
    def __init__(
            self, 
            name: str,
            prefix: str, 
            suffix: typing.Optional[str] = None,
            tag: str = "span",
    ) -> None:
        """
        Initialize the InlineDecorator.
        """
        self.name = name
        self.prefix = re.escape(prefix)
        self.suffix = re.escape(suffix if suffix is not None else prefix)
        self.tag = tag

    def safe_name(self) -> str:
        return self.name.replace('-', '_') + '_inline'

    def build_regex(self) -> str:
        """
        Build the regex pattern for matching text to be decorated.
        """
        return self.prefix + rf"(?!\s)(?P<{self.safe_name()}_text>.+?)(?!\s)" + self.suffix
    
    def parser(self) -> typing.Callable[[mistune.InlineParser, re.Match[str], mistune.InlineState], int]:
        """
        Create a function to parse the text using the regex pattern and populate tokens.
        """
        def parse(
            inline: mistune.InlineParser,
            match: re.Match[str],
            state: mistune.InlineState
        ) -> int:
            """
            Parse the matched text and create a token.
            """
            text = match.group(f'{self.safe_name()}_text')
            new_state = state.copy()
            new_state.src = text
            children = inline.render(new_state)
            state.append_token({
                "type": self.safe_name(),
                "children": children,
            })
            return match.end()

        return parse
    
    def renderer(self) -> typing.Callable[[mistune.BaseRenderer, str], str]:
        """
        Create a function to render the text with HTML tags.
        """

        def render(
            renderer: mistune.BaseRenderer,
            text: str
        ) -> str:
            """
            Render the token into an HTML string.
            """
            return f'<{self.tag} class="{self.name}">{text}</{self.tag}>'

        return render

    def register(self, md: mistune.Markdown) -> None:
        """
        Register the decorator with a Markdown instance.
        """
        md.inline.register(self.safe_name(), self.build_regex(), self.parser())

        if md.renderer and md.renderer.NAME == 'html':
            md.renderer.register(self.safe_name(), self.renderer())
