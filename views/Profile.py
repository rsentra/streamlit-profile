import streamlit as st
import pandas as pd
import datetime
from models import database  as db
from libs import utils as util
# from forms.create import show_new_form, test_form
# from libs.utils import today, years_ago_60

DICT_COL = {'id':'번호', 'name':'이름', 'gender':'성별', 'education':'학력', 'tech_grade':'등급', 'school_name':'학교',
            'department_name':'학과', 'birth_date':'생년월일', 'graduate_date':'졸업년월', 'project_name':'프로젝트',
            'customer':'고객사', 'start_date':'투입일', 'end_date':'종료일', 'role':'역할', 'job':'업무', 'environment':'환경',
            'tech_stack':'기술', 'company':'소속사', 'certi_name':'자격증', 'certi_date':'취득일', 'kosa':'KOSA유무', 'career_period':'총경력',
            'job_type':'소속', 'team':'팀', 'age':'연령', 'project_period':'투입기간', 'first_date':'최초경력일', 'last_date':'최종경력일'}   

# today = datetime.datetime.today()
# years_ago_60 = datetime.datetime(today.year-60,1,1)
today = util.get_days(0)
years_ago_60 = util.get_days(-60)

def init_session():
    if 'id_no' not in st.session_state:
        st.session_state['id_no'] = None
    if 'id_name' not in st.session_state:
        st.session_state['id_name'] = None
    if 'df_profile' not in st.session_state:
        st.session_state['df_profile'] = None 
    if 'df_career' not in st.session_state:
        st.session_state['df_career'] = None 
    if 'df_certi' not in st.session_state:
        st.session_state['df_certi'] = None 
    if 'certi_count' not in st.session_state:
        st.session_state['certi_count'] = 0
    if 'certi_name' not in st.session_state:
        st.session_state['certi_name'] = None
    if 'certi_date' not in st.session_state:
        st.session_state['certi_date'] = None
   
def new_tab():
    init_session()
    
    col1, col2,col3,col4,col5,col6 = st.columns(6)
    form_key= 'register_form'
    with st.form(form_key, border=False):
        with col1:
            # 이름 입력
            name = st.text_input("이름", "", placeholder="필수", key=form_key+'nm')
            # 최종학력 선택
            education_options = ["학사", "석사", "전문학사","박사", "고졸"]
            education = st.selectbox("최종학력", education_options, key=form_key+'edu')
        with col2:
            # 생년월일 입력
            birth_date = st.date_input("생년월일", min_value = years_ago_60, max_value = today, key=form_key+'bir')
            # 학교명 입력 (반드시 입력해야 함)
            school_name = st.text_input("학교명", "", placeholder="필수", key=form_key+'sch')
        with col3:    
            # 성별 선택
            gender_options = ["남", "여"]
            gender = st.selectbox("성별", gender_options, key=form_key+'gen')
            # 학과명 입력 (반드시 입력해야 함)
            department_name = st.text_input("학과명", "", placeholder="필수", key=form_key+'dep')
        with col4:
            # 졸업년월 선택
            graduate_date = st.date_input("졸업년월", min_value = years_ago_60, max_value = today, key=form_key+'gra')
            # 기술등급 선택
            tech_options = ["초급", "중급", "고급", "특급"]
            tech_grade = st.selectbox("기술등급", tech_options, key=form_key+'tech')
        with col5:
            job_type = st.selectbox("소속", ['자사','프리','자사화'], key=form_key+'job')
            team = st.text_input("팀명", key=form_key+'team')
        with col6:
            kosa = st.checkbox('kosa 유무', key=form_key+'kosa')
            certi_name, certi_date = input_certificate('tab1_slider'+form_key)   

        left_col, right_col =  st.columns([0.3,0.7])
        submitted = None
        with left_col:
            # submit를 하면 db에 입력하고 자격증 슬라어더를 초기화함
            submitted = st.form_submit_button("Submit", on_click=util.ini_widget, kwargs={'init_name':'certi_count','init_val':0})
            if submitted:
                dic = {}
                dic['name'] = name
                dic['birth_date'] = datetime.datetime.strftime(birth_date,'%Y-%m-%d')
                dic['gender'], dic['education'] = gender, education
                dic['school_name'], dic['department_name'] = school_name, department_name
                dic['graduate_date'] = datetime.datetime.strftime(graduate_date,'%Y-%m-%d')
                dic['tech_grade'], dic['kosa']= tech_grade, kosa
                dic['team'], dic['job_type'] = team, job_type
                 
                if name =='':
                    st.error("이름을 입력하세요.")
                    return False
                #프로필 테이블 입력
                id_no = db.insert_to_table(schema="members",table="profiles",data=dic, get_seq='members.profiles_id_seq')
                print('insert result = ', id_no, 'certi_list: ', certi_name,'-',st.session_state['certi_name'])
                st.session_state['id_no'] = id_no
                st.session_state['id_name'] = name

                # if len(certi_name) > 0:
                if st.session_state['certi_count'] > 0:
                    print('certi:: ',st.session_state['certi_count'], '=', certi_name)
                    if register_certificates(certi_name, certi_date)==False:
                        st.error("자격 등록 실패")
                     
        with right_col:
            if submitted:
                st.info(f'insert result = {id_no}', icon="ℹ️")
    # 경력 입력
    if st.session_state['id_name']:
        upload_careers('tab1_form')
   
