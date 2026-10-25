import csv
import datetime as dt
import io
import os

import streamlit as st

import danyi as d

st.set_page_config(page_title="225 IChing Pro", page_icon="🔮")


# --- 0. ログイン ---
def _find_password(secrets):
    """Secrets から password を探す（大文字小文字・[見出し] の中も見る）"""
    for key, value in secrets.items():
        if str(key).lower() == "password" and isinstance(value, str) and value.strip():
            return value.strip()
        if hasattr(value, "items"):
            found = _find_password(value)
            if found:
                return found
    return None


def _is_local():
    try:
        host = st.context.headers.get("Host", "")
    except Exception:
        host = ""
    return host.startswith(("localhost", "127.0.0.1"))


def check_password():
    try:  # パスワードは Streamlit の Secrets（password = "..."）に置く。プログラムには書かない
        password = _find_password(st.secrets)
    except Exception:
        password = None
    password = password or os.environ.get("EKISEN_PASSWORD")
    if st.session_state.get("password_correct"):
        return True
    if not password:
        if _is_local():  # 自分のパソコンで動かすときだけ、パスワード無しで開く
            return True
        st.markdown("### 🔐 225 IChing Pro ログイン")
        st.error("パスワードが設定されていません。Streamlit Cloud の Settings → Secrets に "
                 '`password = "…"` を書いて保存してください。')
        return False
    st.markdown("### 🔐 225 IChing Pro ログイン")
    st.warning("""
**【利用上の注意】**
* 誠心誠意の心: 「当たるか当たらないか」を試すような態度は厳禁です。真摯に神仏や易の神に問いかける姿勢を持たなければ、卦にその迷いが表れます。

呼吸を整える: 深呼吸を行い、雑念を払います。

無心になる: 結果に対する期待や恐怖を捨て、ありのままの真実を受け入れる心境（無我・無心）を目指します。

感謝: 卦が出たら、感謝を込めて一礼する。

断易は「占った瞬間」のエネルギーが卦に封じ込められます。礼儀と瞑想は、その瞬間を最も誠実でクリアな状態にするための「儀式」です。

実際の取引はご自身の判断と責任において行ってください。
""")
    entered = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if entered == password:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("⚠️ パスワードが違います")
    return False


if not check_password():
    st.stop()

