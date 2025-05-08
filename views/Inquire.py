import streamlit as st
import pandas as pd
import datetime
from models import database  as db
from libs import utils as util
from st_aggrid import AgGrid, GridUpdateMode, JsCode,ColumnsAutoSizeMode
from st_aggrid.grid_options_builder import GridOptionsBuilder
from views.Profile import disp_df
from views.Profile import DICT_COL
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from io import BytesIO
import plotly.express as px
from libs import utils as util

today = util.get_days(0)
# years_ago_60 = datetime.datetime(today.year-60,1,1)
DICT_DAYS = {'':0,'경력 미입력':-1,'3개월 경과':90,'6개월 경과':180,'1년이상 경과':365}

def init_session():
    if 'df_career' not in st.session_state:
        st.session_state['df_career'] = None 
    if 'df_certi' not in st.session_state:
        st.session_state['df_certi'] = None 
    if 'df_profile' not in st.session_state:
        st.session_state['df_profile'] = None 
    if 'template_file' not in st.session_state:
        st.session_state['template_file'] = None 


def inqiure_tab():

    init_session()

    top_col1,top_col2,top_col3,top_col4,top_col5,top_col6, top_col7 = st.columns([1,2,2,2,2,1,1])
    with top_col1:
        st.markdown('##### :mag_right: ')
    with top_col2:
        search_name = st.text_input('이름', placeholder='검색할 이름', label_visibility="collapsed")
    with top_col3:
        search_type = st.selectbox('형태', placeholder='검색할 조건', options=['','자사','프리','자사화'], label_visibility="collapsed")
    with top_col4:
        search_certi = st.checkbox('자격증보유자only')
    with top_col5:
        search_carr = st.selectbox('경력update필요', help="경력 입력상태를 조회",
                                   options=DICT_DAYS.keys(), label_visibility="collapsed")    
    with top_col6:
        search_employ = st.checkbox('퇴사자')

    query = f" select * from members.profiles"
    df = db.get_data_to_df(query)
    df['kosa'] = df['kosa'].astype(bool)
    
    if st.session_state['df_career'] is None:
        query = f" select * from members.careers"
        st.session_state['df_career']  = db.get_data_to_df(query)

    if st.session_state['df_certi'] is None:
        query = f" select * from members.certificates"
        st.session_state['df_certi'] = db.get_data_to_df(query)

    # object -> date
    st.session_state['df_career']['start_date'] = pd.to_datetime(st.session_state['df_career']['start_date'], format="%Y-%m-%d")
    st.session_state['df_career']['end_date'] = pd.to_datetime( st.session_state['df_career']['end_date'], format="%Y-%m-%d")

    #나이
    df['age'] = df.apply(lambda x: util.diff_date(today, x['birth_date'], method='years'), axis=1)
    df['age'] = df['age'].fillna(0).astype('int')
    #경력기간 산출
    df_cc = st.session_state['df_career'].groupby('id').agg({'start_date':min,'end_date':max})
    df = pd.merge(df.set_index('id'), df_cc[['start_date','end_date']], on='id', how='left').reset_index()
    df['career_period'] = df.apply(lambda x: util.diff_date(today, x['start_date'], method='yearandmonth'), axis=1)
    # df = df.drop(columns=['start_date','end_date'])
    df.rename(columns={'start_date':'first_date','end_date':'last_date'},inplace=True)
    # 자격증
    df_temp = st.session_state['df_certi'].groupby('id')['certi_name'].apply(list).reset_index(name='certi_name')
    df = pd.merge(df, df_temp, on='id',how='left').fillna('')
    df['certi_name'] = [ ','.join(x) for x in df['certi_name']]
    df['birth_date']= pd.to_datetime(df.birth_date, format="%Y-%m-%d")
    df['graduate_date']= pd.to_datetime(df.graduate_date, format="%Y-%m-%d")
    st.session_state['df_profile'] = df

    # display용 dataframe
    df_d = df.copy()  
    if search_name:
        df_d = df_d[df_d['name'].str.contains(search_name)].copy()
    if search_type:
        df_d = df_d[df_d['job_type']==search_type].copy()   
    if search_certi:
        df_d = df_d[df_d['certi_name']!=''].copy()  
    if search_carr:
        i = DICT_DAYS.get(search_carr,0)
        if i < 0: 
            df_d = df_d[df_d['last_date'].isna()].copy()
        else:
            years_ago = today - datetime.timedelta(days = i)
            df_d = df_d[df_d['last_date'] < years_ago].copy()

    if search_employ:
        df_d = df_d[df_d['employ_status'] != ''].copy()
    else:
        df_d = df_d[df_d['employ_status'] == ''].copy()

    with top_col7:
        st.markdown(f':rainbow[{len(df_d)}명]')

    if len(df_d) ==0:
        st.error('No data')
        st.stop()

    #한글명으로 컬럼명 치환
    selected = False
    grid_mode = st.sidebar.radio('grid Type', options = ['dataframe', 'aggrid'], horizontal=True, label_visibility="collapsed", index =1)
    
    if grid_mode != 'aggrid':
        df_grid = df_d.copy()
        df_grid.columns = [DICT_COL.get(x,x) for x in df_grid.columns]

        top_menu = st.columns(3)
        with top_menu[0]:
            sort = st.radio("Sort Data", options=["Sort Yes", "No"], horizontal=True, index=1, label_visibility="collapsed")
        if sort == "Sort Yes":
            with top_menu[1]:
                sort_field = st.selectbox("Sort By", options=df_grid.columns, label_visibility="collapsed")
            with top_menu[2]:
                sort_direction = st.radio(
                    "Direction", options=["⬆️", "⬇️"], horizontal=True, label_visibility="collapsed"
                )
            df_grid = df_grid.sort_values(
                by=sort_field, ascending=sort_direction == "⬆️", ignore_index=True
            )
        # 데이터를 표기할 컨테이너
        pagination = st.container()

        bottom_menu = st.columns((4, 0.5,1.5,1,1))
        with bottom_menu[3]:     
             st.markdown("Page size")
        with bottom_menu[4]:
            batch_size = st.selectbox("Page Size", options=[10, 20, 30], label_visibility="collapsed")
        with bottom_menu[1]:
            st.markdown("Page")
        with bottom_menu[2]:
            total_views = (
                int(len(df_grid) / batch_size) + (1 if len(df_grid) % batch_size > 0 else 0) if int(len(df_grid) / batch_size) >=1 else 1
            )
            current_page = st.number_input(
                "Page", min_value=1, max_value=total_views, step=1, label_visibility="collapsed"
            )
        with bottom_menu[0]:
            st.markdown(f"Page **{current_page}** of **{total_views}** ")

        views = util.split_frame(df_grid, batch_size)

        event = pagination.dataframe(data=views[current_page - 1],
            key="data",
            on_select="rerun",
            selection_mode=["single-row", "multi-column"],
            column_config={
                "생년월일": st.column_config.DateColumn(format="YY년MM월",),
                "졸업년월": st.column_config.DateColumn(format="YY년MM월",),
                "최초경력일": st.column_config.DateColumn(format="YYYY-MM-DD"),
                "최종경력일": st.column_config.DateColumn(format="YYYY-MM-DD"),
            },
            hide_index= True,
            width=2000
        )

        if len(event.selection['rows']) > 0:
            i = event.selection['rows'][0]
            i = i + batch_size * current_page - batch_size  #page고려
            id_no, id_name = df_grid.iloc[i][['번호','이름']]
            
            selected = True
            selected_df = df_d[df_d.id==id_no]
    else: 
        # sel_mode = st.radio('Selection Type2', options = ['single', 'multiple'])
        sel_mode = 'single'
        gd = aggrid_opt_build(df_d)

        gd.configure_selection(selection_mode=sel_mode, use_checkbox=True)
        gridoptions = gd.build()
        grid_table = AgGrid(df_d,
            gridOptions=gridoptions,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            allow_unsafe_jscode=True,
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
            theme='streamlit'
        )

        selected_df = grid_table["selected_rows"]
   
        # df_d.columns = [DICT_COL.get(x,x) for x in df_d.columns]

        if selected_df is not None:
            id_no,id_name = selected_df.iloc[0]['id'],selected_df.iloc[0]['name']
            selected = True
     
    st.divider()
  
    if selected:
        # 기본프로필
        profile_data = selected_df.iloc[0]
        # 경력(최근 우선)
        dataframe = st.session_state.df_career[st.session_state.df_career['id'] == id_no]
        dataframe = dataframe.sort_values(by=['start_date'], ascending=False)
        dataframe['start_date']= pd.to_datetime(dataframe.start_date, format="%Y-%m")
        dataframe['end_date']= pd.to_datetime(dataframe.end_date, format="%Y-%m")
        dataframe['project_period'] = dataframe['start_date'].dt.strftime('%y.%m')+'~'+dataframe['end_date'].dt.strftime('%y.%m')
        
        col1, col2, col3,col4,col5,col6= st.columns(6)
        #기술등급산출
        temp = profile_data['career_period'].split("년")[0]
        cr_yr = 0 if temp  =='' else int(temp) 
        grd = util.tech_grade_calc(cr_yr, profile_data['education'], profile_data['certi_name'])

        col1.markdown(f":rainbow[ {profile_data['name']} ]")
        col2.markdown(f":red[ {profile_data['age']} ]")
        col3.markdown(f":orange[ {profile_data['tech_grade'] } [산출:{grd}] ]")
        col4.markdown(f":blue[ {profile_data['career_period']} ]")
        col5.markdown(f":violet[ {profile_data['job_type']} ]")
        col6.markdown(f":green[ {profile_data['certi_name']} ]")

        if dataframe is None or len(dataframe)==0:
            st.write('경력자료 없음')
        else:
            disp_df(dataframe,date_format="YY.MM")

        #템플릿을 이용한 프로필 생성
        with st.sidebar:
            col1, col2 = st.columns(2)
            col1.markdown(f"{id_name} :rainbow[프로필]")
            with col2:
                 usage_form(col2,selected_df,dataframe)
    
            col1, col2 = st.columns(2)
            header_rows = col1.number_input(":blue[제목행 수]", min_value=1, max_value=3, step=1)
            font_name = col2.text_input(":blue[font_name]",value= "KoPub돋움체 Medium")
                  
            font_size_1 = col1.number_input(":blue[font size(프로필)]", min_value=8, max_value=20, value=10, step=1)
            font_size_2 = col2.number_input(":blue[font size(경력)]", min_value=8, max_value=20, value=10, step=1)
            
            uploaded_file = st.file_uploader(f":orange[템플릿 업로드]", type = 'pptx', label_visibility="collapsed")

            if uploaded_file is not None:
                st.session_state['template_file'] = uploaded_file  
            elif st.session_state['template_file'] is not None:
                print('template exist------------------------')
                uploaded_file = st.session_state['template_file']
                          
            if uploaded_file:
                st.write("template name:", uploaded_file.name)
                profile_data['age'] = str(profile_data['age'])
                # profile_data['birth_date']= pd.to_datetime(profile_data.birth_date, format="%Y-%m-%d")
                # profile_data['last_date']= pd.to_datetime(profile_data.last_date, format="%Y-%m-%d")
                
                dataframe.columns = [DICT_COL.get(x,x) for x in dataframe.columns] 
                # user parameter
                font_name = "KoPub돋움체 Medium" if font_name =='' else font_name
                user_params = {'font_size_2':font_size_2, 'font_size_1':font_size_1, 'font_name':font_name,'header_rows':header_rows}
                # ppt creation using template
                print("ppt:", dataframe)
                pres = util.edit_pres("a", profile_data.rename(DICT_COL), dataframe, uploaded_file, user_params)

                output_name = f'profile_from_{id_name}_db.pptx'

                binary_output = BytesIO()
                pres.save(binary_output) 

                st.download_button(
                    label=":file_folder: Download data as pptx",
                    data=binary_output.getvalue(),
                    file_name=output_name,
                )

