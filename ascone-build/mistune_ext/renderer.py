import logging
import pathlib
import re
import typing

import mistune

logger = logging.getLogger('ascone-build')

TargetTree: typing.TypeAlias = typing.Dict[str, typing.Tuple['TargetTree', typing.Optional[pathlib.Path]]]

class AsconeHTMLRenderer(mistune.HTMLRenderer):

    def link(self, text: str, url: str, title: typing.Optional[str] = None) -> str:
        if self.is_relative_target(url):
            # Strip '.md'-suffix and keep track of it.
            target = url
            is_md = False
            if target.endswith('.md'):
                is_md = True
                target = target[:-3]

            # Do a more relaxed lookup now.
            url = self.lookup_relative_target(target) or url

            # Restore '.md'-suffix.
            if is_md:
                url = f'{url}.md'

        return super().link(text, url, title)

    def image(self, text: str, url: str, title: typing.Optional[str] = None) -> str:
        # If url is relative, then try to get the full path of what
        # it is describing.
        if self.is_relative_target(url):
            url = self.lookup_relative_target(url) or url

        return super().image(text, url, title)
    
    # Targets contain a lookup map of filename/directories
    targets: TargetTree = {}

    def is_relative_target(self, target: str):
        if target.startswith('/'):
            return False
        PROTOCOL_REGEX = r'^\w+://'
        if re.match(PROTOCOL_REGEX, target):
            return False
        return True
    
    def lookup_relative_target(self, target: str) -> typing.Optional[str]:
        # Match starting from filename and ending in the root directory
        target_parts = reversed(pathlib.Path(target).parts)

        hay = self.targets
        result = None
        for needle in target_parts:
            if needle not in hay:
                return target # Fallback
            hay, result = hay[needle]

        if result:
            logger.info(f'Relative map: {target} => {result}')
            return f'/{result}'

        logger.warning(f'No match found for {target}!')
        return target # Fallback
    
    def register_relative_target(self, path: pathlib.Path):
        # Store path, starting from filename and ending in the root directory
        target_path  = list(reversed(path.parts))
        target_depth = len(target_path)

        part_targets = self.targets
        part_depth   = 1
        for part in target_path:
            if part not in part_targets:
                part_targets[part] = ({}, path)
            elif part_depth == target_depth:
                part_targets[part] = (part_targets[part][0], path)

            part_targets = part_targets[part][0]

