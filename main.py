from collectors import DEFAULT_LAST_DATA_PATH, DEFAULT_LAST_DATA_JSON_PATH, LastDataJsonTransformer
from check.main_check import full_proxy_check, load_proxys, print_full_proxy_info


if __name__ == "__main__":
    payload = LastDataJsonTransformer().transform(str(DEFAULT_LAST_DATA_PATH), str(DEFAULT_LAST_DATA_JSON_PATH))
    proxies = load_proxys(str(DEFAULT_LAST_DATA_PATH))
    print(f"Loaded {len(proxies)} proxies from file: {DEFAULT_LAST_DATA_PATH}")
    print(f"Generated JSON dataset with {payload['record_count']} records: {DEFAULT_LAST_DATA_JSON_PATH}")
    alive_proxies = full_proxy_check(proxies, max_workers=150, save_to_db=True)
    print(f"Check completed: {len(alive_proxies)} proxies are alive.")
    for proxy in alive_proxies:
        print_full_proxy_info(proxy)
