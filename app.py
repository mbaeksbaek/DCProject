from flask import Flask, render_template
import mysql.connector
from mysql.connector import Error


DB_HOST   = "127.0.0.1"
DB_PORT   = 3307
DB_USER   = "sytem"
DB_PASS   = ""          # 실제 비밀번호
DB_NAME   = ""

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

app = Flask(__name__)

@app.route("/")
def index():
    return """
    <h1>DCProject Topic Crawler</h1>
    <p><a href="/topics">저장된 토픽 보기 (HTML 테이블)</a></p>
    <p><a href="/api/topics">저장된 토픽 보기 (JSON)</a></p>
    """

@app.route("/api/topics")
def api_get_topics():
    conn = get_db_connection()
    if conn is None:
        return {"error": "DB 연결 실패"}, 500

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
        ORDER BY t.created_at DESC
        LIMIT 100;
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        return {"topics": rows}, 200

    except Error as e:
        print("[DB] Error in /api/topics:", e)
        return {"error": str(e)}, 500

    finally:
        cursor.close()
        conn.close()

@app.route("/topics")
def page_topics():
    conn = get_db_connection()
    if conn is None:
        return "<h2>DB 연결 실패</h2>"

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
        ORDER BY t.created_at DESC
        LIMIT 100;
        """
        cursor.execute(sql)
        topics = cursor.fetchall()
        return render_template("topics.html", topics=topics)

    except Error as e:
        print("[DB] Error in /topics:", e)
        return f"<h2>DB 조회 오류: {e}</h2>"

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
