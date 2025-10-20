import streamlit as st
import psycopg2
import pandas as pd
from configparser import ConfigParser

# TODO Load production from the init file
production = True

# This section is largely obsolete now that secrets are
# being pulled from streamlit.  It's expected to return
# for future use.
def load_config(config_file='database.ini', section='postgresql'):
    """Load database connection parameters from config file"""
    parser = ConfigParser()
    parser.read(config_file)

    db_config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db_config[param[0]] = param[1]
    else:
        raise Exception(f'Section {section} not found in the {config_file} file')

    return db_config

def connect_to_db():
    """Connect to PostgreSQL database and return connection"""
    try:
        # Dangerous debug note when the code is working
        if not production and False:
            st.info(st.secrets)

        conn=st.connection("postgresql", type="sql")

        if (False):  # SQL alchemy connection instead
            from sqlalchemy import create_engine
            db_details = st.secrets["connections"]["postgresql"]
            engine = create_engine(f"postgresql://{db_details['username']}:{db_details['password']}@{db_details['host']}:{db_details['port']}/{db_details['database']}")

        if (False):  # Non streamlit method
                conn = psycopg2.connect(
                host="localhost",
                database="results",
                user="gsmith",
                password=""
        )
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        st.error(f"Error connecting to PostgreSQL database: {error}")
        return None

def run_query(query):
    """Run SQL query and return results as a pandas DataFrame"""
    conn = connect_to_db()
    if conn is not None:
        try:
            df = conn.query(sql=query)
            return df
        except (Exception, psycopg2.DatabaseError) as error:
            st.error(f"Error executing query: {error}")
            return None
    return None

# Local development option to allow writing your own query
def custom_query():
    default_query = "SELECT * FROM submission;"

    query = st.text_area("Enter SQL Query:", default_query, height=150)

    if st.button("Run Query"):
        fetch_with_download(query)

def fetch_with_download(query):
    with st.spinner('Fetching data...'):
        result_df = run_query(query)

        if result_df is not None and not result_df.empty:
            st.success(f"Query returned {len(result_df)} rows")
            st.dataframe(result_df)

            # Option to download as CSV
            csv = result_df.to_csv(index=False)
            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name="query_results.csv",
                mime="text/csv"
            )
        elif result_df is not None and result_df.empty:
            st.info("Query returned no results")

def osm():
    query ="""
WITH
best AS
  (SELECT
    cpu,mem_gb,disk,client,script,clients,conn,hours,nodes,nodes_kips,index_kips,fsync,wal_level,max_wal_gb,db_gb,
      wal_mbps, avg_write_mbps, max_write_mbps, avg_read_mbps, max_read_mbps,avg_package_watts, max_package_watts,
    ROW_NUMBER()
    OVER(
        PARTITION BY cpu,mem_gb,server_ver,script,conn,clients,nodes,fsync,wal_level,max_wal_gb
        ORDER BY nodes_kips DESC,index_kips DESC
    )  AS r
    FROM submission
    WHERE
      max_write_mbps IS NOT NULL AND
      category IS NULL AND
      script like 'osm2pgsql%'
  )
SELECT
    cpu,
    mem_gb,
    substr(disk,1,12) AS disk,
    --substring(server_ver,1,16) AS server_version,
    conn,
    --CASE WHEN client is NULL
    --  THEN cpu || ' ' || mem_gb || 'GB ' || disk
    --  ELSE client::text END AS client,
    --script,
    --clients,
    --tps,
    --hours AS hours,
    --round(nodes/1000000000,1) AS nodes_m,
    nodes_kips,index_kips,fsync,wal_level,max_wal_gb,
      wal_mbps AS wal, avg_write_mbps AS avg_write, max_write_mbps AS max_write, avg_read_mbps AS avg_read, max_read_mbps AS max_read,
      round(avg_package_watts) AS avg_pkg,
      round(max_package_watts) AS max_pkg
FROM best WHERE r=1
ORDER BY nodes_kips DESC,index_kips DESC,script,db_gb;
    """
    fetch_with_download(query)

def pgbench_build():
    query = "SELECT * FROM submission WHERE script LIKE ':-i%';"
    fetch_with_download(query)

def pgbench_select():
    query = "SELECT * FROM submission WHERE script = 'select';"
    fetch_with_download(query)

def builtin_query():
    option = st.radio(
        "Set to explore:",
        ["OSM", "pgbench Build Time", "pgbench SELECT"],
        captions=[
            "OSM",
            "Build time",
            "SELECT",
        ],
    )

    if option == "OSM":
        osm()
    elif option == "pgbench Build Time":
        pgbench_build()
    elif option == "pgbench SELECT":
        pgbench_select()

# Streamlit app
def main():
    st.title("PostgreSQL Benchmark Results Explorer")
    if production:
        builtin_query()
    else:
        custom_query()

if __name__ == "__main__":
    main()