def list_tab():
    header_col = st.columns([2,1,3,1,1])
    
    query = f" select * from members.profiles"
    df = db.get_data_to_df(query)
    df.insert(0,'select', False)
    st.session_state['df_profile'] = df
    with header_col[0]:
        st.markdown('###### :memo: :blue[Profile]과 :blue[경력]관리')
    with header_col[1]:
        chk = st.checkbox("search")
    if chk:
        with header_col[2]:
            name = st.text_input('이름',placeholder="name to search", label_visibility='collapsed')
        if name:
            df = df[df['name'].str.contains(name)]
    with header_col[3]:
        st.markdown(f' ###### :heavy_check_mark: :rainbow[{len(df)}명]')
    
    edited_df = st.data_editor(
        df,
        column_config = {
            "select": st.column_config.CheckboxColumn(
                "Update?",
                help="check for **update** ",
                width="small",
                default=False,
            ),
            'id': st.column_config.NumberColumn("번호"),
            'name': st.column_config.TextColumn(
               "이름",
                required=True,),
            'birth_date': st.column_config.DateColumn(
               "생년월일",
                format="YYYY-MM-DD",
                step=1,
            ),
            'gender': st.column_config.SelectboxColumn(
               "성별",
                width="small",
               options=[ "남",  "여" ],
               required=True,
            ),
            'education': st.column_config.SelectboxColumn(
               "학력",
               help="학력",
               width="small",
               options=[ "학사",  "석사" ,  "전문학사", "박사", "고졸"],
               required=True,
            ),
            'school_name': st.column_config.TextColumn(
                "학교",
                required=True,),
            'department_name': st.column_config.TextColumn(
                "학과",
                required=True,),
            "graduate_date": st.column_config.DateColumn(
               "졸업년월",
                width="small",
                format="YYYY-MM-DD",
                step=1,
                required=True,
            ),
            "tech_grade": st.column_config.SelectboxColumn(
               "등급",
               help="기술등급",
               width="small",
               options=[ "초급",  "중급" ,  "고급",  "특급"],
               required=True,
            ),
            "kosa": st.column_config.CheckboxColumn(
                "kosa 등록?",
                help="Check for **kosa** Registered",
                default=False,
                width="small",
             ),
            "job_type": st.column_config.SelectboxColumn(
                "고용형태",
                help="재직회사 구분",
                width="small",
                options=[ "자사",  "프리" ,  "자사화"],
                required=True,
             ),
            'team': st.column_config.TextColumn(
                "팀",
               required=True,
             ),
        },
        disabled=['id'],
        # num_rows = 'dynamic',
        hide_index = True,
        key = "edit_data",
        width = 2000
    )
      
    selected_df = edited_df[edited_df['select']==True]
    # print("== select count: ", len(selected_df))

    if len(selected_df) > 0:
        query = f" select * from members.careers"
        if st.session_state['df_career'] is None:
           st.session_state['df_career'] = db.get_data_to_df(query)
        df_career = pd.merge(left = selected_df[['id','name']] , right = st.session_state['df_career'], how = "inner", on = "id")
        
        query = f" select * from members.certificates"
        if st.session_state['df_certi'] is None:
           st.session_state['df_certi'] = db.get_data_to_df(query)
        if st.session_state['df_certi'] is None:
            df_certi = pd.DataFrame()
        else:
            df_certi = pd.merge(left = selected_df[['id','name']] , right = st.session_state['df_certi'], how = "inner", on = "id")

        col_11, col_12 = st.columns([2, 1])
        with col_11:
            with st.expander(f"{len(selected_df)}명/ 경력({len(df_career)}건)"):
                if len(df_career) > 0:   
                    disp_df(df_career.sort_values(by=['name','start_date'],ascending=False))
                else: 
                    st.write("경력자료가 없음")
        with col_12:
            with st.expander(f"{len(selected_df)}명/ 자격증({len(df_certi)}건)"):
                if len(df_certi) > 0:  
                    disp_df(df_certi)
                else:
                    st.write("자격증 없음")
            
        col1, col2, col3, col4 = st.columns([2,1,4, 1])
        upd_df = selected_df.drop(columns='select')
        with col1:
            st.button(":ledger: Update", on_click = update_process, args = [upd_df], help="Update profile")
     
        with col2:
            st.button(":warning: Delete", on_click = delete_process, args = [upd_df], help='warning:: 선택 인원의 프로필, 경력을 삭제')
        with col3:
            st.checkbox("경력만 삭제", key='del_career_checked',help='체크 후 삭제버튼을 클릭하면 경력만 삭제합니다')
  
        with col4:
            st.write(len(selected_df),"rows selected")    

        if len(selected_df) == 1:
            id_no, id_name = selected_df[['id','name']].iloc[0]
            # print('upload_id = ', id_no)
            st.session_state['id_no'] = id_no
            st.session_state['id_name'] = id_name
            col_21, col_22 = st.columns(2)
            with col_21:   #경력 업로드
                upload_careers('tab2_form')

            with col_22:   #자격증입력
                with st.form("자격증", border=False):
                    name = st.session_state['id_name']      
                    # st.write(f"****{name}**** 의 자격증 입력")
                    st.session_state['certi_count'] = len(df_certi)
             
                    # certi_name, certi_date = input_certificate('tab2_slider')
                    # datetime.datetime.today()
                    certi_name, certi_date = [None,None], [None,None] 
                    for i in range(len(df_certi)):
                        certi_name[i] = df_certi['certi_name'][i]
                        certi_date[i] = df_certi['certi_date'][i]

                    col1, col2 = st.columns(2)
                    with col1:
                        certi1_name = st.text_input("자격증", key='certi1_name', value = certi_name[0])
                        certi2_name = st.text_input("자격증", key='certi2_name', value = certi_name[1], label_visibility="collapsed")
                    with col2:
                        certi1_date = st.date_input("취득일", key='certi1_date', value = certi_date[0])
                        certi2_date = st.date_input("취득일", key='certi2_date', value = certi_date[1], label_visibility="collapsed")
                    
                    certi_name, certi_date = [],[]
                    if certi1_name:
                        certi_name.append(certi1_name)
                        certi_date.append(certi1_date)
                    if certi2_name:
                        certi_name.append(certi2_name)
                        certi_date.append(certi2_date)
                   
                    col1, col2 = st.columns([1,2])
                   
                    #자격증입력하고 나서 자격증건수를 초기화함
                    with col1:
                        submitted = st.form_submit_button(":bookmark_tabs: 자격증 저장", on_click=util.ini_widget, kwargs={'init_name':'certi_count','init_val':0},
                                                          help="자격증 정보를 저장합니다")
                    with col2:
                        agree = st.checkbox("삭제", help="체크 후 저장 버튼 클릭하면 자격증 정보를 삭제합니다")
         
                    if submitted:
                        if agree:
                            if register_certificates(certi_name, certi_date)==False:
                                st.error("자격증 등록 실패")
                            st.write('삭제완료')
                        elif len(certi_name)==0:
                            st.error("자격증을 입력하세요.")
                            return False
                        else:
                            print('certi:: ',st.session_state['certi_count'], '=', certi_name)
                            if register_certificates(certi_name, certi_date)==False:
                                st.error("자격증 등록 실패")
                            st.write('입력완료')
        else:
            st.info("경력 업로드는 1명씩 가능하며, 추가할 경력만 업로드 要.")


