from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from core.context.check_context import CheckContext


class CheckPipeline:
    def __init__(self, checkers, security_checkers, scorers, repository=None, max_workers: int = 100):
        self.checkers = sorted(checkers, key=lambda item: item.order)
        self.security_checkers = sorted(security_checkers, key=lambda item: item.order)
        self.scorers = scorers
        self.repository = repository
        self.max_workers = max_workers

    def run_for_proxy(self, proxy):
        context = CheckContext(proxy=proxy)

        for checker in self.checkers:
            if not checker.enabled or not checker.supports(context):
                continue
            result = checker.check(context)
            context.add_check_result(result)
            self._apply_check_result(context, result)
            if checker.blocking and not result.success:
                break

        if context.proxy.is_usable:
            for checker in self.security_checkers:
                if checker.enabled and checker.supports(context):
                    result = checker.check(context)
                    context.add_security_result(result)

        for scorer in self.scorers:
            scorer.score(context)

        if self.repository and context.proxy.is_alive:
            self.repository.save_proxy(context.proxy)
        return context

    def run_batch(self, proxies):
        contexts = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {executor.submit(self.run_for_proxy, proxy): proxy for proxy in proxies}
            for future in as_completed(future_map):
                contexts.append(future.result())
        return contexts

    def _apply_check_result(self, context: CheckContext, result) -> None:
        proxy = context.proxy
        if result.checker_name == "tcp_checker":
            if result.success:
                proxy.is_alive = True
            else:
                proxy.record_fail()
                proxy.is_alive = False
            proxy.update_check_time()
            return

        if result.checker_name == "socks5_checker":
            proxy.socks5 = bool(result.metadata.get("socks5"))
        elif result.checker_name == "https_checker":
            proxy.https = bool(result.metadata.get("https"))
        elif result.checker_name == "http_checker":
            proxy.http = bool(result.metadata.get("http"))
            proxy.response_time = result.latency_ms or proxy.response_time
        elif result.checker_name == "protocol_aggregator":
            proxy.http = bool(result.metadata.get("http"))
            proxy.https = bool(result.metadata.get("https"))
            proxy.socks5 = bool(result.metadata.get("socks5"))
            proxy.update_proxy_type()
            if proxy.proxy_type:
                proxy.record_success()
            else:
                proxy.is_alive = False
                proxy.record_fail()
        elif result.checker_name == "anonymity_checker" and result.success:
            proxy.anonymity = result.metadata.get("anonymity")
            proxy.response_time = result.latency_ms or proxy.response_time
        elif result.checker_name in {"exit_geo_checker", "ip_geo_fallback_checker"} and result.success:
            proxy.geo_source = result.metadata.get("geo_source")
            proxy.exit_ip = result.metadata.get("exit_ip", proxy.exit_ip)
            proxy.country = result.metadata.get("country")
            proxy.city = result.metadata.get("city")
            proxy.isp = result.metadata.get("isp")
        elif result.checker_name == "business_availability_checker":
            proxy.business_score = int(result.metadata.get("business_score", 0))
