import streamlit as st
import pandas as pd
import datetime
from models import database  as db
from libs import utils as util
from st_aggrid import AgGrid, GridUpdateMode, JsCode,ColumnsAutoSizeMode,DataReturnMode
from st_aggrid.grid_options_builder import GridOptionsBuilder
# import pygwalker as pyg
# from pygwalker.api.streamlit import StreamlitRenderer
import streamlit.components.v1 as components

# from libs.utils import today
today = util.get_days(0)

DICT_PJT = {'id':'번호', 'project_name':'프로젝트', 'project_mgmr':'PM','customer':'고객사', 'start_date':'시작일',
            'end_date':'종료일', 'master_yn':'주사업', 'co_company':'협력사', 'sales':'매출','cost':'원가', 'os':'OS',
            'dbms':'DBMS', 'sector':'업종', 'solutions':'솔루션','was':'WAS','mgmr_type':'PM유형','project_code':'코드',
            'ratio':'매출이익율'}   
SECTOR_LIST = ['공공','은행','증권','보험/공제','제조','유동','공기업','기타']
DBMS_LIST = ['Oracle','Postgresql','Maria','Mysql','Tibero','Mssql','기타']
OS_LIST = ['linux','windows','unix','기타']

def init_session():
    if 'id_no' not in st.session_state:
        st.session_state['id_no'] = None
    if 'project_name' not in st.session_state:
        st.session_state['project_name'] = None
    if 'df_project' not in st.session_state:
        st.session_state['df_project'] = None 
    if 'grid_table' not in st.session_state:
        st.session_state['grid_table'] = None 
    if 'add_row' not in st.session_state:
        st.session_state['add_row'] = False 

def list_tab():
    init_session()
    query = f" select * from members.projects order by start_date desc"
    df = db.get_data_to_df(query)
    df['master_yn'] = df['master_yn'].astype(bool)
    st.session_state['df_project'] = df

    df_grid = df.copy()
    if st.session_state['grid_table'] is not None: # add_row결과 그리드
        df_grid = st.session_state['grid_table']
    
    grid_mode = 'aggrid'

    if grid_mode != 'aggrid':
        df_grid.insert(0,'select', False)
        df_grid.columns = [DICT_PJT.get(x,x) for x in df_grid.columns]
        edited_df = st.data_editor(
            df_grid,
            column_config = {
                "select": st.column_config.CheckboxColumn(
                    "Update?",
                    help="check for **update** ",
                    width="small",
                    default=False,
                ),
                '프로젝트': st.column_config.Column("프로젝트"),
                '업종': st.column_config.SelectboxColumn(options=SECTOR_LIST,),
                'DBMS': st.column_config.SelectboxColumn(options=DBMS_LIST,),
                'OS': st.column_config.SelectboxColumn(options=OS_LIST,),
                '시작일': st.column_config.DateColumn(format="YYYY-MM-DD",),
                '종료일': st.column_config.DateColumn(format="YYYY-MM-DD",),
                "주사업": st.column_config.CheckboxColumn(
                    default=False,
                    width="small",
                ),
                '매출': st.column_config.NumberColumn(),
                '원가': st.column_config.NumberColumn(),
            },
            disabled=['id'],
            num_rows = 'dynamic',
            hide_index = True,
            key = "changes",
            # width = 2000
        )
        
        upd_df = edited_df[edited_df['select']==True]
        upd_df = upd_df.drop(columns='select')
    else:
        sel_mode = 'multiple'
        gd = aggrid_opt_build(df_grid)
        pre_selected = ''
        if st.session_state['add_row'] == True: #신규이면 첫번째를 pre-select
            pre_selected = '0'
    
        gd.configure_selection(selection_mode=sel_mode, use_checkbox=True, pre_selected_rows=[pre_selected])
        gridoptions = gd.build()
        grid_table = AgGrid(df_grid,gridOptions=gridoptions,
                                # update_mode= GridUpdateMode.SELECTION_CHANGED,  <- 활성화하면 그리드 입력내용이 사라짐
                                data_return_mode=DataReturnMode.AS_INPUT,
                                height = 500,
                                width="100%",
                                allow_unsafe_jscode=True,
                                columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                                theme = 'balham'
                            ) 
        upd_df = grid_table["selected_rows"]
        
    process_col = st.columns([1, 2, 4])
    if grid_mode == 'aggrid':
        with process_col[0]:
            st.checkbox("New row", on_change = add_row, key='add_row', args = [df_grid])

    if upd_df is not None:  
        upd_df = upd_df.fillna('')
        DICT_PJT_R = dict((value, key) for (key, value) in DICT_PJT.items())
        upd_df.columns = [DICT_PJT_R.get(x,x) for x in upd_df.columns]

    # 업데이트 또는 신규 
    if upd_df is not None or st.session_state['add_row'] == True:  
        with process_col[1]:
            st.button("Process :ok:", on_click = update_process, args = [upd_df])
    if upd_df is not None:
        with process_col[2]:
            st.button("delete :warning:", on_click = delete_process, args = [upd_df])     
      
