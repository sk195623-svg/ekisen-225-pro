# 225 IChing Pro（作り直し版）

断易（五行易）の手順どおりに、立卦 → 納甲・六親・世応・六神・伏神 → 月建・日辰・空亡 → 用神の旺衰 → 見立て、を出すアプリです。

## ファイル
| ファイル | 中身 |
|---|---|
| `app.py` | 画面（Streamlit） |
| `danyi.py` | 断易の計算 |
| `requirements.txt` | Streamlit Cloud が入れる部品 |
| `test_danyi.py` | 計算の確認（10/16 兌為沢・10/18 風沢中孚を手計算と照合） |
| `test_app.py` | 画面の確認 |

## 前の版から変わったこと
- 日辰を本当の干支の暦で計算（日本時間）。月建は節入り（立春・啓蟄…）で切り替え。空亡も表示
- 立卦はコイン 3 枚 × 6 回（変爻は 0〜6 本）。「自分で立てた卦（卦名と変爻）」「自分のコインの結果」も入れられる
- 64 卦すべて。八宮・世応・納甲・六親・六神・伏神を表で表示
- 用神（既定は妻財）の旺衰を、月建・日辰・十二運・空亡・発動・回頭生剋・進退神・他の動爻から点数で出し、見立てを表示
- 鑑定を記録して CSV でダウンロードできる（あとで実際の値動きと答え合わせ）
- パスワードはプログラムに書かず、Streamlit の Secrets に置く

## Streamlit Cloud に出す手順
1. 今のアプリの GitHub リポジトリに、`app.py`・`danyi.py`・`requirements.txt` を入れる
   （今のアプリのファイル名が `streamlit_app.py` などなら、Streamlit Cloud の設定で「Main file path」を `app.py` に変えるか、`app.py` の名前をそれに合わせる）
2. Streamlit Cloud のアプリの「Settings → Secrets」に次の 1 行を書く
   ```
   password = "（パスワード）"
   ```
3. 保存すると自動で作り直されます

## 自分のパソコンで動かす
```
python -m pip install streamlit
python -m streamlit run app.py
```
Secrets を置かない場合はパスワード無しで開きます（環境変数 `EKISEN_PASSWORD` を設定すればそのパスワードになる）。