# --- 1. スタイル ---
st.markdown("""
<style>
.report-text { font-size: 18px !important; line-height: 1.7; }
.verdict-box { background-color: #fffaf0; padding: 20px; border-left: 6px solid #d4af37;
  border-radius: 8px; font-size: 20px !important; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
.gua-table { font-size: 17px; border-collapse: collapse; width: 100%; }
.gua-table td, .gua-table th { padding: 4px 8px; border-bottom: 1px solid #eee; text-align: center; }
.moving { color: #c0392b; font-weight: bold; }
div.stButton > button { background: linear-gradient(to right, #d4af37, #f1c40f); color: #fff !important;
  font-size: 22px !important; font-weight: bold !important; height: 64px !important; width: 100% !important;
  border-radius: 50px !important; border: none !important; box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center; color:#333;'>🔮 断易・日経先物鑑定</h1>", unsafe_allow_html=True)
st.write("---")

# --- 2. 占う日時と暦（日本時間） ---
now = dt.datetime.now(d.JST)
with st.sidebar:
    st.markdown("### 📅 占う日時（日本時間）")
    day = st.date_input("日付", now.date())
    tm = st.time_input("時刻", now.time().replace(second=0, microsecond=0))
moment = dt.datetime.combine(day, tm, tzinfo=d.JST)
cal = d.calendar(moment)
with st.sidebar:
    st.markdown(f"**{cal['year']}年 {cal['month']}月 {cal['day']}日**")
    st.markdown(f"月建：**{cal['month'][1]}**　日辰：**{cal['day']}**　空亡：**{cal['void'][0]}・{cal['void'][1]}**")

# --- 3. 立卦 ---
question = st.text_input("占うこと", "今日の日経先物の動き")
use = st.selectbox("用神", ["妻財", "世爻", "子孫", "官鬼", "父母", "兄弟"],
                   help="相場の値段は妻財で見るのが一般的です")
mode = st.radio("卦の立て方", ["コイン3枚×6回（自動）", "自分で立てた卦（卦名と変爻）", "自分のコインの結果（6回分）"],
                horizontal=False)

values = None
if mode == "コイン3枚×6回（自動）":
    st.caption("心を静めて、一礼してから押してください。下の爻から 6 回投げます。")
    if st.button("天の時を演算（立卦）"):
        st.session_state["values"] = d.cast_coins()
        st.session_state["values_mode"] = mode
    if st.session_state.get("values_mode") == mode:
        values = st.session_state.get("values")
elif mode == "自分で立てた卦（卦名と変爻）":
    names = list(d.HEX_LINES)
    name = st.selectbox("本卦", names, index=names.index("乾為天"))
    moving = st.multiselect("変爻（無ければ空のまま）", [1, 2, 3, 4, 5, 6], format_func=lambda i: f"{'初二三四五上'[i-1]}爻")
    values = d.from_name(name, moving)
else:
    labels = {"少陽（表1枚・裏2枚）": 7, "少陰（表2枚・裏1枚）": 8, "老陽（表3枚）＝動": 9, "老陰（裏3枚）＝動": 6}
    cols = st.columns(6)
    values = []
    for i in range(6):
        with cols[i]:
            pick = st.selectbox(f"{'初二三四五上'[i]}爻", list(labels), key=f"coin{i}")
            values.append(labels[pick])
    st.caption("初爻（1 回目）から上爻（6 回目）の順に選んでください。表=3・裏=2 の合計で決めています。")

with st.expander("📖 用神の選び方（何を占うかで選びます）"):
    st.markdown("""
日経先物の上がり下がりを占うなら、**最初から選ばれている「妻財」のままで大丈夫です**。

| 用神 | 表すもの | こんなときに |
|---|---|---|
| **妻財**（既定） | 値段・利益 | 「来週の日経は上がるか」「この取引で利益が出るか」など、ふだんの相場占い |
| 世爻 | 自分自身・自分の立場 | 「自分のポジションはどうなるか」など、自分を中心に見たいとき |
| 子孫 | 好材料・安心・財の元 | 「好材料が出るか」「この不安は解消するか」 |
| 官鬼 | 不安・リスク・波乱 | 「急落や波乱が起きるか」「リスクはどのくらいか」 |
| 父母 | ニュース・発表・指標 | 「今夜の指標・発表の内容はどうか」 |
| 兄弟 | 競争・損失・財を奪うもの | 「損失がふくらむか」「売り方などの勢い」 |

- **迷ったら「妻財」**。相場の値段は妻財で見るのが一般的です。
- **占う前に、問いと用神を決めておく**のが断易の作法です。卦が出てから用神を取り替えると、読みがぶれます。
- 官鬼・兄弟を用神にしたときは、「強い＝波乱・損失が起きやすい」という意味になります。妻財のときとは、良し悪しの向きが逆です。
""")

# --- 4. 鑑定 ---
if values:
    r = d.build_reading(values, moment)
    j = d.judge(r, use)
    title = r["name"] + (f" → {r['changed_name']}" if r["changed_name"] else "（変爻なし）")
    moving_pos = "・".join("初二三四五上"[ln["pos"] - 1] for ln in r["lines"] if ln["moving"])
    st.markdown(f"## 【{title}】")
    st.caption(f"{r['palace']}宮（{r['palace_element']}）{r['kind']}　変爻：{moving_pos or 'なし'}")

    rows = []
    for ln in reversed(r["lines"]):
        mark = ("━━━" if ln["yang"] else "━ ━") + ("　○" if ln["moving"] and ln["yang"] else "　×" if ln["moving"] else "")
        hid = f"{ln['hidden']['relative']}{ln['hidden']['branch']}{ln['hidden']['element']}" if ln["hidden"] else ""
        ch = f"{ln['changed']['relative']}{ln['changed']['branch']}{ln['changed']['element']}" if ln["changed"] else ""
        cls = " class='moving'" if ln["moving"] else ""
        rows.append(f"<tr{cls}><td>{ln['god']}</td><td>{hid}</td><td>{ln['relative']}{ln['branch']}{ln['element']}</td>"
                    f"<td>{ln['role']}</td><td>{mark}</td><td>{ch}</td></tr>")
    st.markdown("<table class='gua-table'><tr><th>六神</th><th>伏神</th><th>本卦</th><th>世応</th><th>爻</th><th>変爻</th></tr>"
                + "".join(rows) + "</table>", unsafe_allow_html=True)

    st.divider()
    st.markdown(f"<div class='verdict-box'><strong>【見立て】{j['verdict']}</strong>（点数 {j['score']:+d}）</div>",
                unsafe_allow_html=True)
    for i, (head, body) in enumerate(d.explain(r, j), start=1):
        st.markdown(f"### {i}. {head}")
        st.markdown("<div class='report-text'>" + body.replace("\n", "<br>") + "</div>", unsafe_allow_html=True)
    with st.expander("用神の点数の内訳"):
        st.markdown("<div class='report-text'>" + "<br>".join(
            f"{'＋' if s > 0 else '－' if s < 0 else '・'}{abs(s) if s else ''} {t}" for s, t in j["factors"]) + "</div>",
            unsafe_allow_html=True)
    st.caption("点数は用神の旺衰を足し合わせた目安です。占いとしてお楽しみください。実際の取引はご自身の判断と責任で。")

    # --- 5. 記録 ---
    if st.button("この鑑定を記録する"):
        rec = {"記録時刻": dt.datetime.now(d.JST).strftime("%Y-%m-%d %H:%M"), "占った日時": moment.strftime("%Y-%m-%d %H:%M"),
               "占うこと": question, "日辰": cal["day"], "月建": cal["month"], "本卦": r["name"],
               "変爻": moving_pos or "なし", "之卦": r["changed_name"] or "", "用神": j["source"],
               "点数": j["score"], "見立て": j["verdict"], "実際の結果": ""}
        st.session_state.setdefault("log", []).append(rec)
        try:  # 自分のパソコンで動かしているときはファイルにも残す（Streamlit Cloud では消えることがある）
            path = "ekisen_log.csv"
            new = not os.path.exists(path)
            with open(path, "a", newline="", encoding="utf-8-sig") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rec))
                if new:
                    w.writeheader()
                w.writerow(rec)
        except OSError:
            pass
        st.success("記録しました")

log = st.session_state.get("log")
if log:
    st.divider()
    st.markdown("### 📒 記録")
    st.dataframe(log, width="stretch")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(log[0]))
    w.writeheader()
    w.writerows(log)
    st.download_button("記録をCSVでダウンロード", buf.getvalue().encode("utf-8-sig"), "ekisen_log.csv", "text/csv")
