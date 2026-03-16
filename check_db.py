import pymysql

# 连接数据库
conn = pymysql.connect(
    host="localhost",
    port=3307,
    user="root",
    password="123456",
    database="proxy_pool",
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

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
