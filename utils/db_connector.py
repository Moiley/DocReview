import pymysql
from dbutils.pooled_db import PooledDB
from config.config import DB_CONFIG

mysql_pool = PooledDB(
    creator=pymysql,
    host=DB_CONFIG["host"],
    user=DB_CONFIG["user"],
    password=DB_CONFIG["password"],
    db=DB_CONFIG["database"],
    charset=DB_CONFIG["charset"],
    maxconnections=10,
    ping=1,
)

def get_db_connection():
    return mysql_pool.connection()

def close_db_connection(conn):
    if "conn" in locals():
        conn.close()