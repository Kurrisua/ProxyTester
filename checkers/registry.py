from __future__ import annotations

from checkers.anonymity.anonymity_checker import AnonymityChecker
from checkers.business.business_availability_checker import BusinessAvailabilityChecker
from checkers.connectivity.tcp_checker import TcpChecker
from checkers.geo.exit_geo_checker import ExitGeoChecker
from checkers.geo.ip_geo_fallback_checker import IpGeoFallbackChecker
from checkers.protocol.http_checker import HttpChecker
from checkers.protocol.https_checker import HttpsChecker
from checkers.protocol.protocol_aggregator import ProtocolAggregator
from checkers.protocol.socks5_checker import Socks5Checker


def build_default_checkers() -> list:
    return [
        TcpChecker(),
        Socks5Checker(),
        HttpsChecker(),
        HttpChecker(),
        ProtocolAggregator(),
        AnonymityChecker(),
        ExitGeoChecker(),
        IpGeoFallbackChecker(),
        BusinessAvailabilityChecker(),
    ]