def aggrid_opt_build(df):
    # print('ag_grid::', df)
    df['start_date'] = pd.to_datetime(df['start_date'])
    df['end_date'] = pd.to_datetime(df['end_date'])
    df['start_date'] = df['start_date'].dt.strftime('%Y-%m-%d')
    df['end_date'] = df['end_date'].dt.strftime('%Y-%m-%d')
    
    gd = GridOptionsBuilder.from_dataframe(df)
    gd.configure_pagination(enabled=True)
    gd.configure_default_column(editable=True,flex=1, minWidth=120, maxWidth=500, resizable=True)
    gd.configure_side_bar()
    gd.configure_column("sales",type=["numericColumn","numberColumnFilter","customNumericFormat"], valueFormatter="data.sales.toLocaleString();")
    gd.configure_column("cost",type=["numericColumn","numberColumnFilter","customNumericFormat"], valueFormatter="data.cost.toLocaleString();")

    gd.configure_column(field='id',editable=False)
    gd.configure_column('sector',cellEditor='agSelectCellEditor', cellEditorParams={'values': SECTOR_LIST })
    gd.configure_column('dbms', cellEditor='agSelectCellEditor', cellEditorParams={'values': DBMS_LIST })
    gd.configure_column('os', cellEditor='agSelectCellEditor', cellEditorParams={'values': OS_LIST })
    for col in df.columns:
        gd.configure_column(field=col, header_name=DICT_PJT.get(col, col),suppressSizeToFit=False) #, Width=6)
    return gd

def update_process(inp_df):
    # progress_text = "Operation in progress. Please wait."

    print('update or insert::: ', inp_df['id'])  
    table = 'members.projects'
    u_key_cols = []
    u_key_cols.append('id') #unique identifier

    res = False
    inp_df['id'] = inp_df['id'].fillna(0)
    # print('df ::: ', inp_df.columns, inp_df['id'])
    temp_df = pd.DataFrame(inp_df[inp_df['id'].isin(['',0])])
    if len(temp_df) > 0:
        temp_df = temp_df.drop(columns='id')
        res =  db.insert_df_to_table(df=temp_df, table="members.projects")
        print('insert completed------------')
        txt = '입력완료'

    temp_df = inp_df[~inp_df['id'].isin(['',0])]
    if len(temp_df) > 0: 
        temp_df['id'] = temp_df.id.astype(int)
        res,cnt = db.update_df_to_table(temp_df, table, u_key_cols)
        if res:
            print('update count: ', cnt)
            txt = "수정완료"
 
    if res: 
        st.session_state['grid_table'] = None
        st.session_state['add_row'] = not st.session_state['add_row'] #입력체크박스 초기화
        st.success(txt) 
        return True
    else:
        st.error('에러')
        return False
       
def delete_process(upd_df):
    for id in upd_df['id']:
        sql = f'delete from members.projects where id = {id} '
        db.execute_sql(sql)

    st.success('삭제완료') 
    return True

