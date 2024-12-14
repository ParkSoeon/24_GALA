### 1. 환경 설정 ----------------------------------------------------------------------
import os
import re

import pandas as pd
import numpy as np

from datetime import datetime
from datetime import timedelta
from datetime import date

import sqlite3 #db 연결

import streamlit as st
from streamlit_calendar import calendar # type: ignore

import plotly.express as px
from PIL import Image

import chardet

from tkinter.filedialog import Open
import json

import openai
from openai import OpenAI

os.environ["OPENAI_API_KEY"] = "YOUR_API_KEY"
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

### 2. streamlit 페이지 스타일 설정 -----------------------------------------------------

#페이지 설정
st.set_page_config(page_title="Demo for streamlit-calendar", page_icon="📆", layout="wide") #페이지 제목과 화면 넓게 설정

#디자인 (CSS 스타일 코드)
header_block = """
<style>
.stAppHeader.st-emotion-cache-12fmjuu.ezrtsby2{
    background-color: #e7ebf1;
}
</style>
"""
st.markdown(header_block, unsafe_allow_html=True)

out_block = """
<style>
.stMainBlockContainer.block-container.st-emotion-cache-1jicfl2.ea3mdgi5{
    background-color: #e7ebf1;
}
</style>
"""
st.markdown(out_block, unsafe_allow_html=True)

upper_block = """
<style>
.stColumn.st-emotion-cache-1h4axjh.e1f1d6gn3{
    background-color: #01369f;
    color: #ffffff;
    padding: 20px;
    justify-content: center; /* 수평 중앙 정렬 */
    align-items: center; /* 수직 중앙 정렬 */
}
</style>
"""
st.markdown(upper_block, unsafe_allow_html=True)

main1_block = """
<style>
.stColumn.st-emotion-cache-1msb0ab.e1f1d6gn3{
    background-color: #ffffff;
    padding: 20px;
    justify-content: center; /* 수평 중앙 정렬 */
    align-items: center; /* 수직 중앙 정렬 */
}
</style>
"""
st.markdown(main1_block, unsafe_allow_html=True)

metric_block = """
<style>
.stMetric{
    padding: 15px;
}
</style>
"""
st.markdown(metric_block, unsafe_allow_html=True)

metriclabel_block = """
<style>
[data-testid="stMetricLabel"]{
    color: #67727b;
}
</style>
"""
st.markdown(metriclabel_block, unsafe_allow_html=True)

metricvalue_block = """
<style>
[data-testid="stMetricValue"]{
    font-size: 30px;
}
</style>
"""
st.markdown(metricvalue_block, unsafe_allow_html=True)

main2_block = """
<style>
.stColumn.st-emotion-cache-136ne36.e1f1d6gn3{
    background-color: #ffffff;
    padding: 20px;
    justify-content: center; /* 수평 중앙 정렬 */
    align-items: center; /* 수직 중앙 정렬 */
}
</style>
"""
st.markdown(main2_block, unsafe_allow_html=True)

# layout
empty1, con1, empty2 = st.columns([0.01, 1.0, 0.01]) #[1] 제목
empty1, con21, con22, empty2 = st.columns([0.01, 0.4, 0.6, 0.01])
empty1, con3, empty2 = st.columns([0.01, 1.0, 0.01])
empty1, con4, empty2 = st.columns([0.01, 1.0, 0.01])

with con1:
    st.title("**📆 민열's 학습플래너**")

