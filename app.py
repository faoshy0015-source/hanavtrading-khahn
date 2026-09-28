import os
import io
import zipfile
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import time
import hmac
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

st.set_page_config(page_title="HanaV Trading", page_icon="📈", layout="wide")

# ==================================================
# APP PASSWORD LOGIN
# Streamlit Cloud > App settings > Secrets:
# APP_PASSWORD = "원하는 비밀번호"
# ==================================================
def _get_app_password():
    try:
        return str(st.secrets["APP_PASSWORD"])
    except Exception:
        return ""

def _check_app_password():
    expected=_get_app_password()
    entered=str(st.session_state.get("_hanav_password",""))
    ok=bool(expected) and hmac.compare_digest(entered, expected)
    st.session_state["_hanav_authenticated"]=ok
    st.session_state["_hanav_login_error"]=not ok
    st.session_state["_hanav_password"]=""

def _logout_hanav():
    st.session_state["_hanav_authenticated"]=False
    st.session_state["_hanav_login_error"]=False

st.session_state.setdefault("_hanav_authenticated",False)
st.session_state.setdefault("_hanav_login_error",False)

if not st.session_state["_hanav_authenticated"]:
    st.markdown("""
    <div style="max-width:430px;margin:11vh auto 22px;text-align:center;">
      <div style="font-size:34px;font-weight:950;color:#00B873;">HanaV Trading</div>
      <div style="margin-top:7px;color:#8FA69D;font-size:13px;font-weight:650;">Private Investment Dashboard</div>
      <div style="margin-top:4px;color:#6F847C;font-size:11px;">Designed &amp; Built by K.H. Ahn</div>
    </div>""",unsafe_allow_html=True)

    if not _get_app_password():
        st.error("APP_PASSWORD가 설정되지 않았습니다. Streamlit Cloud의 App settings → Secrets에 APP_PASSWORD를 추가해 주세요.")
        st.stop()

    _l,_c,_r=st.columns([1,1.15,1])
    with _c:
        st.text_input("비밀번호",type="password",key="_hanav_password",
                      placeholder="비밀번호를 입력하세요",on_change=_check_app_password)
        if st.button("🔐 로그인",use_container_width=True,key="_hanav_login_button"):
            _check_app_password()
            st.rerun()
        if st.session_state.get("_hanav_login_error",False):
            st.error("비밀번호가 올바르지 않습니다.")
    st.stop()


REAL_URL="https://openapi.koreainvestment.com:9443"
PAPER_URL="https://openapivts.koreainvestment.com:29443"

st.markdown("""<style>
:root {
    --hana-green:#00B86B;
    --hana-green-bright:#18D487;
    --hana-green-dark:#087A52;
    --bg:#0B1110;
    --panel:#111A17;
    --panel-2:#16221E;
    --border:#2A3B35;
    --text:#F1F7F4;
    --muted:#9EB0A9;
}
html, body, [data-testid="stAppViewContainer"], .stApp {
    background:var(--bg) !important; color:var(--text) !important; min-height:100vh !important;
}
html, body { margin:0 !important; padding:0 !important; }
header[data-testid="stHeader"] { display:none !important; height:0 !important; }
[data-testid="stToolbar"], [data-testid="stAppToolbar"], [data-testid="stDecoration"], #MainMenu, footer,
.viewerBadge_container__1QSob { display:none !important; }
[data-testid="stAppViewContainer"] > .main { min-height:100vh !important; padding-top:0 !important; }
.main .block-container, [data-testid="stMainBlockContainer"] {
    max-width:100% !important; min-height:100vh !important; padding:.45rem .75rem .65rem .75rem !important;
}
section[data-testid="stSidebar"] {
    background:#0E1714 !important; border-right:1px solid #274039 !important; top:0 !important; height:100vh !important;
}
section[data-testid="stSidebar"] > div { height:100vh !important; padding-top:.35rem !important; }
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
    color:#EAF7F1 !important;
}
section[data-testid="stSidebar"] hr { border-color:#263B34 !important; }
.title {
    background:linear-gradient(90deg,#0E211A 0%,#13251F 55%,#101A17 100%);
    border:1px solid #256E52; border-left:4px solid var(--hana-green-bright);
    padding:11px 15px; font-size:20px; font-weight:800; color:#F4FBF8; letter-spacing:.2px;
}
.head {
    background:linear-gradient(90deg,#123126 0%,#16241F 100%);
    border:1px solid #269668; border-left:4px solid var(--hana-green-bright);
    padding:10px 13px; font-weight:800; color:#F6FCF9;
}
.box {
    background:#14201C; border:1px solid #315047; border-radius:6px; padding:9px; text-align:center;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.02);
}
.lab { color:#9FB6AD; font-size:11px; font-weight:600; }
.val { color:#F4FAF7; font-size:16px; font-weight:800; }
/* 입력창/셀렉트 가독성 */
[data-baseweb="input"] > div, [data-baseweb="select"] > div, [data-testid="stNumberInput"] input {
    background:#F4F7F5 !important; color:#14201C !important; border-color:#78958A !important;
}
[data-baseweb="input"] input, [data-baseweb="select"] input { color:#14201C !important; }
[data-baseweb="select"] svg { fill:#28483D !important; }
/* 버튼: 하나 그린 포인트 */
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
    background:#00A968 !important; color:white !important; border:1px solid #23D18B !important; font-weight:800 !important;
}
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover {
    background:#00BE76 !important; border-color:#52E6AA !important;
}
/* 슬라이더/토글 포인트 */
[data-baseweb="slider"] [role="slider"] { background:#18D487 !important; }
[data-testid="stToggle"] [data-checked="true"] { background:#00A968 !important; }
/* 데이터프레임/알림 */
[data-testid="stDataFrame"] { border:1px solid #2D4A40; border-radius:5px; overflow:hidden; }
[data-testid="stAlert"] { border-color:#315047 !important; }
/* 캡션과 보조 텍스트 */
[data-testid="stCaptionContainer"], .stCaption { color:#91A79E !important; }
/* 스크롤바 */
::-webkit-scrollbar { width:9px; height:9px; }
::-webkit-scrollbar-track { background:#0B1110; }
::-webkit-scrollbar-thumb { background:#315047; border-radius:8px; }
::-webkit-scrollbar-thumb:hover { background:#00A968; }

/* ===== HTS HIGH-CONTRAST OVERRIDES ===== */
.stApp, [data-testid="stAppViewContainer"] { background:#070B0A !important; color:#F7FFFB !important; }
section[data-testid="stSidebar"] { background:#0A100E !important; border-right:1px solid #00B873 !important; }
.title { background:#081611 !important; border:1px solid #00C97B !important; border-left:5px solid #20E99A !important; color:#FFFFFF !important; box-shadow:0 0 12px rgba(0,201,123,.12); }
.head { background:#0B1A15 !important; border:1px solid #00D184 !important; border-left:5px solid #20E99A !important; color:#FFFFFF !important; }
.box { background:#0D1512 !important; border:1px solid #34554A !important; border-top:2px solid #00B873 !important; }
.lab { color:#AFC7BE !important; font-weight:700 !important; }
.val { color:#FFFFFF !important; font-size:17px !important; }
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span { color:#DDEBE5 !important; }
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color:#37F0A7 !important; }
[data-baseweb="input"] > div, [data-baseweb="select"] > div, [data-testid="stNumberInput"] input { background:#F8FFFC !important; color:#07100C !important; border:1px solid #00A968 !important; }
[data-baseweb="select"] * { color:#07100C !important; }
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] { background:#00B873 !important; color:#001B10 !important; border:1px solid #43FFB5 !important; font-weight:900 !important; }
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover { background:#24E89B !important; color:#00130C !important; }
[data-testid="stDataFrame"] { border:1px solid #00A968 !important; }
hr { border-color:#24453A !important; }

/* 오늘의 시장 새로고침 버튼: 흰색 배경 제거 */
.st-key-refresh_today_market button {
    background: transparent !important;
    color: #DDEBE5 !important;
    border: 1px solid #315047 !important;
    font-weight: 800 !important;
}
.st-key-refresh_today_market button:hover {
    background: rgba(0, 184, 115, 0.08) !important;
    color: #37F0A7 !important;
    border-color: #00B873 !important;
}

.st-key-refresh_earnings_top button {
    background: transparent !important;
    color: #DDEBE5 !important;
    border: 1px solid #315047 !important;
    font-weight: 800 !important;
}
.st-key-refresh_earnings_top button:hover {
    background: rgba(0, 184, 115, 0.08) !important;
    color: #37F0A7 !important;
    border-color: #00B873 !important;
}

</style>""",unsafe_allow_html=True)