def usage_form(col,selected_df,dataframe):
    with col:
        with st.popover("사용법 보기"):
            pr_columns = [DICT_COL.get(x,x) for x in selected_df.columns] 
            st.markdown("##### 템플릿 작성할 때 아래 항목을 표 내부에 표시하면 됨")
            st.markdown("- :red[프로필에 사용가능한 항목]- **{ }필수**")
            st.markdown(', '.join([ '{'+ x +'}' for x in pr_columns]))
            st.markdown("- :red[프로젝트 경력에 사용가능한 항목] - **헤더명으로**")
            cr_columns = [DICT_COL.get(x,x) for x in dataframe.columns] 
            st.markdown(', '.join(cr_columns))
            st.markdown("- :blue[경력표의 제목행 수와 폰트를 지정 후 템플릿을 업로드하면 선택한 인원의 프로필을 다운로드 가능]")
            st.markdown("- KoPub돋움체 Medium, KoPub돋움체 Bold, KoPub돋움체 Medium, 맑은 고딕, 나눔바른고딕 .....")

def aggrid_opt_build(df):
    # print('ag_grid::', df)

    df['first_date'] = df['first_date'].dt.strftime('%Y-%m-%d')
    df['last_date'] = df['last_date'].dt.strftime('%Y-%m-%d')
    df['birth_date'] = df['birth_date'].dt.strftime('%y년%m월')
    df['graduate_date'] = df['graduate_date'].dt.strftime('%y년%m월')

    gd = GridOptionsBuilder.from_dataframe(df)
    gd.configure_default_column(
        flex=1,
        minWidth=100,
        maxWidth=500,
        resizable=True,
    )
    gd.configure_pagination(enabled=True)
    gd.configure_default_column(editable=True,flex=1, resizable=True)
    gd.configure_side_bar()

    # gd.configure_column("birth_date", type=["customDateTimeFormat"], custom_format_string='yy년MM월')
    # gd.configure_column("graduate_date", type=["customDateTimeFormat"], custom_format_string='yy년MM월')
  
    gd.configure_column(field='id',editable=False)
    options=['초급','중급','고급','특급']
    gd.configure_column('tech_grade',cellEditor='agSelectCellEditor', cellEditorParams={'values': options })
    options=[ "학사",  "석사" ,  "전문학사", "박사", "고졸"]
    gd.configure_column('education', cellEditor='agSelectCellEditor', cellEditorParams={'values': options })
    options=[ "남",  "여"]
    gd.configure_column('gender', cellEditor='agSelectCellEditor', cellEditorParams={'values': options })
    for col in df.columns:
        gd.configure_column(field=col, header_name=DICT_COL.get(col, col), suppressSizeToFit=False)#, minWidth=20)
    return gd