# 강의 정보
with con21:
    st.markdown('### 📌 학기 일정', unsafe_allow_html=True)
    
    # session state 초기화를 가장 먼저 수행
    if 'start_date' not in st.session_state:
        st.session_state['start_date'] = datetime.now().date()
    if 'total_week' not in st.session_state:
        st.session_state['total_week'] = 15
    if 'subjects_list' not in st.session_state:
        st.session_state['subjects_list'] = []
    if 'subject_count' not in st.session_state:
        st.session_state['subject_count'] = 0
    if 'syllabus_data' not in st.session_state:
        st.session_state['syllabus_data'] = {}
        
    # 개강일과 수업주차는 한 번만 입력
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("개강일을 선택해주세요.", value=st.session_state.start_date)
    with col2:
        total_week = st.slider("전체 수업 일정을 선택해주세요. (예 : 15주)", 1, 18, step=1, value=st.session_state.total_week)

    # 과목 입력 섹션
    st.markdown("---")
    st.markdown("### 📚 과목 정보 입력")
    
    # 과목별 기본 색상 목록
    SUBJECT_COLORS = [
        "#FF6C6C", "#4CAF50", "#2196F3", "#FFC107", "#9C27B0",
        "#FF9800", "#00BCD4", "#E91E63", "#795548", "#607D8B"
    ]
    
    # 새로운 과목 입력
    new_subject = st.text_input("과목을 입력하세요.", key=f"subject_{st.session_state.subject_count}")
    new_options = st.multiselect(
        "해당 과목의 수업 요일을 선택해주세요.",
        ["월요일", "화요일", "수요일", "목요일", "금요일"],
        key=f"options_{st.session_state.subject_count}"
    )
    
    # 색상 선택
    color_idx = len(st.session_state.get('subjects_list', [])) % len(SUBJECT_COLORS)
    selected_color = st.color_picker(
        "과목 색상을 선택하세요.",
        SUBJECT_COLORS[color_idx],
        key=f"color_{st.session_state.subject_count}"
    )
    
    # 파일 저장 함수
    def save_uploaded_file(directory, file, filename):
        """
        :param directory: 저장할 디렉토리
        :param file: 업로드된 파일 객체
        :param filename: 저장할 파일 이름
        :return: 저장된 파일 경로
        """
        if not os.path.exists(directory):
            os.makedirs(directory)

        file_path = os.path.join(directory, filename)
        with open(file_path, 'wb') as f:
            f.write(file.getbuffer())
        return file_path
    
    # CSV 파일 인코딩 감지 함수
    def detect_encoding(file_path):
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        result = chardet.detect(raw_data)
        return result['encoding']
    
    # 강의계획서 CSV 파일 업로드
    uploaded_file = st.file_uploader(
        "강의계획서 CSV 파일을 업로드하세요.",
        type=['csv'],
        key=f"syllabus_{st.session_state.subject_count}"
    )

    syllabus_df = None
    if uploaded_file is not None:
        # 임시 파일로 저장하여 인코딩 감지
        current_time = datetime.now()
        filename = new_subject + '_' + current_time.isoformat().replace(':', "_") + '.csv'
        file_path = save_uploaded_file('temp_csv', uploaded_file, filename)
        
        try:
            # 인코딩 감지
            detected_encoding = detect_encoding(file_path)
            st.info(f"감지된 파일 인코딩: {detected_encoding}")
            
            # 다양한 인코딩으로 시도
            encodings_to_try = [detected_encoding, 'utf-8', 'euc-kr', 'cp949', 'ISO-8859-1']
            success = False
            
            for encoding in encodings_to_try:
                if encoding is None:
                    continue
                try:
                    syllabus_df = pd.read_csv(file_path, encoding=encoding)
                    st.success(f"강의계획서가 성공적으로 업로드되었습니다. (사용된 인코딩: {encoding})")
                    st.dataframe(syllabus_df)
                    success = True
                    break
                except Exception as e:
                    continue
            
            if not success:
                st.error("모든 인코딩 방식으로 시도했으나 파일을 읽을 수 없습니다.")
            
        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")

    # 과목 추가 버튼
    if st.button("과목 추가", key=f"add_{st.session_state.subject_count}"):
        if new_subject and new_options:  # 과목명과 요일이 모두 입력된 경우에만 추가
            new_subject_info = {
                "subject": new_subject,
                "days": new_options,
                "color": selected_color
            }
            
            # 강의계획서 데이터가 있다면 저장
            if syllabus_df is not None:
                st.session_state.syllabus_data[new_subject] = syllabus_df.to_dict('records')
                new_subject_info["has_syllabus"] = True
            else:
                new_subject_info["has_syllabus"] = False
            
            st.session_state.subjects_list.append(new_subject_info)
            st.session_state.subject_count += 1
            st.success(f"'{new_subject}' 과목이 추가되었습니다.")
            st.experimental_rerun()