def add_row(grid_table):

    df = grid_table
    # print('add_row...', st.session_state['add_row'], len(grid_table))
    if st.session_state['add_row'] == False:
        st.session_state['grid_table'] = df[df['project_name']!='']
        return True
       
    DICT_TYPE = {'start_date':'datetime64[ns]', 'end_date':'datetime64[ns]','sales':'int64','cost':'int64','master_yn':'bool'}
    # df = pd.DataFrame(grid_table['data'])
 
    for column in df.columns.values.tolist():
        if DICT_TYPE.get(column,None) is not None:
            df[column] = df[column].astype(DICT_TYPE.get(column))
   
    column_fillers = {
        column: (False if df.dtypes[column].name == "bool" #"BooleanDtype"
            else 0 if df.dtypes[column].name == "int64"
            else '' if df.dtypes[column].name == "object"  
            else datetime.datetime.now() if df.dtypes[column].name == "datetime64[ns]"
            else ''   )
            for column in df.columns.values.tolist()
    }
    
    data = [column_fillers]
    df_empty = pd.DataFrame(data, columns=df.columns)
    df = pd.concat([df_empty, df], axis=0, ignore_index=True)
    st.session_state['grid_table'] = df
    return True

def analysis_tab():
    DICT_SALES= {"1천":10_000_000, "2억":200_000_000, "5억":500_000_000, "10억":1_000_000_000, "20억":2_000_000_000, "무한":999_000_000_000}
    DICT_RATIO= {"0%":0, "5%":5, "10%":10, "15%":15, "20%":20, "100%":100}
    init_session()
    query = f" select * from members.projects order by start_date desc"
    
    if st.session_state['df_project'] is not None:
        df = st.session_state['df_project']
    else:
        df = db.get_data_to_df(query)
        st.session_state['df_project'] = df

    df = df[['project_name','start_date','end_date','sales','cost','master_yn']].copy()

    # df['start_date'] = pd.to_datetime(df['start_date'])
    # df['end_date'] = pd.to_datetime(df['end_date'])
    df =  df.astype({'start_date':str,'end_date':str})
    df['sales'] = df['sales'].astype('int64')
    df['cost'] = df['cost'].astype('int64')
    df['ratio'] = round((100 - df['cost'] / df['sales'] * 100).fillna(0),1)

    cols = ['project_name','start_date','end_date','sales','cost','ratio']
    df_sum = df[cols]
    header_col = st.columns([2,2,4,4])
    with header_col[0]:    
        sel  = st.multiselect('사업년도', options=df_sum['start_date'].str[:4].unique(), label_visibility="collapsed",placeholder="시작년도 선택")
    if sel:
        df_sum = df_sum[df_sum['start_date'].str[:4].isin(sel)]
    with header_col[1]:
        chk  = st.checkbox('Ongoing') 
        if chk:
             df_sum = df_sum[df_sum['end_date'] >= today.strftime('%Y-%m-%d')]
    with header_col[2]:    
        start_sales, end_sales = st.select_slider(
        "Select a range of sale amount",
        options=["1천", "2억", "5억", "10억", "20억", "무한"],
        value=("10억", "20억"), label_visibility="collapsed")
    with header_col[3]:    
        start_ratio, end_ratio = st.select_slider(
        "Select a range of profit",
        options=["0%", "5%", "10%", "15%", "20%", "100%"],
        value=("10%", "20%"), label_visibility="collapsed")   

    sales_left, sales_right = DICT_SALES.get(start_sales), DICT_SALES.get(end_sales)
    ratio_left, ratio_right = DICT_RATIO.get(start_ratio), DICT_RATIO.get(end_ratio)
    df_sum.columns = [DICT_PJT.get(x,x) for x in df_sum.columns]
    st.dataframe(
        df_sum.style.highlight_max(['매출','매출이익율'], props='font-weight:bold;color:#fc034e') \
        .highlight_min(['매출','매출이익율'], color='#ffffcc') \
        .highlight_between(['매출'], color='#18dea3', left=sales_left, right=sales_right) \
        .highlight_between(['매출이익율'], color='#5bd609', left=ratio_left, right=ratio_right) \
        .format('{:.01f}', na_rep='MISS', subset=['매출이익율'])  \
        .format('{:,.0f}', na_rep='MISS', subset=['매출','원가'])  ,
        width=2000
    )

    # with st.expander("show customizable "):
    #     st.subheader('Use Pygwalker')
    #     # pyg_html = pyg.walk(df, return_html=True)
    #     # pyg_app = StreamlitRenderer(df)
    #     pyg_html = pyg.walk(df, return_html=True)
    #     components.html(pyg_html, height=1000, scrolling=True)

def app():
    tab2, tab1 = st.tabs([":memo: $\large List/Edit$",":new: $\large Analyze$"])
    with tab1:
        analysis_tab()

    with tab2:
        list_tab()
        
 