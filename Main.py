import streamlit as st

from streamlit_option_menu import option_menu
from views import Profile as profile
from views import Inquire as inquir
from views import Project as project
from views import Agent as agent
from views import SqlAgent as sql_agent
from st_pages import hide_pages

if 'sidebar_state' not in st.session_state:
    st.session_state.sidebar_state = 'auto'

st.set_page_config(
    page_title="Profile Management",
    page_icon="house",
    layout="wide",  # 또는 wide / centered
    initial_sidebar_state=st.session_state.sidebar_state,  # auto / collapsed
    menu_items={
        'Get Help': 'https://streamlit.io/',
        'Report a bug': 'mailto:jy.yoon@hkcloud.co.kr',
        'About': """# This is a profile & project management system. This is an *extremely* cool app! You can manage data with given menu, also chat with database using sql-agent.
                """
    }
   
)

def hide_sidebar():
    # st.markdown("""
    # <style>
    #     section[data-testid="stSidebar"][aria-expanded="true"]{
    #         display: none;
    #     }
    # </style>
    # """, unsafe_allow_html=True)

    hide_pages(['Main', 'Profile','Inquire','Project','Agent'])  #main과 views 디렉토리에 있는 메뉴를 숨김

    m = st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: rgb(192, 192, 192);
        font-size: 10 px;
        width: 120 px; 
        height: 8 px;            
    }
    </style>""", unsafe_allow_html=True)

# hide_sidebar()

with st.sidebar:
    selected = option_menu("Main Menu", [ 'Profile관리','Profile분석&출력','Project관리','Chat with Database'], #1 메뉴제거
            icons=[ 'book','gear','list-task','android','android'], menu_icon="house", default_index=0,
            styles={
            "container": {"padding": "0!important", "background-color": "#fafafa"},
            "menu-title": {"font-size": "14px","color": "green"},
            "menu-icon": {"font-size": "14px"},
            "icon": {"color": "orange", "font-size": "20px"}, 
            "nav-link": {"font-size": "14px", "text-align": "left", "margin":"0px", "--hover-color": "lightblue"},
            "nav-link-selected": {"background-color": "cadetblue"},
    })
 
st.markdown(
    """
    <style>
    [data-testid="baseButton-secondary"] {
        font-size: 10px;
        color: white;
        background-color: lightskyblue;
    },
    [data-testid="stMarkdownContainer"]  {
        font-size: 10px;
        color: red;
    },
   </style>
    """,
    unsafe_allow_html=True
)

# print('selected: ', selected)
if selected == 'Profile관리':
    profile.app()
if selected == 'Profile분석&출력':
    inquir.app()
if selected == 'Project관리':
    project.app()
if selected == 'Agent':
    agent.app()
if selected == 'Chat with Database':
    sql_agent.app()