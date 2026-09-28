import streamlit as st
import requests
from datetime import datetime
import pytz
import re

# 페이지 기본 설정
st.set_page_config(page_title="달력별 급식 (송탄고)", page_icon="📅", layout="centered")
st.title("우리 학교 달력별 급식 📅")
st.subheader("송탄고등학교 중식 메뉴")

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
    # 메뉴명 끝에 붙은 숫자와 점 제거 (예: 메뉴명 1.2.3.)
    dish = re.sub(r'[\d\.\*]+$', '', dish).strip()
    return dish

# 송탄고등학교 정보 불러오기
school_info = get_songtan_school_info()

if not school_info:
    st.error("송탄고등학교 정보를 불러오지 못했습니다. 네트워크를 확인해 주세요.")
    st.stop()
    
edu_code = school_info['ATPT_OFCDC_SC_CODE']
school_code = school_info['SD_SCHUL_CODE']

# 날짜와 알레르기 스위치를 나란히 배치
col_date, col_toggle = st.columns([2, 1])

# 한국 시간 기준 오늘 날짜 계산
kst = pytz.timezone('Asia/Seoul')
today = datetime.now(kst).date()

with col_date:
    selected_date = st.date_input("날짜를 선택하세요", value=today)

with col_toggle:
    st.write("") # 수직 중앙 정렬을 위한 빈 줄
    st.write("")
    show_allergy = st.toggle("알레르기 정보 보기", value=True)

if selected_date:
    date_str = selected_date.strftime("%Y%m%d")
    
    # 급식 정보 API 요청
    meal_url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    meal_params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": edu_code,
        "SD_SCHUL_CODE": school_code,
        "MLSV_YMD": date_str
    }
    
    try:
        meal_res = requests.get(meal_url, params=meal_params)
        meal_data = meal_res.json()
        
        found_lunch = False
        
        if 'mealServiceDietInfo' in meal_data:
            meals = meal_data['mealServiceDietInfo'][1]['row']
            for meal in meals:
                # 중식 메뉴만 처리
                if meal['MMEAL_SC_NM'] == '중식':
                    found_lunch = True
                    
                    raw_dish_list = meal['DDISH_NM'].split('<br/>')
                    cal_info = meal['CAL_INFO']
                    
                    # 알레르기 정보 스위치 상태에 따라 메뉴 이름 가공
                    if show_allergy:
                        dish_list = raw_dish_list
                    else:
                        dish_list = [clean_allergy_info(d) for d in raw_dish_list]
                    
                    st.divider()
                    
                    # 메뉴 가짓수와 칼로리를 큰 숫자 카드로 표시
                    m1, m2 = st.columns(2)
                    with m1:
                        st.metric(label="🍽️ 메뉴 가짓수", value=f"{len(dish_list)}개")
                    with m2:
                        st.metric(label="🔥 총 칼로리", value=cal_info)
                    
                    st.markdown("### 🍱 오늘의 메뉴")
                    
                    # 메뉴를 카드 형태로 여러 개 나란히 배치 (3열 그리드)
                    cols = st.columns(3)
                    for i, dish in enumerate(dish_list):
                        with cols[i % 3]:
                            with st.container(border=True):
                                # 중앙 정렬된 카드 스타일
                                st.markdown(f"<div style='text-align: center; font-weight: bold; padding: 10px 0;'>{dish}</div>", unsafe_allow_html=True)
                    
                    break
                    
        if not found_lunch:
            st.info("해당 날짜는 급식이 없는 날입니다.")
            
    except Exception:
        st.warning("급식 정보를 불러오는 중 문제가 발생했습니다.")