def secret(k):
    try:
        if k in st.secrets:return str(st.secrets[k]).strip()
    except: pass
    return os.getenv(k,"").strip()

KEY,SEC=secret("KIS_APP_KEY"),secret("KIS_APP_SECRET")

MASTER_URLS = {
    "KOSPI": "https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip",
    "KOSDAQ": "https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip",
}

# KIS 공식 종목 마스터 파일의 고정폭 정의.
KOSPI_WIDTHS = [2,1,4,4,4,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,9,5,5,1,1,1,2,1,1,1,2,2,2,3,1,3,12,12,8,15,21,2,7,1,1,1,1,1,9,9,9,5,9,8,9,3,1,1,1]
KOSPI_COLS = ['그룹코드','시가총액규모','지수업종대분류','지수업종중분류','지수업종소분류','제조업','저유동성','지배구조지수종목','KOSPI200섹터업종','KOSPI100','KOSPI50','KRX','ETP','ELW발행','KRX100','KRX자동차','KRX반도체','KRX바이오','KRX은행','SPAC','KRX에너지화학','KRX철강','단기과열','KRX미디어통신','KRX건설','Non1','KRX증권','KRX선박','KRX섹터_보험','KRX섹터_운송','SRI','기준가','매매수량단위','시간외수량단위','거래정지','정리매매','관리종목','시장경고','경고예고','불성실공시','우회상장','락구분','액면변경','증자구분','증거금비율','신용가능','신용기간','전일거래량','액면가','상장일자','상장주수','자본금','결산월','공모가','우선주','공매도과열','이상급등','KRX300','KOSPI','매출액','영업이익','경상이익','당기순이익','ROE','기준년월','시가총액','그룹사코드','회사신용한도초과','담보대출가능','대주가능']
KOSDAQ_WIDTHS = [2,1,4,4,4,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,9,5,5,1,1,1,2,1,1,1,2,2,2,3,1,3,12,12,8,15,21,2,7,1,1,1,1,9,9,9,5,9,8,9,3,1,1,1]
KOSDAQ_COLS = ['증권그룹구분코드','시가총액 규모 구분 코드 유가','지수업종 대분류 코드','지수 업종 중분류 코드','지수업종 소분류 코드','벤처기업 여부 (Y/N)','저유동성종목 여부','KRX 종목 여부','ETP 상품구분코드','KRX100 종목 여부 (Y/N)','KRX 자동차 여부','KRX 반도체 여부','KRX 바이오 여부','KRX 은행 여부','기업인수목적회사여부','KRX 에너지 화학 여부','KRX 철강 여부','단기과열종목구분코드','KRX 미디어 통신 여부','KRX 건설 여부','(코스닥)투자주의환기종목여부','KRX 증권 구분','KRX 선박 구분','KRX섹터지수 보험여부','KRX섹터지수 운송여부','KOSDAQ150지수여부 (Y,N)','주식 기준가','정규 시장 매매 수량 단위','시간외 시장 매매 수량 단위','거래정지 여부','정리매매 여부','관리 종목 여부','시장 경고 구분 코드','시장 경고위험 예고 여부','불성실 공시 여부','우회 상장 여부','락구분 코드','액면가 변경 구분 코드','증자 구분 코드','증거금 비율','신용주문 가능 여부','신용기간','전일 거래량','주식 액면가','주식 상장 일자','상장 주수(천)','자본금','결산 월','공모 가격','우선주 구분 코드','공매도과열종목여부','이상급등종목여부','KRX300 종목 여부 (Y/N)','매출액','영업이익','경상이익','단기순이익','ROE(자기자본이익률)','기준년월','전일기준 시가총액 (억)','그룹사 코드','회사신용한도초과여부','담보대출가능여부','대주가능여부']

@st.cache_data(ttl=21600, show_spinner=False)
def load_stock_master():
    """KIS 공식 KOSPI/KOSDAQ 마스터에서 종목명 + ROE + 전일거래량을 읽는다."""
    frames=[]
    for market,url in MASTER_URLS.items():
        r=requests.get(url,timeout=20); r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            mst_name=next(n for n in zf.namelist() if n.lower().endswith('.mst'))
            text=zf.read(mst_name).decode('cp949',errors='replace')
        suffix_len=228 if market=='KOSPI' else 222
        widths=KOSPI_WIDTHS if market=='KOSPI' else KOSDAQ_WIDTHS
        cols=KOSPI_COLS if market=='KOSPI' else KOSDAQ_COLS
        items=[]; suffixes=[]
        for row in text.splitlines():
            if len(row)<=suffix_len: continue
            prefix=row[:-suffix_len]; suffix=row[-suffix_len:]
            short_code=prefix[:9].strip(); std_code=prefix[9:21].strip(); stock_name=prefix[21:].strip()
            code=short_code[-6:] if len(short_code)>=6 else short_code.zfill(6)
            if len(code)==6 and code.isdigit() and stock_name:
                items.append({'code':code,'name':stock_name,'market':market,'std_code':std_code})
                suffixes.append(suffix)
        if not items: continue
        meta=pd.read_fwf(io.StringIO('\n'.join(suffixes)),widths=widths,names=cols,dtype=str)
        base=pd.DataFrame(items).reset_index(drop=True)
        if market=='KOSPI':
            base['roe']=pd.to_numeric(meta['ROE'],errors='coerce')
            base['prev_volume']=pd.to_numeric(meta['전일거래량'],errors='coerce')
            base['master_cap']=pd.to_numeric(meta['시가총액'],errors='coerce')
        else:
            base['roe']=pd.to_numeric(meta['ROE(자기자본이익률)'],errors='coerce')
            base['prev_volume']=pd.to_numeric(meta['전일 거래량'],errors='coerce')
            base['master_cap']=pd.to_numeric(meta['전일기준 시가총액 (억)'],errors='coerce')
        frames.append(base)
    if not frames:
        return pd.DataFrame(columns=['code','name','market','std_code','roe','prev_volume','master_cap'])
    master=pd.concat(frames,ignore_index=True)
    return master.drop_duplicates(subset=['code','market']).sort_values(['name','code']).reset_index(drop=True)

def num(v):
    try:return float(str(v or 0).replace(",",""))
    except:return 0.0

