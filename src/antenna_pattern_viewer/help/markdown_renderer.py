"""
Markdown to HTML renderer with LaTeX equation support via MathJax.

Adapted from UmbraAntennaDesigner's help system. Provides a self-contained
markdown-to-HTML converter with support for:
- Headers, paragraphs, lists, tables, blockquotes, code blocks
- Inline formatting (bold, italic, code, links)
- LaTeX equations via MathJax 3 CDN (display and inline)
- Graceful fallback to Unicode text when MathJax is unavailable
"""

import re
from typing import Optional


class MarkdownRenderer:
    """Render markdown to HTML with LaTeX math support via MathJax."""

    # MathJax configuration for LaTeX rendering
    MATHJAX_CONFIG = '''
    <script>
    MathJax = {
        tex: {
            inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
            displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
            processEscapes: true,
            processEnvironments: true
        },
        options: {
            skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
        },
        svg: {
            fontCache: 'global'
        }
    };
    </script>
    <script id="MathJax-script" async
            src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js">
    </script>
    '''

    # CSS styling
    DEFAULT_CSS = '''
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        line-height: 1.6;
        color: #333;
        margin: 20px;
        background-color: #fff;
    }
    h1 {
        color: #2c3e50;
        border-bottom: 2px solid #2980b9;
        padding-bottom: 10px;
        margin-top: 0;
    }
    h2 {
        color: #34495e;
        margin-top: 25px;
        border-bottom: 1px solid #bdc3c7;
        padding-bottom: 5px;
    }
    h3 {
        color: #7f8c8d;
        margin-top: 20px;
    }
    h4 {
        color: #95a5a6;
        margin-top: 15px;
    }
    p {
        margin: 10px 0;
    }
    code {
        background-color: #f8f9fa;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 90%;
        color: #c7254e;
    }
    pre {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 5px;
        padding: 15px;
        margin: 15px 0;
        overflow-x: auto;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 13px;
        line-height: 1.4;
    }
    pre code {
        background-color: transparent;
        padding: 0;
        color: inherit;
    }
    ul, ol {
        padding-left: 25px;
        margin: 10px 0;
    }
    li {
        margin: 5px 0;
    }
    blockquote {
        border-left: 4px solid #2980b9;
        padding: 10px 15px;
        margin: 15px 0;
        background-color: #f8f9fa;
        color: #555;
    }
    blockquote.note {
        border-left-color: #f39c12;
        background-color: #fef9e7;
    }
    blockquote.warning {
        border-left-color: #e74c3c;
        background-color: #fdedec;
    }
    table {
        border-collapse: collapse;
        margin: 15px 0;
        width: 100%;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 10px;
        text-align: left;
    }
    th {
        background-color: #f8f9fa;
        font-weight: 600;
    }
    tr:nth-child(even) {
        background-color: #fafafa;
    }
    a {
        color: #2980b9;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    .equation {
        margin: 20px 0;
        text-align: center;
        font-family: 'Cambria Math', 'Times New Roman', serif;
        font-size: 110%;
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 5px;
        color: #2c3e50;
        line-height: 1.8;
    }
    .equation-fallback {
        margin: 15px 0;
        padding: 12px 20px;
        background-color: #f0f4f8;
        border-left: 4px solid #2980b9;
        font-family: 'Cambria Math', 'Times New Roman', serif;
        font-size: 105%;
        color: #2c3e50;
    }
    hr {
        border: none;
        border-top: 1px solid #ddd;
        margin: 25px 0;
    }
    '''

    def __init__(self, enable_mathjax: bool = True, custom_css: Optional[str] = None):
        """
        Initialize the markdown renderer.

        Args:
            enable_mathjax: Whether to include MathJax for LaTeX rendering
            custom_css: Optional custom CSS to override defaults
        """
        self.enable_mathjax = enable_mathjax
        self.css = custom_css if custom_css else self.DEFAULT_CSS

    def render(self, markdown_text: str, title: str = "", section: str = "") -> str:
        """
        Convert markdown to HTML with LaTeX support.

        Args:
            markdown_text: Markdown content to render
            title: Optional document title
            section: Optional section breadcrumb

        Returns:
            Complete HTML document string
        """
        body_html = self._convert_markdown(markdown_text)

        html_parts = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '<meta charset="UTF-8">',
            f'<title>{title}</title>',
            f'<style>{self.css}</style>',
        ]

        if self.enable_mathjax:
            html_parts.append(self.MATHJAX_CONFIG)

        html_parts.extend([
            '</head>',
            '<body>',
        ])

        if section:
            html_parts.append(f'<div class="section-header"><h2>{section}</h2></div>')

        html_parts.extend([
            body_html,
            '</body>',
            '</html>'
        ])

        return '\n'.join(html_parts)

    def _convert_markdown(self, text: str) -> str:
        """Convert markdown syntax to HTML."""
        if not self.enable_mathjax:
            text = self._convert_display_equations(text)

        lines = text.split('\n')
        html_lines = []
        in_code_block = False
        code_lang = ''
        in_list = False
        list_type = None
        in_table = False
        table_rows = []
        in_equation_block = False
        equation_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Handle display equation blocks ($$...$$) when MathJax is enabled
            if self.enable_mathjax and line.strip() == '$$':
                if in_equation_block:
                    html_lines.append('<div class="equation">$$')
                    html_lines.extend(equation_lines)
                    html_lines.append('$$</div>')
                    equation_lines = []
                    in_equation_block = False
                else:
                    self._close_list(html_lines, in_list, list_type)
                    in_list = False
                    in_equation_block = True
                i += 1
                continue

            if in_equation_block:
                equation_lines.append(line)
                i += 1
                continue

            # Handle code blocks
            if line.strip().startswith('```'):
                if in_code_block:
                    html_lines.append('</code></pre>')
                    in_code_block = False
                    code_lang = ''
                else:
                    code_lang = line.strip()[3:].strip()
                    lang_class = f' class="language-{code_lang}"' if code_lang else ''
                    html_lines.append(f'<pre><code{lang_class}>')
                    in_code_block = True
                i += 1
                continue

            if in_code_block:
                escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_lines.append(escaped)
                i += 1
                continue

            # Handle tables
            if '|' in line and not line.strip().startswith('|--'):
                if not in_table:
                    in_table = True
                    table_rows = []
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if cells:
                    table_rows.append(cells)
                i += 1
                continue
            elif in_table and (line.strip().startswith('|--') or line.strip().startswith('| --')):
                i += 1
                continue
            elif in_table and '|' not in line:
                html_lines.append(self._render_table(table_rows))
                in_table = False
                table_rows = []

            # Handle headers
            if line.startswith('#### '):
                self._close_list(html_lines, in_list, list_type)
                in_list = False
                html_lines.append(f'<h4>{self._inline_format(line[5:])}</h4>')
            elif line.startswith('### '):
                self._close_list(html_lines, in_list, list_type)
                in_list = False
                html_lines.append(f'<h3>{self._inline_format(line[4:])}</h3>')
            elif line.startswith('## '):
                self._close_list(html_lines, in_list, list_type)
                in_list = False
                html_lines.append(f'<h2>{self._inline_format(line[3:])}</h2>')
            elif line.startswith('# '):
                self._close_list(html_lines, in_list, list_type)
                in_list = False
                html_lines.append(f'<h1>{self._inline_format(line[2:])}</h1>')

            # Handle blockquotes
            elif line.startswith('> '):
                self._close_list(html_lines, in_list, list_type)
                in_list = False
                quote_content = line[2:]
                if '**NOTE:' in quote_content or '**TODO:' in quote_content:
                    html_lines.append(f'<blockquote class="note">{self._inline_format(quote_content)}</blockquote>')
                elif '**WARNING:' in quote_content:
                    html_lines.append(f'<blockquote class="warning">{self._inline_format(quote_content)}</blockquote>')
                else:
                    html_lines.append(f'<blockquote>{self._inline_format(quote_content)}</blockquote>')

            # Handle unordered lists
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                if not in_list or list_type != 'ul':
                    self._close_list(html_lines, in_list, list_type)
                    html_lines.append('<ul>')
                    in_list = True
                    list_type = 'ul'
                content = line.strip()[2:]
                html_lines.append(f'<li>{self._inline_format(content)}</li>')

            # Handle ordered lists
            elif re.match(r'^\s*\d+\.\s', line):
                if not in_list or list_type != 'ol':
                    self._close_list(html_lines, in_list, list_type)
                    html_lines.append('<ol>')
                    in_list = True
                    list_type = 'ol'
                content = re.sub(r'^\s*\d+\.\s', '', line)
                html_lines.append(f'<li>{self._inline_format(content)}</li>')

            # Handle horizontal rules
            elif line.strip() in ['---', '***', '___']:
                self._close_list(html_lines, in_list, list_type)
                in_list = False
                html_lines.append('<hr>')

            # Handle paragraphs
            elif line.strip():
                self._close_list(html_lines, in_list, list_type)
                in_list = False
                html_lines.append(f'<p>{self._inline_format(line)}</p>')

            # Empty lines
            else:
                self._close_list(html_lines, in_list, list_type)
                in_list = False

            i += 1

        # Close any remaining structures
        self._close_list(html_lines, in_list, list_type)
        if in_code_block:
            html_lines.append('</code></pre>')
        if in_table and table_rows:
            html_lines.append(self._render_table(table_rows))

        return '\n'.join(html_lines)

    def _close_list(self, html_lines: list, in_list: bool, list_type: Optional[str]):
        """Close an open list if needed."""
        if in_list and list_type:
            html_lines.append(f'</{list_type}>')

    def _render_table(self, rows: list) -> str:
        """Render a markdown table to HTML."""
        if not rows:
            return ''

        html = ['<table>']

        # First row is header
        html.append('<thead><tr>')
        for cell in rows[0]:
            html.append(f'<th>{self._inline_format(cell)}</th>')
        html.append('</tr></thead>')

        # Remaining rows are body
        if len(rows) > 1:
            html.append('<tbody>')
            for row in rows[1:]:
                html.append('<tr>')
                for cell in row:
                    html.append(f'<td>{self._inline_format(cell)}</td>')
                html.append('</tr>')
            html.append('</tbody>')

        html.append('</table>')
        return '\n'.join(html)

    def _inline_format(self, text: str) -> str:
        """Apply inline formatting (bold, italic, code, links)."""
        # Inline code
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

        # Bold
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', text)

        # Italic
        text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
        text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)

        # Links [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

        # Handle inline LaTeX when MathJax not available
        if not self.enable_mathjax:
            text = self._convert_latex_to_text(text)

        return text

    def _convert_display_equations(self, text: str) -> str:
        """Convert display equations ($$...$$) to styled divs when MathJax isn't available."""
        def convert_display_math(match):
            latex = match.group(1).strip()
            readable = self._latex_to_readable(latex)
            readable = re.sub(r'\n+', '<br>', readable)
            return f'<div class="equation-fallback">{readable}</div>'

        text = re.sub(r'\$\$(.*?)\$\$', convert_display_math, text, flags=re.DOTALL)
        return text

    def _convert_latex_to_text(self, text: str) -> str:
        """Convert LaTeX math to readable text when MathJax isn't available."""
        def convert_inline_math(match):
            latex = match.group(1)
            readable = self._latex_to_readable(latex)
            return f'<span style="font-family: serif; font-style: italic; color: #2c3e50;">{readable}</span>'

        text = re.sub(r'\$([^$]+)\$', convert_inline_math, text)
        return text

    def _latex_to_readable(self, latex: str) -> str:
        """Convert LaTeX notation to readable Unicode text."""
        replacements = [
            # Greek letters
            (r'\\alpha', 'α'), (r'\\beta', 'β'), (r'\\gamma', 'γ'),
            (r'\\delta', 'δ'), (r'\\epsilon', 'ε'), (r'\\varepsilon', 'ε'),
            (r'\\zeta', 'ζ'), (r'\\eta', 'η'), (r'\\theta', 'θ'),
            (r'\\iota', 'ι'), (r'\\kappa', 'κ'), (r'\\lambda', 'λ'),
            (r'\\mu', 'μ'), (r'\\nu', 'ν'), (r'\\xi', 'ξ'),
            (r'\\pi', 'π'), (r'\\rho', 'ρ'), (r'\\sigma', 'σ'),
            (r'\\tau', 'τ'), (r'\\upsilon', 'υ'), (r'\\phi', 'φ'),
            (r'\\varphi', 'φ'), (r'\\chi', 'χ'), (r'\\psi', 'ψ'),
            (r'\\omega', 'ω'),
            (r'\\Gamma', 'Γ'), (r'\\Delta', 'Δ'), (r'\\Theta', 'Θ'),
            (r'\\Lambda', 'Λ'), (r'\\Xi', 'Ξ'), (r'\\Pi', 'Π'),
            (r'\\Sigma', 'Σ'), (r'\\Phi', 'Φ'), (r'\\Psi', 'Ψ'),
            (r'\\Omega', 'Ω'),
            # Operators and symbols
            (r'\\times', '×'), (r'\\cdot', '·'), (r'\\div', '÷'),
            (r'\\pm', '±'), (r'\\mp', '∓'), (r'\\leq', '≤'), (r'\\geq', '≥'),
            (r'\\neq', '≠'), (r'\\approx', '≈'), (r'\\equiv', '≡'),
            (r'\\propto', '∝'), (r'\\infty', '∞'),
            (r'\\partial', '∂'), (r'\\nabla', '∇'),
            (r'\\int', '∫'), (r'\\sum', 'Σ'), (r'\\prod', 'Π'),
            (r'\\sqrt', '√'),
            (r'\\rightarrow', '→'), (r'\\leftarrow', '←'),
            (r'\\Rightarrow', '⇒'), (r'\\Leftarrow', '⇐'),
            # Formatting
            (r'\\mathbf\{([^}]+)\}', r'\1'), (r'\\mathbf', ''),
            (r'\\mathrm\{([^}]+)\}', r'\1'), (r'\\mathrm', ''),
            (r'\\text\{([^}]+)\}', r'\1'), (r'\\text', ''),
            (r'\\hat\{([^}]+)\}', '\\1\u0302'), (r'\\hat', ''),
            (r'\\vec\{([^}]+)\}', '\\1\u20d7'), (r'\\vec', ''),
            (r'\\bar\{([^}]+)\}', '\\1\u0304'), (r'\\bar', ''),
            # Fractions
            (r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)'),
            # Subscripts and superscripts
            (r'_\{([^}]+)\}', r'_\1'), (r'\^{([^}]+)\}', r'^\1'),
            (r'_(\w)', r'_\1'), (r'\^(\w)', r'^\1'),
            # Clean up braces
            (r'\{', ''), (r'\}', ''),
            (r'\\,', ' '), (r'\\;', ' '), (r'\\quad', '  '),
            (r'\\left', ''), (r'\\right', ''),
            (r'\\\[', ''), (r'\\\]', ''),
        ]

        result = latex
        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result)

        return result


def render_markdown_to_html(markdown_text: str, title: str = "",
                            section: str = "", enable_mathjax: bool = True) -> str:
    """
    Convenience function to render markdown to HTML.

    Args:
        markdown_text: Markdown content to render
        title: Optional document title
        section: Optional section breadcrumb
        enable_mathjax: Whether to include MathJax for LaTeX

    Returns:
        Complete HTML document string
    """
    renderer = MarkdownRenderer(enable_mathjax=enable_mathjax)
    return renderer.render(markdown_text, title, section)
