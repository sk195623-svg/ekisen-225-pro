import streamlit as st
import json
import datetime
import random
import yfinance as yf

# --- 0. セキュリティ設定 ---
PASSWORD = "nk225"  # ここを好きなパスワードに変更してください

def check_password():
    """正しいパスワードが入力されたらTrueを返す"""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # パスワード入力画面の表示
    st.title("🔐 認証が必要です")
    st.write("このツールは限定公開です。アクセスコードを入力してください。")
    password_input = st.text_input("パスワード", type="password")
    
    if st.button("ログイン"):
        if password_input == PASSWORD:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("⚠️ パスワードが違います")
    return False

# パスワードチェックを実行（通らなければここで停止）
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

# --- 2. ロジック設定 ---
# --- 2. ロジック設定（修正版） ---
def get_market_status():
    hour = datetime.datetime.now().hour
    # 日中：9時〜16時（1-3爻）、ナイト：それ以外（4-6爻）
    if 9 <= hour < 16:
        # 名前（文字列）と、対応する爻のリスト（数値）をセットで返す
        return "日中セッション", [1, 2, 3]
    else:
        return "ナイトセッション", [4, 5, 6]


# --- 2. ロジック設定（先物リアルタイム修正版） ---
def get_nikkei_price():
    try:
        # Tickerを NK=F (CME日経先物) に設定
        ticker = yf.Ticker("NK=F")
        # 直近1日のデータを1分足で取得（最も確実な最新値を取るため）
        data = ticker.history(period="1d", interval="1m")
        
        if not data.empty:
            # 最新の終値
            current_price = data['Close'].iloc[-1]
            # 本日の始値（その日最初のデータ）
            open_price = data['Open'].iloc[0]
            # 前日比（または本日始値比）の計算
            change = current_price - open_price
            return current_price, change
        else:
            # 万が一先物が取れない場合のバックアップ（現物指数）
            backup = yf.Ticker("^N225").history(period="1d")
            if not backup.empty:
                return backup['Close'].iloc[-1], backup['Close'].iloc[-1] - backup['Open'].iloc[-1]
            return 0, 0
    except Exception as e:
        # エラー時は0を返さず、ログに出力（デバッグ用）
        print(f"価格取得エラー: {e}")
        return 0, 0


# --- サイドバーの表示ラベルも変更 ---
price, change = get_nikkei_price()
st.sidebar.metric("日経225先物 (リアルタイム)", f"{price:,.0f}", f"{change:+.0f}")

# --- 3. UIデザイン設定 ---
st.set_page_config(page_title="225 IChing Pro", layout="centered")

st.markdown("""
    <style>
    .stButton>button {
        width: 100%; height: 100px; font-size: 32px !important;
        font-weight: bold !important; background-color: #ff4b4b !important;
        color: white !important; border-radius: 15px;
    }
    .stMarkdown p { font-size: 22px !important; line-height: 1.6; }
    .stAlert p { font-size: 24px !important; }
    h2 { font-size: 48px !important; }
    h3 { font-size: 36px !important; }
    </style>
    """, unsafe_allow_html=True)

# サイドバー情報
price, change = get_nikkei_price()
st.sidebar.metric("日経平均 (参考現物)", f"{price:,.0f}", f"{change:+.0f}")
market_phase, target_yaos = get_market_status()
st.sidebar.write(f"現在：{market_phase}")

if st.sidebar.button("ログアウト"):
    st.session_state["password_correct"] = False
    st.rerun()

st.title("🏯 日経225先物研究会：易占トレード Pro")

# --- 4. 演算ボタン（巨大） ---
if st.button("天の時を演算（立卦）"):
    if not master_data: st.stop()
    
    gua_name = random.choice(list(master_data.keys()))
    yao_num = str(random.choice(target_yaos))
    gua_info = master_data[gua_name]
    yao_info = gua_info["yao"][yao_num]
    score = (gua_info["base_score"] + yao_info["score"]) // 2

    st.divider()
    
    # 1. ヘッダーエリア
    st.markdown(f"### 【本卦】 {gua_name}")
    color = "#1C83E1" if score < 0 else "#FF4B4B"
    st.markdown(f"<h2 style='color:{color}; text-align:center;'>期待値指数：{score}</h2>", unsafe_allow_html=True)
    
    # 2. ブロック・レイアウト
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**【基本性質】**\n\n{gua_info['base_property']}")
    with col2:
        st.warning(f"**【本日のアクション】**\n\n{yao_info['action']}")
        
    # 3. 秘伝テキスト
    st.success(f"**【{yao_num}爻の秘伝テキスト】**\n\n{yao_info}")

    # 4. 卦のビジュアル
    st.write("---")
    st.write("▼ 卦象（現在の波動）")
    visual_bars = []
    for i in range(1, 7):
        is_yang = random.choice([True, False]) 
        bar_design = "━━━━━━━━━━━━" if is_yang else "━━━━━　　━━━━━"
        if str(i) == yao_num:
            visual_bars.append(f"<span style='color:#ff4b4b; font-size:36px; font-weight:bold;'>▶ {bar_design} （第{i}爻）</span>")
        else:
            visual_bars.append(f"<span style='color:#ccc; font-size:30px;'>　 {bar_design}</span>")
    
    st.markdown(f"<div style='text-align:center; line-height:1.4;'>{'<br>'.join(reversed(visual_bars))}</div>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:right; font-size:18px;'>（全体勢力：{gua_info['base_score']}）</p>", unsafe_allow_html=True)
