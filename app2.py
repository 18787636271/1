import streamlit as st
import sqlite3
import hashlib
import time
from datetime import datetime

DB_PATH = "dating_app.db"


# ----------------------------
# 自定义CSS样式
# ----------------------------
def load_css():
    st.markdown("""
    <style>
    /* 全局样式 */
    .stApp {
        background: #f5f5f5;
    }

    /* 主容器 */
    .main .block-container {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    }

    /* 卡片样式 */
    .profile-card {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin: 1rem 0;
        transition: all 0.3s ease;
        border: 1px solid #eee;
    }

    .profile-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }

    /* 按钮样式 */
    .stButton > button {
        border-radius: 25px;
        font-weight: 600;
        padding: 0.5rem 2rem;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
        border: 2px solid #ff6b9d;
        background: white;
        color: #ff6b9d;
    }

    .stButton > button:hover {
        background: #ff6b9d;
        color: white;
        transform: scale(1.03);
        box-shadow: 0 4px 12px rgba(255,107,157,0.3);
    }

    /* 主要按钮样式 */
    .stButton > button[kind="primary"] {
        background: #ff6b9d;
        color: white;
        border: none;
    }

    .stButton > button[kind="primary"]:hover {
        background: #ff4d84;
    }

    /* 聊天气泡 */
    .chat-bubble {
        padding: 12px 16px;
        margin: 8px;
        border-radius: 18px;
        max-width: 70%;
        word-wrap: break-word;
    }

    .chat-bubble.sent {
        background: #ff6b9d;
        color: white;
        float: right;
        margin-left: auto;
        border-bottom-right-radius: 4px;
    }

    .chat-bubble.received {
        background: #f0f0f0;
        color: #333;
        float: left;
        border-bottom-left-radius: 4px;
    }

    /* 统计卡片 */
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid #eee;
        transition: all 0.3s ease;
    }

    .stat-card:hover {
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }

    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
        color: #ff6b9d;
    }

    .stat-label {
        font-size: 1rem;
        color: #888;
    }

    /* 标题样式 */
    .gradient-text {
        color: #ff6b9d;
        font-weight: bold;
    }

    /* 输入框样式 */
    .stTextInput > div > div > input {
        border-radius: 25px;
        border: 2px solid #e0e0e0;
        padding: 0.5rem 1rem;
        background: white;
    }

    .stTextInput > div > div > input:focus {
        border-color: #ff6b9d;
        box-shadow: 0 0 0 2px rgba(255,107,157,0.1);
    }

    /* 选择框样式 */
    .stSelectbox > div > div > select {
        border-radius: 25px;
    }

    /* 侧边栏样式 */
    .css-1d391kg {
        background: white;
    }

    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }

    .stTabs [data-baseweb="tab"] {
        color: #888;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        color: #ff6b9d;
        border-bottom-color: #ff6b9d;
    }

    /* 展开器样式 */
    .streamlit-expanderHeader {
        border-radius: 10px;
        background: #fafafa;
    }

    /* 表单样式 */
    .stForm {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    </style>
    """, unsafe_allow_html=True)


# ----------------------------
# Utils
# ----------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def now_ts():
    return int(time.time())


def show_toast(message, type="success"):
    """显示Toast消息"""
    emoji = "✅" if type == "success" else "❌"
    st.toast(f"{emoji} {message}")


