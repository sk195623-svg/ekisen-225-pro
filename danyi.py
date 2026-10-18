"""断易（五行易）の計算エンジン。

立卦 → 納甲・六親・世応・六神・伏神 → 月建・日辰・空亡 → 用神の旺衰 → 判断、までを行う。
画面（app.py）からは cast_coins / from_name / build_reading / judge を使う。
"""
import datetime as dt
import math
import secrets

STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
ELEMENT = dict(zip(BRANCHES, "水土木木土火火土金金土水"))
GEN = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}   # A が生じるもの
CTRL = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}  # A が剋すもの
JST = dt.timezone(dt.timedelta(hours=9))

CLASH = {a: b for a, b in ["子午", "丑未", "寅申", "卯酉", "辰戌", "巳亥"]}
CLASH.update({b: a for a, b in CLASH.items()})
COMBINE = {a: b for a, b in ["子丑", "寅亥", "卯戌", "辰酉", "巳申", "午未"]}
COMBINE.update({b: a for a, b in COMBINE.items()})
ADVANCE = {"亥": "子", "寅": "卯", "巳": "午", "申": "酉", "丑": "辰", "辰": "未", "未": "戌", "戌": "丑"}
RETREAT = {b: a for a, b in ADVANCE.items()}

STAGES = ["長生", "沐浴", "冠帯", "臨官", "帝旺", "衰", "病", "死", "墓", "絶", "胎", "養"]
CHANGSHENG = {"木": "亥", "火": "寅", "土": "申", "金": "巳", "水": "申"}  # 断易は土を水と同じく申に長生

# 八卦（爻は下から）
TRIGRAMS = {"乾": (1, 1, 1), "兌": (1, 1, 0), "離": (1, 0, 1), "震": (1, 0, 0),
            "巽": (0, 1, 1), "坎": (0, 1, 0), "艮": (0, 0, 1), "坤": (0, 0, 0)}
TRIGRAM_OF = {v: k for k, v in TRIGRAMS.items()}
NATURE = {"乾": "天", "兌": "沢", "離": "火", "震": "雷", "巽": "風", "坎": "水", "艮": "山", "坤": "地"}
NAJIA = {"乾": ("子寅辰", "午申戌"), "坎": ("寅辰午", "申戌子"), "艮": ("辰午申", "戌子寅"),
         "震": ("子寅辰", "午申戌"), "巽": ("丑亥酉", "未巳卯"), "離": ("卯丑亥", "酉未巳"),
         "坤": ("未巳卯", "丑亥酉"), "兌": ("巳卯丑", "亥酉未")}
NAJIA_STEM = {"乾": "甲壬", "坎": "戊戊", "艮": "丙丙", "震": "庚庚",
              "巽": "辛辛", "離": "己己", "坤": "乙癸", "兌": "丁丁"}
PALACE_ELEMENT = {"乾": "金", "兌": "金", "離": "火", "震": "木", "巽": "木", "坎": "水", "艮": "土", "坤": "土"}

_ORDER = "乾兌離震巽坎艮坤"
_NAMES = {
    "乾": "乾為天 天沢履 天火同人 天雷无妄 天風姤 天水訟 天山遯 天地否",
    "兌": "沢天夬 兌為沢 沢火革 沢雷随 沢風大過 沢水困 沢山咸 沢地萃",
    "離": "火天大有 火沢睽 離為火 火雷噬嗑 火風鼎 火水未済 火山旅 火地晋",
    "震": "雷天大壮 雷沢帰妹 雷火豊 震為雷 雷風恒 雷水解 雷山小過 雷地予",
    "巽": "風天小畜 風沢中孚 風火家人 風雷益 巽為風 風水渙 風山漸 風地観",
    "坎": "水天需 水沢節 水火既済 水雷屯 水風井 坎為水 水山蹇 水地比",
    "艮": "山天大畜 山沢損 山火賁 山雷頤 山風蠱 山水蒙 艮為山 山地剥",
    "坤": "地天泰 地沢臨 地火明夷 地雷復 地風升 地水師 地山謙 坤為地",
}
HEX_NAME = {}  # 爻(下から6つ) -> 卦名
for _upper, _row in _NAMES.items():
    for _lower, _name in zip(_ORDER, _row.split()):
        HEX_NAME[TRIGRAMS[_lower] + TRIGRAMS[_upper]] = _name
