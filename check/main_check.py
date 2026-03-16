from collections.abc import Iterable

from check.geo import check_geo_by_ip, check_geo_with_retry
from collectors.file_collector import FileProxyCollector
from services.proxy_check_service import ProxyCheckService


def load_proxys(file_path):
    return FileProxyCollector().collect(file_path)


def test_one_proxy(proxy):
    service = ProxyCheckService(repository=None)
    result = service.run_full_check([proxy], max_workers=1, save_to_db=False)
    return result[0] if result else proxy


def test_proxies_type(proxies, max_workers=150):
    return set(ProxyCheckService(repository=None).run_full_check(proxies, max_workers=max_workers, save_to_db=False))


def print_content_type(proxy):
    print(f"Proxy: {proxy.ip}:{proxy.port}")
    print(f"  Alive: {proxy.is_alive}")
    print(f"  Type: {proxy.proxy_type}")
    print(f"  Protocols - HTTP: {proxy.http}, HTTPS: {proxy.https}, SOCKS5: {proxy.socks5}")
    print(f"  Anonymity: {proxy.anonymity}")
    print(f"  Response Time: {proxy.response_time:.2f}ms" if proxy.response_time else "  Response Time: N/A")
    print(f"  Business Score: {proxy.business_score}/3")
    print(f"  Quality Score: {proxy.quality_score}")
    print(f"  Security Risk: {proxy.security_risk}")
    print(f"  Last Check: {proxy.last_check_time}")


def test_proxy_geo(proxy):
    exit_ok = check_geo_with_retry(proxy, timeout=5, max_retries=2)
    ip_geo = check_geo_by_ip(proxy.ip)
    print(f"Proxy: {proxy.ip}:{proxy.port}")
    print(f"  Exit Geo   : {proxy.country}, {proxy.city}, {proxy.isp} (source: {proxy.geo_source})" if exit_ok else "  Exit Geo   : Failed")
    print(f"  IP Geo     : {ip_geo['country']}, {ip_geo['city']}, {ip_geo['isp']} (source: {ip_geo['source']})" if ip_geo else "  IP Geo     : Failed")


def full_proxy_check(proxies: Iterable, max_workers=150, save_to_db=True):
    return ProxyCheckService().run_full_check(proxies, max_workers=max_workers, save_to_db=save_to_db)


def print_full_proxy_info(proxy):
    print("\n" + "-" * 60)
    print(f"IP: {proxy.ip}:{proxy.port}")
    print(f"Source: {proxy.source}")
    print(f"Status: {'Alive' if proxy.is_alive else 'Dead'}")
    print(f"Proxy Type: {proxy.proxy_type}")
    print(f"Protocols: HTTP={proxy.http}, HTTPS={proxy.https}, SOCKS5={proxy.socks5}")
    print(f"Anonymity: {proxy.anonymity}")
    print(f"Country: {proxy.country}")
    print(f"City: {proxy.city}")
    print(f"ISP: {proxy.isp}")
    print(f"Response Time: {proxy.response_time:.2f}ms" if proxy.response_time else "Response Time: N/A")
    print(f"Business Score: {proxy.business_score}/3")
    print(f"Quality Score: {proxy.quality_score}")
    print(f"Security Risk: {proxy.security_risk}")
    print(f"Security Flags: {proxy.security_flags}")
    print(f"Success Count: {proxy.success_count}")
    print(f"Fail Count: {proxy.fail_count}")
    print(f"Last Check: {proxy.last_check_time}")
    print("-" * 60)
