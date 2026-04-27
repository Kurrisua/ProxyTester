from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from storage.mysql.connection import create_connection, get_connection_config


config = get_connection_config()
safe_config = {key: value for key, value in config.items() if key not in {"password", "cursorclass"}}
print("数据库连接配置:", safe_config)

conn = create_connection()

cursor = conn.cursor()

# 查询代理数量
cursor.execute("SELECT COUNT(*) as total FROM proxies")
total = cursor.fetchone()['total']
print(f"数据库中代理总数: {total}")

# 查询前10条代理数据
cursor.execute("SELECT * FROM proxies ORDER BY last_check_time DESC LIMIT 10")
proxies = cursor.fetchall()

print("\n前10条代理数据:")
for i, proxy in enumerate(proxies, 1):
    print(f"\n{i}. IP: {proxy['ip']}:{proxy['port']}")
    print(f"   Source: {proxy['source']}")
    print(f"   Country: {proxy['country']}")
    print(f"   City: {proxy['city']}")
    print(f"   Proxy Type: {proxy['proxy_type']}")
    print(f"   Anonymity: {proxy['anonymity']}")
    print(f"   Response Time: {proxy['response_time']}")
    print(f"   Is Alive: {proxy['is_alive']}")
    print(f"   Last Check: {proxy['last_check_time']}")

# 关闭连接
cursor.close()
conn.close()
