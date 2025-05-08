import streamlit as st
import os
import pandas as pd
# import psycopg2
import pymysql

def get_conn_postgres_st():
    ''' st.connection이용 '''
    
   # Initialize connection.
   # st.connection은 .streamlit/secrets.toml 파일을 참조함
    return st.connection("postgresql", type="sql")

def get_conn_postgres(conn_name=None):

    host = os.getenv('db_host')
    
    if host is not None:   #도커 컨테이너에서 실행시 환경변수로 설정값
        print('host environment= ', host)
        conn_name = os.getenv('db_dialect')
        username = os.getenv('db_username')
        password = os.getenv('db_password')
        database = os.getenv('db_name')
    else:                 #secrets.toml을 이용할때
        conn_name = st.secrets["connections_dbms"]["conn_name"]
        host = st.secrets[conn_name]["host"]
        username = st.secrets[conn_name]["username"]
        password = st.secrets[conn_name]["password"]
        database = st.secrets[conn_name]["database"]
        # dsn = f'{st.secrets[conn_name]["host"]}:{st.secrets[conn_name]["port"]}/{st.secrets[conn_name]["database"]}'
        # encoding = st.secrets[conn_name]["encoding"]
        
    if "mysql" in conn_name:
        try:
            # connection = pymysql.connect(username, password, dsn, encoding=encoding)
            connection = pymysql.connect(host=host, database=database, user=username, password=password)
        except Exception as ex:
            print('Could not connect to database:', ex)
            return ex

        print("SUCCESS: Connecting mysql succeeded")
        return connection
    
    if "postgresql" in conn_name:
        try:
            connection = psycopg2.connect(host=host, database=database, user=username, password=password)
        except Exception as ex:
            print('Could not connect to database:', ex)
            return ex
        print("SUCCESS: Connecting postgresql succeeded")
        return connection

def get_db_url():
    host = os.getenv('db_host')
    
    if host is not None:   #도커 컨테이너에서 실행시 환경변수로 설정값
        print('host environment= ', host)
        conn_name = os.getenv('db_dialect')
        username = os.getenv('db_username')
        password = os.getenv('db_password')
        database = os.getenv('db_name')
        db_uri = f"mysql+pymysql://{username}:{password}@{host}/{database}"
    else:                 #secrets.toml을 이용할때
        conn_name = st.secrets["connections_dbms"]["conn_name"]
        host = st.secrets[conn_name]["host"]
        username = st.secrets[conn_name]["username"]
        password = st.secrets[conn_name]["password"]
        database = st.secrets[conn_name]["database"]
        port = st.secrets[conn_name]["port"]
        db_uri = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    return db_uri

# @st.cache_data
def get_data_to_df(sql):
    try:
        conn = get_conn_postgres()
     
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            cols = [x[0].lower() for x in cursor.description]

        df = pd.DataFrame(rows, columns = cols)
        # for c in df.columns:
        #     if df[c].dtype == object:
        #        df[c] = df[c].astype("string")

        conn.close()

    except (Exception) as ex:
        print('error message :', ex)
        conn.close()
        return None
   
    if len(df) == 0:
        print('No data found')  
        return None

    return df

def insert_to_table(schema , table , data, mode='insert', repl_cond=None, get_seq=None):
    #접속db를 읽어옴
    conn_name = os.getenv('db_dialect')
    if conn_name is None:   
        conn_name = st.secrets["connections_dbms"]["conn_name"]

    # it_processing = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # it_processing = pd.to_datetime(it_processing)
    res_seq = 0
   
    # 딕셔너리를 받아서 db에 입력: key는 컬럼이름과 같아야함
    cols = ','.join(list(data.keys()))
    vals = str(tuple(data.values()))
    if schema:
        table = f"{schema}.{table}"

    sql = f"""insert into {table} (  {cols}  ) values  {vals}"""

    if get_seq:
        seq_sql = f"""SELECT currval('{get_seq}')"""
    if "mysql" in conn_name: 
        seq_sql = f'''SELECT LAST_INSERT_ID()'''

    # replace이면 기존 데이터 삭제
    if mode=='replace':
        del_sql = f"""delete from {table} where {repl_cond}"""
        if repl_cond == None:
            return False
        
    try:
        conn = get_conn_postgres()

        with conn.cursor() as cursor:
            if mode=='replace':
                cursor.execute(del_sql)

            cursor.execute(sql)

            if get_seq:
                cursor.execute(seq_sql)
                res_seq = cursor.fetchone()[0]

            conn.commit()

        conn.close()

    except (Exception) as ex:
        conn.rollback()
        conn.close()
        print("Error: " , ex)
        return False

    return res_seq

def insert_df_to_table(df, table, mode='insert', repl_cond=None):
        """
        Using cursor.executemany() to insert the dataframe
        """
        # Create a list of tupples from the dataframe values
        tuples = list(set([tuple(x) for x in df.to_numpy()]))
        # Comma-separated dataframe columns
        cols = ','.join(list(df.columns))

        query = f"INSERT INTO {table} ({cols}) VALUES ({ (',%s'*len(df.columns))[1:] })" 
        print('insert_df_to_table = ',query)

       # replace이면 기존 데이터 삭제
        if mode=='replace':
            del_sql = f"""delete from {table} where {repl_cond}"""
            if repl_cond == None:
                return False
            
        try:
            conn = get_conn_postgres()
            
            with conn.cursor() as cur:
                if mode=='replace':
                    cur.execute(del_sql)
                if len(df) > 0:
                    cur.executemany(query, tuples)
                conn.commit()

            conn.close()

        except (Exception) as error:
            print("Error: %s" % error)
            conn.rollback()
            conn.close()
            return False
        
        return True

def update_df_to_table(df_u, table, u_key_cols):
    ''' df를 받아서 업데이트함 : df, 테이블명, unique key컬럼 '''
    temp = df_u.columns
    # key컬럼을 제외한 cols를 생성
    # temp = list(filter(lambda x: x not in u_key_cols, temp))
    # cols = ','.join(list(temp))
    cols = list(filter(lambda x: x not in u_key_cols, temp))
    succ_cnt = 0
    try:
        conn = get_conn_postgres()

        # df 개수만큼 반복
        for i, row in df_u.iterrows():
            #업데이트할 컬럼값을 생성 from df
            # vals = "'" + "','".join([str(t) for t in row[cols.split(',')]]) + "'" 
            # u_key_vals = list(row[u_key_cols])
            vals = [ str(t) for t in row[cols]]
            u_key_vals = row[u_key_cols]

            # update query생성
            query = f"update {table} SET  " 
            for x, y in zip(cols, vals):
                query +=  f"{x} = '{y}' ,"
            query = query[:-1]

            where = 'where '
            for x,y in zip (u_key_cols,u_key_vals):
                where += f"{x} = '{y}'  and "
            query = query + where.rstrip(' and ')
            print('update-', i,':',query)
            succ_cnt += 1
    
            with conn.cursor() as cursor:
                cursor.execute(query)
        #업데이트 완료 후 커밋        
        conn.commit()
        conn.close()

    except (Exception) as error:
            print("Error: %s" % error)
            conn.rollback()
            conn.close()
            return False, 0
    
    return True, succ_cnt


def execute_sql(query):
    ''' sql를 받아서 처리함 '''
    try:
        conn = get_conn_postgres()

        with conn.cursor() as cursor:
            cursor.execute(query)
        #업데이트 완료 후 커밋        
        conn.commit()
        conn.close()

    except (Exception) as error:
            print("Error: %s" % error)
            conn.rollback()
            conn.close()
            return False
    
    return True

