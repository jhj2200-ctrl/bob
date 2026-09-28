import streamlit as st
import requests
import re
from collections import Counter
import pandas as pd
import plotly.express as px

# 페이지 기본 설정
st.set_page_config(page_title="메뉴별 급식 (송탄고)", page_icon="📊", layout="wide")
st.title("우리 학교 메뉴별 급식 📊")
st.subheader("송탄고등학교 급식 메뉴 통계 (2025년 9월 ~ 2026년 9월)")

@st.cache_data
def get_songtan_school_info():
    """송탄고등학교의 교육청 코드와 학교 코드를 가져오는 함수"""
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {
        "Type": "json",
        "pIndex": 1,
        "pSize": 10,
        "SCHUL_NM": "송탄고등학교"
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        if 'schoolInfo' in data:
            return data['schoolInfo'][1]['row'][0]
    except Exception:
        pass
    return None

def clean_allergy_info(dish):
    """메뉴 이름에서 알레르기 번호와 특수기호를 제거하는 함수"""
    # 괄호와 그 안의 내용 제거 (예: (1.2.3.))
    dish = re.sub(r'\([\d\.\*]+\)', '', dish)
    # 메뉴명 끝에 붙은 숫자와 점 제거
    dish = re.sub(r'[\d\.\*]+$', '', dish).strip()
    return dish

@st.cache_data(show_spinner="2025년 9월~2026년 9월 급식 데이터를 불러오는 중입니다...")
def fetch_all_meals(edu_code, school_code, from_date, to_date):
    """지정한 기간 동안의 전체 급식 데이터를 페이지네이션으로 모두 수집하는 함수"""
    # Secrets 설정에서 API 키 가져오기
    api_key = st.secrets.get("NEIS_API_KEY", "")
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    
    p_index = 1
    p_size = 1000  # 나이스 API 1회 최대 요청 건수
    all_meals = []
    
    while True:
        params = {
            "Type": "json",
            "pIndex": p_index,
            "pSize": p_size,
            "ATPT_OFCDC_SC_CODE": edu_code,
            "SD_SCHUL_CODE": school_code,
            "MLSV_FROM_YMD": from_date,
            "MLSV_TO_YMD": to_date
        }
        if api_key:
            params["KEY"] = api_key
            
        try:
            res = requests.get(url, params=params)
            data = res.json()
            
            if 'mealServiceDietInfo' not in data:
                break
                
            head = data['mealServiceDietInfo'][0]['head']
            total_count = head[0]['list_total_count']
            rows = data['mealServiceDietInfo'][1]['row']
            
            all_meals.extend(rows)
            
            # 전체 건수만큼 모두 받았거나 더 이상 받아올 데이터가 없으면 종료
            if len(all_meals) >= total_count or not rows:
                break
                
            p_index += 1
        except Exception:
            break
            
    return all_meals

# 송탄고등학교 정보 불러오기
school_info = get_songtan_school_info()

if not school_info:
    st.error("송탄고등학교 정보를 불러오지 못했습니다. 네트워크를 확인해 주세요.")
    st.stop()

edu_code = school_info['ATPT_OFCDC_SC_CODE']
school_code = school_info['SD_SCHUL_CODE']

# 2025년 9월 1일 ~ 2026년 9월 30일 기간 지정
FROM_DATE = "20250901"
TO_DATE = "20260930"

raw_meals = fetch_all_meals(edu_code, school_code, FROM_DATE, TO_DATE)

# 중식 메뉴만 필터링
lunch_meals = [m for m in raw_meals if m.get('MMEAL_SC_NM') == '중식']

if not lunch_meals:
    st.info("해당 기간의 중식 급식 데이터가 없습니다.")
else:
    # 데이터 가공 및 집계
    menu_counter = Counter()
    total_days = len(lunch_meals) # 중식이 제공된 총 일수

    for meal in lunch_meals:
        raw_dishes = meal.get('DDISH_NM', '').split('<br/>')
        
        # 하루 내 중복 메뉴 제거 (같은 날 같은 메뉴가 두 번 나와도 하루로 처리)
        day_dishes = set()
        for raw_dish in raw_dishes:
            cleaned = clean_allergy_info(raw_dish)
            if cleaned:
                day_dishes.add(cleaned)
        
        for dish in day_dishes:
            menu_counter[dish] += 1

    top_menu_list = menu_counter.most_common()

    if not top_menu_list:
        st.info("집계할 메뉴 데이터가 없습니다.")
    else:
        # 1위 메뉴 정보 계산
        top_1_name = top_menu_list[0][0]
        top_1_count = top_menu_list[0][1]
        top_1_ratio = (top_1_count / total_days) * 100

        # 상단 주요 지표 카드 (Metric)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="📅 총 집계 날수", value=f"{total_days}일")
        with col2:
            st.metric(label="🥇 가장 자주 나온 메뉴 1위", value=top_1_name)
        with col3:
            st.metric(label="📊 1위 등장 비율", value=f"{top_1_count}일 ({top_1_ratio:.1f}%)")

        st.divider()

        # 조회 범위 조절 슬라이더
        max_rank = min(50, len(top_menu_list))
        top_n = st.slider("조회할 메뉴 순위 수 (TOP N)", min_value=5, max_value=max_rank, value=10, step=1)

        # TOP N 데이터프레임 생성
        df_top = pd.DataFrame([
            {
                "순위": i + 1,
                "메뉴": item[0],
                "출현일수": item[1],
                "비율": (item[1] / total_days) * 100
            }
            for i, item in enumerate(top_menu_list[:top_n])
        ])

        st.markdown(f"### 🏆 메뉴 출현 빈도 TOP {top_n}")

        # Plotly 가로 막대그래프 생성
        # - 1위가 맨 위에 오도록 autorange="reversed" 처리
        # - 값이 클수록 진한 푸른색(Blues)으로 표현
        fig = px.bar(
            df_top,
            x="출현일수",
            y="메뉴",
            orientation="h",
            color="출현일수",
            color_continuous_scale="Blues",
            text=df_top.apply(lambda r: f"{r['출현일수']}일 ({r['비율']:.1f}%)", axis=1),
            labels={"출현일수": "등장 일수 (일)", "메뉴": "메뉴명"}
        )

        fig.update_layout(
            yaxis=dict(autorange="reversed"), # 1위가 맨 위에 오도록 역순 설정
            coloraxis_showscale=False,       # 범례 숨김
            height=max(400, top_n * 35),
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_title="등장 일수 (일)",
            yaxis_title=""
        )
        fig.update_traces(textposition="outside")

        st.plotly_chart(fig, use_container_width=True)

        # 상세 데이터 목록
        with st.expander("📋 상세 데이터 목록 보기"):
            df_display = df_top.copy()
            df_display["비율"] = df_display["비율"].map(lambda x: f"{x:.1f}%")
            df_display["출현일수"] = df_display["출현일수"].map(lambda x: f"{x}일")
            st.dataframe(df_display.set_index("순위"), use_container_width=True)
