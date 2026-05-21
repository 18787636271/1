import streamlit as st
import sqlite3
import hashlib
import time
from datetime import datetime

DB_PATH = "dating_app.db"

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

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # users: role = 'user' or 'admin'
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        pw_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        banned INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL
    )
    """)

    # profile
    cur.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        nickname TEXT,
        gender TEXT,
        age INTEGER,
        city TEXT,
        bio TEXT,
        looking_for TEXT,
        height_cm INTEGER,
        job TEXT,
        updated_at INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # likes: user -> target (status: like/skip)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        target_user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        UNIQUE(user_id, target_user_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(target_user_id) REFERENCES users(id)
    )
    """)

    # messages between matched users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user_id INTEGER NOT NULL,
        to_user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(from_user_id) REFERENCES users(id),
        FOREIGN KEY(to_user_id) REFERENCES users(id)
    )
    """)

    # reports (demo)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reporter_id INTEGER NOT NULL,
        target_user_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        handled INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(reporter_id) REFERENCES users(id),
        FOREIGN KEY(target_user_id) REFERENCES users(id)
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
            SET nickname=?, gender=?, age=?, city=?, bio=?, looking_for=?, height_cm=?, job=?, updated_at=?
            WHERE user_id=?
        """, (
            data.get("nickname"), data.get("gender"), data.get("age"), data.get("city"),
            data.get("bio"), data.get("looking_for"), data.get("height_cm"), data.get("job"),
            now_ts(), user_id
        ))
    else:
        cur.execute("""
            INSERT INTO profiles(user_id, nickname, gender, age, city, bio, looking_for, height_cm, job, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (
            user_id, data.get("nickname"), data.get("gender"), data.get("age"), data.get("city"),
            data.get("bio"), data.get("looking_for"), data.get("height_cm"), data.get("job"),
            now_ts()
        ))
    conn.commit()
    conn.close()

def get_profile(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.username, u.role, u.banned,
               p.nickname, p.gender, p.age, p.city, p.bio, p.looking_for, p.height_cm, p.job
        FROM users u
        LEFT JOIN profiles p ON p.user_id = u.id
        WHERE u.id = ?
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

def is_matched(a: int, b: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1
        FROM likes l1
        JOIN likes l2 ON l1.user_id = l2.target_user_id AND l1.target_user_id = l2.user_id
        WHERE l1.user_id=? AND l1.target_user_id=? AND l1.action='like' AND l2.action='like'
        LIMIT 1
    """, (a, b))
    row = cur.fetchone()
    conn.close()
    return row is not None

def record_like(user_id: int, target_id: int, action: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO likes(user_id, target_user_id, action, created_at)
        VALUES(?,?,?,?)
        ON CONFLICT(user_id, target_user_id) DO UPDATE SET action=excluded.action, created_at=excluded.created_at
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
          )
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
        WHERE l1.user_id = ? AND l1.action='like' AND l2.action='like' AND u.banned=0
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
        VALUES(?,?,?,?)
    """, (from_id, to_id, content, now_ts()))
    conn.commit()
    conn.close()

def get_chat(a: int, b: int, limit: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM messages
        WHERE (from_user_id=? AND to_user_id=?) OR (from_user_id=? AND to_user_id=?)
        ORDER BY created_at DESC
        LIMIT ?
    """, (a, b, b, a, limit))
    rows = cur.fetchall()
    conn.close()
    return list(reversed(rows))