HEX_LINES = {v: k for k, v in HEX_NAME.items()}


def _build_palaces():
    """八宮: 爻 -> (宮, 世の位置, 本宮/一世…/遊魂/帰魂)"""
    table = {}
    for palace, tri in TRIGRAMS.items():
        cur = list(tri + tri)
        table[tuple(cur)] = (palace, 6, "本宮")
        for i in range(5):
            cur[i] ^= 1
            table[tuple(cur)] = (palace, i + 1, "一二三四五"[i] + "世")
        cur[3] ^= 1
        table[tuple(cur)] = (palace, 4, "遊魂")
        cur[0:3] = list(tri)
        table[tuple(cur)] = (palace, 3, "帰魂")
    return table


PALACE = _build_palaces()
SIX_GODS = ["青龍", "朱雀", "勾陳", "螣蛇", "白虎", "玄武"]
GOD_START = {"甲": 0, "乙": 0, "丙": 1, "丁": 1, "戊": 2, "己": 3, "庚": 4, "辛": 4, "壬": 5, "癸": 5}


def relative(palace_element, element):
    """六親"""
    if element == palace_element:
        return "兄弟"
    if GEN[palace_element] == element:
        return "子孫"
    if CTRL[palace_element] == element:
        return "妻財"
    if CTRL[element] == palace_element:
        return "官鬼"
    return "父母"


def stage(element, branch):
    """十二運"""
    start = BRANCHES.index(CHANGSHENG[element])
    return STAGES[(BRANCHES.index(branch) - start) % 12]


# ---------------- 暦（日本時間） ----------------

def _sun_longitude(moment_utc):
    """太陽の視黄経（度）。Meeus の簡易式（誤差 0.01 度ほど）"""
    jd = moment_utc.timestamp() / 86400 + 2440587.5
    t = (jd - 2451545.0) / 36525
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
         + (0.019993 - 0.000101 * t) * math.sin(2 * m) + 0.000289 * math.sin(3 * m))
    omega = math.radians(125.04 - 1934.136 * t)
    return (l0 + c - 0.00569 - 0.00478 * math.sin(omega)) % 360


def ganzhi(index):
    return STEMS[index % 10] + BRANCHES[index % 12]


