from __future__ import annotations

import argparse
import fnmatch
import jinja2
import logging
import os
import pathlib
import typing
import shutil
import re

import bs4
import frontmatter
import sass
import mistune
import mistune.plugins.abbr
import mistune.plugins.footnotes
import mistune.plugins.formatting
import mistune.plugins.table
import mistune.plugins.task_lists
import mistune.plugins.math

import mistune.directives

import mistune_ext.custom_inline
import mistune_ext.wikilink
import mistune_ext.image
import mistune_ext.renderer

logger = logging.getLogger('ascone-build')

def apply_custom_rules(md: mistune.Markdown):
    """
    Apply our custom rulez to Mistune!
    """
    mistune_ext.custom_inline.InlineDecorator("effect-rainbow", r"//").register(md)
    mistune_ext.custom_inline.InlineDecorator("effect-shake", r"##").register(md)
    mistune_ext.custom_inline.InlineDecorator("effect-wave", r"((", r"))").register(md)
    mistune_ext.custom_inline.InlineDecorator("effect-spin", r"@@").register(md)

def glob_files(directory: pathlib.Path):
    """
    Globs all markdown files in a directory.
    """
    # Initialize an empty list to store matching file paths.
    md_files   : typing.List[pathlib.Path] = []
    other_files: typing.List[pathlib.Path] = []

    # Walk through the directory tree starting from 'directory'.
    for root, _, filenames in os.walk(directory):
        # Convert the current root path to an absolute path.
        root = pathlib.Path(root).absolute()

        # Filter files matching the pattern '*.md' (i.e., Markdown files).
        for filename in filenames:
            # Append the full path of each matching file to the matches
            # list, but keep markdown files separate.
            if fnmatch.fnmatch(filename, '*.md'):
                md_files.append(root.joinpath(filename))
            elif filename.split('.')[-1] in ['txt', 'png', 'jpg', 'jpeg', 'gif']:
                other_files.append(root.joinpath(filename))

    # Return the list of matching file paths.
    return (md_files, other_files)

NavTree: typing.TypeAlias = typing.Dict[str, typing.Tuple['NavTree', object]]

