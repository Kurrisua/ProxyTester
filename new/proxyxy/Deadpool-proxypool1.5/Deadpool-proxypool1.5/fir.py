import requests
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading
from typing import Set, Dict, List
import time

# 线程锁用于安全地更新集合
proxy_lock = threading.Lock()


def clean_proxy_line(line):
    """
    清理并格式化单行代理数据，只返回 "ip:端口" 或 "域名:端口" 的形式。
    """
    line = line.strip()
    # 先剥离协议头和认证信息
    if "//" in line:
        line = line.split('//')[-1]
    if "@" in line:
        line = line.split('@')[-1]

    # 再处理可能存在的国家等额外信息
    parts = line.split(':')
    if len(parts) > 2:
        line = f"{parts[0]}:{parts[1]}"

    if ':' in line and line.split(':')[0] and line.split(':')[1]:
        return line.strip()
    return None


def deduce_protocol(original_line, default_protocol):
    """
    根据原始行内容推断协议。
    """
    line_lower = original_line.lower()
    if 'socks5' in line_lower:
        return 'socks5'
    if 'socks4' in line_lower:
        return 'socks4'
    if 'socks' in line_lower:
        return 'socks5'  # 默认为 SOCKS5
    if 'http' in line_lower:
        return 'http'
    return default_protocol


