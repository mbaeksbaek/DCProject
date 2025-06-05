import time
import socket
from sshtunnel import SSHTunnelForwarder
import mysql.connector
from mysql.connector import Error

# do not execute this script : test purpose only

SSH_HOST = "100.24.135.186"
SSH_PORT = 22
SSH_USER = "ec2-user"
SSH_PRIVATE_KEY = r"C:\Users\mbaek\.ssh\DCProject-key.pem"

DB_HOST_INTERNAL = "127.0.0.1"
DB_PORT_INTERNAL = 3306
DB_USER = "system"
DB_PASSWORD = "Qortmdals38043482!@"  
DB_NAME = "DCProject"

LOCAL_BIND_HOST = "127.0.0.1"
LOCAL_BIND_PORT = 3307
def wait_for_port(host: str, port: int, timeout: float = 5.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.2)
    return False



def main():
    tunnel = None
    try:
        print("[SSH Tunnel] Opening SSH tunnel…")
        tunnel = SSHTunnelForwarder(
            (SSH_HOST, SSH_PORT),
            ssh_username=SSH_USER,
            ssh_pkey=SSH_PRIVATE_KEY,
            remote_bind_address=(DB_HOST_INTERNAL, DB_PORT_INTERNAL),
            local_bind_address=(LOCAL_BIND_HOST, LOCAL_BIND_PORT)
        )
        tunnel.start()
        print(f"[SSH Tunnel] Opened {LOCAL_BIND_HOST}:{LOCAL_BIND_PORT} → {DB_HOST_INTERNAL}:{DB_PORT_INTERNAL}")

        print(f"[SSH Tunnel] Waiting for local port {LOCAL_BIND_HOST}:{LOCAL_BIND_PORT} to open…", end="", flush=True)
        if not wait_for_port(LOCAL_BIND_HOST, LOCAL_BIND_PORT, timeout=5):
            print("X")
            return
        print("O")

        print(f"[DB] Connecting to MySQL at {LOCAL_BIND_HOST}:{LOCAL_BIND_PORT}…")
        conn = mysql.connector.connect(
            host=LOCAL_BIND_HOST,
            port=LOCAL_BIND_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
            connection_timeout=10
        )
        if conn.is_connected():
            print("[DB] Connection successful via SSH tunnel")
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            print(f"[DB] Tables in '{DB_NAME}':")
            for (tbl,) in tables:
                print("   -", tbl)
            cursor.close()
            conn.close()
        else:
            print("[DB] Connection failed: Unknown reason")

    except Error as e:
        print("[DB] Connection failed with Error:", e)
    except Exception as ex:
        print("[SSH Tunnel] Unexpected Error:", ex)
    finally:
        if tunnel is not None and tunnel.is_active:
            tunnel.stop()
            print("[SSH Tunnel] Closed")

if __name__ == "__main__":
    main()