def calendar(moment):
    """年・月・日の干支と空亡。moment はタイムゾーン付き datetime（日本時間で日付を決める）"""
    local = moment.astimezone(JST)
    day_idx = (local.date().toordinal() + 14) % 60          # 0 = 甲子
    month_k = int(((_sun_longitude(moment.astimezone(dt.timezone.utc)) - 315) % 360) // 30)  # 0 = 寅月（立春から）
    year = local.year - (1 if local.month <= 2 and month_k >= 10 else 0)
    year_idx = (year - 4) % 60
    month_stem = ((year_idx % 5) * 2 + 2 + month_k) % 10
    month_branch = (2 + month_k) % 12
    month_idx = next(i for i in range(60) if i % 10 == month_stem and i % 12 == month_branch)
    xun = day_idx - day_idx % 10
    void = BRANCHES[(xun + 10) % 12] + BRANCHES[(xun + 11) % 12]
    return {"date": local, "year": ganzhi(year_idx), "month": ganzhi(month_idx),
            "day": ganzhi(day_idx), "void": void}


# ---------------- 立卦 ----------------

def cast_coins():
    """コイン 3 枚 × 6 回（下の爻から）。表=3・裏=2 の合計で 6老陰・7少陽・8少陰・9老陽"""
    rng = secrets.SystemRandom()
    return [sum(rng.choice((2, 3)) for _ in range(3)) for _ in range(6)]


def from_name(name, moving=()):
    """卦名と変爻（1〜6）から爻の値を作る"""
    lines = HEX_LINES[name]
    return [(9 if y else 6) if (i + 1) in moving else (7 if y else 8) for i, y in enumerate(lines)]


# ---------------- 組み立て ----------------

def _line_info(lines, palace_el):
    lower, upper = TRIGRAM_OF[tuple(lines[:3])], TRIGRAM_OF[tuple(lines[3:])]
    branches = NAJIA[lower][0] + NAJIA[upper][1]
    stems = NAJIA_STEM[lower][0] * 3 + NAJIA_STEM[upper][1] * 3
    return [{"stem": stems[i], "branch": b, "element": ELEMENT[b], "relative": relative(palace_el, ELEMENT[b])}
            for i, b in enumerate(branches)]


def build_reading(values, moment):
    """values: 下から 6 つの 6/7/8/9"""
    cal = calendar(moment)
    yin_yang = tuple(1 if v in (7, 9) else 0 for v in values)
    moving = [v in (6, 9) for v in values]
    changed = tuple(y ^ 1 if m else y for y, m in zip(yin_yang, moving))
    palace, shi, kind = PALACE[yin_yang]
    pel = PALACE_ELEMENT[palace]
    lines = _line_info(yin_yang, pel)
    changed_lines = _line_info(changed, pel)   # 変爻の六親は本卦の宮で見る
    pure = _line_info(TRIGRAMS[palace] * 2, pel)
    present = {ln["relative"] for ln in lines}
    god0 = GOD_START[cal["day"][0]]
    for i, ln in enumerate(lines):
        ln.update(pos=i + 1, yang=yin_yang[i], moving=moving[i], god=SIX_GODS[(god0 + i) % 6],
                  role="世" if i + 1 == shi else ("応" if i + 1 == (shi + 2) % 6 + 1 else ""),
                  changed=changed_lines[i] if moving[i] else None,
                  hidden=pure[i] if pure[i]["relative"] not in present else None)
    return {"calendar": cal, "values": list(values), "name": HEX_NAME[yin_yang],
            "changed_name": HEX_NAME[changed] if any(moving) else None,
            "palace": palace, "palace_element": pel, "kind": kind, "shi": shi, "lines": lines}


# ---------------- 旺衰と判断 ----------------

def strength(branch, cal, moving=False, changed=None, others=()):
    """旺衰の要因を (点数, 説明) の一覧で返す"""
    el, mon, day = ELEMENT[branch], cal["month"][1], cal["day"][1]
    mel, dele = ELEMENT[mon], ELEMENT[day]
    f = []
    # 月建
    if branch == mon:
        f.append((2, f"月建 {mon} に臨む（旺）"))
    elif CLASH[branch] == mon:
        f.append((-2, f"月建 {mon} に冲される（月破）"))
    else:
        if el == mel:
            f.append((2, f"月建 {mon} と同じ五行（旺）"))
        elif GEN[mel] == el:
            f.append((1, f"月建 {mon} から生じられる（相）"))
        elif CTRL[mel] == el:
            f.append((-2, f"月建 {mon} に剋される（死）"))
        elif CTRL[el] == mel:
            f.append((-1, f"月建 {mon} を剋す側で力を使う（囚）"))
        else:
            f.append((0, f"月建 {mon} を生じて気が漏れる（休）"))
        if COMBINE[branch] == mon:
            f.append((1, f"月建 {mon} と合（月合）"))
    so_far = sum(s for s, _ in f)
    # 日辰
    if branch == day:
        f.append((2, f"日辰 {day} に臨む"))
    elif COMBINE[branch] == day:
        f.append((0, f"日辰 {day} と合（{'合住＝動きが縛られる' if moving else '合起'}）"))
    elif CLASH[branch] == day:
        if moving:
            f.append((-2 if so_far <= 0 else 0, f"日辰 {day} に冲される（{'冲散' if so_far <= 0 else '冲されても旺相で耐える'}）"))
        else:
            f.append((1 if so_far > 0 else -2, f"日辰 {day} に冲される（{'暗動' if so_far > 0 else '日破'}）"))
    elif GEN[dele] == el:
        f.append((2, f"日辰 {day} から生じられる"))
    elif dele == el:
        f.append((1, f"日辰 {day} と比和"))
    elif CTRL[dele] == el:
        f.append((-2, f"日辰 {day} に剋される"))
    st_day = stage(el, day)
    if st_day in ("長生", "臨官", "帝旺"):
        f.append((1, f"日辰で{st_day}"))
    elif st_day in ("墓", "絶"):
        f.append((-1, f"日辰で{st_day}（{'入墓' if st_day == '墓' else '絶'}）"))
    # 空亡
    if branch in cal["void"]:
        f.append((0 if moving or so_far > 0 else -2,
                  "空亡（動爻・旺相なので真空ではなく、出空を待つ）" if moving or so_far > 0 else "空亡（真空）"))
    # 発動と変化
    if moving:
        f.append((1, "発動している"))
        if changed:
            c, cel = changed, ELEMENT[changed]
            if GEN[cel] == el:
                f.append((2, f"{c}に化して回頭生"))
            elif CTRL[cel] == el:
                f.append((-3, f"{c}に化して回頭剋"))
            if ADVANCE.get(branch) == c:
                f.append((1, f"{c}に化して化進神（勢いが増す）"))
            elif RETREAT.get(branch) == c:
                f.append((-1, f"{c}に化して化退神（勢いが引いていく）"))
            if c in cal["void"]:
                f.append((-1, f"化空（{c}は空亡）"))
            st_c = stage(el, c)
            if st_c in ("墓", "絶"):
                f.append((-1, f"化{st_c}"))
    # 他の動爻
    for o in others:
        oel = ELEMENT[o["branch"]]
        if GEN[oel] == el:
            f.append((1, f"{o['pos']}爻 {o['relative']} {o['branch']}{oel} が動いて生じる"))
        elif CTRL[oel] == el:
            f.append((-1, f"{o['pos']}爻 {o['relative']} {o['branch']}{oel} が動いて剋す"))
    return f


def judge(reading, use="妻財"):
    """用神を決めて旺衰を出し、相場の見立てを返す"""
    lines, cal = reading["lines"], reading["calendar"]
    movers = [ln for ln in lines if ln["moving"]]
    notes = []
    if use == "世爻":
        target = next(ln for ln in lines if ln["role"] == "世")
        source = f"世爻（{target['pos']}爻 {target['relative']} {target['branch']}）"
    else:
        cands = [ln for ln in lines if ln["relative"] == use]
        if cands:
            cands.sort(key=lambda ln: (not ln["moving"], ln["role"] == "", ln["pos"]))
            target = cands[0]
            source = f"{target['pos']}爻 {use} {target['branch']}{target['element']}"
        else:
            emerged = [ln for ln in movers if ln["changed"]["relative"] == use]
            hidden = [ln for ln in lines if ln["hidden"] and ln["hidden"]["relative"] == use]
            if emerged:
                ln = emerged[0]
                target = dict(ln["changed"], pos=ln["pos"], moving=False, changed=None, role="", god=ln["god"])
                source = f"{ln['pos']}爻の変爻に化出した {use} {target['branch']}{target['element']}"
                notes.append(f"用神は本卦に無く、{ln['pos']}爻が動いて化出（動きの中から値段が出てくる）")
            elif hidden:
                ln = hidden[0]
                target = dict(ln["hidden"], pos=ln["pos"], moving=False, changed=None, role="", god=ln["god"])
                source = f"{ln['pos']}爻の下の伏神 {use} {target['branch']}{target['element']}"
                notes.append("用神は伏神（表に出ていない＝方向感が見えにくい）")
            else:
                return {"source": f"{use}が見つかりません", "factors": [], "score": 0, "verdict": "判断できません", "notes": []}
    others = [ln for ln in movers if ln["pos"] != target["pos"]]
    factors = strength(target["branch"], cal, target["moving"],
                       target["changed"]["branch"] if target.get("changed") else None, others)
    if source.startswith(f"{target['pos']}爻の下の伏神"):
        fly = lines[target["pos"] - 1]
        if GEN[fly["element"]] == target["element"]:
            factors.append((1, f"飛神 {fly['branch']}{fly['element']} が伏神を生じる"))
        elif CTRL[fly["element"]] == target["element"]:
            factors.append((-1, f"飛神 {fly['branch']}{fly['element']} が伏神を剋す"))
        factors.append((-1, "伏神なので表に出にくい"))
    score = sum(s for s, _ in factors)
    if score >= 3:
        verdict = "上昇基調"
    elif score >= 1:
        verdict = "やや強含み"
    elif score >= -1:
        verdict = "もみ合い"
    elif score >= -2:
        verdict = "やや弱含み"
    else:
        verdict = "下落基調"
    texts = " ".join(t for _, t in factors)
    if "化退神" in texts:
        notes.append("化退神：勢いは時間とともに引いていく（後半は鈍りやすい）")
    if "化進神" in texts:
        notes.append("化進神：後半に勢いが増しやすい")
    if "回頭剋" in texts:
        notes.append("回頭剋：動いても途中で崩れやすい")
    shi = next(ln for ln in lines if ln["role"] == "世")
    if use == "妻財" and shi["relative"] == "兄弟":
        notes.append("兄弟持世：財が逃げやすい（上値が重い・利が乗りにくい）")
    for ln in movers:
        if use == "妻財" and ln["relative"] == "子孫":
            notes.append(f"原神の子孫（{ln['pos']}爻）が発動：財を生じる追い風")
        if use == "妻財" and ln["relative"] == "兄弟":
            notes.append(f"忌神の兄弟（{ln['pos']}爻）が発動：財を剋す向かい風")
        if ln["relative"] == "父母":
            notes.append(f"父母（{ln['pos']}爻）が発動：ニュース・発表がきっかけになりやすい")
    return {"source": source, "factors": factors, "score": score, "verdict": verdict, "notes": notes,
            "target": target}


# ---------------- 解説文 ----------------

MEANING = {
    "乾為天": "剛健・純陽。勢いは強いが、上りつめれば反落も", "天沢履": "虎の尾を踏む。慎重に進めば無難",
    "天火同人": "仲間が集まる。同じ方向に人が集まりやすい", "天雷无妄": "作為なし。予想外の動きに注意、自然体で",
    "天風姤": "思わぬ出会い。不意の材料が出やすい", "天水訟": "争い。売り買いが対立して決着しにくい",
    "天山遯": "退く。勢いが衰え、引き際を探す", "天地否": "ふさがる。閉塞感・停滞",
    "沢天夬": "決断・決壊。一方向へ大きく動く転換点", "兌為沢": "喜び。にぎやかだが口先（噂）にも注意",
    "沢火革": "改める。流れが変わる", "沢雷随": "随う。流れについていく",
    "沢風大過": "重すぎる。行き過ぎ・限界", "沢水困": "行き詰まり。苦しい停滞",
    "沢山咸": "感応。材料に敏感に反応する", "沢地萃": "集まる。資金や注文が集まる",
    "火天大有": "大いに有つ。盛大・好調", "火沢睽": "そむく。ちぐはぐな動き",
    "離為火": "明るさ。華やかだが変わりやすい", "火雷噬嗑": "噛み砕く。障害を突破する",
    "火風鼎": "鼎。安定・新しい体制", "火水未済": "未完成。決着せず混沌",
    "火山旅": "旅。落ち着かず不安定", "火地晋": "進む・日の出。順調に上る",
    "雷天大壮": "大いに盛ん。猛進、行き過ぎに注意", "雷沢帰妹": "順序を誤る。勇み足",
    "雷火豊": "盛大の極み。ピークの後は欠ける", "震為雷": "震動。驚くような動き、音ばかりで実は少ないことも",
    "雷風恒": "恒久。今の流れが続く", "雷水解": "解ける。停滞がほどける",
    "雷山小過": "少し過ぎる。小さく行き過ぎる", "雷地予": "予め楽しむ。期待先行",
    "風天小畜": "少し止める。小さな足踏み", "風沢中孚": "真心・信。素直な流れだが中は虚",
    "風火家人": "内を固める。堅実", "風雷益": "益す。利益が増す",
    "巽為風": "従う・入る。迷いやすく出入りが多い", "風水渙": "散る。不安や資金が散る",
    "風山漸": "少しずつ進む。じわじわ", "風地観": "観る。様子見",
    "水天需": "待つ。時期を待つ", "水沢節": "節度。区切り・抑え",
    "水火既済": "完成。整った後は乱れやすい", "水雷屯": "産みの苦しみ。もたつく",
    "水風井": "井戸。変わらない・地味", "坎為水": "険難。困難が重なる",
    "水山蹇": "足止め。進みにくい", "水地比": "親しむ。足並みが揃う",
    "山天大畜": "大いに蓄える。力をためる", "山沢損": "減らす。損して得取れ",
    "山火賁": "飾る。見かけ倒しに注意", "山雷頤": "養う。口（ニュース）で動く",
    "山風蠱": "腐敗と立て直し。混乱の後始末", "山水蒙": "蒙い。先が見えない",
    "艮為山": "止まる。動かない", "山地剥": "剥がれる。崩れていく",
    "地天泰": "安泰。通じる・好調", "地沢臨": "臨む。勢いが近づく",
    "地火明夷": "明かりが傷つく。暗い局面", "地雷復": "一陽来復。反転の兆し",
    "地風升": "昇る。じわじわ上昇", "地水師": "戦い。集団での争い",
    "地山謙": "謙虚。目立たないが底堅い", "坤為地": "柔順・受け身。流れに従う",
}
RELATIVE_MEANING = {"父母": "ニュース・発表・指標", "兄弟": "競争・損失・財を奪うもの", "子孫": "好材料・安心・財の元",
                    "妻財": "値段・利益", "官鬼": "不安・リスク・波乱"}
GOD_MEANING = {"青龍": "喜び・吉事", "朱雀": "ニュース・噂・口舌", "勾陳": "停滞・もたつき",
               "螣蛇": "迷い・乱高下・思わぬこと", "白虎": "激しさ・急変", "玄武": "思惑・だまし・見えにくい動き"}


def _level(score):
    if score >= 3:
        return "旺相（元気）"
    if score >= 1:
        return "やや強い"
    if score >= -1:
        return "強くも弱くもない"
    return "弱い（休囚）"


def _day_effect(day_branch, target_branch, void):
    """日ごとの目安: 日の十二支が用神にどう働くか"""
    el, tel = ELEMENT[day_branch], ELEMENT[target_branch]
    if day_branch == target_branch:
        s = "用神の日（値日）。動きが出やすい"
        if target_branch in void:
            s += "。空亡が明ける（出空）"
        return s
    if CLASH[day_branch] == target_branch:
        return "用神を冲す。強ければ動きが出て、弱ければ散る" + ("。冲で空亡が明ける（出空）" if target_branch in void else "")
    if COMBINE[day_branch] == target_branch:
        return "用神と合。足止め・もみ合いやすい"
    st_ = stage(tel, day_branch)
    if st_ == "墓":
        return "用神が入墓。値動きが鈍りやすい"
    if st_ == "絶":
        return "用神が絶。力が抜けやすい"
    if GEN[el] == tel:
        return "用神を生じる。追い風"
    if CTRL[el] == tel:
        return "用神を剋す。向かい風"
    if el == tel:
        return "用神と比和。やや追い風"
    return "大きな働きなし"


def explain(reading, j, days=5):
    """見立ての解説を (見出し, 本文) の一覧で返す"""
    lines, cal = reading["lines"], reading["calendar"]
    out = []
    # 1. 卦の流れ
    flow = f"本卦「{reading['name']}」は {MEANING[reading['name']]}。"
    if reading["changed_name"]:
        flow += f"之卦「{reading['changed_name']}」は {MEANING[reading['changed_name']]}。"
        flow += f"「{reading['name']}」の状態から「{reading['changed_name']}」へ移っていく流れです。"
    else:
        flow += "変爻が無いので、今の状態がそのまま続きやすい卦です。"
    out.append(("卦の流れ", flow))
    if not j["factors"]:
        return out
    # 2. 用神
    t = j["target"]
    good = [x for s, x in j["factors"] if s > 0]
    bad = [x for s, x in j["factors"] if s < 0]
    text = f"用神は {j['source']}。力は「{_level(j['score'])}」です。"
    if good:
        text += "助けになっているのは、" + "、".join(good) + "。"
    if bad:
        text += "足を引っ張っているのは、" + "、".join(bad) + "。"
    neutral = [x for s, x in j["factors"] if s == 0]
    if neutral:
        text += "そのほか、" + "、".join(neutral) + "。"
    if t.get("god"):
        text += f"用神には{t['god']}（{GOD_MEANING[t['god']]}）が付いています。"
    out.append(("用神（値段）の状態", text))
    # 3. 世爻・応爻
    shi = next(ln for ln in lines if ln["role"] == "世")
    ying = next(ln for ln in lines if ln["role"] == "応")
    shi_score = sum(s for s, _ in strength(shi["branch"], cal, shi["moving"],
                                           shi["changed"]["branch"] if shi["changed"] else None))
    text = (f"世爻（自分の立場）は {shi['pos']}爻 {shi['relative']} {shi['branch']}{shi['element']}・{shi['god']}で、"
            f"力は「{_level(shi_score)}」。{shi['relative']}は{RELATIVE_MEANING[shi['relative']]}を表します。"
            f"応爻（相場・相手）は {ying['pos']}爻 {ying['relative']} {ying['branch']}{ying['element']}。")
    if GEN[ying["element"]] == shi["element"]:
        text += "応が世を生じていて、相場が自分に味方しやすい形です。"
    elif CTRL[ying["element"]] == shi["element"]:
        text += "応が世を剋していて、相場に振り回されやすい形です。"
    elif CLASH[ying["branch"]] == shi["branch"]:
        text += "世と応が冲していて、思惑がぶつかりやすい形です。"
    if t.get("role") == "世" and j["source"].endswith(f"{t['branch']}{t['element']}") and "伏神" not in j["source"]:
        text += "用神が世に付いています（値動きを自分の手でつかみやすい）。"
    out.append(("世爻と応爻", text))
    # 4. 動爻
    movers = [ln for ln in lines if ln["moving"]]
    if movers:
        parts = []
        for ln in movers:
            c = ln["changed"]
            s = (f"{ln['pos']}爻 {ln['relative']} {ln['branch']}{ln['element']}（{ln['god']}＝{GOD_MEANING[ln['god']]}）が動き、"
                 f"{c['relative']} {c['branch']}{c['element']}に変わります。{ln['relative']}は{RELATIVE_MEANING[ln['relative']]}。")
            if GEN[c["element"]] == ln["element"]:
                s += "回頭生で、動きに力が足されます。"
            elif CTRL[c["element"]] == ln["element"]:
                s += "回頭剋で、動いても途中で崩れやすい。"
            if ADVANCE.get(ln["branch"]) == c["branch"]:
                s += "化進神で、勢いが増していく。"
            elif RETREAT.get(ln["branch"]) == c["branch"]:
                s += "化退神で、勢いが引いていく。"
            parts.append(s)
        out.append(("動いた爻", "".join(parts)))
    else:
        out.append(("動いた爻", "変爻はありません。大きな変化よりも、今の状態が続きやすい形です。"))
    # 5. 日ごとの目安
    rows = []
    d0 = cal["date"].date()
    k = 0
    while len(rows) < days and k < 14:
        dd = d0 + dt.timedelta(days=k)
        k += 1
        if dd.weekday() >= 5:
            continue
        gz = ganzhi((dd.toordinal() + 14) % 60)
        rows.append(f"{dd.month}/{dd.day}({'月火水木金土日'[dd.weekday()]}) {gz}：{_day_effect(gz[1], t['branch'], cal['void'])}")
    out.append(("日ごとの目安（遊び半分で）", "\n".join(rows)))
    # 6. まとめ
    v = j["verdict"]
    summary = {"上昇基調": "値段を表す用神がしっかりしていて、上方向に動きやすい見立てです。",
               "やや強含み": "用神にほどほどの力があり、どちらかといえば上方向。",
               "もみ合い": "用神の力は五分五分。方向感が出にくく、もみ合いやすい見立てです。",
               "やや弱含み": "用神の力が足りず、どちらかといえば下方向、または上値が重い見立てです。",
               "下落基調": "用神が弱く傷ついていて、下方向に動きやすい見立てです。"}.get(v, "")
    if j["notes"]:
        summary += "ポイントは、" + "／".join(j["notes"]) + "。"
    out.append(("まとめ", summary))
    return out