def cli():
    # Initialize an argument parser.
    parser = argparse.ArgumentParser(description="")

    # Define the command-line arguments.
    parser.add_argument(
        '--source',
        type=str,
        required=False,
        default='./_content',
        help='Directory containing Markdown.'
    )
    parser.add_argument(
        '--templates',
        type=str,
        required=False,
        default='./_templates',
        help='Directory containing Jinja2 templates.'
    )
    parser.add_argument(
        '--static',
        type=str,
        required=False,
        default='./_static',
        help='Directory containing static assets.'
    )
    parser.add_argument(
        '--styles',
        type=str,
        required=False,
        default='./_styles',
        help='Directory containing static assets.'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=False,
        default='./_dist',
        help='Output directory.'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Use verbose logging.'
    )

    # Parse the provided command-line arguments.
    args = parser.parse_args()

    # Configure the logger.
    log_stream = logging.StreamHandler()
    log_stream.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', '%H:%M:%S'))
    logger.addHandler(log_stream)
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    logger.info('Starting \'ascone-build\'!')

    # Convert the source and output directories to absolute paths.
    source_dir = pathlib.Path(args.source).absolute()
    output_dir = pathlib.Path(args.output).absolute()
    template_dir = pathlib.Path(args.templates).absolute()
    static_dir = pathlib.Path(args.static).absolute()
    styles_dir = pathlib.Path(args.styles).absolute()

    logger.info(f'Source    : {source_dir}')
    logger.info(f'Output    : {output_dir}')
    logger.info(f'Templates : {template_dir}')

    logger.info('Deleting pre-existing output dir')
    shutil.rmtree(path=output_dir, ignore_errors=True)

    logger.info('Copying static file contents')
    static_output_dir = output_dir.joinpath('static')
    shutil.copytree(src=static_dir, dst=static_output_dir, dirs_exist_ok=True)

    if styles_dir.exists():
        try:
            sass.compile(
                dirname=(str(styles_dir), str(output_dir.joinpath('static'))),
                output_style='compact'
            )
        except Exception as e:
            logger.error(f'Error compiling .sass in \'{styles_dir}\':\n{e}')

    # Initialize a markdown transpiler.
    logger.info('Initializing \'mistune\'...')
    renderer = mistune_ext.renderer.AsconeHTMLRenderer(escape=False)
    transpile = mistune.Markdown(
        renderer=renderer,
        plugins=[
            mistune.plugins.abbr.abbr,
            mistune.plugins.footnotes.footnotes,
            mistune.plugins.formatting.mark,
            mistune.plugins.formatting.strikethrough,
            mistune.plugins.table.table,
            mistune.plugins.task_lists.task_lists,
            mistune.plugins.math.math,
            mistune.directives.FencedDirective([
                mistune.directives.Image(),
            ]),
            mistune_ext.image.plugin,
            mistune_ext.wikilink.plugin,
            apply_custom_rules,
        ]
    )

    # Get the Jinja2 environment.
    templates = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))

    abs_md_paths, abs_asset_paths = glob_files(source_dir)
    num_md_files = len(abs_md_paths)

    md_files: dict[pathlib.Path, frontmatter.Post] = {}
    for i, abs_md_path in enumerate(abs_md_paths):
        # Determine the corresponding HTML output path.
        md_path = abs_md_path.relative_to(source_dir).with_suffix('')

        # Ensure the renderer can find this file
        renderer.register_relative_target(md_path)

        logger.info(f'[{i+1}/{num_md_files}] Processing: {md_path}')

        # Read the markdown content from the input file.
        with open(abs_md_path, 'r', encoding='utf-8') as file_stream:
            file = frontmatter.load(file_stream)
        meta = file.metadata

        # Extract draft property.
        is_draft = 'draft' in meta and meta['draft']

        # Ensure a default title.
        if 'title' not in meta:
            meta['title'] = md_path.name

        # Update the metadata.
        file.metadata = meta

        if not is_draft:
            md_files[md_path] = file
    
    # Create a mapping from relative asset paths to absolute asset paths
    asset_files: dict[pathlib.Path, pathlib.Path] = {}
    for i, abs_asset_path in enumerate(abs_asset_paths):
        # Determine the corresponding output path.
        rel_asset_path = abs_asset_path.relative_to(source_dir)

        # Ensure the renderer can find this file.
        renderer.register_relative_target(rel_asset_path)

        # Update mapping for future use.
        asset_files[rel_asset_path] = abs_asset_path

    # Update number of files since we may have skipped a few.
    num_md_files = len(md_files)

    # Convert the list of files into a tree-like structure. Which
    # can be used to generate the directory listing recursively.
    logger.info('Building navigation tree')
    nav_tree: NavTree = {}
    new_files: dict[pathlib.Path, frontmatter.Post] = {}
    for rel_path, file in md_files.items():
        node = nav_tree
        prev_data: tuple[NavTree, object] = ({}, None)

        # Split the path up into its parts.
        for i, part in enumerate(rel_path.parts[:-1]):
            # Add an empty node if it's not in the current node.
            if part not in node:
                index_path = pathlib.Path(f'{"/".join(rel_path.parts[:i + 1])}/index')
                if index_path not in md_files:
                    logger.info(f'Found dir without index: {index_path}')
                    new_files[index_path] = frontmatter.Post('')

                node[part] = ({}, {
                    'item': f'{index_path.parts[-2]}',
                    'url': f'/{index_path}.html',
                    'title': part,
                })

            # Keep track of the found (node, meta)-datatuple.
            prev_data = node[part]

            # Repeat this on the found node in the datatuple.
            node = prev_data[0]

        part = rel_path.parts[-1]

        if part == 'index':
            continue

        # Update the last found datatuple with the file's
        # metadata. We're replacing prev_data[1], but tuples
        # are passed by value so we have to construct it.
        node[part] = (node[part][0] if part in node else {}, {
            'item': f'{rel_path.parts[-1]}',
            'url': f'/{rel_path.as_posix()}.html',
            'title': file.metadata['title'],
        })

    md_files = md_files | new_files

    # Process each markdown file found in the source directory.
    for i, (rel_path, file) in enumerate(md_files.items()):
        logger.info(f'[{i+1}/{num_md_files}] Rendering: {rel_path}')
        meta = file.metadata

        # Find child pages
        child_pages = nav_tree
        for part in rel_path.parts:
            if part != 'index':
                child_pages = child_pages[part][0]

        # Determine the corresponding HTML output path.
        output_path = output_dir.joinpath(rel_path.with_suffix('.html'))
        
        # Attempt to find an associated template.
        try:
            template_name = meta['template'] or 'default' if 'template' in meta else 'default'
            template = templates.get_or_select_template([
                f'{template_name}{suffix}' for suffix in [
                    '.html.jinja2',
                    '.html.jinja',
                    '.html.j2',
                    '.html.j',
                    '.html',
                    '.jinja2',
                    '.jinja',
                    '.j2',
                    '.j',
                ]
            ])
        except Exception as e:
            logger.error(f'Error selecting a template for \'{rel_path}\':\n{e}')
            continue

        # Convert the markdown content to HTML using mistune.
        try:
            html_content = str(transpile(file.content))
        except Exception as e:
            logger.error(f'Error transpiling \'{rel_path}\' into HTML:\n{e}')
            continue

        # Replace horizontal lines with sectioning. Mistune will
        # use '<hr />'.
        if '' != html_content:
            html_content = '<section>' + html_content.replace('<hr />', '</section><section>') + '</section>'

        # Now try to inject that HTML content into a Jinja2 template.
        try:
            html = template.render({
                'meta': meta,
                'bread_crumbs': list(rel_path.parts),
                'child_pages': child_pages,
                'content': str(html_content),
                'nav': nav_tree,
            })
        except Exception as e:
            logger.error(f'Error rendering the template \'{template.name}\' for \'{rel_path}\':\n{e}')
            continue


        # The generated HTML is really ugly, so yes, I'm gonna use a whole
        # library to make it look a little nicer. :)
        html = bs4.BeautifulSoup(markup=html, features='html.parser')

        # TODO: move this somewhere else
        # Wrap individual chars in an element
        def wrap_chars(soup: bs4.BeautifulSoup, element: bs4.Tag):
            children: list[bs4.element.Tag] = []
            for child in element.contents:
                if isinstance(child, bs4.element.NavigableString):
                    for char in child:
                        span = soup.new_tag('span', **{'class': 'char'}) # type: ignore
                        span.string = str(char)
                        children.append(span)
                elif isinstance(child, bs4.element.Tag):
                    if child.name == 'span' and len(child.get_text()) <= 1:
                        children.append(child)
                    else:
                        children.append(wrap_chars(soup, child))

            element.clear(False)
            for child in children:
                element.append(child)
            return element
        
        # Wrap chars in spans that start with 'effect-'.
        for span in html.find_all('span', class_=re.compile(r'^effect-.*')):
            span.replace_with(
                wrap_chars(html, span) # type: ignore
            )

        # Ensure the output directory exists and write the HTML content to the file.
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # And write the HTML out to a file.
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(str(html))

    num_assets = len(asset_files)
    for i, (rel_asset_path, abs_asset_path) in enumerate(asset_files.items()):
        logger.info(f'[{i+1}/{num_assets}] Copying: {rel_asset_path}')

        # Use relative path to derive final output path.
        output_path = output_dir.joinpath(rel_asset_path)
        
        # Ensure output directory exists.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(abs_asset_path, output_path)