class KIS:
    def __init__(self,k,s,paper=False):
        self.k,self.s=k,s; self.base=PAPER_URL if paper else REAL_URL; self.token=""
    def auth(self):
        r=requests.post(self.base+"/oauth2/tokenP",json={"grant_type":"client_credentials","appkey":self.k,"appsecret":self.s},timeout=15)
        d=r.json()
        if not r.ok or not d.get("access_token"):raise RuntimeError(d.get("error_description") or d.get("msg1") or r.text[:250])
        self.token=d["access_token"]
    def get(self,path,tr,params):
        if not self.token:self.auth()
        h={"content-type":"application/json; charset=utf-8","authorization":f"Bearer {self.token}",
           "appkey":self.k,"appsecret":self.s,"tr_id":tr,"custtype":"P"}
        r=requests.get(self.base+path,headers=h,params=params,timeout=15)
        try:d=r.json()
        except:raise RuntimeError(r.text[:250])
        if d.get("msg_cd")=="EGW00123":
            self.auth(); h["authorization"]=f"Bearer {self.token}"
            d=requests.get(self.base+path,headers=h,params=params,timeout=15).json()
        if str(d.get("rt_cd","0"))!="0":raise RuntimeError(f"{d.get('msg_cd','')} {d.get('msg1','API 오류')}")
        return d
    def price(self,c):
        return self.get("/uapi/domestic-stock/v1/quotations/inquire-price","FHKST01010100",
                        {"FID_COND_MRKT_DIV_CODE":"J","FID_INPUT_ISCD":c}).get("output",{})
    def chart(self,c,p):
        end=datetime.now(); start=end-timedelta(days={"D":365,"W":1095,"M":2920}[p])
        return self.get("/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice","FHKST03010100",
          {"FID_COND_MRKT_DIV_CODE":"J","FID_INPUT_ISCD":c,"FID_INPUT_DATE_1":start.strftime("%Y%m%d"),
           "FID_INPUT_DATE_2":end.strftime("%Y%m%d"),"FID_PERIOD_DIV_CODE":p,"FID_ORG_ADJ_PRC":"0"}).get("output2",[])
    def estimate_perform(self,c):
        # KIS 국내주식-187 종목추정실적. 공식 문서상 모의투자는 미지원.
        if self.base == PAPER_URL:
            raise RuntimeError("종목추정실적 API는 모의투자에서 지원되지 않습니다. 모의투자 API를 끄고 조회해 주세요.")
        return self.get("/uapi/domestic-stock/v1/quotations/estimate-perform","HHKST668300C0",
                        {"SHT_CD":str(c).zfill(6)})
    def scan(self,mkt,cnt,lo,hi,vol,r1,r2):
        return self.get("/uapi/domestic-stock/v1/ranking/fluctuation","FHPST01700000",
          {"FID_COND_MRKT_DIV_CODE":"J","FID_COND_SCR_DIV_CODE":"20170","FID_INPUT_ISCD":mkt,
           "FID_RANK_SORT_CLS_CODE":"0","FID_INPUT_CNT_1":str(cnt),"FID_PRC_CLS_CODE":"0",
           "FID_INPUT_PRICE_1":str(lo or ""),"FID_INPUT_PRICE_2":str(hi or ""),"FID_VOL_CNT":str(vol or ""),
           "FID_TRGT_CLS_CODE":"0","FID_TRGT_EXLS_CLS_CODE":"0","FID_DIV_CLS_CODE":"0",
           "FID_RSFL_RATE1":str(r1),"FID_RSFL_RATE2":str(r2)}).get("output",[])

@st.cache_resource(show_spinner=False)
def client(k,s,p):
    x=KIS(k,s,p);x.auth();return x
@st.cache_data(ttl=10,show_spinner=False)
def price(k,s,p,c):return client(k,s,p).price(c)
@st.cache_data(ttl=60,show_spinner=False)
def chart(k,s,p,c,per):return client(k,s,p).chart(c,per)
@st.cache_data(ttl=20,show_spinner=False)
def scan(k,s,p,m,c,lo,hi,v,r1,r2):return client(k,s,p).scan(m,c,lo,hi,v,r1,r2)
@st.cache_data(ttl=21600,show_spinner=False)
def estimate_perform(k,s,p,c):
    # client()는 cache_resource이므로 코드 수정 후에도 이전 KIS 인스턴스가 남을 수 있다.
    # estimate_perform 메서드 존재 여부에 의존하지 않고 공통 get()으로 직접 호출한다.
    x = client(k,s,p)
    if p:
        raise RuntimeError("종목추정실적 API는 모의투자에서 지원되지 않습니다. 모의투자 API를 끄고 조회해 주세요.")
    return x.get(
        "/uapi/domestic-stock/v1/quotations/estimate-perform",
        "HHKST668300C0",
        {"SHT_CD":str(c).zfill(6)}
    )

def chartdf(rows):
    if not rows:return pd.DataFrame()
    d=pd.DataFrame(rows).rename(columns={"stck_bsop_date":"date","stck_oprc":"open","stck_hgpr":"high",
      "stck_lwpr":"low","stck_clpr":"close","acml_vol":"volume"})
    need=["date","open","high","low","close","volume"]
    if not all(x in d for x in need):return pd.DataFrame()
    d["date"]=pd.to_datetime(d["date"],format="%Y%m%d",errors="coerce")
    for x in need[1:]:d[x]=pd.to_numeric(d[x],errors="coerce")
    d=d.dropna().sort_values("date")
    for n in [5,20,60,120]:d[f"MA{n}"]=d["close"].rolling(n).mean()
    return d

def in_range(value, low, high, enabled=True):
    if not enabled: return True
    if value is None or pd.isna(value): return False
    return float(low) <= float(value) <= float(high)

def ma_match(d, condition):
    if condition == "사용 안 함": return True
    if d is None or d.empty or len(d) < 60: return False
    last=d.iloc[-1]
    if condition == "정배열 (5>20>60)":
        return pd.notna(last['MA60']) and last['MA5'] > last['MA20'] > last['MA60']
    if condition == "역배열 (5<20<60)":
        return pd.notna(last['MA60']) and last['MA5'] < last['MA20'] < last['MA60']
    if len(d) < 21: return False
    prev=d.iloc[-2]
    if condition == "5/20 골든크로스":
        return pd.notna(prev['MA20']) and prev['MA5'] <= prev['MA20'] and last['MA5'] > last['MA20']
    if condition == "5/20 데드크로스":
        return pd.notna(prev['MA20']) and prev['MA5'] >= prev['MA20'] and last['MA5'] < last['MA20']
    if condition == "20/60 골든크로스":
        return pd.notna(prev['MA60']) and prev['MA20'] <= prev['MA60'] and last['MA20'] > last['MA60']
    return True

def pro_filter_candidates(k,s,paper,base_rows,master,settings):
    """등락률 순위 후보를 KIS 현재가 + 마스터 ROE + 일봉으로 2차 필터링."""
    if not base_rows: return []
    mlookup=master.drop_duplicates('code').set_index('code') if not master.empty else pd.DataFrame()
    out=[]
    for i,row in enumerate(base_rows):
        code=str(row.get('mksc_shrn_iscd') or row.get('stck_shrn_iscd') or '').zfill(6)
        if len(code)!=6: continue
        try:
            q=price(k,s,paper,code)
            cur=num(q.get('stck_prpr')); turnover=num(q.get('acml_tr_pbmn'))/1e8
            cap=num(q.get('hts_avls')); per=num(q.get('per'))
            high250=num(q.get('d250_hgpr'))
            near_pct=((high250-cur)/high250*100) if high250>0 and cur>0 else None
            roe=None; prev_vol=None; market=''
            if not mlookup.empty and code in mlookup.index:
                mr=mlookup.loc[code]
                if isinstance(mr,pd.DataFrame): mr=mr.iloc[0]
                roe=pd.to_numeric(mr.get('roe'),errors='coerce')
                prev_vol=pd.to_numeric(mr.get('prev_volume'),errors='coerce')
                market=str(mr.get('market',''))
            cur_vol=num(q.get('acml_vol'))
            surge=(cur_vol/float(prev_vol)*100) if prev_vol is not None and pd.notna(prev_vol) and float(prev_vol)>0 else None
            if settings['market']!='전체' and market and market!=settings['market']: continue
            if settings['turnover_on'] and turnover < settings['turnover_min']: continue
            if settings['cap_on'] and not in_range(cap,settings['cap_min'],settings['cap_max']): continue
            if settings['surge_on'] and (surge is None or surge < settings['surge_min']): continue
            if settings['high_on'] and (near_pct is None or near_pct > settings['high_near']): continue
            if settings['per_on'] and not in_range(per,settings['per_min'],settings['per_max']): continue
            if settings['roe_on'] and not in_range(roe,settings['roe_min'],settings['roe_max']): continue
            d=None
            if settings['ma_condition']!='사용 안 함':
                d=chartdf(chart(k,s,paper,code,'D'))
                if not ma_match(d,settings['ma_condition']): continue

            earnings_signal=''
            earnings_score=None
            earnings_reason=''
            if settings.get('earnings_improve_on',False):
                try:
                    fdf=naver_fundamental_2025_2028(code)
                    earnings_signal,earnings_score,earnings_reason=earnings_momentum(fdf)
                except Exception:
                    # 컨센서스 조회가 안 되는 종목은 '실적개선 종목만' 필터에서 제외
                    continue
                if earnings_signal != '📈 실적개선':
                    continue

            enriched=dict(row)
            enriched.update({'_code':code,'_per':per,'_roe':roe,'_turnover_100m':turnover,'_cap_100m':cap,
                             '_surge_pct':surge,'_near_high_pct':near_pct,
                             '_earnings_signal':earnings_signal,'_earnings_score':earnings_score,
                             '_earnings_reason':earnings_reason})
            out.append(enriched)
            if len(out)>=settings['result_count']: break
            time.sleep(0.04)
        except Exception:
            continue
    return out

