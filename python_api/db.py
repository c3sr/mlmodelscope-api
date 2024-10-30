import psycopg2
import psycopg2.extras
import os
from datetime import datetime
import uuid
import json
# get environment variables
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_USER = os.environ.get('DB_USER', 'user')
DB_PASS = os.environ.get('DB_PASS', 'password')
DB_NAME = os.environ.get('DB_NAME', 'db')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
def get_db_cur_con(cursor_factory=psycopg2.extras.RealDictCursor):
    conn = psycopg2.connect(DATABASE_URL)
    
    cur = conn.cursor(cursor_factory=cursor_factory)
    return cur, conn

def get_model_by_id(model_id, cur, conn):
        cur.execute("SELECT name, version, framework_id FROM models WHERE id = %s", (model_id,))
        model = cur.fetchone()
        return model
def get_framework_by_id(framework_id, cur, conn):
        cur.execute("SELECT name, version FROM frameworks WHERE id = %s", (framework_id,))
        framework = cur.fetchone()
        return framework
def close_db_cur_con(cur, conn):
    cur.close()
    conn.close()

def create_trial( model_id, experiment_id, cur, conn,source_id="",completed_at=None):
    trial_id= str(uuid.uuid4())
    if source_id!="":
        cur.execute("INSERT INTO trials (id,model_id,created_at,updated_at,completed_at,experiment_id,source_trial_id) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", (trial_id,model_id,   datetime.now(),   datetime.now()  ,datetime.now()  , experiment_id,source_id))
    else:
        cur.execute("INSERT INTO trials (id,model_id,created_at,updated_at,experiment_id) VALUES (%s,%s,%s,%s,%s) RETURNING id", (trial_id, model_id,   datetime.now(),   datetime.now() , experiment_id))
    conn.commit()
    return trial_id

def create_trial_inputs(trial_id, inputs, cur, conn):
    cur.execute("SELECT MAX(id) as id FROM trial_inputs")
    try:
        max_id = int(cur.fetchone()["id"])
    except:
        max_id = 0
    cur.execute("INSERT INTO trial_inputs (id,created_at,updated_at,trial_id, url) VALUES (%s,%s,%s,%s, %s)", (max_id+1, datetime.now(),   datetime.now(),trial_id, json.dumps(inputs)))
    conn.commit()

def create_expriement( cur, conn):
    experiment_id= str(uuid.uuid4())
    cur.execute("INSERT INTO experiments (id,created_at,updated_at,user_id) VALUES (%s,%s,%s ,%s)", (experiment_id,   datetime.now(),   datetime.now(), 'anonymous'))
    conn.commit()
    return experiment_id


def get_trial_by_model_and_input(model_id, input_urls):
    # Check if input_urls is a list of json objects with src and inputType keys
    if not all(isinstance(item, dict) and 'src' in item and 'inputType' in item for item in input_urls):
        raise ValueError("Each input_url must be a JSON object with 'src' and 'inputType' keys")

    # Construct the input_query based on the number of input_urls
    if len(input_urls) == 1:
        input_url = input_urls[0]["src"]
        input_query = "url LIKE %s"
        input_values = [f"%{input_url}%"]
    elif len(input_urls) == 2:
        input_url_1 = input_urls[0]["src"]
        input_url_2 = input_urls[1]["src"]
        input_query = "url LIKE %s OR url LIKE %s"
        input_values = [f"%{input_url_1}%", f"%{input_url_2}%"]
    else:
        return None

    # Main query to get trial details
    query = f"""
        SELECT trials.*, 
               experiments.*, 
               models.*, 
               trial_inputs.*
        FROM trials
        JOIN experiments ON trials.experiment_id = experiments.id
        JOIN models ON trials.model_id = models.id
        JOIN trial_inputs ON trials.id = trial_inputs.trial_id
        WHERE trials.results IS NOT NULL
        AND trials.model_id = %s
        AND ({input_query})
    """
    
    print(f"Debug: SQL Query: {query}")
    print(f"Debug: Input Values: {input_values}")



    # Main query to get trial details
    query = f"""
        SELECT trials.*, 
               experiments.*, 
               models.*, 
               trial_inputs.*
        FROM trials
        JOIN experiments ON trials.experiment_id = experiments.id
        JOIN models ON trials.model_id = models.id
        JOIN trial_inputs ON trials.id = trial_inputs.trial_id
        WHERE trials.completed_at IS NOT NULL
        AND trials.model_id = %s
        AND ({input_query})
    """
    debug_query = query % tuple([model_id] + input_values)
    print(f"Debug: SQL Query: {debug_query}")
    # Execute the query
    try:
        # Replace with your database connection setup
        cur, conn = get_db_cur_con()
        cur.execute(query, [model_id] + input_values)

        # Fetch the result
        trial = cur.fetchone()

        if trial is None:
            print("Debug: No trial found")
            return None
        
        # Fetch column names for reference
        colnames = [desc[0] for desc in cur.description]
        # print(f"Debug: Columns: {colnames}")
        # print(f"Debug: Trial Data: {trial}")

        # Assuming the columns are returned in the order you expect
        # You may need to adjust this depending on your database schema
        return (trial['trial_id'])


    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        return None
   