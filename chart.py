import pymysql
import pandas as pd
import matplotlib.pyplot as plt
import os


def get_env(key, default=None, required=False):
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"环境变量 {key} 未设置！")
    return value


# ======================
# 读取配置（带校验）
# ======================
db_config = {
    "host": get_env("DB_HOST", "localhost"),
    "port": int(get_env("DB_PORT", 3307)),
    "user": get_env("DB_USER", "root"),
    "password": get_env("DB_PASSWORD", required=True),  # ⭐必须有密码
    "database": get_env("DB_NAME", "proxy_pool"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

# ======================
# （可选）调试输出（不会打印密码）
# ======================
print("数据库连接配置：")
print({
    "host": db_config["host"],
    "port": db_config["port"],
    "user": db_config["user"],
    "database": db_config["database"]
})


# ======================
# 建立连接
# ======================
try:
    conn = pymysql.connect(**db_config)
    print("✅ 数据库连接成功！")
except Exception as e:
    print("❌ 数据库连接失败：", e)
    raise

conn = pymysql.connect(**db_config)

# 读取数据
df = pd.read_sql("SELECT * FROM proxies", conn)
conn.close()

print("总数据量:", len(df))


# ======================
# 2. 数据预处理
# ======================
df['country'] = df['country'].fillna('Unknown')
df['anonymity'] = df['anonymity'].fillna('Unknown')


# ======================
# 3. 图1：各国家代理数量
# ======================
country_counts = df['country'].value_counts().head(10)

plt.figure()
country_counts.plot(kind='bar')
plt.title("Top 10 Countries by Proxy Count")
plt.xlabel("Country")
plt.ylabel("Count")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()


# ======================
# 4. 图2：代理存活情况
# ======================
alive_counts = df['is_alive'].value_counts()

# 映射标签
alive_counts.index = ['Dead', 'Alive'] if 0 in alive_counts.index else ['Alive']

plt.figure()
alive_counts.plot(kind='bar')
plt.title("Proxy Alive Status")
plt.xlabel("Status")
plt.ylabel("Count")
plt.tight_layout()
plt.show()


# ======================
# 5. 图3：存活代理质量评分
# ======================
alive_df = df[df['is_alive'] == 1]

score_counts = alive_df['business_score'].value_counts().sort_index()

plt.figure()
score_counts.plot(kind='bar')
plt.title("Business Score Distribution (Alive Proxies)")
plt.xlabel("Score (0-3)")
plt.ylabel("Count")
plt.tight_layout()
plt.show()


# ======================
# 6. 图4：代理匿名性统计
# ======================
anon_counts = df['anonymity'].value_counts()

plt.figure()
anon_counts.plot(kind='bar')
plt.title("Proxy Anonymity Distribution")
plt.xlabel("Anonymity Level")
plt.ylabel("Count")
plt.xticks(rotation=30)
plt.tight_layout()
plt.show()