@st.cache_data(ttl=3600, show_spinner=False)
def naver_fundamental_2025_2028(code):
    """Naver/WiseReport Financial Summary annual data for 2025~2028.

    Flow:
      1) Open WiseReport v2 company overview page for the selected code.
      2) Extract the fresh encparam/id generated for that company page.
      3) Call cF1001.aspx AJAX Financial Summary.
      4) Extract Operating profit (reported basis preferred), EPS, PER and ROE.

    This is a public-web HTML integration, not an official Open API. If the provider
    changes the HTML/AJAX contract this parser may need an update.
    """
    code = str(code).zfill(6)
    base = "https://navercomp.wisereport.co.kr/v2"
    parent_url = f"{base}/company/c1010001.aspx"
    ajax_url = f"{base}/company/ajax/cF1001.aspx"

    sess = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    parent = sess.get(parent_url, params={"cmp_cd": code, "cn": ""}, headers=headers, timeout=20)
    parent.raise_for_status()
    parent.encoding = parent.apparent_encoding or "utf-8"
    html = parent.text

    # WiseReport creates these values on the parent page. Do not hard-code them.
    enc_patterns = [
        r"encparam\s*:\s*['\"]([^'\"]+)['\"]",
        r"encparam\s*=\s*['\"]([^'\"]+)['\"]",
        r"['\"]encparam['\"]\s*:\s*['\"]([^'\"]+)['\"]",
    ]
    id_patterns = [
        r"\bid\s*:\s*['\"]([A-Za-z0-9+/=_-]+)['\"]",
        r"\bid\s*=\s*['\"]([A-Za-z0-9+/=_-]+)['\"]",
        r"['\"]id['\"]\s*:\s*['\"]([A-Za-z0-9+/=_-]+)['\"]",
    ]
    def first_match(patterns, text):
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                return m.group(1)
        return None

    encparam = first_match(enc_patterns, html)
    encid = first_match(id_patterns, html)
    if not encparam or not encid:
        raise RuntimeError("WiseReport 종목별 인증 파라미터(encparam/id)를 찾지 못했습니다.")

    ajax_headers = {
        **headers,
        "Referer": parent.url,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "text/html, */*; q=0.01",
    }

    def clean(x):
        return re.sub(r"\s+", " ", str(x).replace("\xa0", " ")).strip()

    def flatten_col(col):
        if isinstance(col, tuple):
            parts=[]
            for x in col:
                z=clean(x)
                if z and not z.lower().startswith("unnamed") and z not in parts:
                    parts.append(z)
            return " ".join(parts)
        return clean(col)

    def fetch_summary(freq_typ):
        params = {
            "cmp_cd": code,
            "fin_typ": "0",       # 주재무제표
            "freq_typ": freq_typ, # Y=annual; A is fallback for some layouts
            "encparam": encparam,
            "id": encid,
        }
        rr = sess.get(ajax_url, params=params, headers=ajax_headers, timeout=20)
        rr.raise_for_status()
        rr.encoding = rr.apparent_encoding or "utf-8"
        if len(rr.text.strip()) < 100:
            raise RuntimeError(f"Financial Summary 응답이 비어 있습니다. (freq={freq_typ})")
        try:
            tabs = pd.read_html(io.StringIO(rr.text))
        except Exception as e:
            raise RuntimeError(f"Financial Summary HTML 파싱 실패 (freq={freq_typ}): {e}")
        return tabs

    tables=[]
    errors=[]
    for freq in ("Y", "A"):
        try:
            tables.extend(fetch_summary(freq))
            if tables:
                break
        except Exception as e:
            errors.append(str(e))
    if not tables:
        raise RuntimeError("Financial Summary AJAX 조회 실패: " + " / ".join(errors[-2:]))

    # Pick the table containing the four target metrics and annual year headers.
    candidates=[]
    for t in tables:
        if t is None or t.empty:
            continue
        d=t.copy()
        d.columns=[flatten_col(c) for c in d.columns]
        blob=(" ".join(d.columns)+" "+" ".join(clean(x) for x in d.astype(str).values.ravel()[:5000])).upper()
        metric_score=sum(k in blob for k in ["영업이익","EPS","PER","ROE"])
        year_score=sum(str(y) in blob for y in [2025,2026,2027,2028])
        candidates.append((metric_score*10+year_score,d))
    candidates.sort(key=lambda x:x[0], reverse=True)
    if not candidates or candidates[0][0] < 30:
        raise RuntimeError("Financial Summary 표에서 영업이익/EPS/PER/ROE를 찾지 못했습니다.")
    d=candidates[0][1]

    # Identify year columns from the flattened MultiIndex header.  A header such as
    # '연간 2026/12(E) (IFRS연결)' maps to 2026.
    year_cols={}
    for c in d.columns:
        m=re.search(r"(2025|2026|2027|2028)\s*[/.-]?\s*\d{0,2}", clean(c))
        if m:
            year_cols[int(m.group(1))]=c
    # Some pandas versions keep the period labels in the first data row.
    if len(year_cols)<2:
        for ridx in range(min(3,len(d))):
            for c in d.columns:
                m=re.search(r"(2025|2026|2027|2028)\s*[/.-]?\s*\d{0,2}", clean(d.iloc[ridx][c]))
                if m:
                    year_cols[int(m.group(1))]=c
    if not year_cols:
        raise RuntimeError("Financial Summary에서 2025~2028 연간 열을 찾지 못했습니다.")

    # The first column is normally 주요재무정보.  Search every cell in the first
    # few columns so minor layout changes do not break the row lookup.
    search_cols=list(d.columns)[:min(3,len(d.columns))]
    row_labels=[]
    for idx,row in d.iterrows():
        label=" ".join(clean(row[c]) for c in search_cols)
        row_labels.append((idx,label))

    def find_metric_row(metric):
        normalized=[(idx,re.sub(r"\s+","",lab).upper()) for idx,lab in row_labels]
        if metric=="영업이익":
            # Naver Financial Summary shows a separate 발표기준 row when consensus exists.
            for idx,lab in normalized:
                if "영업이익(발표기준)" in lab:
                    return idx
            for idx,lab in normalized:
                if "영업이익" in lab and "영업이익률" not in lab:
                    return idx
        targets={"EPS":["EPS(원)","EPS"],"PER":["PER(배)","PER"],"ROE":["ROE(%)","ROE"]}[metric]
        for target in targets:
            z=target.replace(" ","").upper()
            for idx,lab in normalized:
                if z in lab:
                    return idx
        return None

    rows={m:find_metric_row(m) for m in ["영업이익","EPS","PER","ROE"]}
    if rows["영업이익"] is None or rows["EPS"] is None:
        raise RuntimeError("Financial Summary에서 영업이익 또는 EPS 행을 찾지 못했습니다.")

    def parse_num(v):
        z=clean(v).replace(",","").replace("원","").replace("배","").replace("%","")
        z=z.replace("−","-")
        if z.lower() in ("","-","--","nan","none","n/a"):
            return float("nan")
        neg=z.startswith("(") and z.endswith(")")
        z=z.strip("()")
        # Keep only a normal signed decimal number; footnote text is discarded.
        m=re.search(r"[-+]?\d+(?:\.\d+)?",z)
        if not m:
            return float("nan")
        val=float(m.group(0))
        return -abs(val) if neg else val

    out=[]
    for year in [2025,2026,2027,2028]:
        col=year_cols.get(year)
        rec={"연도":year,"구분":"A" if year==2025 else "E"}
        for metric,ridx in rows.items():
            rec[metric]=parse_num(d.loc[ridx,col]) if col is not None and ridx is not None else float("nan")
        out.append(rec)
    result=pd.DataFrame(out)
    if result[["영업이익","EPS","PER","ROE"]].isna().all().all():
        raise RuntimeError("2025~2028 Financial Summary 값이 모두 비어 있습니다.")
    return result

