from check.main_check import full_proxy_check, load_proxys, print_full_proxy_info


if __name__ == "__main__":
    proxies = load_proxys("lastData.txt")
    print(f"Loaded {len(proxies)} proxies from file")
    alive_proxies = full_proxy_check(proxies, max_workers=150, save_to_db=True)
    print(f"Check completed: {len(alive_proxies)} proxies are alive.")
    for proxy in alive_proxies:
        print_full_proxy_info(proxy)
