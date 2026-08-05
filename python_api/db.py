import psycopg2
import psycopg2.extras
import os
from datetime import datetime
import uuid
import json
import time

# get environment variables
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '15432')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASS = os.environ.get('DB_PASS', os.environ.get('DB_PASSWORD', ''))
DB_NAME = os.environ.get('DB_NAME', 'postgres')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
LOCAL_GPT2_MODEL_ID = 10000


def get_db_cur_con(cursor_factory=psycopg2.extras.RealDictCursor):
    conn = psycopg2.connect(DATABASE_URL)
    
    cur = conn.cursor(cursor_factory=cursor_factory)
    return cur, conn


def ensure_local_gpt2_model(cur, conn):
    cur.execute(
        "SELECT id FROM models WHERE LOWER(name) = %s AND output_type = %s",
        ("gpt_2", "text_to_text"),
    )
    model = cur.fetchone()
    if model:
        return model["id"]

    cur.execute("SELECT id FROM frameworks WHERE LOWER(name) = %s", ("pytorch",))
    framework = cur.fetchone()
    if not framework:
        raise ValueError("PyTorch framework metadata is required for local GPT-2.")

    cur.execute(
        """
        INSERT INTO models (
            id, created_at, updated_at, attribute_top1, attribute_top5,
            attribute_kind, attribute_manifest_author, attribute_training_dataset,
            description, detail_graph_checksum, detail_graph_path,
            detail_weights_checksum, detail_weights_path, framework_id,
            input_description, input_type, license, name, output_description,
            output_type, version, short_description, url_github, url_citation,
            url_link1, url_link2
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s
        )
        ON CONFLICT (id) DO NOTHING
        RETURNING id
        """,
        (
            LOCAL_GPT2_MODEL_ID,
            datetime.now(),
            datetime.now(),
            "",
            "",
            "Transformer",
            "OpenAI",
            "WebText",
            "PyTorch GPT-2 text generation model for local text-to-text experiments.",
            "",
            "huggingface:gpt2",
            "",
            "",
            framework["id"],
            "Input prompt text.",
            "TEXT",
            "MIT",
            "GPT_2",
            "Generated continuation text.",
            "text_to_text",
            "1.0",
            "GPT-2 is a transformer language model that generates a continuation from a text prompt.",
            "https://github.com/huggingface/transformers",
            "https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf",
            "https://huggingface.co/gpt2",
            "",
        ),
    )
    inserted = cur.fetchone()
    conn.commit()
    if inserted:
        return inserted["id"]

    cur.execute(
        "SELECT id FROM models WHERE id = %s",
        (LOCAL_GPT2_MODEL_ID,),
    )
    model = cur.fetchone()
    return model["id"] if model else None

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
    while True:
        try:
            # Fetch the latest max ID
            cur.execute("SELECT MAX(id) as id FROM trial_inputs")
            max_id = cur.fetchone()["id"]
            max_id = int(max_id) if max_id is not None else 0  # Handle NULL case
            
            # Attempt to insert with incremented ID
            cur.execute("""
                INSERT INTO trial_inputs (id, created_at, updated_at, trial_id, url)
                VALUES (%s, %s, %s, %s, %s)
            """, (max_id + 1, datetime.now(), datetime.now(), trial_id, json.dumps(inputs)))

            conn.commit()
            break  # Exit loop on success
     
        except Exception as e:
            print(f"Unexpected error: {e}")
            conn.rollback()  # Rollback in case of duplicate key violation
            time.sleep(0.1)  # Small delay before retrying to avoid excessive looping
            continue  # Retry fetching max_id and inserting again

def create_expriement( cur, conn):
    experiment_id= str(uuid.uuid4())
    cur.execute("INSERT INTO experiments (id,created_at,updated_at,user_id) VALUES (%s,%s,%s ,%s)", (experiment_id,   datetime.now(),   datetime.now(), 'anonymous'))
    conn.commit()
    return experiment_id


def _load_result(result):
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return None
    return result


def result_matches_explanation(result, explanation):
    result = _load_result(result)
    if not result or result.get("error"):
        return False
    if not explanation or not explanation.get("enabled"):
        return True

    stored = result.get("explanation") or {}
    return (
        stored.get("status") == "complete"
        and stored.get("schemaVersion") == "1.3"
        and stored.get("method") == explanation.get("method")
        and stored.get("topK") == explanation.get("topK")
    )


def get_trial_by_model_and_input(model_id, input_urls, explanation=None):
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

    query = f"""
        SELECT trials.id AS trial_id,
               trials.result
        FROM trials
        JOIN trial_inputs ON trials.id = trial_inputs.trial_id
        WHERE trials.completed_at IS NOT NULL
        AND trials.model_id = %s
        AND ({input_query})
        ORDER BY trials.completed_at DESC
    """
    cur = None
    conn = None
    try:
        cur, conn = get_db_cur_con()
        cur.execute(query, [model_id] + input_values)
        for trial in cur.fetchall():
            if result_matches_explanation(trial["result"], explanation):
                return trial["trial_id"]
        return None
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        return None
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