def earnings_momentum(df):
    """2025A~2028E 영업이익/EPS/PER/ROE 흐름을 정량 요약한다.

    반환: (라벨, 점수, 근거문구)
    - 영업이익/EPS 성장 방향을 가장 크게 반영
    - ROE 개선은 보조 가점/감점
    - PER은 이익/EPS가 성장하는 상황에서 부담 완화 여부만 보조 반영
    """
    if df is None or df.empty:
        return "⚪ 데이터부족", 0, "재무 컨센서스 데이터 없음"
    x=df.copy().sort_values('연도')
    for c in ['영업이익','EPS','PER','ROE']:
        x[c]=pd.to_numeric(x[c],errors='coerce')

    score=0
    reasons=[]

    def direction(col, weight_up, weight_down, label):
        nonlocal score
        v=x[col].dropna()
        if len(v)<2: return None
        first,last=float(v.iloc[0]),float(v.iloc[-1])
        if first == 0: return None
        chg=(last-first)/abs(first)*100
        # 작은 변동은 중립 처리
        if chg >= 5:
            score += weight_up
            reasons.append(f"{label} 증가")
            return 'up'
        if chg <= -5:
            score -= weight_down
            reasons.append(f"{label} 감소")
            return 'down'
        reasons.append(f"{label} 보합")
        return 'flat'

    op_dir=direction('영업이익',2,2,'영업이익')
    eps_dir=direction('EPS',2,2,'EPS')
    roe_dir=direction('ROE',1,1,'ROE')

    per=x['PER'].dropna()
    if len(per)>=2 and op_dir=='up' and eps_dir=='up':
        p0,p1=float(per.iloc[0]),float(per.iloc[-1])
        if p0>0 and p1>0:
            if p1 <= p0*0.95:
                score += 1
                reasons.append('Forward PER 부담 완화')
            elif p1 >= p0*1.15:
                score -= 1
                reasons.append('Forward PER 상승')

    # 핵심 이익지표가 서로 반대면 과도한 분류를 피한다.
    if op_dir=='up' and eps_dir=='down': score=min(score,1)
    if op_dir=='down' and eps_dir=='up': score=max(score,-1)

    if score >= 3:
        label='📈 실적개선'
    elif score <= -3:
        label='📉 실적둔화'
    else:
        label='➡️ 중립'
    return label, score, ' · '.join(reasons) if reasons else '판단 데이터 부족'


@st.cache_data(ttl=21600, show_spinner=False)
def auto_earnings_top5(candidate_records):
    """시총 상위 후보 → 거래대금 1차 정렬 → WiseReport 실적모멘텀 TOP 5.

    candidate_records는 (code, name, market, master_cap) 튜플 목록.
    결과는 6시간 캐시한다.
    """
    # 1차: 시가총액 상위 후보 중 현재 거래대금 확인
    liquid=[]
    for code,name,market,master_cap in candidate_records:
        try:
            q=price(KEY,SEC,False,str(code).zfill(6))
            turnover=num(q.get("acml_tr_pbmn"))  # 원
            if turnover <= 0:
                continue
            liquid.append({
                "code":str(code).zfill(6), "name":str(name), "market":str(market),
                "master_cap":float(master_cap) if master_cap is not None and pd.notna(master_cap) else 0.0,
                "turnover":float(turnover),
            })
            time.sleep(0.03)
        except Exception:
            continue

    # 거래대금 상위 20개만 컨센서스 분석
    liquid=sorted(liquid, key=lambda x:x["turnover"], reverse=True)[:20]
    if not liquid:
        return []

    def analyze(rec):
        try:
            fdf=naver_fundamental_2025_2028(rec["code"])
            label,score,reason=earnings_momentum(fdf)
            if label != "📈 실적개선":
                return None
            y2028=fdf[fdf["연도"]==2028]
            eps28=float(y2028["EPS"].iloc[0]) if not y2028.empty and pd.notna(y2028["EPS"].iloc[0]) else None
            out=dict(rec)
            out.update({"signal":label,"score":int(score),"reason":reason,"eps_2028":eps28})
            return out
        except Exception:
            return None

    # WiseReport는 네트워크 I/O이므로 제한된 동시 요청으로 첫 계산 시간을 줄인다.
    results=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures=[ex.submit(analyze,rec) for rec in liquid]
        for fut in as_completed(futures):
            r=fut.result()
            if r:
                results.append(r)

    # 점수 → 거래대금 → 시총 순
    results.sort(key=lambda x:(x["score"],x["turnover"],x["master_cap"]), reverse=True)
    return results[:5]

def earnings_top_panel_html(rows):
    if not rows:
        body=(
            '<div style="color:#8FA69D;font-size:12px;line-height:1.45;">'
            '실적개선 종목을 계산하지 못했거나 컨센서스가 부족합니다.</div>'
        )
    else:
        medals=["🥇","🥈","🥉","4","5"]
        parts=[]
        for i,r in enumerate(rows[:5]):
            parts.append(
                f'<div style="display:flex;justify-content:space-between;gap:6px;padding:4px 0;'
                f'border-bottom:1px solid #183028;">'
                f'<span style="color:#DDEBE5;font-weight:750;">{medals[i]}&nbsp; {r["name"]}</span>'
                f'<span style="color:#FF6B75;font-weight:900;">+{r["score"]}점</span></div>'
            )
        body=''.join(parts)
    return (
        '<div style="background:#0D1512;border:1px solid #315047;border-radius:6px;'
        'padding:9px 10px;margin:8px 0 6px 0;">'
        '<div style="color:#37F0A7;font-size:15px;font-weight:900;margin-bottom:4px;">📈 실적개선 TOP 5</div>'
        + body +
        '<div style="color:#718A80;font-size:10px;margin-top:6px;">'
        '기준: 2025A→2028E · 시총 40→거래대금 20 · 6시간 캐시</div></div>'
    )


def fmt_profit(v):
    if v is None or pd.isna(v): return "-"
    # 원 단위 → 억원
    return f"{v/1e8:,.0f}억"

def fmt_metric(v, suffix=""):
    if v is None or pd.isna(v): return "-"
    return f"{v:,.2f}{suffix}"

def profit_trend_label(df):
    if df is None or df.empty or len(df)<2: return "판단 데이터 부족"
    vals=pd.to_numeric(df['영업이익'],errors='coerce').dropna()
    if len(vals)<2: return "판단 데이터 부족"
    a,b=float(vals.iloc[-2]),float(vals.iloc[-1])
    base=max(abs(a),1.0)
    ch=(b-a)/base*100
    if ch>=10: return f"↗ 개선 ({ch:+.1f}%)"
    if ch<=-10: return f"↘ 악화 ({ch:+.1f}%)"
    return f"→ 정체 ({ch:+.1f}%)"

