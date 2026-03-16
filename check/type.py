from core.context.check_context import CheckContext
from core.models.proxy_model import ProxyModel
from checkers.anonymity.anonymity_checker import AnonymityChecker
from checkers.business.business_availability_checker import BusinessAvailabilityChecker
from checkers.protocol.http_checker import HttpChecker
from checkers.protocol.https_checker import HttpsChecker
from checkers.protocol.protocol_aggregator import ProtocolAggregator
from checkers.protocol.socks5_checker import Socks5Checker


def check_socks5(ip, port, timeout=5):
    context = CheckContext(proxy=ProxyModel(ip=ip, port=int(port)))
    context.proxy.is_alive = True
    return Socks5Checker(timeout=timeout).check(context).success


def check_https(ip, port, timeout=5):
    context = CheckContext(proxy=ProxyModel(ip=ip, port=int(port)))
    context.proxy.is_alive = True
    return HttpsChecker(timeout=timeout).check(context).success


def check_http(ip, port, timeout=10, retry_times=2):
    context = CheckContext(proxy=ProxyModel(ip=ip, port=int(port)))
    context.proxy.is_alive = True
    result = HttpChecker(timeout=timeout, retry_times=retry_times).check(context)
    return result.success, result.latency_ms, result.metadata.get("working_target")


def check_anonymity_with_retry(ip, port, proxy_type, timeout=10, retry_times=2):
    context = CheckContext(proxy=ProxyModel(ip=ip, port=int(port)))
    context.proxy.is_alive = True
    context.proxy.proxy_type = proxy_type
    result = AnonymityChecker(timeout=timeout, retry_times=retry_times).check(context)
    return result.metadata.get("anonymity"), result.latency_ms


def check_business_availability(ip, port, proxy_type, timeout=10):
    context = CheckContext(proxy=ProxyModel(ip=ip, port=int(port)))
    context.proxy.is_alive = True
    context.proxy.proxy_type = proxy_type
    result = BusinessAvailabilityChecker(timeout=timeout).check(context)
    return result.metadata.get("business_score", 0)


def check_proxy_with_details(ip, port, timeout=5, retry_times=2):
    proxy = ProxyModel(ip=ip, port=int(port))
    proxy.is_alive = True
    context = CheckContext(proxy=proxy)
    socks = Socks5Checker(timeout=timeout).check(context)
    https = HttpsChecker(timeout=timeout).check(context)
    http = HttpChecker(timeout=timeout, retry_times=retry_times).check(context)
    context.add_check_result(socks)
    context.add_check_result(https)
    context.add_check_result(http)
    aggregate = ProtocolAggregator().check(context)
    proxy.socks5 = socks.success
    proxy.https = https.success
    proxy.http = http.success
    proxy.update_proxy_type()
    anonymity = None
    response_time = http.latency_ms
    business_score = 0
    if aggregate.success:
        anonym = AnonymityChecker(timeout=timeout, retry_times=retry_times).check(context)
        biz = BusinessAvailabilityChecker(timeout=timeout).check(context)
        anonymity = anonym.metadata.get("anonymity")
        response_time = anonym.latency_ms or response_time
        business_score = biz.metadata.get("business_score", 0)
    return proxy.socks5, proxy.https, proxy.http, proxy.proxy_type, anonymity, response_time, business_score