def disp_df(edited_df, hide_idx=True, date_format="YYYY-MM-DD"):
    disp_df = edited_df.copy().fillna('')
    disp_df.columns = [DICT_COL.get(x,x) for x in disp_df.columns]
  
    st.dataframe(disp_df,
                column_config={
                  '투입일': st.column_config.DateColumn(format=date_format),
                  '종료일': st.column_config.DateColumn(format=date_format),
                  '생년월일': st.column_config.DateColumn(format=date_format),
                  '졸업년월': st.column_config.DateColumn(format=date_format),
                  '최초경력일': st.column_config.DateColumn(format=date_format),
                  '최종경력일': st.column_config.DateColumn(format=date_format),
                },
                hide_index=hide_idx, 
                use_container_width =True,
                width=2000,
    )
    return True

def register_certificates(certi_name, certi_date):
    id_no = st.session_state['id_no'] 
    dic = {}
    dic['id'] = [id_no] * len(certi_name)
    dic['certi_name'] = certi_name
    dic['certi_date'] = certi_date
    df_certi = pd.DataFrame(dic)
    repl_cond = f"id = {id_no}"
    res = db.insert_df_to_table(df=df_certi,table="members.certificates", mode='replace',repl_cond=repl_cond)
    return res

def input_certificate(key_exp): 
     # 자격증명칭,취득년월 입력 (2개 가능)
    certificates = []
    acquisition_dates = []   
    ini_val = 0
    if st.session_state['certi_count'] > 0:
        ini_val = st.session_state['certi_count']
    
    with st.expander("자격증 수"):
        values = st.slider("자격증 수",0, 2, ini_val, label_visibility="hidden", key=key_exp)
        i=0
        while i < values:
            certificate = st.text_input("자격증명칭", "", key=f'{key_exp}{i}_cert')
            if certificate:
                certificates.append(certificate)
            acquisition_date = st.date_input("취득년월", key=f'{key_exp}{i}_ym',value=None, min_value = years_ago_60, max_value = today)
            if certificate:
                acquisition_dates.append(acquisition_date)
            i += 1
            print(i, '번 자격증:',certificate)
        st.session_state['certi_count'] = len(certificates)

    return certificates,acquisition_dates

