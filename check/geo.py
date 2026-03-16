from core.context.check_context import CheckContext
from core.models.proxy_model import ProxyModel
from checkers.geo.exit_geo_checker import ExitGeoChecker
from checkers.geo.ip_geo_fallback_checker import IpGeoFallbackChecker


def check_geo_via_proxy(proxy, timeout=5):
    context = CheckContext(proxy=proxy)
    result = ExitGeoChecker(timeout=timeout).check(context)
    if result.success:
        proxy.geo_source = result.metadata.get("geo_source")
        proxy.exit_ip = result.metadata.get("exit_ip")
        proxy.country = result.metadata.get("country")
        proxy.city = result.metadata.get("city")
        proxy.isp = result.metadata.get("isp")
        return True
    return False


def check_geo_by_ip(ip, timeout=5):
    proxy = ProxyModel(ip=ip, port=0)
    context = CheckContext(proxy=proxy)
    result = IpGeoFallbackChecker(timeout=timeout).check(context)
    if not result.success:
        return None
    return {
        "country": result.metadata.get("country"),
        "city": result.metadata.get("city"),
        "isp": result.metadata.get("isp"),
        "source": result.metadata.get("geo_source"),
    }


def check_geo_with_retry(proxy, timeout=5, max_retries=2):
    for _ in range(max_retries + 1):
        if check_geo_via_proxy(proxy, timeout):
            return True
    result = check_geo_by_ip(proxy.ip, timeout)
    if result:
        proxy.country = result["country"]
        proxy.city = result["city"]
        proxy.isp = result["isp"]
        proxy.geo_source = result["source"]
        return True
    return False