def report_user(reporter_id: int, target_id: int, reason: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reports(reporter_id, target_user_id, reason, created_at)
        VALUES(?,?,?,?)
    """, (reporter_id, target_id, reason, now_ts()))
    conn.commit()
    conn.close()

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
    for k in ["user_id", "chat_with"]:
        if k in st.session_state:
            del st.session_state[k]

def require_login():
    return "user_id" in st.session_state

# ----------------------------
# UI
# ----------------------------
def page_auth():
    st.title("相亲交友 Demo（Streamlit + SQLite）")

    tab1, tab2 = st.tabs(["登录", "注册"])

    with tab1:
        username = st.text_input("用户名", key="login_u")
        password = st.text_input("密码", type="password", key="login_p")
        if st.button("登录", use_container_width=True):
            ok, msg = do_login(username, password)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

        st.info("管理员账号默认：admin / admin123（可登录后在管理员界面修改/扩展）")

    with tab2:
        username = st.text_input("用户名", key="reg_u")
        password = st.text_input("密码", type="password", key="reg_p")
        if st.button("注册", use_container_width=True):
            ok, msg = do_register(username, password)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

def page_user_home(user_id: int):
    me = get_profile(user_id)

    st.sidebar.write(f"当前用户：**{me['username']}**")
    if st.sidebar.button("退出登录"):
        logout()
        st.rerun()

    if me["role"] == "admin":
        st.sidebar.success("你是管理员，可在左侧菜单进入管理员界面")

    menu = st.sidebar.radio("菜单", ["我的资料", "浏览/匹配", "我的匹配", "聊天", "账号设置"], index=0)

    if menu == "我的资料":
        st.header("我的资料")

        col1, col2 = st.columns(2)
        with col1:
            nickname = st.text_input("昵称", value=me["nickname"] or "")
            gender = st.selectbox("性别", ["男", "女", "其他", "保密"], index=["男","女","其他","保密"].index(me["gender"]) if me["gender"] in ["男","女","其他","保密"] else 3)
            age = st.number_input("年龄", min_value=18, max_value=99, value=int(me["age"] or 18))
            city = st.text_input("城市", value=me["city"] or "")
        with col2:
            height_cm = st.number_input("身高(cm)", min_value=120, max_value=230, value=int(me["height_cm"] or 170))
            job = st.text_input("职业", value=me["job"] or "")
            looking_for = st.text_input("择偶偏好（简述）", value=me["looking_for"] or "")
        bio = st.text_area("自我介绍", value=me["bio"] or "", height=120)

        if st.button("保存资料", use_container_width=True):
            upsert_profile(user_id, dict(
                nickname=nickname, gender=gender, age=int(age), city=city,
                bio=bio, looking_for=looking_for, height_cm=int(height_cm), job=job
            ))
            st.success("已保存")
            st.rerun()

    elif menu == "浏览/匹配":
        st.header("浏览/匹配")

        with st.expander("筛选条件", expanded=True):
            f_gender = st.selectbox("对方性别", ["不限", "男", "女", "其他", "保密"], index=0)
            f_city = st.text_input("城市（精确匹配，可留空）", value="")
            c1, c2 = st.columns(2)
            with c1:
                f_age_min = st.number_input("最小年龄", min_value=18, max_value=99, value=18)
            with c2:
                f_age_max = st.number_input("最大年龄", min_value=18, max_value=99, value=99)

        if st.button("给我推荐一个", use_container_width=True):
            st.session_state["candidate_id"] = get_next_candidate(
                user_id,
                dict(gender=f_gender, city=f_city, age_min=f_age_min, age_max=f_age_max)
            )

        cand_id = st.session_state.get("candidate_id")
        if not cand_id:
            st.info("点击“给我推荐一个”开始浏览")
            return

        cand = get_profile(cand_id)
        if not cand:
            st.warning("候选人不存在")
            return

        st.subheader(f"候选人：{cand['nickname'] or cand['username']}")
        st.write(f"- 性别：{cand['gender'] or '未填写'}")
        st.write(f"- 年龄：{cand['age'] or '未填写'}")
        st.write(f"- 城市：{cand['city'] or '未填写'}")
        st.write(f"- 身高：{cand['height_cm'] or '未填写'}")
        st.write(f"- 职业：{cand['job'] or '未填写'}")
        st.write(f"- 简介：{cand['bio'] or '未填写'}")
        st.caption(f"用户ID：{cand_id}")

        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            if st.button("点赞 ❤️", use_container_width=True):
                record_like(user_id, cand_id, "like")
                if is_matched(user_id, cand_id):
                    st.success("恭喜！互相喜欢，已匹配成功")
                else:
                    st.info("已点赞，等待对方回应")
                st.session_state["candidate_id"] = None
                st.rerun()
        with c2:
            if st.button("跳过 ❌", use_container_width=True):
                record_like(user_id, cand_id, "skip")
                st.session_state["candidate_id"] = None
                st.rerun()
        with c3:
            reason = st.text_input("举报原因（可选）", key=f"rep_{cand_id}")
            if st.button("举报", use_container_width=True):
                report_user(user_id, cand_id, reason or "不当行为")
                st.warning("已举报（管理员将处理）")

    elif menu == "我的匹配":
        st.header("我的匹配")
        ids = get_matches(user_id)
        if not ids:
            st.info("暂无匹配，先去浏览/匹配吧")
            return

        for other_id in ids:
            other = get_profile(other_id)
            with st.container(border=True):
                st.subheader(other["nickname"] or other["username"])
                st.write(f"{other['gender'] or '未填'} / {other['age'] or '未填'} / {other['city'] or '未填'} / {other['job'] or '未填'}")
                cols = st.columns([1,1])
                if cols[0].button("去聊天", key=f"chat_{other_id}", use_container_width=True):
                    st.session_state["chat_with"] = other_id
                    st.rerun()
                if cols[1].button("查看资料", key=f"view_{other_id}", use_container_width=True):
                    st.session_state["view_profile"] = other_id
                    st.rerun()

        vp = st.session_state.get("view_profile")
        if vp:
            other = get_profile(vp)
            st.divider()
            st.subheader("资料详情")
            st.write(other)

    elif menu == "聊天":
        st.header("聊天（仅限互相喜欢）")
        matches = get_matches(user_id)
        if not matches:
            st.info("暂无匹配，无法聊天")
            return

        # choose partner
        options = []
        id_to_label = {}
        for oid in matches:
            p = get_profile(oid)
            label = f"{p['nickname'] or p['username']} (id={oid})"
            options.append(label)
            id_to_label[label] = oid

        default_partner = st.session_state.get("chat_with")
        default_idx = 0
        if default_partner and default_partner in matches:
            # find index by label
            for i, lab in enumerate(options):
                if id_to_label[lab] == default_partner:
                    default_idx = i
                    break

        chosen = st.selectbox("选择聊天对象", options, index=default_idx)
        partner_id = id_to_label[chosen]
        st.session_state["chat_with"] = partner_id

        # show messages
        chat = get_chat(user_id, partner_id, limit=100)
        for m in chat:
            who = "我" if m["from_user_id"] == user_id else "对方"
            ts = datetime.fromtimestamp(m["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
            st.write(f"[{ts}] **{who}：** {m['content']}")

        content = st.text_input("输入消息", key="msg_input")
        if st.button("发送", use_container_width=True):
            if not content.strip():
                st.error("消息不能为空")
            else:
                # double-check match
                if not is_matched(user_id, partner_id):
                    st.error("你们已非匹配状态（或不存在匹配）")
                else:
                    send_message(user_id, partner_id, content.strip())
                    st.session_state["msg_input"] = ""
                    st.rerun()

    elif menu == "账号设置":
        st.header("账号设置")
        st.warning("演示版仅提供基础功能")

        if st.button("清空我的浏览记录（likes）", use_container_width=True):
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM likes WHERE user_id=?", (user_id,))
            conn.commit()
            conn.close()
            st.success("已清空")
            st.rerun()

def page_admin(user_id: int):
    me = get_profile(user_id)
    if me["role"] != "admin":
        st.error("无权限访问管理员界面")
        return

    st.sidebar.write("管理员菜单")
    admin_menu = st.sidebar.radio("管理员功能", ["概览", "用户管理", "举报处理"], index=0)

    if admin_menu == "概览":
        st.header("数据概览")
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
            FROM likes l1 JOIN likes l2
            ON l1.user_id=l2.target_user_id AND l1.target_user_id=l2.user_id
            WHERE l1.action='like' AND l2.action='like' AND l1.user_id < l1.target_user_id
        """)
        matches_n = cur.fetchone()["n"]
        conn.close()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("用户数", users_n)
        c2.metric("封禁数", banned_n)
        c3.metric("点赞数", likes_n)
        c4.metric("匹配对数", matches_n)

    elif admin_menu == "用户管理":
        st.header("用户管理")
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.id, u.username, u.role, u.banned, u.created_at,
                   p.nickname, p.gender, p.age, p.city
            FROM users u
            LEFT JOIN profiles p ON p.user_id=u.id
            ORDER BY u.id DESC
        """)
        rows = cur.fetchall()
        conn.close()

        for r in rows:
            with st.container(border=True):
                ts = datetime.fromtimestamp(r["created_at"]).strftime("%Y-%m-%d")
                st.write(f"**ID {r['id']}** | {r['username']} | role={r['role']} | banned={r['banned']} | created={ts}")
                st.write(f"{r['nickname'] or '-'} / {r['gender'] or '-'} / {r['age'] or '-'} / {r['city'] or '-'}")
                if r["role"] != "admin":
                    col1, col2 = st.columns(2)
                    if col1.button("封禁", key=f"ban_{r['id']}", use_container_width=True):
                        conn = get_conn()
                        cur = conn.cursor()
                        cur.execute("UPDATE users SET banned=1 WHERE id=?", (r["id"],))
                        conn.commit()
                        conn.close()
                        st.success("已封禁")
                        st.rerun()
                    if col2.button("解封", key=f"unban_{r['id']}", use_container_width=True):
                        conn = get_conn()
                        cur = conn.cursor()
                        cur.execute("UPDATE users SET banned=0 WHERE id=?", (r["id"],))
                        conn.commit()
                        conn.close()
                        st.success("已解封")
                        st.rerun()

    elif admin_menu == "举报处理":
        st.header("举报处理")
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT r.*, u1.username AS reporter_name, u2.username AS target_name
            FROM reports r
            JOIN users u1 ON u1.id=r.reporter_id
            JOIN users u2 ON u2.id=r.target_user_id
            ORDER BY r.id DESC
        """)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            st.info("暂无举报")
            return

        for r in rows:
            with st.container(border=True):
                ts = datetime.fromtimestamp(r["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
                st.write(f"举报ID {r['id']} | 时间 {ts} | handled={r['handled']}")
                st.write(f"举报人：{r['reporter_name']} (id={r['reporter_id']})")
                st.write(f"被举报：{r['target_name']} (id={r['target_user_id']})")
                st.write(f"原因：{r['reason']}")

                c1, c2 = st.columns(2)
                if c1.button("标记已处理", key=f"handled_{r['id']}", use_container_width=True):
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("UPDATE reports SET handled=1 WHERE id=?", (r["id"],))
                    conn.commit()
                    conn.close()
                    st.success("已标记")
                    st.rerun()
                if c2.button("封禁被举报用户", key=f"ban_target_{r['id']}", use_container_width=True):
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("UPDATE users SET banned=1 WHERE id=?", (r["target_user_id"],))
                    cur.execute("UPDATE reports SET handled=1 WHERE id=?", (r["id"],))
                    conn.commit()
                    conn.close()
                    st.warning("已封禁并标记处理")
                    st.rerun()

def main():
    st.set_page_config(page_title="相亲交友Demo", layout="wide")
    init_db()

    if not require_login():
        page_auth()
        return

    user_id = st.session_state["user_id"]
    me = get_profile(user_id)
    if me["banned"] == 1:
        st.error("账号已封禁")
        logout()
        return

    # Global layout
    st.sidebar.title("相亲交友 Demo")

    # Admin entry
    if me["role"] == "admin":
        mode = st.sidebar.selectbox("模式", ["用户端", "管理员端"], index=0)
        if mode == "管理员端":
            page_admin(user_id)
            return

    page_user_home(user_id)

if __name__ == "__main__":
    main()