import pytest
import os
import sys
import tempfile
import markdown

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "Website"))

def test_markdown_rendering():
    md_content = "# Hello\n\nThis is **bold** text."
    html = markdown.markdown(md_content)
    assert "<h1>Hello</h1>" in html
    assert "<strong>bold</strong>" in html

def test_css_file_exists():
    css_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "Website", "static", "box5.css"
    )
    assert os.path.exists(css_path)
    with open(css_path) as f:
        content = f.read()
        assert ":root" in content
        assert "--primary-color" in content

def test_templates_exist():
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Website", "templates")
    for name in ["login.html", "index.html", "view.html"]:
        path = os.path.join(base, name)
        assert os.path.exists(path)