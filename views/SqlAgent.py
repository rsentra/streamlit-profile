import streamlit as st
from typing import Annotated, Literal,TypedDict
# from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
import pandas as pd
import json
import os
# from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from libs.utils import local_embedding, get_local_vector

OPENAI_MODEL_NAME = "gpt-4o-mini"
ANTROPIC_MODEL_NAME = "claude-3-5-sonnet-20240620"

def LangGraph_run():
    # Define the state for storing messages
    class State(TypedDict):
        messages: Annotated[list, add_messages]

    def chatbot(state: State):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}
 
    import json
    from langchain_core.messages import ToolMessage
    class BasicToolNode:
        """A node that runs the tools requested in the last AIMessage."""

        def __init__(self, tools: list) -> None:
            self.tools_by_name = {tool.name: tool for tool in tools}

        def __call__(self, inputs: dict):
            if messages := inputs.get("messages", []):
                message = messages[-1]
            else:
                raise ValueError("No message found in input")
            outputs = []
            for tool_call in message.tool_calls:
                tool_result = self.tools_by_name[tool_call["name"]].invoke(
                    tool_call["args"]
                )
                outputs.append(
                    ToolMessage(
                        content=json.dumps(tool_result, ensure_ascii=False),
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                )
            return {"messages": outputs}


    def route_tools(
        state: State,
    ) -> Literal["tools", "__end__"]:
        """
        Use in the conditional_edge to route to the ToolNode if the last message
        has tool calls. Otherwise, route to the end.
        """
        if isinstance(state, list):
            ai_message = state[-1]
        elif messages := state.get("messages", []):
            ai_message = messages[-1]
        else:
            raise ValueError(f"No messages found in input state to tool_edge: {state}")

        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            return "tools"
        return "__end__"

    
    if st.session_state.model_choice == "Anthropic Claude":
        llm = ChatAnthropic(
            model=ANTROPIC_MODEL_NAME,
            temperature=0, verbose=True,
            api_key=st.session_state.api_key
        )
    elif st.session_state.model_choice == "OpenAI ChatGPT":
        llm = ChatOpenAI(
            model=OPENAI_MODEL_NAME,
            temperature=0, verbose=True,
            api_key=st.session_state.api_key
        )
   
    # os.environ['TAVILY_API_KEY'] = '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'
    # tool = TavilySearchResults(max_results=2)
    tool = sql_tool
    tools = [tool]    
    llm_with_tools = llm.bind_tools(tools)  

    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)

    tool_node = BasicToolNode(tools=[tool])
    graph_builder.add_node("tools", tool_node)

   
    # The `tools_condition` function returns "tools" if the chatbot asks to use a tool, and "__end__" if
    # it is fine directly responding. This conditional routing defines the main agent loop.
    graph_builder.add_conditional_edges(
        "chatbot",
        route_tools,
        # The following dictionary lets you tell the graph to interpret the condition's outputs as a specific node
        # It defaults to the identity function, but if you
        # want to use a node named something else apart from "tools",
        # You can update the value of the dictionary to something else
        # e.g., "tools": "my_tools"
        {"tools": "tools", "__end__": "__end__"},
    )

    # Any time a tool is called, we return to the chatbot to decide the next step
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "chatbot")
    graph = graph_builder.compile()

    try:
        # Get the mermaid PNG as bytes
        # graph_bytes = graph.get_graph().draw_mermaid_png()
        # Convert the bytes to an image and display it in Streamlit
        # st.image(graph_bytes, caption="Chatbot Graph")
        # st.markdown('###### :robot_face: :blue[개발자 프로필]과 :blue[프로젝트 정보]에 대해 자유롭게 질문해주세요')
        pass
    except Exception as e:
        st.error(f"Failed to display graph: {e}")

    if "messages_03" not in st.session_state:
        st.session_state.messages_03 = []

    # Display all previous messages
    for message in st.session_state.messages_03:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Get new user input and process it
    if prompt := st.chat_input("질문하세요?"):
        st.session_state.messages_03.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Prepare the entire chat history to send to the model
        full_conversation = [(msg["role"], msg["content"]) for msg in st.session_state.messages_03]
        print("full_conversation::::", full_conversation)
        i = 0
        # Generate response using the model with the full conversation history
        for event in graph.stream({"messages": full_conversation}):
            for value in event.values():
                # i = i + 1
                # st.write("values ", i, " :", value)

                # 첫 번째 메시지가 AIMessage인 경우에만 처리 
                if isinstance(value["messages"][0], AIMessage):
                    ai_message = value["messages"][0]

                    # tool_calls가 없는 경우에만 response에 값 할당
                    if not hasattr(ai_message, 'tool_calls') or not ai_message.tool_calls:
                        response = ai_message.content
                        st.session_state.messages_03.append({"role": "assistant", "content": response})
                        with st.chat_message("assistant"):
                            st.markdown(response)

