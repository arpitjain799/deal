from pathlib import Path
from textwrap import dedent

import pytest
import deal
from sphinx.cmd.build import build_main


@deal.raises(ValueError, ZeroDivisionError)
def example_sphinx():
    """Example function.

    :return: The return value. True for success, False otherwise.
    :rtype: bool
    """
    return True


@deal.raises(ValueError, ZeroDivisionError)
def example_google():
    """Example function.

    Returns:
        bool: The return value. True for success, False otherwise.
    """
    return True


@pytest.mark.parametrize('style', ['Sphinx', 'Google'])
def test_sphinx(style: str, tmp_path: Path):
    path_in = tmp_path / 'in'
    path_in.mkdir()
    path_out = tmp_path / 'out'
    (path_in / 'conf.py').write_text(dedent(f"""
        import deal

        def setup(app):
            deal.AutoDoc.{style}.register(app)
    """))
    (path_in / 'index.rst').write_text(dedent(f"""
        .. autofunction:: tests.test_sphinx.example_{style.lower()}
    """))
    exit_code = build_main([str(path_in), str(path_out), '-ET'])
    assert exit_code == 0
    content = (path_out / 'index.html').read_text()
    assert 'ValueError' in content
    assert 'ZeroDivisionError' in content
