import streamlit as st
import json
import datetime
import random
import yfinance as yf
import pytz

# --- 0. セキュリティ設定 ---
PASSWORD = "nk225" 

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    st.markdown("<h1 style='font-size: 32px; text-align:center;'>🔐 225 IChing Pro</h1>", unsafe_allow_html=True)
    password_input = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if password_input == PASSWORD:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("⚠️ パスワードが違います")
    return False

if not check_password():
    st.stop()

# --- 1. データ読み込み ---
def load_data():
    try:
        with open('iching_master.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        st.error("iching_master.json が見つかりません。")
        return {}

master_data = load_data()

# --- 2. 市場価格取得（日経平均現物 ^N225 のみ） ---
@st.cache_data(ttl=30)
def get_nikkei_price():
    try:
        ticker = yf.Ticker("^N225")
        # 最新の気配値(last_price)を取得
        info = ticker.fast_info
        price = info['last_price']
        change = price - info['previous_close']
        return price, change
    except:
        return 0, 0

# --- 3. 市場ステータス判定（8:45-15:45 / 17:00-06:00） ---
def get_market_status():
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.datetime.now(jst)
    current_time = now.hour + now.minute / 60.0

    # 日中セッション（08:45 〜 15:45）
    if 8.75 <= current_time <= 15.75:
        status = "日中セッション"
        # 8:45-11:00=1爻, 11:00-13:30=2爻, 13:30-15:45=3爻
        target_yao = 1 if current_time < 11.0 else (2 if current_time < 13.5 else 3)
    # 夜間セッション（17:00 〜 翌06:00）
    elif current_time >= 17.0 or current_time <= 6.0:
        status = "夜間セッション"
        # 17:00-21:00=4爻, 21:00-01:00=5爻, 01:00-06:00=6爻
        if 17.0 <= current_time < 21.0: target_yao = 4
        elif current_time >= 21.0 or current_time < 1.0: target_yao = 5
        else: target_yao = 6
    else:
        status = "セッション外（待機）"
        target_yao = 1
        
    return status, target_yao

# --- 4. 先物トレード用語変換（占断用） ---
def to_futures_term(text):
    mapping = {"銘柄": "相場", "現物": "先物", "強い株": "強い波動", "買い。": "ロング。", "売り。": "ショート。"}
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text

# --- 5. 卦象ビジュアル（一行HTML・下から積み上げ・変爻赤） ---
def draw_hexagram_visual(active_yao, is_yang_list):
    st.write("---")
    st.markdown("### 📊 卦象ビジュアル（波動）")
    # 下(1)から上(6)へ描画
    for i in range(6, 0, -1):
        is_yang = is_yang_list[i-1]
        is_active = (i == int(active_yao))
        color = "#FF4B4B" if is_active else "#333333"
        
        if is_yang:
            bar_html = f'<div style="width:260px; height:28px; background-color:{color}; border-radius:4px;"></div>'
        else:
            bar_html = f'<div style="display:flex; width:260px; justify-content:space-between;"><div style="width:120px; height:28px; background-color:{color}; border-radius:4px;"></div><div style="width:120px; height:28px; background-color:{color}; border-radius:4px;"></div></div>'
        
        row_content = f'<div style="display:flex; justify-content:center; align-items:center; margin:12px 0;">{bar_html}<div style="width:110px; margin-left:20px; font-weight:bold; color:{color}; font-size:18px;">第{i}爻 {"(変爻)" if is_active else ""}</div></div>'
        st.markdown(row_content, unsafe_allow_html=True)

# --- 6. メインUI ---
st.set_page_config(page_title="225 IChing Pro", layout="centered")

# 価格・ステータス取得
price, change = get_nikkei_price()
m_phase, auto_yao = get_market_status()

# タイトル（32px）
st.markdown("<h1 style='font-size: 32px; text-align:center;'>🏯 日経225研究会：易占トレード Pro</h1>", unsafe_allow_html=True)

# サイドバー（重複なし）
st.sidebar.markdown("### 📈 日経平均株価")
if price > 0:
    st.sidebar.metric("日経平均 (Live)", f"{price:,.0f} 円", f"{change:+.0f} 円")
else:
    st.sidebar.warning("価格データ取得中...")

st.sidebar.divider()
st.sidebar.write(f"現在の状況：**{m_phase}**")
st.sidebar.info(f"自動判定の注目爻：**第{auto_yao}爻**")

# 立卦ボタン
st.markdown("""<style>.stButton>button { width: 100%; height: 80px; font-size: 26px !important; font-weight: bold !important; background-color: #ff4b4b !important; color: white !important; border-radius: 12px; }</style>""", unsafe_allow_html=True)

if st.button("天の時を演算（立卦）"):
    if not master_data:
        st.error("JSONデータが読み込めていません。")
    else:
        # ランダム立卦
        gua_name = random.choice(list(master_data.keys()))
        yao_num = str(auto_yao)
        gua_info = master_data[gua_name]
        yao_info = gua_info["yao"][yao_num]
        score = (gua_info["base_score"] + yao_info["score"]) // 2
        
        # 陽陰生成（ビジュアル用）
        is_yang_list = [random.choice([True, False]) for _ in range(6)]

        st.divider()
        st.markdown(f"### 【本卦】 {gua_name}")
        color_score = "#1C83E1" if score < 0 else "#FF4B4B"
        st.markdown(f"<h2 style='color:{color_score}; text-align:center; font-size:48px;'>期待値指数：{score}</h2>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**【波動性質】**\n\n{to_futures_term(gua_info['base_property'])}")
        with col2:
            st.warning(f"**【戦略アクション】**\n\n{to_futures_term(yao_info['action'])}")
            
        st.success(f"**【第{yao_num}爻の秘伝テキスト】**\n\n{to_futures_term(yao_info.get('text', '詳細はマスターファイル参照'))}")

        # 下から積み上げビジュアル
        draw_hexagram_visual(yao_num, is_yang_list)

st.divider()
st.caption(f"最終更新：{datetime.datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')}")