def chat_run():
    # Sidebar to reset session state
    with st.sidebar:
        if st.button("Reset Chat Session"):
            st.session_state.clear()
            # st.experimental_rerun()  # Rerun the app to reflect the changes
        if st.button("Reset Chat Message"):
            st.session_state.messages_03.clear()

    # Page title
    st.header("Chatbot with Database Tool")
    st.markdown("Database에 있는 프로필,프로젝트 정보에 대해 질문할 수 있습니다. LLM 모델의 api key를 Submit하면 질문이 가능합니다.")

    if "model_choice" not in st.session_state:
        st.session_state.model_choice = "OpenAI ChatGPT"  # 기본 선택값 설정

    # 모델 선택
    with st.sidebar:
        model_choice  = st.radio("Choose your model", ["OpenAI ChatGPT" ,"Anthropic Claude"])   

    # 선택이 변경되었는지 확인하고, 변경되었다면 세션을 초기화
    if model_choice != st.session_state.model_choice:
        st.session_state.clear()  # 현재 세션 정보 모두 초기화
        st.session_state.model_choice = model_choice  # 새로운 선택값을 세션에 저장      

    # Check if the API key has been submitted
    if "api_key_submitted" not in st.session_state:
        st.session_state.api_key_submitted = False
    if "show_query" not in st.session_state:
        st.session_state.show_query = False

    # If the API key has not been submitted, display the input field
    with st.sidebar: 
        if not st.session_state.api_key_submitted:
            if st.session_state.model_choice == "Anthropic Claude":
                api_key = st.text_input("Please input your Anthropic API Key:", type="password")
            elif st.session_state.model_choice == "OpenAI ChatGPT":
                api_key = st.text_input("Please input your OpenAI API Key:", type="password")
            if api_key.lower() == 'jy':
                api_key = get_api_key()

            # Button to submit the API key
            if st.button("Submit Key"):
                if len(api_key) > 5:
                    st.session_state.api_key = api_key
                    st.session_state.api_key_submitted = True
                else:
                    st.warning("Please input your API Key.")

        st.session_state.show_query = st.checkbox("Include Query In AI Message")

    # After API key submission, start the chatbot interaction
    if st.session_state.api_key_submitted:
        LangGraph_run()

def get_api_key():
    if st.session_state.model_choice == "Anthropic Claude":
        return st.secrets["llm_api_key"]["antropic_key"]
    else:
        return st.secrets["llm_api_key"]["openai_key"]

def get_few_shots():
    ''' few_shot prompt file read '''
    f_name = 'few_shots.json'
    with open(f'v_db/{f_name}','r', encoding='utf-8') as f:
        data=json.load(f)
    return data

def save_few_shots(df):
    f_name = 'few_shots.json'
    a = ''
    for i, row in df.iterrows():
        if not row['question']:
            continue
        q = row['question'].replace("\n","")
        e = row['example'].replace('\n','')
        s = f"\"{q}\": \"{e}\",\n"
        print(s)
        a += s
    a = "{" + a[:-2] + "\n}"
    with open(f'v_db/{f_name}','w', encoding='utf-8') as f:
        f.write(a)
   
def few_shots_display():
    st.markdown(":blue[예시 query]를 입력하면 성능향상에 도움이 됩니다. :blue[+ 또는 del 키/버튼을 이용하여 추가,삭제후 save] 하세요.")
    few_shots = get_few_shots()
    df = pd.DataFrame(few_shots.items(),columns=['question','example'])
    # df.insert(0,'select', False)
    edited_df = st.data_editor(
        df,
        hide_index = True,
        num_rows ='dynamic',
        key = "edit_data",
    )
    if st.button(label="Save Data"):
        save_few_shots(edited_df)     # few shot을 json으로 저장 
        get_fewshot_vector(mode='replace') # few shot embedding
        # edited_rows = st.session_state["edit_data"].get("edited_rows")
        # added_rows = st.session_state["edit_data"].get("added_rows")
        # st.write(edited_df)
        st.success("Data saved")
       
        
    # df = pd.concat([df, added_rows])
    # print(df)

def get_fewshot_vector(mode='load'):
    ''' get_fewshot_vector ( 신규생성 또는 기존 load) '''
    from langchain.schema import Document
    if mode == 'new' or mode == 'replace':
        few_shots = get_few_shots()
        to_vectorize = [
            Document(page_content=question, metadata={"input": question,"query": few_shots[question]})
            for question in few_shots.keys()
        ]
        vector_db = local_embedding(to_vectorize,index_name="fewshots2")
    else:
        vector_db = get_local_vector('fewshots2')
    return vector_db