# calendar
with con22:
    st.markdown("### ✏️ 학습 플래너")

    mode = st.selectbox(
        "Calendar Mode:",
        (
            "daygrid",
            "timegrid",
            "timeline",
            "list",
            "multimonth",
        ),
    )

    def create_class_events(subjects_list, start_date, total_weeks):
        events = []
        day_mapping = {
            "월요일": 0,
            "화요일": 1,
            "수요일": 2,
            "목요일": 3,
            "금요일": 4
        }
        
        # 시작일을 datetime 객체로 변환
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        # 시작일이 월요일이 되도록 조정
        current_date = start_date
        while current_date.weekday() != 0:
            current_date = current_date - timedelta(days=1)
        
        # 각 과목별로 이벤트 생성
        for subject_info in subjects_list:
            subject = subject_info["subject"]
            class_days = subject_info["days"]
            subject_color = subject_info["color"]  # 과목별 색상 사용
            
            # total_weeks 동안의 수업 일정 생성
            for week in range(total_weeks):
                for day in class_days:
                    if day in day_mapping:
                        day_num = day_mapping[day]
                        class_date = current_date + timedelta(days=day_num + (week * 7))
                        
                        event = {
                            "title": f"{subject} {week + 1}주차",
                            "color": subject_color,  # 과목별 색상 적용
                            "start": class_date.strftime('%Y-%m-%d'),
                            "end": class_date.strftime('%Y-%m-%d'),
                            "resourceId": "a"
                        }
                        events.append(event)
        
        return events

    calendar_options = {
        "editable": "true",
        "navLinks": "true",
        "selectable": "true"
    }

    # 모드별 옵션 설정
    if mode == "daygrid":
        calendar_options.update({
            "headerToolbar": {
                "left": "today prev,next",
                "center": "title",
                "right": "dayGridDay,dayGridWeek,dayGridMonth"
            },
            "initialView": "dayGridMonth"
        })
    elif mode == "timegrid":
        calendar_options.update({
            "initialView": "timeGridWeek"
        })
    elif mode == "timeline":
        calendar_options.update({
            "headerToolbar": {
                "left": "today prev,next",
                "center": "title",
                "right": "timelineDay,timelineWeek,timelineMonth"
            },
            "initialView": "timelineMonth"
        })
    elif mode == "list":
        calendar_options.update({
            "initialView": "listMonth"
        })
    elif mode == "multimonth":
        calendar_options.update({
            "initialView": "multiMonthYear"
        })

    # 등록된 과목이 있을 때만 이벤트 생성
    events = []
    if st.session_state.get('subjects_list') and len(st.session_state['subjects_list']) > 0:
        try:
            events = create_class_events(
                subjects_list=st.session_state['subjects_list'],
                start_date=start_date,
                total_weeks=total_week
            )
            # 디버깅을 위한 이벤트 출력
            st.write(f"생성된 이벤트 수: {len(events)}")
        except Exception as e:
            st.error(f"이벤트 생성 중 오류 발생: {str(e)}")

    # 캘린더 렌더링
    calendar(
        events=events,
        options=calendar_options,
        custom_css="""
        .fc-event-past {
            opacity: 0.8;
        }
        .fc-event-time {
            font-style: italic;
        }
        .fc-event-title {
            font-weight: 700;
        }
        .fc-toolbar-title {
            font-size: 2rem;
        }
        """,
        key=f"calendar_{mode}_{len(events)}"  # key를 이벤트 수에 따라 변경하도록 수정
    )
    
