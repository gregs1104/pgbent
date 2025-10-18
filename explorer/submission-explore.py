import streamlit as st
import psycopg2
import pandas as pd
from configparser import ConfigParser

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
        # For this example, using direct connection parameters
        # In production, use load_config() to load from a config file
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
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except (Exception, psycopg2.DatabaseError) as error:
            st.error(f"Error executing query: {error}")
            conn.close()
            return None
    return None

# Streamlit app
def main():
    st.title("PostgreSQL Benchmark Results Explorer")
    
    # Sample query - can be replaced with user input
    default_query = "SELECT * FROM submission;"
    
    # Allow user to input custom SQL query
    query = st.text_area("Enter SQL Query:", default_query, height=150)
    
    if st.button("Run Query"):
        with st.spinner('Fetching data...'):
            # Run the query
            result_df = run_query(query)
            
            if result_df is not None and not result_df.empty:
                # Display results
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

if __name__ == "__main__":
    main()
