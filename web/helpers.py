import re
from flask import request
from urllib.parse import urlparse, urljoin


# only within app context
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def is_url_for(url, domain):
    """domain = without .www"""
    domain_parsed = urlparse(domain)
    re_domain = re.compile(f"^(www\\.)?{domain_parsed.netloc}$")
    try:
        url_parsed = urlparse(url)
        return url_parsed.scheme == domain_parsed.scheme \
            and re_domain.search(url_parsed.netloc) is not None
    except Exception:
        return False