def reserved_tab():

    df_profile =  st.session_state['df_profile']
    df_profile =  df_profile[df_profile['employ_status']=='']

    # df_career =  st.session_state['df_career']
    df_profile['age'] = df_profile['age'].fillna(0)
    df_sum = df_profile.groupby(['tech_grade','age','job_type','team'])['name'].count().reset_index().rename(columns={'name':'count'})
    df_sum['age2'] = ((df_sum['age'] // 10) * 10)
    df_sum.loc[df_sum['tech_grade']=='','tech_grade'] = 'N/A'
    df_sum.loc[df_sum['team']=='','team'] = 'N/A'
    DICT_COL_NAME = {'등급별':'tech_grade','연령별':'age2','소속별':'job_type'}
    # st.stop()
    opt = st.radio('Your Choice', options=['등급별','연령별','소속별'],horizontal=True, label_visibility="collapsed")
    names = DICT_COL_NAME.get(opt, opt)

    chart_menu = st.columns(2)
    with chart_menu[0]:
        fig3 = px.bar(
            df_sum.groupby([names])['count'].sum().reset_index(),
            y="count",
            x=names,
            color=names,
            template = "seaborn",
            barmode='stack',
            text_auto=True,
            title=opt + '인원  ' + '      ⬇️click bar to show list'
            )
        fig3.update_xaxes(title_text=None,tickfont_family='KoPub돋움체 Medium', tickfont_color='blue', tickfont_size=12)
        fig3.update_yaxes(title_text=None)
        fig3.update_layout(legend_title_text=None,title_x =0.3)
        event3 = st.plotly_chart(fig3, key="bar_grade", on_select='rerun')
        
    with chart_menu[1]:
        fig = px.pie(
            df_sum,
            values="count",
            names=names,
            color=names,
            title=opt + ' %'
        )
        fig.update_traces(textposition='auto',textinfo='percent+value', textfont_size=12,textfont_color="black") 
        fig.update_layout(legend_title_text=None,title_x =0.3)  
        event = st.plotly_chart(fig, key="pie_grade", on_select='rerun')

    if len(event3.selection['points'])>0:
        click_label = event3.selection['points'][0]['label']
        click_label = '' if click_label =='N/A' else click_label
        if names =='age2':
            disp_df(df_profile[df_profile['age']//10==click_label/10])
        else:
            disp_df(df_profile[df_profile[names]==click_label])
   

#     st.sidebar.markdown('''
#                     - ## Medium Article : 
#                         [**Automate Streamlit Web App using Interactive AgGrid with Google Sheets**](https://medium.com/towards-data-science/automate-streamlit-web-app-using-interactive-aggrid-with-google-sheets-81b93fd9e648).
                    
#                     - ## Link to the YouTube videos :
#                         - 1. [AgGrid Part 1](https://youtu.be/F54ELJwspos)
#                         - 2. [AgGrid Part 2](https://youtu.be/Zs9-8trPadU)
#                         - 3. [AgGrid Part 3](https://youtu.be/sOFM334iILs)
#                 ''' )
    
#     # st.sidebar.video('https://youtu.be/F54ELJwspos')
#     # st.sidebar.video('https://youtu.be/Zs9-8trPadU')

#     st.subheader("This is how AgGrid Table looks!")

#     gd = aggrid_opt_build(df)

#     col1, col2 = st.columns(2)
#     with col1:
#         _funct = st.radio(label="Functions", options = ['Display','Highlight','Delete'])

#     if _funct == 'Display':
#         with col2:
#             sel_mode = st.radio('Selection Type', options = ['single', 'multiple'])
#         gd.configure_selection(selection_mode=sel_mode, use_checkbox=True)
#         gridoptions = gd.build()
#         grid_table = AgGrid(df,
#                             gridOptions=gridoptions,
#                             update_mode= GridUpdateMode.SELECTION_CHANGED,
#                             height= 500,
#                             width='100%',
#                             allow_unsafe_jscode=True,
#                             enable_enterprise_modules = True,
#                             fit_columns_on_grid_load = True,
#                             # columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
#         )
#                             # theme = 'balham')

     
#         selected_df = grid_table["selected_rows"]
#         st.subheader("Output")
#         st.write(selected_df)

#     if _funct == 'Highlight':
#         col_opt = st.selectbox(label ='Select column',options = df.columns)
#         cellstyle_jscode = JsCode("""
#             function(params){
#                 if (params.value == 'Alpha') {
#                     return {
#                         'color': 'black',
#                         'backgroundColor' : 'orange'
#                 }
#                 }
#                 if (params.value == 'B.1.258') {
#                     return{
#                         'color'  : 'black',
#                         'backgroundColor' : 'red'
#                     }
#                 }
#                 else{
#                     return{
#                         'color': 'black',
#                         'backgroundColor': 'lightpink'
#                     }
#                 }
        
#         };
#         """)
#         gd.configure_columns(col_opt, cellStyle=cellstyle_jscode)
#         gridOptions = gd.build()
#         grid_table = AgGrid(df, 
#                 gridOptions = gridOptions, 
#                 enable_enterprise_modules = True,
#                 fit_columns_on_grid_load = True,
#                 height=500,
#                 width='100%',
#                 # theme = "material",
#                 update_mode = GridUpdateMode.SELECTION_CHANGED,
#                 reload_data = True,
#                 allow_unsafe_jscode=True,
#                 )
        
#     if _funct == 'Delete':
    
#         js = JsCode("""
#         function(e) {
#             let api = e.api;
#             let sel = api.getSelectedRows();
#             api.applyTransaction({remove: sel})    
#         };
#         """     
#         )  
        
#         gd.configure_selection(selection_mode= 'single')
#         gd.configure_grid_options(onRowSelected = js, pre_selected_rows=[])
#         gridOptions = gd.build()
#         grid_table = AgGrid(df, 
#                     gridOptions = gridOptions, 
#                     enable_enterprise_modules = True,
#                     fit_columns_on_grid_load = True,
#                     height=500,
#                     width='100%',
#                     # theme = "streamlit",
#                     update_mode = GridUpdateMode.SELECTION_CHANGED,
#                     reload_data = True,
#                     allow_unsafe_jscode=True,
#                     )    
#         st.balloons()
#         st.info("Total Rows :" + str(len(grid_table['data'])))   


def app():
    tab1, tab2 = st.tabs([":printer: $\large  Print$", ':roll_of_paper: $\large  Analyze$'])
    with tab1:
        inqiure_tab()

    with tab2:
        reserved_tab()
        