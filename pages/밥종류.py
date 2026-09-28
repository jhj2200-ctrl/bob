import streamlit as st
import requests
import re
from collections import Counter
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="밥 종류 분석 (송탄고)", page_icon="🍚", layout="wide")
st.title("급식 밥 종류 분석 🍚")
st.subheader("송탄고등학교 급식에서 가장 많이 나온 밥은?")

@st.cache_data
def get_songtan_school_info():
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {"Type": "json", "pIndex": 1, "pSize": 10, "SCHUL_NM": "송탄고등학교"}
    try:
        res = requests.get(url, params=params)
        data = res.json()
        if 'schoolInfo' in data:
            return data['schoolInfo'][1]['row'][0]
    except Exception:
        pass
    return None

def clean_allergy_info(dish):
    dish = re.sub(r'\([\d\.\*]+\)', '', dish)
    dish = re.sub(r'[\d\.\*]+$', '', dish).strip()
    return dish

@st.cache_data(show_spinner="급식 데이터를 분석 중입니다...")
def fetch_all_meals(edu_code, school_code, from_date, to_date):
    api_key = st.secrets.get("NEIS_API_KEY", "")
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    p_index = 1
    p_size = 1000
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
            if len(all_meals) >= total_count or not rows:
                break
            p_index += 1
        except Exception:
            break
            
    return all_meals

school_info = get_songtan_school_info()
if not school_info:
    st.error("송탄고등학교 정보를 불러올 수 없습니다.")
    st.stop()

edu_code = school_info['ATPT_OFCDC_SC_CODE']
school_code = school_info['SD_SCHUL_CODE']

raw_meals = fetch_all_meals(edu_code, school_code, "20250901", "20260930")
lunch_meals = [m for m in raw_meals if m.get('MMEAL_SC_NM') == '중식']

if not lunch_meals:
    st.info("급식 데이터가 없습니다.")
else:
    total_days = len(lunch_meals)
    rice_counter = Counter()

    for meal in lunch_meals:
        raw_dishes = meal.get('DDISH_NM', '').split('<br/>')
        for raw_dish in raw_dishes:
            cleaned = clean_allergy_info(raw_dish)
            # 메뉴명에 '밥'이 들어간 항목 필터링
            if '밥' in cleaned:
                rice_counter[cleaned] += 1

    top_rice = rice_counter.most_common()

    if not top_rice:
        st.info("밥 메뉴 데이터를 찾을 수 없습니다.")
    else:
        top_1_name = top_rice[0][0]
        top_1_count = top_rice[0][1]
        top_1_ratio = (top_1_count / total_days) * 100

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📅 전체 급식 제공일", f"{total_days}일")
        with col2:
            st.metric("🥇 최다 등장 밥", top_1_name)
        with col3:
            st.metric("📊 1위 밥 제공 비율", f"{top_1_count}회 ({top_1_ratio:.1f}%)")

        st.divider()

        df_rice = pd.DataFrame([
            {
                "순위": i + 1,
                "밥 종류": item[0],
                "제공 횟수": item[1],
                "제공 비율(%)": round((item[1] / total_days) * 100, 1)
            }
            for i, item in enumerate(top_rice)
        ])

        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.markdown("### 📊 밥 종류별 제공 횟수 TOP 10")
            df_top10 = df_rice.head(10)
            fig = px.bar(
                df_top10,
                x="제공 횟수",
                y="밥 종류",
                orientation="h",
                color="제공 횟수",
                color_continuous_scale="Oranges",
                text=df_top10.apply(lambda r: f"{r['제공 횟수']}회 ({r['제공 비율(%)']}%)", axis=1)
            )
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                coloraxis_showscale=False,
                height=400
            )
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.markdown("### 📋 전체 밥 종류 순위표")
            st.dataframe(df_rice.set_index("순위"), use_container_width=True, height=400)
