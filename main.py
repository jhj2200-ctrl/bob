import streamlit as st
import requests
from datetime import datetime
import pytz
import re

# 페이지 기본 설정
st.set_page_config(page_title="학교 급식 찾아보기", page_icon="🍱")
st.title("학교 급식 찾아보기 🍱")

def get_schools(school_name):
    """나이스 API를 통해 학교 목록을 가져오는 함수"""
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "SCHUL_NM": school_name
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if 'schoolInfo' in data:
            return data['schoolInfo'][1]['row']
    except Exception:
        pass
    return []

def expand_school_name(name):
    """축약된 학교 이름을 정식 명칭으로 풀어주는 함수"""
    # '여고'로 끝나는 경우 '여자고등학교'로 변환
    name = re.sub(r'여고$', '여자고등학교', name)
    # '고'로 끝나는데 '고등학교'가 아닌 경우 '고등학교'로 변환
    if not name.endswith('고등학교'):
        name = re.sub(r'고$', '고등학교', name)
    return name

# 학교 이름 입력
search_name = st.text_input("학교 이름을 입력하세요 (예: 수도여고, 광남고)")

if search_name:
    # 1차 검색
    schools = get_schools(search_name)
    
    # 결과가 없으면 이름을 풀어서 2차 검색
    if not schools:
        expanded_name = expand_school_name(search_name)
        if expanded_name != search_name:
            schools = get_schools(expanded_name)
            
    # 최종적으로 학교를 찾지 못한 경우
    if not schools:
        st.info("학교를 찾을 수 없습니다. 이름을 다시 확인해 주세요.")
    else:
        # 동명이교 구분을 위해 지역명(LCTN_SC_NM)과 함께 표시
        school_options = {f"{s['SCHUL_NM']} ({s['LCTN_SC_NM']})": s for s in schools}
        selected_school_name = st.selectbox("학교를 선택하세요", list(school_options.keys()))
        selected_school = school_options[selected_school_name]

        # 한국 시간 기준 오늘 날짜 계산
        kst = pytz.timezone('Asia/Seoul')
        today = datetime.now(kst).date()
        
        # 달력에서 날짜 선택
        selected_date = st.date_input("날짜를 선택하세요", value=today)

        if selected_date:
            date_str = selected_date.strftime("%Y%m%d")
            edu_code = selected_school['ATPT_OFCDC_SC_CODE']
            school_code = selected_school['SD_SCHUL_CODE']

            # 급식 정보 요청
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
                        # 중식 메뉴만 찾기
                        if meal['MMEAL_SC_NM'] == '중식':
                            found_lunch = True
                            dish_list = meal['DDISH_NM'].split('<br/>')
                            cal_info = meal['CAL_INFO']
                            
                            st.subheader("🍽️ 오늘의 중식 메뉴")
                            st.caption("메뉴명 옆의 숫자는 알레르기 유발 물질 번호입니다.")
                            
                            for dish in dish_list:
                                st.write(f"- {dish}")
                                
                            st.write("---")
                            st.write(f"**열량:** {cal_info}")
                            break
                            
                if not found_lunch:
                    st.info("해당 날짜의 중식 급식 정보가 없습니다.")
                    
            except Exception:
                st.info("급식 정보를 불러오는 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.")