with con3:
    if len(st.session_state.subjects_list) > 0:
        st.markdown("### 📚 등록된 강의 목록")
        
        # 공통 버튼 스타일 정의
        st.markdown(
            """
            <style>
            div[data-testid="stButton"] > button {
                width: 100%;
                padding: 0.5rem;
                height: 42px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        # 과목 정보를 담을 테이블 생성
        for idx, subject_info in enumerate(st.session_state.subjects_list):
            # 과목별 컨테이너 생성
            with st.container():
                # 배경색 있는 div로 감싸기
                st.markdown(f"""
                    <div style="
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 10px;
                        background-color: {subject_info['color']}15;
                        border-left: 5px solid {subject_info['color']};
                    ">
                    <h3 style="color: {subject_info['color']}; margin-bottom: 10px;">
                        {subject_info['subject']}
                    </h3>
                    <p><strong>수업 요일:</strong> {', '.join(subject_info['days'])}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([3, 3, 4])  # 동일한 버튼 크기를 위한 비율 조정
                with col1:
                    # 강의계획서 확인 버튼
                    if subject_info.get('has_syllabus', False):
                        if st.button("📋 강의계획서", key=f"syllabus_view_con3_{idx}"):
                            st.session_state['current_syllabus'] = subject_info['subject']
                            
                with col2:
                    # 삭제 버튼
                    if st.button("🗑️ 삭제", key=f"delete_con3_{idx}"):
                        deleted_subject = st.session_state.subjects_list.pop(idx)
                        if deleted_subject['subject'] in st.session_state.syllabus_data:
                            del st.session_state.syllabus_data[deleted_subject['subject']]
                        st.experimental_rerun()
                
                # 강의계획서 표시
                if st.session_state.get('current_syllabus') == subject_info['subject']:
                    syllabus_data = st.session_state.syllabus_data.get(subject_info['subject'])
                    if syllabus_data:
                        st.markdown("### 📑 강의계획서")
                        st.dataframe(pd.DataFrame(syllabus_data))
                        if st.button("닫기", key=f"close_syllabus_{idx}"):
                            del st.session_state['current_syllabus']
                            st.experimental_rerun()
                
                st.markdown("---")
    else:
        st.info("👆 등록된 강의가 없습니다. 위에서 강의를 추가해주세요.")
        
class ExamPlanner:
    def __init__(self):
        self.initialize_session_state()
        
    @staticmethod
    def initialize_session_state():
        """Initialize all session state variables"""
        session_vars = {
            "file_path": None,
            "df": None,
            "exam_week": None,
            "start_week": None,
            "end_week": None,
            "gpt_response": None,
            "gpt_input": None,
            "gpt_requested": False,
            "exam_week_date": date.today()
        }
        
        for var, default in session_vars.items():
            if var not in st.session_state:
                st.session_state[var] = default

    def load_file_list(self, temp_csv_path):
        """Load available CSV files from temp directory"""
        if os.path.exists(temp_csv_path):
            return [f for f in os.listdir(temp_csv_path) if f.endswith('.csv')]
        return []

    def load_file(self, file_path):
        """Load and validate the selected file"""
        try:
            # 먼저 CP949로 시도
            try:
                df = pd.read_csv(file_path, encoding='cp949')
            except UnicodeDecodeError:
                # CP949 실패시 EUC-KR 시도
                try:
                    df = pd.read_csv(file_path, encoding='euc-kr')
                except UnicodeDecodeError:
                    # 마지막으로 UTF-8 시도
                    df = pd.read_csv(file_path, encoding='utf-8')
            
            if not all(col in df.columns for col in ["강의주차", "강의내용"]):
                st.error("필수 열(강의주차, 강의내용)이 없습니다.")
                return None
            return df
        except Exception as e:
            st.error(f"파일 로드 중 오류 발생: {e}")
            return None
    
    def handle_exam_range(self, df):
        """Handle exam range selection and GPT request"""
        lecture_weeks = df["강의주차"].tolist()
        lecture_content = df["강의내용"].tolist()
        lecture_options = [
            f"{week} - {content}" for week, content in zip(lecture_weeks, lecture_content)
        ]

        # Set default values for range selection
        if st.session_state.start_week is None:
            st.session_state.start_week = lecture_options[0]
        if st.session_state.end_week is None:
            st.session_state.end_week = lecture_options[-1]

        # Range selection UI
        start_week = st.selectbox(
            "시험범위 시작:",
            lecture_options,
            index=lecture_options.index(st.session_state.start_week),
            key="start_week_selector"
        )
        end_week = st.selectbox(
            "시험범위 종료:",
            lecture_options,
            index=lecture_options.index(st.session_state.end_week),
            key="end_week_selector"
        )

        st.session_state.start_week = start_week
        st.session_state.end_week = end_week

        return start_week, end_week, lecture_options

    def prepare_gpt_request(self, df, start_week, end_week, lecture_options):
        """Prepare and display selected content and GPT request"""
        start_index = lecture_options.index(start_week)
        end_index = lecture_options.index(end_week)

        if start_index <= end_index:
            selected_content = "\n".join(
                f"{week} {content}"
                for week, content in zip(
                    df.iloc[start_index:end_index + 1]["강의주차"].tolist(),
                    df.iloc[start_index:end_index + 1]["강의내용"].tolist()
                )
            )

            st.info("선택한 시험 범위의 강의 내용:")
            st.text(selected_content)

            gpt_input = self.format_gpt_input(start_week, end_week)
            st.info("GPT에게 요청할 질문")
            st.text(gpt_input)
            st.session_state.gpt_input = gpt_input

            return gpt_input
        else:
            st.warning("시험 범위 종료가 시작보다 앞설 수 없습니다.")
            return None

    def format_gpt_input(self, start_week, end_week):
        """Format the input for GPT API"""
        return f"""
        저는 중간고사를 준비하는 학생입니다.
        다음은 저의 중간고사 일정과 시험범위입니다.
        해당 일자의 2주 전부터 저의 시험범위를 확인하여, 공부 계획을 작성해주세요.
        ### 시험 일자 ###
        {st.session_state.exam_week_date}
        ### 시험 범위 ###
        {start_week} - {end_week}
        응답은 반드시 JSON 형식으로 작성해주세요.
        """

def main():
    with con4:
        menu = ['중간고사계획', '빈 메뉴']
        choice = st.sidebar.selectbox('메뉴', menu)
        
        if choice == menu[0]:
            planner = ExamPlanner()
            
            st.markdown("### 🎯 중간고사계획")
            
            # File handling
            current_dir = os.getcwd()
            temp_csv_path = os.path.join(current_dir, 'temp_csv')
            
            try:
                # Get file list and create file selection UI
                csv_files = planner.load_file_list(temp_csv_path)
                
                st.info("이전에 업로드한 강의 계획 파일 중 하나를 선택하세요:")
                file_type = st.selectbox("파일 형식 선택:", ["CSV"])

                if file_type == "CSV" and csv_files:
                    selected_file = st.selectbox("CSV 파일 선택:", csv_files)
                    file_path = os.path.join(temp_csv_path, selected_file)
                    st.success(f"선택한 파일: {file_path}")

                    if st.button("파일 불러오기"):
                        df = planner.load_file(file_path)
                        if df is not None:
                            st.session_state.df = df
                            st.success(f"파일을 성공적으로 불러왔습니다.")
                            st.dataframe(df)

                    # Handle exam planning if file is loaded
                    if st.session_state.df is not None:
                        df = st.session_state.df

                        # Step 1: Exam date selection
                        st.subheader("<<1단계>> 중간고사 날짜 선택")
                        exam_date = st.date_input(
                            "중간고사 날짜를 선택하세요:",
                            value=st.session_state.exam_week_date
                        )
                        st.session_state.exam_week_date = exam_date
                        st.success(f"선택한 중간고사 날짜: {exam_date}")

                        # Step 2: Exam range selection
                        st.subheader("<<2단계>> 중간고사 범위 지정")
                        start_week, end_week, lecture_options = planner.handle_exam_range(df)
                        
                        gpt_input = planner.prepare_gpt_request(df, start_week, end_week, lecture_options)
                        
                        if gpt_input and st.button("GPT에게 시험 계획 요청"):
                            if not st.session_state.gpt_requested:
                                try:
                                    st.info("GPT에 시험 계획 요청 중...")
                                    response = client.chat.completions.create(
                                        model="gpt-4o-mini",
                                        messages=[
                                            {"role": "system", "content": "You are an assistant that helps students prepare for exams."},
                                            {"role": "user", "content": gpt_input}
                                        ],
                                        max_tokens=4096,
                                        temperature=0.7
                                    )
                                    gpt_response = response.choices[0].message.content.strip()
                                    st.session_state.gpt_response = gpt_response
                                    st.session_state.gpt_requested = True
                                except Exception as e:
                                    st.error(f"GPT 요청 중 오류 발생: {e}")

                            # Display GPT response
                            if st.session_state.gpt_response:
                                st.subheader("GPT의 시험 계획 응답 (텍스트):")
                                st.text(st.session_state.gpt_response)

                                try:
                                    # Clean and parse JSON response
                                    cleaned_response = st.session_state.gpt_response.strip()
                                    cleaned_response = re.sub(r"^(['\"]{3}json|```json)", "", cleaned_response, flags=re.IGNORECASE).strip()
                                    cleaned_response = re.sub(r"(['\"]{3}|```)$", "", cleaned_response, flags=re.IGNORECASE).strip()
                                    parsed_json = json.loads(cleaned_response)
                                    
                                    st.subheader("GPT의 시험 계획 응답 (JSON):")
                                    st.json(parsed_json)
                                except json.JSONDecodeError as e:
                                    st.error(f"GPT 응답을 JSON으로 파싱할 수 없습니다: {e}")
                                    st.text("디버깅용 응답 데이터:")
                                    st.text(repr(cleaned_response))
                else:
                    st.warning(f"{file_type} 형식의 파일이 없습니다.")

            except Exception as e:
                st.error(f"파일 목록을 가져오는 중 오류가 발생했습니다: {e}")
                
        else:
            st.markdown("### 이 대시보드 설명")

if __name__ == "__main__":
    main()