def create_avatar(username, avatar_color="#ff6b9d"):
    """创建默认头像（显示用户名首字母）"""
    first_letter = username[0].upper() if username else "?"
    return f"""
    <div style="width: 80px; height: 80px; border-radius: 50%; background: {avatar_color}; 
         display: flex; align-items: center; justify-content: center; color: white; font-size: 2.5rem; font-weight: bold; 
         box-shadow: 0 4px 12px rgba(255,107,157,0.2);">
        {first_letter}
    </div>
    """

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # users: role = 'user' or 'admin'
    cur.execute("""
                CREATE TABLE IF NOT EXISTS users
                (
                    id
                    INTEGER
                    PRIMARY
                    KEY
                    AUTOINCREMENT,
                    username
                    TEXT
                    UNIQUE
                    NOT
                    NULL,
                    pw_hash
                    TEXT
                    NOT
                    NULL,
                    role
                    TEXT
                    NOT
                    NULL
                    DEFAULT
                    'user',
                    banned
                    INTEGER
                    NOT
                    NULL
                    DEFAULT
                    0,
                    created_at
                    INTEGER
                    NOT
                    NULL
                )
                """)

    # profile
    cur.execute("""
                CREATE TABLE IF NOT EXISTS profiles
                (
                    user_id
                    INTEGER
                    PRIMARY
                    KEY,
                    nickname
                    TEXT,
                    gender
                    TEXT,
                    age
                    INTEGER,
                    city
                    TEXT,
                    bio
                    TEXT,
                    looking_for
                    TEXT,
                    height_cm
                    INTEGER,
                    job
                    TEXT,
                    avatar_color
                    TEXT
                    DEFAULT
                    '#667eea',
                    updated_at
                    INTEGER,
                    FOREIGN
                    KEY
                (
                    user_id
                ) REFERENCES users
                (
                    id
                )
                    )
                """)

    # likes: user -> target (status: like/skip)
    cur.execute("""
                CREATE TABLE IF NOT EXISTS likes
                (
                    id
                    INTEGER
                    PRIMARY
                    KEY
                    AUTOINCREMENT,
                    user_id
                    INTEGER
                    NOT
                    NULL,
                    target_user_id
                    INTEGER
                    NOT
                    NULL,
                    action
                    TEXT
                    NOT
                    NULL,
                    created_at
                    INTEGER
                    NOT
                    NULL,
                    UNIQUE
                (
                    user_id,
                    target_user_id
                ),
                    FOREIGN KEY
                (
                    user_id
                ) REFERENCES users
                (
                    id
                ),
                    FOREIGN KEY
                (
                    target_user_id
                ) REFERENCES users
                (
                    id
                )
                    )
                """)

    # messages between matched users
    cur.execute("""
                CREATE TABLE IF NOT EXISTS messages
                (
                    id
                    INTEGER
                    PRIMARY
                    KEY
                    AUTOINCREMENT,
                    from_user_id
                    INTEGER
                    NOT
                    NULL,
                    to_user_id
                    INTEGER
                    NOT
                    NULL,
                    content
                    TEXT
                    NOT
                    NULL,
                    created_at
                    INTEGER
                    NOT
                    NULL,
                    FOREIGN
                    KEY
                (
                    from_user_id
                ) REFERENCES users
                (
                    id
                ),
                    FOREIGN KEY
                (
                    to_user_id
                ) REFERENCES users
                (
                    id
                )
                    )
                """)

    # reports (demo)
    cur.execute("""
                CREATE TABLE IF NOT EXISTS reports
                (
                    id
                    INTEGER
                    PRIMARY
                    KEY
                    AUTOINCREMENT,
                    reporter_id
                    INTEGER
                    NOT
                    NULL,
                    target_user_id
                    INTEGER
                    NOT
                    NULL,
                    reason
                    TEXT
                    NOT
                    NULL,
                    created_at
                    INTEGER
                    NOT
                    NULL,
                    handled
                    INTEGER
                    NOT
                    NULL
                    DEFAULT
                    0,
                    FOREIGN
                    KEY
                (
                    reporter_id
                ) REFERENCES users
                (
                    id
                ),
                    FOREIGN KEY
                (
                    target_user_id
                ) REFERENCES users
                (
                    id
                )
                    )
                """)

    conn.commit()

    # Create default admin if not exists
    cur.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO users(username, pw_hash, role, banned, created_at) VALUES(?,?,?,?,?)",
            ("admin", hash_password("admin123"), "admin", 0, now_ts())
        )
        conn.commit()
    conn.close()


