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

def create_trial( model_id, experiment_id, cur, conn):
    trial_id= str(uuid.uuid4())
    cur.execute("INSERT INTO trials (id,model_id,created_at,updated_at ,experiment_id) VALUES (%s,%s,%s,%s, %s) RETURNING id", (trial_id,model_id,   datetime.now(),   datetime.now()  , experiment_id))
    conn.commit()
    return trial_id

def create_trial_inputs(trial_id, inputs, cur, conn):
    cur.execute("INSERT INTO trial_inputs (created_at,updated_at,trial_id, url) VALUES (%s,%s,%s, %s)", ( datetime.now(),   datetime.now(),trial_id, json.dumps(inputs)))
    conn.commit()

def create_expriement( cur, conn):
    experiment_id= str(uuid.uuid4())
    cur.execute("INSERT INTO experiments (id,created_at,updated_at,user_id) VALUES (%s,%s,%s ,%s)", (experiment_id,   datetime.now(),   datetime.now(), 'anonymous'))
    conn.commit()
    return experiment_id


def get_trial_by_model_and_input(model_id, input_url):

    input_query = """
            SELECT trial_id
            FROM trial_inputs
            WHERE url = %s
        """

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
        AND trials.id  IN ({input_query})
    """

    # Execute the query
    cur,conn=get_db_cur_con()
    cur.execute(query, ( model_id,input_url))

    # Fetch the result
    trial = cur.fetchone()

    if trial is None:
        return None
    
    print(trial['experiment_id'], trial['trial_id'])
    return (trial['experiment_id'], trial['trial_id'],trial["completed_at"]) 



