import os
import sys

import streamlit as st
import psycopg2
import pandas as pd
from configparser import ConfigParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from submission_studies import study_sql

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
            return result_df
        elif result_df is not None and result_df.empty:
            st.info("Query returned no results")
            return None

def osm():
    return fetch_with_download(study_sql("osm-leaderboard"))

def osm_network():
    return fetch_with_download(study_sql("osm-network"))

def osm_power():
    return fetch_with_download(study_sql("osm-power"))

def osm_checkpoint():
    fetch_with_download(study_sql("osm-checkpoint"))

def osm_dirty_mem():
    fetch_with_download(study_sql("osm-dirty-memory"))

def pgbench_build():
    df=fetch_with_download(study_sql("pgbench-build"))

    selection = st.dataframe(
        df,
        selection_mode=["single-row"],
        use_container_width=True)

    print(selection)

    if (False):
    # Process the selection
        if selection["selection"]:
            selected_indices = selection["selection"]["rows"]
            if selected_indices:
                st.write("Selected Rows:")
                # Use pandas .iloc[] to retrieve the actual row data
                selected_rows_df = df.iloc[selected_indices]
                st.dataframe(selected_rows_df)
            else:
                st.write("No rows selected.")

def pgbench_select():
    fetch_with_download(study_sql("pgbench-select"))

def draw_perf_watt(df):
    if df is None:
        st.info("Exiting draw_perf_watt, data frame undefined")
        return

    df=df.set_index('cpu')

    st.info("PostgreSQL Open Street Map Loading: CPU Speed vs. Power")
    st.info("Loading speed in kNodes/sec")
    st.bar_chart(horizontal=True,data=df,y=('nodes_kips'))
    st.info("CPU Maximum Watts")
    st.bar_chart(horizontal=True,data=df,y=('max_pkg'))
    st.info("Loading speed vs Power Consumption")
    st.scatter_chart(data=df,x='max_pkg',y='nodes_kips',color='cpu_c')

    return

def builtin_query():
    option = st.radio(
        "Set to explore:",
        ["OSM Power", "OSM Leaderboard", "OSM Network", "OSM Checkpoint", "OSM Dirty Memory", "pgbench Build Time", "pgbench SELECT"],
        captions=[
            "OSM Power Use Study",
            "OSM Leaderboard",
            "OSM Network Speed Study",
            "OSM Checkpoint Study",
            "OSM Dirty Memory Study",
            "Build time",
            "SELECT",
        ],
    )

    if option == "OSM Leaderboard":
        osm()
    elif option == "OSM Network":
        osm_network()
    elif option == "OSM Power":
        draw_perf_watt(osm_power())
    elif option == "OSM Dirty Memory":
        osm_dirty_mem()
    elif option == "OSM Checkpoint":
        osm_checkpoint()
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
