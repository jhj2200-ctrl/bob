import streamlit as st
import requests
import re
from datetime import datetime
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="인기메뉴 주기 분석 (송탄고)", page_icon="📅", layout="wide")
st.title("인기 메뉴 주기 & 요일 패턴 분석 📅")
st.subheader("내가 좋아하는 메뉴는 몇 일에 한 번, 무슨 요일에 나올까?")

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

@st.cache_data(show_spinner="급식 데이터를 불러오는 중입니다...")
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

raw_meals = fetch_all_meals(
    school_info['ATPT_OFCDC_SC_CODE'],
    school_info['SD_SCHUL_CODE'],
    "20250901",
    "20260930"
)
lunch_meals = [m for m in raw_meals if m.get('MMEAL_SC_NM') == '중식']

# 대표적인 인기 메뉴 키워드 및 직접 입력 옵션
popular_keywords = ["돈가스", "치킨", "떡볶이", "스파게티", "제육", "우동", "탕수육", "피자", "직접 입력"]
selected_kw = st.selectbox("분석할 인기 메뉴 키워드를 선택하세요", popular_keywords)

if selected_kw == "직접 입력":
    target_keyword = st.text_input("검색할 메뉴 단어를 입력하세요 (예: 마라탕, 햄버거)", value="치킨").strip()
else:
    target_keyword = selected_kw

if target_keyword and lunch_meals:
    matched_dates = []
    
    for meal in lunch_meals:
        raw_dishes = meal.get('DDISH_NM', '').split('<br/>')
        date_str = meal.get('MLSV_YMD')
        
        # 키워드가 포함된 메뉴가 있는지 확인
        has_match = any(target_keyword in clean_allergy_info(d) for d in raw_dishes)
        if has_match and date_str:
            dt = datetime.strptime(date_str, "%Y%m%d")
            matched_dates.append(dt)

    matched_dates.sort()

    if not matched_dates:
        st.info(f"'{target_keyword}' 키워드가 포함된 급식이 검색 기간 내에 없습니다.")
    else:
        # 주기(날짜 간격) 계산
        intervals = []
        for i in range(1, len(matched_dates)):
            diff_days = (matched_dates[i] - matched_dates[i-1]).days
            intervals.append(diff_days)

        avg_interval = sum(intervals) / len(intervals) if intervals else 0

        # 요일별 집계
        weekdays_kr = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        day_counts = {day: 0 for day in weekdays_kr[:5]} # 주중 요일만
        
        for dt in matched_dates:
            day_name = weekdays_kr[dt.weekday()]
            if day_name in day_counts:
                day_counts[day_name] += 1

        # 핵심 지표 카드
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label=f"총 등장 횟수 ('{target_keyword}')", value=f"{len(matched_dates)}회")
        with col2:
            st.metric(label="평균 제공 주기", value=f"약 {avg_interval:.1f}일 마다" if intervals else "1회 출현")
        with col3:
            most_frequent_day = max(day_counts, key=day_counts.get)
            st.metric(label="가장 많이 나온 요일", value=f"{most_frequent_day} ({day_counts[most_frequent_day]}회)")

        st.divider()

        col_graph1, col_graph2 = st.columns(2)

        with col_graph1:
            st.markdown(f"### 🗓️ '{target_keyword}' 요일별 출현 빈도")
            df_day = pd.DataFrame(list(day_counts.items()), columns=["요일", "횟수"])
            fig_day = px.bar(
                df_day,
                x="요일",
                y="횟수",
                color="횟수",
                color_continuous_scale="Purples",
                text="횟수"
            )
            fig_day.update_layout(coloraxis_showscale=False)
            fig_day.update_traces(textposition="outside")
            st.plotly_chart(fig_day, use_container_width=True)

        with col_graph2:
            st.markdown(f"### ⏱️ 제공 날짜 간격(일) 변화")
            if intervals:
                df_inter = pd.DataFrame({
                    "회차": [f"{i+1}회차 간격" for i in range(len(intervals))],
                    "간격(일)": intervals
                })
                fig_inter = px.line(
                    df_inter,
                    x="회차",
                    y="간격(일)",
                    markers=True,
                    title="다음 등장까지 걸린 일수"
                )
                st.plotly_chart(fig_inter, use_container_width=True)
            else:
                st.info("2회 이상 등장해야 간격을 계산할 수 있습니다.")

        with st.expander(f"📋 '{target_keyword}' 등장했던 날짜 전체보기"):
            date_list_df = pd.DataFrame([
                {
                    "날짜": dt.strftime("%Y-%m-%d"),
                    "요일": weekdays_kr[dt.weekday()]
                }
                for dt in matched_dates
            ])
            st.dataframe(date_list_df, use_container_width=True)