def fig(d,n,c):
    """HTS형 가격 + 거래량 차트. Plotly subplot을 명시적으로 구성한다."""
    if d is None or d.empty:
        return None

    f = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.015,
        row_heights=[0.78, 0.22]
    )

    f.add_trace(go.Candlestick(
        x=d["date"], open=d["open"], high=d["high"], low=d["low"], close=d["close"],
        name="가격",
        increasing_line_color="#FF4D5A", increasing_fillcolor="#FF4D5A",
        decreasing_line_color="#3D8BFF", decreasing_fillcolor="#3D8BFF"
    ), row=1, col=1)

    ma_colors = {"MA5":"#21E6A1", "MA20":"#F4F4F4", "MA60":"#FFD54A", "MA120":"#D98CFF"}
    for ma, color in ma_colors.items():
        if ma in d.columns:
            f.add_trace(go.Scatter(
                x=d["date"], y=d[ma], name=ma, mode="lines",
                line=dict(color=color, width=1.5), connectgaps=False
            ), row=1, col=1)

    volume_colors = ["#FF4D5A" if cl >= op else "#3D8BFF" for op, cl in zip(d["open"], d["close"])]
    f.add_trace(go.Bar(
        x=d["date"], y=d["volume"], name="거래량",
        marker=dict(color=volume_colors, line=dict(width=0)), opacity=0.85,
        hovertemplate="%{x|%Y-%m-%d}<br>거래량 %{y:,.0f}<extra></extra>"
    ), row=2, col=1)

    f.update_layout(
        title=dict(text=f"{n} | {c}", font=dict(size=16, color="#FFFFFF"), x=0.01),
        height=700,
        autosize=True,
        paper_bgcolor="#080D0B",
        plot_bgcolor="#080D0B",
        font=dict(color="#DCEAE4", size=12),
        margin=dict(l=8, r=12, t=48, b=8),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#101A16", bordercolor="#00C97B", font_color="#FFFFFF"),
        legend=dict(orientation="h", y=1.02, x=0, bgcolor="rgba(0,0,0,0)"),
        bargap=0.08,
        dragmode="pan"
    )
    f.update_xaxes(
        rangeslider_visible=False,
        gridcolor="#1D302A", zeroline=False,
        showspikes=True, spikecolor="#00C97B", spikethickness=1,
        spikemode="across", spikesnap="cursor",
        tickfont=dict(color="#AFC7BE")
    )
    f.update_yaxes(
        side="right", gridcolor="#1D302A", zeroline=False,
        tickfont=dict(color="#CFE0D9"), fixedrange=False,
        row=1, col=1
    )
    f.update_yaxes(
        side="right", gridcolor="#16251F", zeroline=False,
        tickfont=dict(color="#9FB7AE"), title_text="거래량",
        row=2, col=1
    )
    return f