def get_example_selector():
    ''' get_example_selector '''
    from langchain_core.example_selectors import SemanticSimilarityExampleSelector
 
    example_selector = SemanticSimilarityExampleSelector(
        vectorstore=get_fewshot_vector(),
        k=5,
        input_keys=["input"],
    )
    return example_selector

def get_fewshot_promt(example_selector):
    ''' get_fewshot_promt '''
    from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate

    system_prefix = """You are an agent designed to interact with a SQL database.
    Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
    Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most {top_k} results.
    You can order the results by a relevant column to return the most interesting examples in the database.
    Never query for all the columns from a specific table, only ask for the relevant columns given the question.
    Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. 
    Also, pay attention to which column is in which table.
    Pay attention to use CURRENT_DATE function to get the current date, if the question involves 'today'.

    You have access to tools for interacting with the database.
    Only use the given tools. Only use the information returned by the tools to construct your final answer.
    You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

    DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

    If the question does not seem related to the database, just return "I don't know" as the answer.

    Here are some examples of user inputs and their corresponding SQL queries:"""

    dynamic_few_shot_prompt = FewShotPromptTemplate(
        example_selector = example_selector,
        example_prompt=PromptTemplate.from_template(
            "User input: {input}\nSQL query: {query}"
        ),
        input_variables=["input", "dialect", "top_k"],
        prefix=system_prefix,
        suffix=""
    )
    full_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate(prompt=dynamic_few_shot_prompt),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    return full_prompt

def get_db():
    ''' db information '''
    from langchain_community.utilities import SQLDatabase
    from models import database  as db
    # db_uri = f"mysql+pymysql://root:hkc!@172.16.0.121:3306/members"
    db_uri = db.get_db_url()
    print("db_uri::::", db_uri)
    db = SQLDatabase.from_uri(db_uri,sample_rows_in_table_info=2,indexes_in_table_info=True,view_support =True)
    return db

def get_sql_agent(full_prompt):
    from langchain_community.agent_toolkits import create_sql_agent
    from langchain_openai import ChatOpenAI

    if st.session_state.model_choice == "Anthropic Claude":
        llm = ChatAnthropic(
            model=ANTROPIC_MODEL_NAME,
            temperature=0, verbose=True,
            api_key=st.session_state.api_key
        )
        agent_type = "tool-calling"
        
    elif st.session_state.model_choice == "OpenAI ChatGPT":
        llm = ChatOpenAI(
            model=OPENAI_MODEL_NAME,
            temperature=0, verbose=True,
            api_key=st.session_state.api_key
        )
        agent_type = "openai-tools"

    dynamic_few_shot_agent = create_sql_agent(
            llm=llm,
            db=get_db(),
            prompt=full_prompt,
            agent_type=agent_type,
            verbose=True,
            stream_runnable = False,
            top_k=9999,
    )
    return dynamic_few_shot_agent

@tool
def sql_tool(query: str) -> str:
    """ sql agent를 통해 질문에 대한 답변을 반환한다."""
    query = st.session_state.messages_03[-1]['content']
    print("query::::", query)
    example_selector = get_example_selector()
    full_prompt = get_fewshot_promt(example_selector)
    agent = get_sql_agent(full_prompt)

    if st.session_state.show_query == True:
        query = query + "\n 위 질문에 대한 SQL 쿼리도 응답에 포함해주세요"
    res = agent.invoke({"input": query})
    print("result::::", res)
    return res

# 미사용 function
def sql_run():
    with st.sidebar:
        if st.button("Reset Chat Session"):
            st.session_state.clear()
            # st.experimental_rerun()  # Rerun the app to reflect the changes

    # Page title
    st.title("LangGraph SQL Agent2")
   
    if user_qry := st.chat_input("What is up?"):
        example_selector = get_example_selector()
        full_prompt = get_fewshot_promt(example_selector)
        agent = get_sql_agent(full_prompt)
        if st.session_state.show_query == True:
            user_qry = user_qry + "\n 위 질문에 대한 SQL 쿼리도 응답에 포함해주세요"
        res = agent.run({"input":user_qry})
        print("result:", res)
        st.markdown(res)

if __name__ == "__main__":
    chat_run()

def app():

    chat_run()
 
    with st.sidebar:
        chk = st.checkbox("Show Database & Few-shots",True)

    if chk:
        with st.expander("See database explanation"):
            db = get_db()
            lis = db.get_table_info().split('\n')
            st.markdown(' 테이블 정보는 다음과 같습니다')
            for txt in lis:
                st.markdown(txt)

        with st.expander("See few-shots [example query]"):
            few_shots_display()
   