import datetime
import mysql.connector
from mysql.connector import Error


DB_HOST   = "127.0.0.1"
DB_PORT   = 3307
DB_USER   = "system"
DB_PASS   = "" 
DB_NAME   = ""

# do not execute this script : debug purpose only

def crawl_example_website():
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    return [
        ("첫 번째 토픽", "이것은 첫 번째 더미 콘텐츠입니다.", 100, 5),
        ("두 번째 토픽", "이것은 두 번째 더미 콘텐츠입니다.", 250, 12),
        ("세 번째 토픽", "이것은 세 번째 더미 콘텐츠입니다.", 75, 3),
    ]

def get_db_connection():

    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            charset="utf8mb4"
        )
        return conn
    except Error as e:
        print("[DB] Connection error:", e)
        return None

def save_crawled_data(website_name, base_url, crawled_items):
    """
    1) websites 테이블에 website_name이 존재하지 않으면 INSERT (컬럼: name, url)
    2) Topics 테이블에 (website_id, title, content, created_at, updated_at) 저장
    3) Metrics 테이블에 (topic_id, views, comments, recorded_at) 저장
    """
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT website_id FROM websites WHERE name = %s", (website_name,))
        row = cursor.fetchone()
        if row:
            website_id = row[0]
        else:
            cursor.execute(
                "INSERT INTO websites (name, url) VALUES (%s, %s)",
                (website_name, base_url)
            )
            conn.commit()
            website_id = cursor.lastrowid
            print(f"[DB] Inserted new website '{website_name}' with ID {website_id}")

        saved_count = 0
        for title, content, view_cnt, comment_cnt in crawled_items:
            now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

            sql_topic = """
                INSERT INTO Topics (website_id, title, content, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE title = title
            """
            cursor.execute(sql_topic, (website_id, title, content, now, now))
            conn.commit()

            cursor.execute(
                "SELECT topic_id FROM Topics WHERE website_id=%s AND title=%s AND created_at=%s",
                (website_id, title, now)
            )
            topic_row = cursor.fetchone()
            if not topic_row:
                print("[DB] Failed to fetch topic_id for:", title)
                continue
            topic_id = topic_row[0]

            sql_metric = """
                INSERT INTO Metrics (topic_id, views, comments, recorded_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  views    = VALUES(views),
                  comments = VALUES(comments)
            """
            cursor.execute(sql_metric, (topic_id, view_cnt, comment_cnt, now))
            conn.commit()

            saved_count += 1

        print(f"[DB] Saved {saved_count} rows into Topics/Metrics for '{website_name}'.")

    except Error as e:
        print("[DB] Error while saving crawled data:", e)
    finally:
        cursor.close()
        conn.close()

def print_saved_data(website_name, limit=10):
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
        SELECT
          w.name            AS website_name,
          t.title           AS title,
          t.content         AS content,
          m.views           AS view_count,
          m.comments        AS comment_count,
          t.created_at      AS topic_created,
          m.recorded_at     AS metric_recorded
        FROM Topics AS t
        JOIN websites AS w   ON t.website_id = w.website_id
        JOIN Metrics  AS m   ON t.topic_id     = m.topic_id
        WHERE w.name = %s
        ORDER BY t.created_at DESC
        LIMIT %s;
        """
        cursor.execute(sql, (website_name, limit))
        rows = cursor.fetchall()

        print(f"--- Saved data for '{website_name}' (limit {limit} rows) ---")
        for row in rows:
            print(
                f"[{row['website_name']}] "
                f"TITLE: \"{row['title']}\" | "
                f"CONTENT: \"{row['content'][:30]}...\" | "
                f"VIEWS: {row['view_count']} | "
                f"COMMENTS: {row['comment_count']} | "
                f"CREATED_AT: {row['topic_created']} | "
                f"METRIC_AT: {row['metric_recorded']}"
            )

    except Error as e:
        print("[DB] Error while fetching saved data:", e)
    finally:
        cursor.close()
        conn.close()

def main():
    crawled = crawl_example_website()
    save_crawled_data("EXAMPLE_WEBSITE", "https://example.com", crawled)
    print_saved_data("EXAMPLE_WEBSITE", limit=10)

if __name__ == "__main__":
    main()