@st.cache_data(ttl=60, show_spinner=False)
def public_market_quote(symbol):
    """공개 시세 endpoint에서 최근 두 종가를 읽어 지수/환율과 등락률을 계산한다."""
    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{requests.utils.quote(symbol, safe='')}"
    r=requests.get(
        url,
        params={"range":"5d","interval":"1d","includePrePost":"false","events":"div,splits"},
        headers={"User-Agent":"Mozilla/5.0"},
        timeout=10
    )
    r.raise_for_status()
    result=r.json().get("chart",{}).get("result") or []
    if not result: raise RuntimeError("시세 응답 없음")
    node=result[0]
    closes=((node.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    closes=[float(x) for x in closes if x is not None]
    if not closes: raise RuntimeError("종가 데이터 없음")
    cur=closes[-1]; prev=closes[-2] if len(closes)>=2 else None
    rate=((cur-prev)/prev*100) if prev not in (None,0) else None
    return cur,rate

def market_panel_html(items):
    valid_rates=[r for _,_,r in items if r is not None]
    avg=sum(valid_rates)/len(valid_rates) if valid_rates else 0
    mood="🟢 강세" if avg>=0.5 else ("🔴 약세" if avg<=-0.5 else "⚪ 중립")
    rows=[]
    for label,value,rate in items:
        if value is None:
            value_txt="-"; rate_txt="-"; color="#AFC7BE"
        else:
            value_txt=f"{value:,.2f}"
            rate_txt="-" if rate is None else f"{rate:+.2f}%"
            color="#AFC7BE" if rate is None else ("#FF4D5A" if rate>0 else ("#3D8BFF" if rate<0 else "#DCEAE4"))
        rows.append(
            f'<div style="display:flex;justify-content:space-between;gap:8px;padding:3px 0;border-bottom:1px solid #183028;">'
            f'<span style="color:#DDEBE5;font-weight:700;">{label}</span>'
            f'<span><b style="color:#FFFFFF;">{value_txt}</b>&nbsp;&nbsp;<b style="color:{color};">{rate_txt}</b></span></div>'
        )
    return (
        '<div style="background:#0D1512;border:1px solid #00B873;border-radius:6px;padding:9px 10px;margin:4px 0 8px 0;">'
        '<div style="color:#37F0A7;font-size:15px;font-weight:900;margin-bottom:5px;">📊 오늘의 시장</div>'
        + ''.join(rows) +
        f'<div style="display:flex;justify-content:space-between;padding-top:7px;">'
        f'<span style="color:#AFC7BE;font-weight:700;">시장 분위기</span>'
        f'<span style="color:#FFFFFF;font-weight:900;">{mood}</span></div></div>'
    )

st.markdown('<div class="title">HanaV Trading </div>',unsafe_allow_html=True)

if not KEY or not SEC:
    st.error("KIS_APP_KEY / KIS_APP_SECRET이 설정되지 않았습니다.")
    st.code('$env:KIS_APP_KEY="본인의_APP_KEY"\n$env:KIS_APP_SECRET="본인의_APP_SECRET"\nstreamlit run app.py',language="powershell")
    st.warning("키 값은 채팅에 보내지 마세요.")
    st.stop()

with st.sidebar:
    st.markdown(
        """
        <div style="margin:0 0 8px 0; padding:0;">
            <div style="color:#37F0A7; font-size:18px; font-weight:900; line-height:1.15;">
                HanaV Trading
            </div>
            <div style="color:#8FA69D; font-size:11px; font-weight:600; letter-spacing:0.3px; margin-top:2px;">
                Designed &amp; Built by K.H. Ahn
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    paper=False
    market_symbols=[
        ("KOSPI","^KS11"),("KOSDAQ","^KQ11"),("NASDAQ","^IXIC"),
        ("DOW","^DJI"),("USD/KRW","KRW=X"),
    ]
    market_items=[]
    for market_label, market_symbol in market_symbols:
        try: mv,mr=public_market_quote(market_symbol)
        except Exception: mv,mr=None,None
        market_items.append((market_label,mv,mr))
    st.markdown(market_panel_html(market_items), unsafe_allow_html=True)
    if st.button("🔄 오늘의 시장 새로고침", use_container_width=True, key="refresh_today_market"):
        public_market_quote.clear()
        st.rerun()
    st.caption("지수·환율은 최근 확인 가능한 시세 기준 · 약 1분 캐시")

    # 종목마스터는 실적 TOP과 전체 종목 검색이 함께 사용한다.
    try:
        master = load_stock_master()
    except Exception as e:
        st.error(f"종목 마스터 다운로드 오류: {e}")
        master = pd.DataFrame([{
            "code":"005930","name":"삼성전자","market":"KOSPI","std_code":"",
            "roe":float("nan"),"prev_volume":float("nan"),"master_cap":float("nan")
        }])

    # 시총 상위 40개를 1차 후보로 삼고, 함수 내부에서 거래대금 상위 20개로 다시 축소한다.
    top_candidates = master.copy()
    if "master_cap" in top_candidates.columns:
        top_candidates["master_cap"] = pd.to_numeric(top_candidates["master_cap"], errors="coerce")
        top_candidates = top_candidates.dropna(subset=["master_cap"]).sort_values("master_cap", ascending=False).head(40)
    else:
        top_candidates = top_candidates.head(40)
    candidate_records = tuple(
        (str(r.code).zfill(6), str(r.name), str(r.market),
         float(r.master_cap) if hasattr(r,"master_cap") and pd.notna(r.master_cap) else 0.0)
        for r in top_candidates.itertuples()
    )

    with st.spinner("실적개선 TOP 분석 중... 최초 계산은 잠시 걸릴 수 있습니다."):
        try:
            earnings_top = auto_earnings_top5(candidate_records)
        except Exception:
            earnings_top = []

    st.markdown(earnings_top_panel_html(earnings_top), unsafe_allow_html=True)
    if st.button("🔄 실적 TOP 새로고침", use_container_width=True, key="refresh_earnings_top"):
        auto_earnings_top5.clear()
        naver_fundamental_2025_2028.clear()
        st.rerun()

    st.divider()
    st.subheader("전체 종목 검색")
    search_market = st.selectbox("검색 시장", ["전체", "KOSPI", "KOSDAQ"], key="stock_search_market")
    q=st.text_input("종목명 또는 6자리 코드","삼성전자").strip()

    search_df = master
    if search_market != "전체":
        search_df = search_df[search_df["market"] == search_market]

    if q:
        q_lower = q.lower()
        mask = (
            search_df["code"].astype(str).str.contains(q, regex=False) |
            search_df["name"].astype(str).str.lower().str.contains(q_lower, regex=False)
        )
        hits_df = search_df[mask].copy()
        # 정확한 코드/종목명을 먼저 표시
        hits_df["_exact"] = ((hits_df["code"] == q) | (hits_df["name"].str.lower() == q_lower)).astype(int)
        hits_df = hits_df.sort_values(["_exact", "name"], ascending=[False, True]).head(100)
    else:
        hits_df = search_df.head(100).copy()

    if hits_df.empty:
        st.warning("검색 결과가 없습니다.")
        fallback = master[master["code"] == "005930"]
        hits_df = fallback if not fallback.empty else master.head(1)

    options = [f"{r.code} | {r.name} | {r.market}" for r in hits_df.itertuples()]
    pick=st.selectbox("검색 결과", options)
    selected = pick.split(" | ")
    code, name = selected[0].strip(), selected[1].strip()
    st.caption(f"전체 종목 {len(master):,}개 로드 · 검색 결과 {len(hits_df):,}개")
    st.divider()
    st.subheader("조건검색 PRO")
    market=st.selectbox("시장",["전체","KOSPI","KOSDAQ"])
    mcode={"전체":"0000","KOSPI":"0001","KOSDAQ":"1001"}[market]
    a,b=st.columns(2)
    with a:
        r1=st.number_input("최소 등락률 %",value=0.0,step=.5)
        lo=st.number_input("최저 가격",value=0,step=100)
    with b:
        r2=st.number_input("최대 등락률 %",value=30.0,step=.5)
        hi=st.number_input("최고 가격",value=1000000,step=1000)
    vol=st.number_input("최소 거래량",value=0,step=10000)

    st.markdown("##### PRO 필터")
    turnover_on=st.checkbox("거래대금",False)
    turnover_min=st.number_input("최소 거래대금 (억원)",0.0,1000000.0,100.0,50.0,disabled=not turnover_on)
    cap_on=st.checkbox("시가총액",False)
    c1,c2=st.columns(2)
    with c1: cap_min=st.number_input("시총 최소(억원)",0.0,100000000.0,0.0,1000.0,disabled=not cap_on)
    with c2: cap_max=st.number_input("시총 최대(억원)",0.0,100000000.0,100000000.0,1000.0,disabled=not cap_on)
    surge_on=st.checkbox("거래량 급증",False)
    surge_min=st.number_input("전일 거래량 대비 최소 %",0.0,10000.0,150.0,10.0,disabled=not surge_on,
                              help="현재 누적거래량 ÷ 종목 마스터의 전일거래량 × 100")
    high_on=st.checkbox("250일 신고가 근접",False)
    high_near=st.number_input("최고가와 최대 거리 %",0.0,100.0,5.0,0.5,disabled=not high_on,
                              help="예: 5% = 현재가가 250일 최고가에서 5% 이내")
    ma_condition=st.selectbox("이평선 조건",["사용 안 함","정배열 (5>20>60)","역배열 (5<20<60)","5/20 골든크로스","5/20 데드크로스","20/60 골든크로스"])
    per_on=st.checkbox("PER",False)
    p1,p2=st.columns(2)
    with p1: per_min=st.number_input("PER 최소",-1000.0,10000.0,0.0,1.0,disabled=not per_on)
    with p2: per_max=st.number_input("PER 최대",-1000.0,10000.0,30.0,1.0,disabled=not per_on)
    roe_on=st.checkbox("ROE",False)
    o1,o2=st.columns(2)
    with o1: roe_min=st.number_input("ROE 최소 %",-1000.0,1000.0,0.0,1.0,disabled=not roe_on)
    with o2: roe_max=st.number_input("ROE 최대 %",-1000.0,1000.0,100.0,1.0,disabled=not roe_on)
    earnings_improve_on=st.checkbox(
        "📈 실적개선 종목만", False,
        help="WiseReport 2025A~2028E의 영업이익·EPS·PER·ROE 흐름을 종합해 '실적개선'으로 판정된 종목만 남깁니다. 컨센서스가 없는 종목은 제외됩니다."
    )
    candidate_count=st.slider("1차 후보 수",10,50,40,5,help="KIS 등락률 순위에서 먼저 가져올 후보 수")
    result_count=st.slider("최종 결과 수",5,30,20,5)
    run_scan=st.button("조건검색 PRO 실행",type="primary",use_container_width=True)

    st.divider()
    if st.button("🔒 로그아웃",use_container_width=True,key="_hanav_logout_button"):
        _logout_hanav()
        st.rerun()

try:client(KEY,SEC,paper)
except Exception as e:
    st.error(f"KIS 인증 실패: {e}");st.stop()

if run_scan:
    try:
        settings={
            'market':market,'turnover_on':turnover_on,'turnover_min':turnover_min,
            'cap_on':cap_on,'cap_min':cap_min,'cap_max':cap_max,
            'surge_on':surge_on,'surge_min':surge_min,'high_on':high_on,'high_near':high_near,
            'ma_condition':ma_condition,'per_on':per_on,'per_min':per_min,'per_max':per_max,
            'roe_on':roe_on,'roe_min':roe_min,'roe_max':roe_max,
            'earnings_improve_on':earnings_improve_on,'result_count':result_count
        }
        spinner_text = "조건검색 PRO 분석 중 · PER/ROE/시총/기술조건을 확인하고 있습니다..."
        if earnings_improve_on:
            spinner_text = "조건검색 PRO 분석 중 · 1차 필터 통과 종목의 2025~2028 실적 컨센서스까지 확인하고 있습니다..."
        with st.spinner(spinner_text):
            base=scan(KEY,SEC,paper,mcode,candidate_count,lo,hi,vol,r1,r2)
            st.session_state.rows=pro_filter_candidates(KEY,SEC,paper,base,master,settings)
        st.session_state.pop("matches_table",None)
        st.session_state.pro_candidate_count=len(base)
    except Exception as e:
        st.error(f"조건검색 PRO 오류: {e}")
rows=st.session_state.get("rows",[])
rd=pd.DataFrame(rows) if rows else pd.DataFrame()

# 조건검색 결과가 있을 때만 접을 수 있는 전체폭 결과표를 표시합니다.
# 검색 전에는 MATCHES/안내 영역을 만들지 않아 종목 상세와 차트가 화면 전체 폭을 사용합니다.
if not rd.empty:
    with st.expander(f"🔎 조건검색 PRO 결과 · {len(rd)}종목", expanded=False):
        cc=next((x for x in ["_code","mksc_shrn_iscd","stck_shrn_iscd"] if x in rd),None)
        nc=next((x for x in ["hts_kor_isnm","prdt_name"] if x in rd),None)
        colmap={cc:"코드",nc:"종목명","stck_prpr":"현재가","prdy_ctrt":"등락률","acml_vol":"거래량",
                "_turnover_100m":"거래대금(억)","_cap_100m":"시총(억)","_per":"PER","_roe":"ROE",
                "_surge_pct":"거래량비%","_near_high_pct":"신고가거리%","_earnings_signal":"실적판정"}
        cols=[x for x in colmap if x and x in rd.columns]
        v=rd[cols].copy().rename(columns={x:colmap[x] for x in cols})
        for x in ["거래대금(억)","시총(억)","PER","ROE","거래량비%","신고가거리%"]:
            if x in v.columns: v[x]=pd.to_numeric(v[x],errors="coerce").round(2)
        # 표의 행을 클릭하면 해당 종목을 오른쪽 차트에 즉시 반영합니다.
        event = st.dataframe(
            v, hide_index=True, use_container_width=True, height=520,
            on_select="rerun", selection_mode="single-row", key="matches_table"
        )
        if cc and nc:
            selected_rows = []
            try:
                selected_rows = event.selection.rows
            except Exception:
                pass
            if selected_rows:
                idx = int(selected_rows[0])
                if 0 <= idx < len(rd):
                    chosen = rd.iloc[idx]
                    code = str(chosen[cc]).zfill(6)
                    name = str(chosen[nc])
            else:
                # 클릭 전에는 첫 번째 검색 결과를 기본 차트 종목으로 사용합니다.
                chosen = rd.iloc[0]
                code = str(chosen[cc]).zfill(6)
                name = str(chosen[nc])
        st.caption(f"1차 후보 {st.session_state.get('pro_candidate_count', len(rd))}개 → 최종 {len(rd)}개 · 행 클릭 시 오른쪽 차트 변경")

try:qv=price(KEY,SEC,paper,code)
except Exception as e:st.error(f"현재가 조회 오류: {e}");st.stop()
api_name=qv.get("hts_kor_isnm") or qv.get("prdt_name") or name
cur,rate,volume,value,cap=[num(qv.get(x)) for x in ["stck_prpr","prdy_ctrt","acml_vol","acml_tr_pbmn","hts_avls"]]
selected_signal=""
selected_signal_reason=""
try:
    _selected_fund=naver_fundamental_2025_2028(code)
    selected_signal,_,selected_signal_reason=earnings_momentum(_selected_fund)
except Exception:
    _selected_fund=pd.DataFrame()
signal_html=f" &nbsp; <span style='font-size:14px'>{selected_signal}</span>" if selected_signal else ""
st.markdown(f'<div class="head">{api_name} | {code}{signal_html}<span style="float:right">{cur:,.0f} &nbsp; {rate:+.2f}%</span></div>',unsafe_allow_html=True)
cs=st.columns(5)
vals=[("현재가",f"{cur:,.0f}"),("등락률",f"{rate:+.2f}%"),("거래량",f"{volume:,.0f}"),
      ("거래대금",f"{value/1e8:,.1f}억"),("시가총액",f"{cap:,.0f}억" if cap else "-")]
for c,(l,v) in zip(cs,vals):
    with c:st.markdown(f'<div class="box"><div class="lab">{l}</div><div class="val">{v}</div></div>',unsafe_allow_html=True)

# ===== 기업실적 상세보기 =====
selected_market = "KOSPI"
try:
    mr = master[master["code"].astype(str) == str(code).zfill(6)]
    if not mr.empty: selected_market = str(mr.iloc[0].get("market","KOSPI"))
except Exception:
    pass

with st.expander("📊 기업실적 상세보기 · 2025~2028 영업이익 / EPS / PER / ROE", expanded=False):
    st.caption("네이버 증권 종목분석 Financial Summary 기준 · 2025A 확정실적 + 2026E~2028E 컨센서스입니다.")
    try:
        f3 = _selected_fund if '_selected_fund' in locals() and not _selected_fund.empty else naver_fundamental_2025_2028(code)
        if f3.empty:
            st.info("이 종목은 2025~2028 재무데이터를 불러오지 못했습니다. 신규상장·ETF·일부 종목은 데이터가 제한될 수 있습니다.")
        else:
            view=pd.DataFrame({
                "구분":["영업이익","EPS","PER","ROE"],
                **{f'{int(r["연도"])}{r.get("구분","")}':[("-" if pd.isna(r["영업이익"]) else f'{r["영업이익"]:,.0f}'), ("-" if pd.isna(r["EPS"]) else f'{r["EPS"]:,.0f}원'), fmt_metric(r["PER"],"배"), fmt_metric(r["ROE"],"%")] for _,r in f3.iterrows()}
            })
            st.dataframe(view, hide_index=True, use_container_width=True)

            mom_label,mom_score,mom_reason=earnings_momentum(f3)
            st.markdown(f"**실적 모멘텀 : {mom_label}** &nbsp; · &nbsp; 점수 `{mom_score:+d}`")
            st.caption(f"판정 근거 · {mom_reason}")
            st.markdown(f"**영업이익 추세 : {profit_trend_label(f3)}**")
            op=f3.dropna(subset=["영업이익"]).copy()
            if not op.empty:
                pf=go.Figure(go.Bar(x=op["연도"].astype(str), y=op["영업이익"], text=[f"{x:,.0f}" for x in op["영업이익"]], textposition="outside"))
                pf.update_layout(title="2025~2028 영업이익 추이", height=300, margin=dict(l=8,r=8,t=45,b=8), paper_bgcolor="#080D0B", plot_bgcolor="#080D0B", font=dict(color="#DCEAE4"), xaxis_title="연도", yaxis_title="영업이익(억원)", showlegend=False)
                pf.update_xaxes(gridcolor="#1D302A")
                pf.update_yaxes(gridcolor="#1D302A")
                st.plotly_chart(pf, use_container_width=True, theme=None, key=f"fundamental_profit_{code}")
            st.caption("※ 출처: 네이버 증권 종목분석에 연결된 WiseReport Financial Summary. 2026E~2028E는 컨센서스이며 수시로 변경될 수 있습니다. 공개 HTML 구조 변경 시 조회 기능 수정이 필요할 수 있습니다.")
    except Exception as e:
        st.warning(f"기업실적 조회 실패: {e}")

st.write("")
pername=st.selectbox("차트 주기",["일봉","주봉","월봉"])
per={"일봉":"D","주봉":"W","월봉":"M"}[pername]
try:
    raw_chart = chart(KEY,SEC,paper,code,per)
    d = chartdf(raw_chart)
    if d.empty:
        st.warning("차트 데이터가 없습니다. 현재가는 조회되지만 KIS 차트 데이터가 비어 있습니다.")
    else:
        chart_fig = fig(d, api_name, code)
        st.plotly_chart(
            chart_fig,
            use_container_width=True,
            theme=None,
            key=f"price_volume_{code}_{per}",
            config={
                "displaylogo":False,
                "scrollZoom":True,
                "responsive":True,
                "modeBarButtonsToRemove":["lasso2d","select2d"]
            }
        )
except Exception as e:st.error(f"차트 조회 오류: {e}")

st.caption("HanaV Trading PRO · KIS Open API 조회/분석 버전 · PER/ROE/시총/거래대금/거래량급증/신고가/이평선/실적개선 조건검색 · WiseReport 2025~2028 실적 분석 · 주문/자동매매 미포함")