def update_process(upd_df):
    # progress_text = "Operation in progress. Please wait."
    table = 'members.profiles'
    u_key_cols = []
    u_key_cols.append('id') #unique identifier

    res,cnt = db.update_df_to_table(upd_df, table, u_key_cols)
    if res:
        print('update count: ', cnt)
    
    if res:
        st.info("수정완료")
    else:
        st.error("수정 실패..날짜 데이터 오류이므로 날짜 데이터를 입력바람")
    return True

def delete_process(upd_df):
    if st.session_state['del_career_checked'] == True:
        del_flag = 'career'
    else:  #delete all info
        del_flag = 'profile,certi,career'

    for id in upd_df['id']:
        if 'certi' in del_flag:
            sql = f'delete from members.certificates where id = {id} '
            db.execute_sql(sql)
            st.session_state['df_certi'] = None
        if 'career' in del_flag:
            sql = f'delete from members.careers where id = {id} '
            db.execute_sql(sql)
            st.session_state['df_career'] = None
        if 'profile' in del_flag:
            sql = f'delete from members.profiles where id = {id} '
            db.execute_sql(sql)
            st.session_state['df_profile'] = None

    return True

def upload_careers(tab_name):
    submitted2 = False
    with st.form(tab_name, border=False):
        name = st.session_state['id_name']      
        uploaded_file = st.file_uploader(f"****{name}**** 의 프로젝트 경력 업로드", type = ['xlsx','CSV'])
        if uploaded_file is not None:
            if uploaded_file.name.endswith(".csv"):
                dataframe = pd.read_csv(uploaded_file)
            else:
                dataframe = pd.read_excel(uploaded_file)
            # st.write(dataframe)

        submitted2 = st.form_submit_button(":memo: 경력 저장", help="업로드한 자료를 경력DB에 추가합니다. 수정하려면 경력 다운로드 -> 삭제 -> 수정파일 재업로드하세요.")
        if submitted2:
            if uploaded_file is  None:
                st.error('파일을 선택하세요')
                return False
            
            #불필요한 컬럼 지우기
            del_cols = [ x for x in dataframe.columns if x in (['id','번호','이름','성명'])]
            dataframe = dataframe.drop(columns=del_cols)
            dataframe.fillna('', inplace=True)
            if len(dataframe.columns) != 10:
                # print(dataframe)
                st.error('필요한 10개의 컬럼을 모두 포함하세요')
                return False
            
            dataframe.insert(0,'id', st.session_state['id_no'])
            dataframe.columns = ['id','project_name','customer','start_date','end_date','role','job','environment','tech_stack','company','etc']
            if db.insert_df_to_table(dataframe, "members.careers") == False:
                st.error('데이터베이스 저장 실패..데이터의 정합성(날짜 데이티 등)을 확인하세요')
                return False
            st.session_state['df_career'] = None  # 세션값 초기화
    
    if submitted2:
        query = f" select * from members.careers where id = {st.session_state['id_no']}"
        dataframe2 = db.get_data_to_df(query)
        st.write(dataframe2)
        st.session_state['id_name'] = None


def app():
    tab2, tab1 = st.tabs([":memo: $\large List/Edit$",":new: $\large New$"])
    with tab1:
        new_tab()

    with tab2:
        list_tab()
        
 