def create_session():
    """创建带重试机制的会话"""
    session = requests.Session()
    retry_strategy = Retry(
        total=2,  # 最多重试2次
        backoff_factor=0.5,  # 重试延迟
        status_forcelist=[500, 502, 503, 504]  # 这些状态码会重试
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,  # 连接池大小
        pool_maxsize=20  # 最大连接数
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_source(source: Dict, timeout: int = 10) -> tuple:
    """
    从单个源获取代理数据
    返回: (http_proxies, socks5_proxies, source_name, success_flag)
    """
    http_set = set()
    socks5_set = set()
    success = False

    try:
        session = create_session()
        response = session.get(source['url'], timeout=timeout)
        response.raise_for_status()

        content = response.text.strip()
        lines = content.split('\n')

        # 批量处理，减少循环开销
        for line in lines:
            if not line.strip():
                continue

            # 智能推断协议
            protocol = deduce_protocol(line, source['protocol'])

            # 清理代理地址
            cleaned_proxy = None
            if source['parser'] in ['text', 'json-list']:
                cleaned_proxy = clean_proxy_line(line)
            elif source['parser'] == 'json':
                try:
                    proxy_info = json.loads(line)
                    host = proxy_info.get("host")
                    port = proxy_info.get("port")
                    if host and port:
                        cleaned_proxy = f"{host}:{port}"
                except json.JSONDecodeError:
                    continue

            if cleaned_proxy:
                if protocol == 'http':
                    http_set.add(f"{cleaned_proxy} {source['name']}")
                elif protocol == 'socks5':
                    socks5_set.add(f"{cleaned_proxy} {source['name']}")

        success = True
        print(f"[✓] {source['name']}: 获取成功 (HTTP:{len(http_set)}, SOCKS5:{len(socks5_set)})")

    except requests.exceptions.Timeout:
        print(f"[✗] {source['name']}: 超时")
    except requests.exceptions.ConnectionError:
        print(f"[✗] {source['name']}: 连接错误")
    except Exception as e:
        print(f"[✗] {source['name']}: 错误 - {str(e)[:50]}")

    return http_set, socks5_set, source['name'], success


def fetch_and_save_proxies():
    """
    并行获取所有源的代理数据
    """
    start_time = time.time()

    # 代理源定义
    SOURCES = [
        {"name": "TheSpeedX/PROXY-List",
         "url": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt", "parser": "text",
         "protocol": "socks5"},
        {"name": "hookzof/socks5_list", "url": "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
         "parser": "text", "protocol": "socks5"},
        {"name": "ProxyScraper/ProxyScraper",
         "url": "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/socks5.txt", "parser": "text",
         "protocol": "socks5"},
        {"name": "proxifly/free-proxy-list",
         "url": "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt",
         "parser": "text", "protocol": "http"},
        {"name": "zloi-user/hideip.me",
         "url": "https://raw.githubusercontent.com/zloi-user/hideip.me/master/socks5.txt", "parser": "text",
         "protocol": "socks5"},
        {"name": "gfpcom/free-proxy-list",
         "url": "https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/list/socks5.txt", "parser": "text",
         "protocol": "socks5"},
        {"name": "monosans/proxy-list",
         "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies.json", "parser": "json-list",
         "protocol": "socks5"},
        {"name": "fate0/proxylist", "url": "https://raw.githubusercontent.com/fate0/proxylist/master/proxy.list",
         "parser": "json", "protocol": "http"},
        # 添加更多源可以提高成功率
        {"name": "jetkai/proxy-list",
         "url": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
         "parser": "text", "protocol": "http"},
        {"name": "jetkai/proxy-list-socks5",
         "url": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
         "parser": "text", "protocol": "socks5"},
         {"name":"get_free_proxy",
         "url":"https://raw.githubusercontent.com/wiki/gfpcom/free-proxy-list/lists/socks5.txt",
         "parser": "text", "protocol": "socks5"},
         {"name":"get_free_proxy",
         "url":"https://raw.githubusercontent.com/wiki/gfpcom/free-proxy-list/lists/https.txt",
         "parser": "text", "protocol": "http"}
    ]

    # 使用集合存储代理
    http_proxies = set()
    socks5_proxies = set()

    # 并行获取数据 - 使用线程池
    max_workers = min(10, len(SOURCES))  # 最大线程数设为10
    successful_sources = 0

    print(f"[*] 开始并行获取 {len(SOURCES)} 个源的代理数据 (最大线程数: {max_workers})...\n")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_source = {
            executor.submit(fetch_source, source): source
            for source in SOURCES
        }

        # 收集结果
        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                http_set, socks5_set, name, success = future.result(timeout=15)

                if success:
                    # 使用锁安全地更新主集合
                    with proxy_lock:
                        http_proxies.update(http_set)
                        socks5_proxies.update(socks5_set)
                    successful_sources += 1

            except Exception as e:
                print(f"[!] {source['name']}: 结果处理失败 - {str(e)[:50]}")

    # 保存结果
    output_dir = os.getcwd()

    # 打印统计信息
    elapsed_time = time.time() - start_time
    print(f"\n{'=' * 50}")
    print(f"[*] 统计信息:")
    print(f"    - 总源数量: {len(SOURCES)}")
    print(f"    - 成功源数量: {successful_sources}")
    print(f"    - 总耗时: {elapsed_time:.2f} 秒")
    print(f"    - HTTP代理总数: {len(http_proxies)}")
    print(f"    - SOCKS5代理总数: {len(socks5_proxies)}")
    print(f"{'=' * 50}\n")

    # 保存文件
    save_proxies_to_file(http_proxies, "http.txt", output_dir)
    save_proxies_to_file(socks5_proxies, "git.txt", output_dir)

    return http_proxies, socks5_proxies


def save_proxies_to_file(proxies_set, filename, output_dir):
    """保存代理到文件"""
    if not proxies_set:
        print(f"\n[-] 代理列表 '{filename}' 为空，无需保存。")
        return

    file_path = os.path.join(output_dir, filename)
    try:
        os.makedirs(output_dir, exist_ok=True)
        sorted_proxies = sorted(list(proxies_set))

        # 批量写入，提高效率
        with open(file_path, 'w', encoding='utf-8', buffering=8192) as f:
            f.write('\n'.join(sorted_proxies) + '\n')

        print(f"[✓] {len(sorted_proxies)} 个代理已保存到: {file_path}")

    except Exception as e:
        print(f"[!] 保存文件 '{filename}' 时出错: {e}")


if __name__ == "__main__":
    fetch_and_save_proxies()