def get_user_by_username(username: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row


def get_user_by_id(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


def upsert_profile(user_id: int, data: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM profiles WHERE user_id = ?", (user_id,))
    exists = cur.fetchone()
    if exists:
        cur.execute("""
                    UPDATE profiles
                    SET nickname=?,
                        gender=?,
                        age=?,
                        city=?,
                        bio=?,
                        looking_for=?,
                        height_cm=?,
                        job=?,
                        avatar_color=?,
                        updated_at=?
                    WHERE user_id = ?
                    """, (
                        data.get("nickname"), data.get("gender"), data.get("age"), data.get("city"),
                        data.get("bio"), data.get("looking_for"), data.get("height_cm"), data.get("job"),
                        data.get("avatar_color", "#667eea"), now_ts(), user_id
                    ))
    else:
        cur.execute("""
                    INSERT INTO profiles(user_id, nickname, gender, age, city, bio, looking_for, height_cm, job,
                                         avatar_color, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id, data.get("nickname"), data.get("gender"), data.get("age"), data.get("city"),
                        data.get("bio"), data.get("looking_for"), data.get("height_cm"), data.get("job"),
                        data.get("avatar_color", "#667eea"), now_ts()
                    ))
    conn.commit()
    conn.close()


def get_profile(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                SELECT u.id,
                       u.username,
                       u.role,
                       u.banned,
                       p.nickname,
                       p.gender,
                       p.age,
                       p.city,
                       p.bio,
                       p.looking_for,
                       p.height_cm,
                       p.job,
                       p.avatar_color
                FROM users u
                         LEFT JOIN profiles p ON p.user_id = u.id
                WHERE u.id = ?
                """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


def safe_get(row, key, default=""):
    """安全获取sqlite3.Row的值"""
    if row and key in row.keys() and row[key] is not None:
        return row[key]
    return default


def is_matched(a: int, b: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                SELECT 1
                FROM likes l1
                         JOIN likes l2 ON l1.user_id = l2.target_user_id AND l1.target_user_id = l2.user_id
                WHERE l1.user_id = ?
                  AND l1.target_user_id = ?
                  AND l1.action = 'like'
                  AND l2.action = 'like' LIMIT 1
                """, (a, b))
    row = cur.fetchone()
    conn.close()
    return row is not None


def record_like(user_id: int, target_id: int, action: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                INSERT INTO likes(user_id, target_user_id, action, created_at)
                VALUES (?, ?, ?, ?) ON CONFLICT(user_id, target_user_id) DO
                UPDATE SET action =excluded.action, created_at=excluded.created_at
                """, (user_id, target_id, action, now_ts()))
    conn.commit()
    conn.close()


def get_next_candidate(user_id: int, filters: dict):
    """
    Pick a candidate not yet liked/skipped by user, not self, not banned, role user.
    Apply simple filters: gender, city, age range
    """
    conn = get_conn()
    cur = conn.cursor()

    gender = filters.get("gender")
    city = filters.get("city")
    age_min = filters.get("age_min")
    age_max = filters.get("age_max")

    query = """
            SELECT u.id
            FROM users u
                     LEFT JOIN profiles p ON p.user_id = u.id
            WHERE u.id != ?
          AND u.role = 'user'
          AND u.banned = 0
          AND u.id NOT IN (
              SELECT target_user_id FROM likes WHERE user_id = ?
          ) \
            """
    params = [user_id, user_id]

    if gender and gender != "不限":
        query += " AND COALESCE(p.gender,'') = ?"
        params.append(gender)
    if city and city.strip():
        query += " AND COALESCE(p.city,'') = ?"
        params.append(city.strip())
    if age_min is not None:
        query += " AND COALESCE(p.age, 0) >= ?"
        params.append(int(age_min))
    if age_max is not None:
        query += " AND COALESCE(p.age, 999) <= ?"
        params.append(int(age_max))

    query += " ORDER BY RANDOM() LIMIT 1"

    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return int(row["id"])


def get_matches(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                SELECT DISTINCT u.id as other_id
                FROM likes l1
                         JOIN likes l2 ON l1.user_id = l2.target_user_id AND l1.target_user_id = l2.user_id
                         JOIN users u ON u.id = l1.target_user_id
                WHERE l1.user_id = ?
                  AND l1.action = 'like'
                  AND l2.action = 'like'
                  AND u.banned = 0
                ORDER BY u.id DESC
                """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [int(r["other_id"]) for r in rows]


def send_message(from_id: int, to_id: int, content: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                INSERT INTO messages(from_user_id, to_user_id, content, created_at)
                VALUES (?, ?, ?, ?)
                """, (from_id, to_id, content, now_ts()))
    conn.commit()
    conn.close()


def get_chat(a: int, b: int, limit: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                SELECT *
                FROM messages
                WHERE (from_user_id = ? AND to_user_id = ?)
                   OR (from_user_id = ? AND to_user_id = ?)
                ORDER BY created_at DESC LIMIT ?
                """, (a, b, b, a, limit))
    rows = cur.fetchall()
    conn.close()
    return list(reversed(rows))


def report_user(reporter_id: int, target_id: int, reason: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
                INSERT INTO reports(reporter_id, target_user_id, reason, created_at)
                VALUES (?, ?, ?, ?)
                """, (reporter_id, target_id, reason, now_ts()))
    conn.commit()
    conn.close()


def get_user_stats(user_id: int):
    """获取用户统计数据"""
    conn = get_conn()
    cur = conn.cursor()

    # 点赞数
    cur.execute("SELECT COUNT(*) as n FROM likes WHERE user_id=? AND action='like'", (user_id,))
    likes_given = cur.fetchone()["n"]

    # 被点赞数
    cur.execute("SELECT COUNT(*) as n FROM likes WHERE target_user_id=? AND action='like'", (user_id,))
    likes_received = cur.fetchone()["n"]

    # 匹配数
    matches = len(get_matches(user_id))

    # 消息数
    cur.execute("""
                SELECT COUNT(*) as n
                FROM messages
                WHERE from_user_id = ?
                   OR to_user_id = ?
                """, (user_id, user_id))
    messages_count = cur.fetchone()["n"]

    conn.close()

    return {
        "likes_given": likes_given,
        "likes_received": likes_received,
        "matches": matches,
        "messages": messages_count
    }


# ----------------------------
# Auth
# ----------------------------
def do_register(username: str, password: str):
    username = username.strip()
    if not username or not password:
        return False, "用户名和密码不能为空"
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users(username, pw_hash, role, banned, created_at) VALUES(?,?,?,?,?)",
            (username, hash_password(password), "user", 0, now_ts())
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False, "用户名已存在"
    conn.close()
    return True, "注册成功，请登录"


def do_login(username: str, password: str):
    row = get_user_by_username(username.strip())
    if not row:
        return False, "用户不存在"
    if row["banned"] == 1:
        return False, "账号已被封禁"
    if row["pw_hash"] != hash_password(password):
        return False, "密码错误"
    st.session_state["user_id"] = int(row["id"])
    return True, "登录成功"


def logout():
    for k in ["user_id", "chat_with", "admin_mode"]:
        if k in st.session_state:
            del st.session_state[k]


def require_login():
    return "user_id" in st.session_state


# ----------------------------
# UI Components
# ----------------------------
def profile_card(profile_data, show_actions=True):
    """用户资料卡片"""
    avatar_color = safe_get(profile_data, "avatar_color", "#667eea")
    nickname = safe_get(profile_data, "nickname", "")
    username = safe_get(profile_data, "username", "")
    display_name = nickname or username or "未设置"
    first_letter = display_name[0].upper()

    card_html = f"""
    <div class="profile-card">
        <div style="text-align: center;">
            <div style="width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, {avatar_color} 0%, #764ba2 100%); 
                 display: inline-flex; align-items: center; justify-content: center; color: white; font-size: 2rem; font-weight: bold; margin-bottom: 1rem;">
                {first_letter}
            </div>
            <h3 style="margin: 0.5rem 0;">{display_name}</h3>
        </div>
        <div style="margin-top: 1rem;">
            <p>🎯 性别：{safe_get(profile_data, "gender", "未填写")}</p>
            <p>🎂 年龄：{safe_get(profile_data, "age", "未填写")}</p>
            <p>📍 城市：{safe_get(profile_data, "city", "未填写")}</p>
            <p>📏 身高：{safe_get(profile_data, "height_cm", "未填写")} cm</p>
            <p>💼 职业：{safe_get(profile_data, "job", "未填写")}</p>
            <p>💝 择偶偏好：{safe_get(profile_data, "looking_for", "未填写")}</p>
            <p>📝 简介：{safe_get(profile_data, "bio", "未填写")}</p>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def chat_bubble(content, is_sent, timestamp):
    """聊天气泡"""
    bubble_class = "sent" if is_sent else "received"
    time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M")

    bubble_html = f"""
    <div style="overflow: hidden; margin: 10px 0;">
        <div class="chat-bubble {bubble_class}">
            <div>{content}</div>
            <div style="font-size: 0.7rem; opacity: 0.7; margin-top: 5px;">{time_str}</div>
        </div>
    </div>
    """
    st.markdown(bubble_html, unsafe_allow_html=True)


def stat_card(number, label, icon):
    """统计卡片"""
    card_html = f"""
    <div class="stat-card">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
        <div class="stat-number">{number}</div>
        <div class="stat-label">{label}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


# ----------------------------
# Pages
# ----------------------------
def page_auth():
    st.markdown('<h1 class="gradient-text" style="text-align: center; font-size: 3rem;">💕 缘来是你</h1>',
                unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666; font-size: 1.2rem;">遇见你的命中注定</p>',
                unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔑 登录", "✨ 注册"])

    with tab1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                username = st.text_input("👤 用户名", placeholder="请输入用户名")
                password = st.text_input("🔒 密码", type="password", placeholder="请输入密码")
                submitted = st.form_submit_button("🚀 登录", use_container_width=True)

                if submitted:
                    ok, msg = do_login(username, password)
                    if ok:
                        show_toast("登录成功！欢迎回来 💕")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        show_toast(msg, "error")

        st.info("💡 管理员账号：admin / admin123")

    with tab2:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("register_form"):
                username = st.text_input("👤 用户名", placeholder="设置您的用户名")
                password = st.text_input("🔒 密码", type="password", placeholder="设置密码（至少6位）")
                submitted = st.form_submit_button("🎉 开始缘分之旅", use_container_width=True)

                if submitted:
                    ok, msg = do_register(username, password)
                    if ok:
                        show_toast("注册成功！请登录 ✨")
                    else:
                        show_toast(msg, "error")


def page_user_home(user_id: int):
    me = get_profile(user_id)
    stats = get_user_stats(user_id)

    # 获取用户信息
    nickname = safe_get(me, "nickname", "")
    username = safe_get(me, "username", "")
    display_name = nickname or username
    avatar_color = safe_get(me, "avatar_color", "#667eea")

    # 侧边栏
    with st.sidebar:
        st.markdown(create_avatar(display_name, avatar_color), unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center;'>{display_name}</h3>", unsafe_allow_html=True)

        # 用户统计
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("💕 匹配", stats["matches"])
            st.metric("❤️ 获赞", stats["likes_received"])
        with col2:
            st.metric("👍 点赞", stats["likes_given"])
            st.metric("💬 消息", stats["messages"])

        st.markdown("---")

        if st.button("🚪 退出登录", use_container_width=True):
            logout()
            st.rerun()

        if safe_get(me, "role") == "admin":
            st.markdown("---")
            st.success("👑 管理员模式可用")
            if st.button("🔧 管理员面板", use_container_width=True):
                st.session_state["admin_mode"] = True
                st.rerun()

    # 主菜单
    menu = st.radio(
        "",
        ["🏠 我的主页", "💕 缘分推荐", "💑 我的匹配", "💬 聊天室", "⚙️ 设置"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if menu == "🏠 我的主页":
        st.markdown('<h2 class="gradient-text">🌟 我的主页</h2>', unsafe_allow_html=True)

        # 统计概览
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            stat_card(stats["likes_given"], "送出点赞", "👍")
        with col2:
            stat_card(stats["likes_received"], "收到点赞", "❤️")
        with col3:
            stat_card(stats["matches"], "成功匹配", "💑")
        with col4:
            stat_card(stats["messages"], "消息数", "💬")

        st.markdown("---")

        # 个人资料展示
        col1, col2 = st.columns([2, 3])
        with col1:
            st.markdown(create_avatar(display_name, avatar_color), unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center;'>{display_name}</h3>", unsafe_allow_html=True)
            st.caption(f"🆔 ID: {safe_get(me, 'id')}")

        with col2:
            profile_card(dict(me), show_actions=False)

    elif menu == "💕 缘分推荐":
        st.markdown('<h2 class="gradient-text">💕 缘分推荐</h2>', unsafe_allow_html=True)

        with st.expander("🎯 筛选条件", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                f_gender = st.selectbox("对方性别", ["不限", "男", "女", "其他", "保密"], index=0)
                f_city = st.text_input("🏙️ 城市", placeholder="输入城市名")
            with col2:
                f_age_min = st.number_input("最小年龄", min_value=18, max_value=99, value=18)
                f_age_max = st.number_input("最大年龄", min_value=18, max_value=99, value=99)
            with col3:
                st.write("")
                st.write("")
                if st.button("🎲 随机推荐", use_container_width=True):
                    st.session_state["candidate_id"] = get_next_candidate(
                        user_id,
                        dict(gender=f_gender, city=f_city, age_min=f_age_min, age_max=f_age_max)
                    )

        cand_id = st.session_state.get("candidate_id")
        if not cand_id:
            st.info("👆 点击「随机推荐」开始浏览潜在对象")
            return

        cand = get_profile(cand_id)
        if not cand:
            st.warning("暂无符合条件的用户")
            return

        # 候选人卡片
        st.markdown("---")
        profile_card(dict(cand))

        # 操作按钮
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("❤️ 喜欢", use_container_width=True, type="primary"):
                record_like(user_id, cand_id, "like")
                if is_matched(user_id, cand_id):
                    st.balloons()
                    show_toast("🎉 恭喜！互相喜欢，匹配成功！")
                else:
                    show_toast("已点赞，等待对方回应")
                st.session_state["candidate_id"] = None
                time.sleep(0.5)
                st.rerun()

        with col2:
            if st.button("👎 跳过", use_container_width=True):
                record_like(user_id, cand_id, "skip")
                st.session_state["candidate_id"] = None
                st.rerun()

        with col3:
            reason = st.text_input("举报原因", placeholder="选填", key=f"rep_{cand_id}")
            if st.button("🚨 举报", use_container_width=True):
                report_user(user_id, cand_id, reason or "不当行为")
                show_toast("已举报，管理员将处理", "error")

    elif menu == "💑 我的匹配":
        st.markdown('<h2 class="gradient-text">💑 我的匹配</h2>', unsafe_allow_html=True)

        ids = get_matches(user_id)
        if not ids:
            st.info("💔 还没有匹配，快去发现缘分吧！")
            return

        st.success(f"🎉 你有 {len(ids)} 个匹配！")

        for other_id in ids:
            other = get_profile(other_id)
            with st.container():
                col1, col2, col3 = st.columns([2, 3, 1])
                with col1:
                    other_avatar_color = safe_get(other, "avatar_color", "#667eea")
                    other_display_name = safe_get(other, "nickname") or safe_get(other, "username", "?")
                    first_letter = other_display_name[0].upper()
                    st.markdown(f"""
                    <div style="width: 60px; height: 60px; border-radius: 50%; background: linear-gradient(135deg, {other_avatar_color} 0%, #764ba2 100%); 
                         display: inline-flex; align-items: center; justify-content: center; color: white; font-size: 1.5rem; font-weight: bold;">
                        {first_letter}
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.subheader(other_display_name)
                    st.write(
                        f"{safe_get(other, 'gender', '未填')} · {safe_get(other, 'age', '未填')}岁 · {safe_get(other, 'city', '未填')}")

                with col3:
                    if st.button("💬", key=f"chat_{other_id}", help="开始聊天"):
                        st.session_state["chat_with"] = other_id
                        st.rerun()
                    if st.button("👤", key=f"view_{other_id}", help="查看资料"):
                        with st.expander("查看详细资料"):
                            profile_card(dict(other), show_actions=False)

                st.markdown("---")

    elif menu == "💬 聊天室":
        st.markdown('<h2 class="gradient-text">💬 聊天室</h2>', unsafe_allow_html=True)

        matches = get_matches(user_id)
        if not matches:
            st.info("💔 需要先匹配才能聊天哦")
            return

        # 选择聊天对象
        options = []
        id_to_label = {}
        for oid in matches:
            p = get_profile(oid)
            label = f"{safe_get(p, 'nickname') or safe_get(p, 'username')} (ID: {oid})"
            options.append(label)
            id_to_label[label] = oid

        default_partner = st.session_state.get("chat_with")
        default_idx = 0
        if default_partner and default_partner in matches:
            for i, lab in enumerate(options):
                if id_to_label[lab] == default_partner:
                    default_idx = i
                    break

        chosen = st.selectbox("选择聊天对象", options, index=default_idx)
        partner_id = id_to_label[chosen]
        st.session_state["chat_with"] = partner_id

        partner = get_profile(partner_id)

        # 聊天头部
        partner_avatar_color = safe_get(partner, "avatar_color", "#667eea")
        partner_display_name = safe_get(partner, "nickname") or safe_get(partner, "username", "?")
        first_letter = partner_display_name[0].upper()
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 1rem; padding: 1rem; background: white; border-radius: 15px; margin-bottom: 1rem;">
            <div style="width: 50px; height: 50px; border-radius: 50%; background: linear-gradient(135deg, {partner_avatar_color} 0%, #764ba2 100%); 
                 display: flex; align-items: center; justify-content: center; color: white; font-size: 1.2rem; font-weight: bold;">
                {first_letter}
            </div>
            <div>
                <h4 style="margin: 0;">{partner_display_name}</h4>
                <small style="color: #666;">{safe_get(partner, 'city', '未知')}</small>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 消息区域
        chat_container = st.container()
        with chat_container:
            chat = get_chat(user_id, partner_id, limit=100)
            for m in chat:
                is_sent = m["from_user_id"] == user_id
                chat_bubble(m['content'], is_sent, m['created_at'])

        # 输入区域
        st.markdown("---")
        col1, col2 = st.columns([5, 1])
        with col1:
            content = st.text_input("", placeholder="输入消息...", key="msg_input", label_visibility="collapsed")
        with col2:
            if st.button("📤 发送", use_container_width=True):
                if not content.strip():
                    show_toast("消息不能为空", "error")
                elif not is_matched(user_id, partner_id):
                    show_toast("你们已不是匹配关系", "error")
                else:
                    send_message(user_id, partner_id, content.strip())
                    st.rerun()

    elif menu == "⚙️ 设置":
        st.markdown('<h2 class="gradient-text">⚙️ 个人设置</h2>', unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["📝 编辑资料", "🎨 个性化"])

        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                nickname = st.text_input("昵称", value=safe_get(me, "nickname"))
                gender = st.selectbox("性别", ["男", "女", "其他", "保密"],
                                      index=["男", "女", "其他", "保密"].index(safe_get(me, "gender")) if safe_get(me,
                                                                                                                   "gender") in [
                                                                                                              "男",
                                                                                                              "女",
                                                                                                              "其他",
                                                                                                              "保密"] else 3)
                age = st.number_input("年龄", min_value=18, max_value=99, value=int(safe_get(me, "age", 18)))
                city = st.text_input("城市", value=safe_get(me, "city"))
            with col2:
                height_cm = st.number_input("身高(cm)", min_value=120, max_value=230,
                                            value=int(safe_get(me, "height_cm", 170)))
                job = st.text_input("职业", value=safe_get(me, "job"))
                looking_for = st.text_input("择偶偏好", value=safe_get(me, "looking_for"),
                                            placeholder="例如：温柔体贴、有责任心")

            bio = st.text_area("自我介绍", value=safe_get(me, "bio"), height=120,
                               placeholder="介绍一下自己，让更多人了解你...")

            if st.button("💾 保存资料", use_container_width=True, type="primary"):
                current_avatar_color = safe_get(me, "avatar_color", "#667eea")
                upsert_profile(user_id, dict(
                    nickname=nickname, gender=gender, age=int(age), city=city,
                    bio=bio, looking_for=looking_for, height_cm=int(height_cm), job=job,
                    avatar_color=current_avatar_color
                ))
                show_toast("资料已更新！✨")
                time.sleep(0.5)
                st.rerun()

        with tab2:
            st.subheader("🎨 选择头像颜色")
            colors = ["#ff6b9d", "#667eea", "#4facfe", "#43e97b", "#fa709a", "#f6d365", "#f093fb", "#a8edea"]
            color_names = ["浪漫粉", "优雅紫", "天空蓝", "清新绿", "热情红", "活力黄", "梦幻粉", "薄荷绿"]

            cols = st.columns(4)
            for i, (color, name) in enumerate(zip(colors, color_names)):
                with cols[i % 4]:
                    if st.button(f"{name}", key=f"color_{i}", help=f"选择{name}"):
                        conn = get_conn()
                        cur = conn.cursor()
                        cur.execute("UPDATE profiles SET avatar_color=? WHERE user_id=?", (color, user_id))
                        conn.commit()
                        conn.close()
                        show_toast(f"头像颜色已更新为{name}！")
                        st.rerun()

        st.markdown("---")
        st.warning("⚠️ 危险操作")
        if st.button("🗑️ 清空浏览记录", use_container_width=True):
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM likes WHERE user_id=?", (user_id,))
            conn.commit()
            conn.close()
            show_toast("浏览记录已清空")


def page_admin(user_id: int):
    me = get_profile(user_id)
    if safe_get(me, "role") != "admin":
        st.error("⛔ 无权限访问")
        return

    st.sidebar.markdown("# 👑 管理员面板")

    if st.sidebar.button("⬅️ 返回用户模式"):
        st.session_state["admin_mode"] = False
        st.rerun()

    admin_menu = st.sidebar.radio("", ["📊 数据概览", "👥 用户管理", "🚨 举报处理"])

    if admin_menu == "📊 数据概览":
        st.markdown('<h2 class="gradient-text">📊 数据概览</h2>', unsafe_allow_html=True)

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM users WHERE role='user'")
        users_n = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM users WHERE banned=1")
        banned_n = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM likes WHERE action='like'")
        likes_n = cur.fetchone()["n"]
        cur.execute("""
                    SELECT COUNT(*) AS n
                    FROM likes l1
                             JOIN likes l2
                                  ON l1.user_id = l2.target_user_id AND l1.target_user_id = l2.user_id
                    WHERE l1.action = 'like'
                      AND l2.action = 'like'
                      AND l1.user_id < l1.target_user_id
                    """)
        matches_n = cur.fetchone()["n"]
        conn.close()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            stat_card(users_n, "总用户", "👥")
        with col2:
            stat_card(banned_n, "封禁", "🚫")
        with col3:
            stat_card(likes_n, "点赞数", "❤️")
        with col4:
            stat_card(matches_n, "匹配对", "💑")

    elif admin_menu == "👥 用户管理":
        st.markdown('<h2 class="gradient-text">👥 用户管理</h2>', unsafe_allow_html=True)

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
                    SELECT u.id,
                           u.username,
                           u.role,
                           u.banned,
                           u.created_at,
                           p.nickname,
                           p.gender,
                           p.age,
                           p.city
                    FROM users u
                             LEFT JOIN profiles p ON p.user_id = u.id
                    ORDER BY u.id DESC
                    """)
        rows = cur.fetchall()
        conn.close()

        for r in rows:
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 2, 1, 1])

                with col1:
                    first_letter = r['username'][0].upper()
                    st.markdown(f"""
                    <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                         display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                        {first_letter}
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.write(f"**{r['username']}**")
                    r_nickname = r['nickname'] if r['nickname'] else '未设置'
                    r_city = r['city'] if r['city'] else '未知'
                    st.caption(f"{r_nickname} · {r_city}")

                with col3:
                    banned_status = "🔴 已封" if r["banned"] else "🟢 正常"
                    st.write(banned_status)

                with col4:
                    if r["role"] != "admin":
                        if r["banned"]:
                            if st.button("✅ 解封", key=f"unban_{r['id']}"):
                                conn = get_conn()
                                cur = conn.cursor()
                                cur.execute("UPDATE users SET banned=0 WHERE id=?", (r["id"],))
                                conn.commit()
                                conn.close()
                                show_toast("用户已解封")
                                st.rerun()
                        else:
                            if st.button("🚫 封禁", key=f"ban_{r['id']}"):
                                conn = get_conn()
                                cur = conn.cursor()
                                cur.execute("UPDATE users SET banned=1 WHERE id=?", (r["id"],))
                                conn.commit()
                                conn.close()
                                show_toast("用户已封禁", "error")
                                st.rerun()

                st.markdown("---")

    elif admin_menu == "🚨 举报处理":
        st.markdown('<h2 class="gradient-text">🚨 举报处理</h2>', unsafe_allow_html=True)

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
                    SELECT r.*, u1.username AS reporter_name, u2.username AS target_name
                    FROM reports r
                             JOIN users u1 ON u1.id = r.reporter_id
                             JOIN users u2 ON u2.id = r.target_user_id
                    ORDER BY r.id DESC
                    """)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            st.info("🎉 暂无举报")
            return

        for r in rows:
            with st.container():
                st.markdown(f"""
                <div class="profile-card">
                    <h4>🚨 举报 #{r['id']}</h4>
                    <p>📅 {datetime.fromtimestamp(r['created_at']).strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>👤 举报人：{r['reporter_name']} (ID: {r['reporter_id']})</p>
                    <p>🎯 被举报：{r['target_name']} (ID: {r['target_user_id']})</p>
                    <p>📝 原因：{r['reason']}</p>
                    <p>📌 状态：{'✅ 已处理' if r['handled'] else '⏳ 待处理'}</p>
                </div>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                if col1.button("✅ 标记已处理", key=f"handle_{r['id']}", use_container_width=True):
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("UPDATE reports SET handled=1 WHERE id=?", (r["id"],))
                    conn.commit()
                    conn.close()
                    show_toast("已标记为处理完成")
                    st.rerun()

                if col2.button("🚫 封禁用户", key=f"ban_{r['id']}", use_container_width=True):
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("UPDATE users SET banned=1 WHERE id=?", (r["target_user_id"],))
                    cur.execute("UPDATE reports SET handled=1 WHERE id=?", (r["id"],))
                    conn.commit()
                    conn.close()
                    show_toast("已封禁用户", "error")
                    st.rerun()


def main():
    st.set_page_config(
        page_title="💕 缘来是你 - 相亲交友",
        page_icon="💕",
        layout="wide",
        initial_sidebar_state="auto"
    )

    # 加载自定义CSS
    load_css()

    init_db()

    if not require_login():
        page_auth()
        return

    user_id = st.session_state["user_id"]
    me = get_profile(user_id)

    if me["banned"] == 1:
        st.error("⛔ 账号已被封禁")
        logout()
        return

    # 管理员模式检查
    if safe_get(me, "role") == "admin" and st.session_state.get("admin_mode"):
        page_admin(user_id)
        return

    page_user_home(user_id)


if __name__ == "__main__":
    main()