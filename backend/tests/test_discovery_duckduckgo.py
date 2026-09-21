from hubapp.discovery.duckduckgo import _unwrap_redirect


def test_unwraps_ddg_redirect_link():
    href = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.roborock.com%2Fmanuals%2Fs7.pdf&rut=abc123"
    assert _unwrap_redirect(href) == "https://www.roborock.com/manuals/s7.pdf"


def test_leaves_direct_links_unchanged():
    href = "https://www.roborock.com/manuals/s7.pdf"
    assert _unwrap_redirect(href) == href
