
from fastapi import FastAPI, Depends, HTTPException, Query,Request
from typing import List, Optional
import psycopg2
import psycopg2.extras
import os
# from pydantic import BaseModel
import uvicorn
import json
import pika
import os
from db import *
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uuid
from mq import *
import logging

from typing import Optional
from  schema_mlmodelscope import *
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
logging.basicConfig(level=logging.INFO)
#enable cors
@app.middleware("http")
async def add_cors_header(request, call_next):
    response = await call_next(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

    # enable cors
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logging.error(f"An error occurred: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "An internal server error occurred."},
    )

# route /models
@app.get("/models")
async def get_models(
    framework_id: Optional[int] = Query(None),
    task: Optional[str] = Query(None),
    architecture: Optional[str] = Query(None),
    query: Optional[str] = Query(None)
):
    # cur
    # cur = db.cur(cur_factory=psycopg2.extras.Dictcur)
    cur,conn=get_db_cur_con()
    sql_query = """
    SELECT models.*, frameworks.name as framework_name, frameworks.version as framework_version, array_agg(architectures.name) as architectures
    FROM models
    JOIN frameworks ON frameworks.id = models.framework_id
    LEFT JOIN architectures ON architectures.framework_id = frameworks.id
    WHERE 1=1
    """

    params = {}

    if framework_id:
        sql_query += " AND models.framework_id = %(framework_id)s"
        params['framework_id'] = framework_id

    if task:
        sql_query += " AND models.output_type = %(task)s"
        params['task'] = task

    if architecture:
        sql_query += " AND architectures.name = %(architecture)s"
        params['architecture'] = architecture

    if query:
        wildcard = f"%{query.lower()}%"
        sql_query += " AND (LOWER(models.name) LIKE %(wildcard)s OR LOWER(models.description) LIKE %(wildcard)s)"
        params['wildcard'] = wildcard

    sql_query += " GROUP BY models.id, frameworks.name, frameworks.version"

    cur.execute(sql_query, params)
    rows = cur.fetchall()

    models = []
    for row_dict in rows:

        model = {
            "id": row_dict["id"],
            "created_at": row_dict["created_at"].isoformat(),
            "updated_at": row_dict["updated_at"].isoformat(),
            "attributes": {
                "Top1": row_dict["attribute_top1"],
                "Top5": row_dict["attribute_top5"],
                "kind": row_dict["attribute_kind"],
                "manifest_author": row_dict["attribute_manifest_author"],
                "training_dataset": row_dict["attribute_training_dataset"]
            },
            "description": row_dict["description"],
            "short_description": row_dict["short_description"],
            "model": {
                "graph_checksum": row_dict["detail_graph_checksum"],
                "graph_path": row_dict["detail_graph_path"],
                "weights_checksum": row_dict["detail_weights_checksum"],
                "weights_path": row_dict["detail_weights_path"]
            },
            "framework": {
                "id": row_dict["framework_id"],
                "name": row_dict["framework_name"],
                "version": row_dict["framework_version"],
                "architectures": [{"name": arch} for arch in row_dict["architectures"]]
            },
            "input": {
                "description": row_dict["input_description"],
                "type": row_dict["input_type"]
            },
            "license": row_dict["license"],
            "name": row_dict["name"],
            "output": {
                "description": row_dict["output_description"],
                "type": row_dict["output_type"]
            },
            "url": {
                "github": row_dict["url_github"],
                "citation": row_dict["url_citation"],
                "link1": row_dict["url_link1"],
                "link2": row_dict["url_link2"]
            },
            "version": row_dict["version"]
        }
        models.append(model)

    cur.close()

    return {"models": [dict(model) for model in models]}
    # return models
@app.get("/models/{model_id}")
async def get_model(model_id: int):
    cur,conn=get_db_cur_con()
    # get all models from the database as json
    query=""" SELECT models.*, frameworks.name as framework_name, frameworks.version as framework_version, array_agg(architectures.name) as architectures
    FROM models
    JOIN frameworks ON frameworks.id = models.framework_id
    LEFT JOIN architectures ON architectures.framework_id = frameworks.id WHERE models.id = %s GROUP BY models.id, frameworks.name, frameworks.version"""
    # cur.execute(f"SELECT * FROM models WHERE id={model_id} AND deleted_at IS NULL")
    cur.execute(query, (model_id,))
    row_dict = cur.fetchone()

    model = {
        "id": row_dict["id"],
        "created_at": row_dict["created_at"].isoformat(),
        "updated_at": row_dict["updated_at"].isoformat(),
        "attributes": {
            "Top1": row_dict["attribute_top1"],
            "Top5": row_dict["attribute_top5"],
            "kind": row_dict["attribute_kind"],
            "manifest_author": row_dict["attribute_manifest_author"],
            "training_dataset": row_dict["attribute_training_dataset"]
        },
        "description": row_dict["description"],
        "short_description": row_dict["short_description"],
        "model": {
            "graph_checksum": row_dict["detail_graph_checksum"],
            "graph_path": row_dict["detail_graph_path"],
            "weights_checksum": row_dict["detail_weights_checksum"],
            "weights_path": row_dict["detail_weights_path"]
        },
        "framework": {
            "id": row_dict["framework_id"],
            "name": row_dict["framework_name"],
            "version": row_dict["framework_version"],
            "architectures": [{"name": arch} for arch in row_dict["architectures"]]
        },
        "input": {
            "description": row_dict["input_description"],
            "type": row_dict["input_type"]
        },
        "license": row_dict["license"],
        "name": row_dict["name"],
        "output": {
            "description": row_dict["output_description"],
            "type": row_dict["output_type"]
        },
        "url": {
            "github": row_dict["url_github"],
            "citation": row_dict["url_citation"],
            "link1": row_dict["url_link1"],
            "link2": row_dict["url_link2"]
        },
        "version": row_dict["version"]
    }
    cur.close()
    return{"models": [model]}

@app.get("/frameworks")
async def get_frameworks():
    cur,conn=get_db_cur_con()

    cur.execute("""
            SELECT f.id as framework_id, f.name as framework_name, f.version,
                   a.name as architecture_name
            FROM frameworks f
            LEFT JOIN architectures a ON a.framework_id = f.id
        """)
    rows = cur.fetchall()
    cur.close()

    frameworks_dict = {}
    for row in rows:
        framework_id = row["framework_id"]
        if framework_id not in frameworks_dict:
            frameworks_dict[framework_id] = {
                'id': framework_id,
                'name': row["framework_name"],
                'version': row["version"],
                'architectures': []
            }
        if row["architecture_name"] is not None:
            frameworks_dict[framework_id]['architectures'].append({
                'name': row["architecture_name"]
            })

    return {"frameworks":[framework for framework in frameworks_dict.values()]}


@app.get("/frameworks/{framework_id}")
async def get_framework(framework_id: int):
    # get all models from the database as json
    cur,conn=get_db_cur_con()
    cur.execute(f"SELECT * FROM frameworks WHERE id={framework_id}")
    framework = cur.fetchone()
    # print(model)
    json_framework = Framework(*framework).to_dict()
    return{"framework": json_framework}
    cur.close()
    # return models

@app.get("/")
async def version():
    return {"version": "0.1.0"}


@app.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    cur,conn=get_db_cur_con()
    cur.execute("""
                SELECT e.id AS experiment_id,
                       t.id AS trial_id,
                       t.created_at,
                       t.completed_at,
                       t.source_trial_id
                FROM experiments e
                JOIN trials t ON e.id = t.experiment_id
                WHERE e.id = %s
            """, (experiment_id,))

            # Fetch all results
    rows = cur.fetchall()
    print(rows)
    if not rows:
        raise Exception(f"No experiment found with ID {experiment_id}")

    # Prepare the response structure
    result = {
        "id": rows[0]['experiment_id'],
        "trials": [],
        "user_id": "anonymous"
    }

    for row in rows:
        trial = {
            "id": row['trial_id'],
            "created_at": row['created_at'],
            "completed_at": row['completed_at'],
            "source_trial": row['source_trial_id']
        }
        result["trials"].append(trial)
    return result

@app.options("/predict")
async def options_predict():
    return JSONResponse(
        content={},
        headers={
            "Allow": "OPTIONS, POST",
            "Access-Control-Allow-Methods": "OPTIONS, POST",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )



class PredictRequest(BaseModel):
    architecture: str
    batchSize: int
    desiredResultModality: str
    gpu: bool
    inputs: Optional[List[dict]] = Field(default=None)
    # input_url: Optional[str] = Field(default=None)
    context: Optional[List[str]] = Field(default=[])
    model: int
    traceLevel: str
    config : Optional[dict] = Field(default={})
    experiment : Optional[str] = Field(default=None)

@app.post("/predict")
async def predict(request: PredictRequest):
    #get the request body

    # data = request.get_json()
    # print(data)
    # print(request)

    architecture = request.architecture
    batch_size = request.batchSize
    desired_result_modality = request.desiredResultModality
    gpu = request.gpu
    inputs = request.inputs
    # input_url = request.input_url
    model_id = request.model
    trace_level = request.traceLevel
    context = request.context
    # if input_url and not inputs:
    #     inputs=[input_url]
    has_multi_input=False
    if inputs and len(inputs)>1:
        has_multi_input=True
    config = request.config
    # print(inputs[0])
    
    experiment_id=request.experiment
    # print(experiment_id)
   
     
    # experiment_id=create_expriement( cur, conn)

    trial= get_trial_by_model_and_input( model_id, inputs)
    # print(trial)
    if not experiment_id:
        cur,conn=get_db_cur_con()
        experiment_id=create_expriement(cur, conn)


    # print(trail)
    # if trail[2]
    # print("trial")
    if trial: #existing trial
        # print(trail[2])
        
        cur,conn=get_db_cur_con()
        source_trial = trial
        
        model=get_model_by_id(model_id,cur,conn)
        new_trial_id=create_trial( model_id, experiment_id, cur, conn,source_trial)
        # if not experiment_id:
        #     experiment_id=create_expriement(cur, conn)

        return {"experimentId": experiment_id, "trialId": new_trial_id, "model_id": model["name"], "input_url": inputs}
    else:
        cur,conn=get_db_cur_con()

        # create a new trial and generate a new uuid experiment
        # cur,conn=get_db_cur_con()
        

        

        trial_id=create_trial( model_id, experiment_id, cur, conn)
        create_trial_inputs(trial_id, inputs, cur, conn)
        # print(trial_id)


        model=get_model_by_id(model_id,cur,conn)
        framework = get_framework_by_id(model['framework_id'],cur,conn)


        context={}
        queue_name=f"agent-{framework['name']}-amd64".lower()

        

        message= makePredictMessage(architecture, batch_size, desired_result_modality, gpu, inputs,has_multi_input,context,config, model["name"], trace_level, 0, "localhost:6831")

        sendPredictMessage(message,queue_name,trial_id)
        return {"experimentId": experiment_id, "trialId": trial_id, "model_id": model["name"],"input_url": inputs}



    # print(trail)
    

@app.delete("/trial/{trial_id}")
async def delete_trial(trial_id: str):
    pass

@app.get("/trial/{trial_id}")
async def get_trial(trial_id: str):
    cur,conn=get_db_cur_con()

    # check if trial has a source trial 
    cur.execute("""
            SELECT * FROM trials t
            WHERE t.id = %s
        """, (trial_id,))
    row = cur.fetchone()
    if row["source_trial_id"] is not None:
        # print("\n\n\n\n\n\n\n\n\n\n")
        # print(row["source_trial_id"])
        source_trial= await get_trial(row["source_trial_id"])
        return source_trial
    print(row)
    # else
                
    cur.close()
    cur,conn=get_db_cur_con()

    
    cur.execute("""
            SELECT t.id AS trial_id,
                t.result,
                t.source_trial_id as source_trial_id,
                    t.completed_at,
                    ti.url AS input_url,
                    m.id AS modelId,
                    m.created_at AS model_created_at,

                    m.updated_at AS model_updated_at,
                    m.attribute_top1 AS top1,
                    m.attribute_top5 AS top5,
                    m.attribute_kind AS kind,
                    m.attribute_manifest_author AS manifest_author,
                    m.attribute_training_dataset AS training_dataset,
                    m.description,
                    m.short_description,
                m.detail_graph_checksum AS graph_checksum,
                m.detail_graph_path AS graph_path,
                m.detail_weights_checksum AS weights_checksum,
                m.detail_weights_path AS weights_path,
                f.id AS framework_id,
                    f.name AS framework_name,
                    f.version AS framework_version,
                    m.input_description,
                    m.input_type,
                    m.license,
                    m.name AS model_name,
                    m.output_description,
                    m.output_type,
                    m.url_github,
                    m.url_citation,
                    m.url_link1,
                    m.url_link2,
                    a.name AS architecture_name
            FROM trials t
            JOIN trial_inputs ti ON t.id = ti.trial_id
            
            JOIN models m ON t.model_id = m.id
            JOIN frameworks f ON m.framework_id = f.id
            LEFT JOIN architectures a ON a.framework_id = f.id
            WHERE t.id = %s
        """, (trial_id,))

        # Fetch the result
    row = cur.fetchone()

    if not row:
        raise Exception(f"No trial found with ID {trial_id}")
        # return None
    print(row) 
    
    if row["source_trial_id"] is not None:
        # print("\n\n\n\n\n\n\n\n\n\n")
        # print(row["source_trial_id"])
        
        return get_trial(row["source_trial_id"])
    # print(row)
    # Prepare the response structure
    result = {
        "id": row['trial_id'],
        "inputs": json.loads(row['input_url']),
        "completed_at": row['completed_at'],
        "results": 

            json.loads(row["result"]) if row["result"] is not None else None
            
                
        ,
        "model": {
            "id": row['modelid'],
            "created_at": row['model_created_at'],
            "updated_at": row['model_updated_at'],
            "attributes": {
                "Top1": row['top1'],
                "Top5": row['top5'],
                "kind": row['kind'],
                "manifest_author": row['manifest_author'],
                "training_dataset": row['training_dataset']
            },
            "description": row['description'],
            "short_description": row['short_description'],
            "model": {
                "graph_checksum": row['graph_checksum'],
                "graph_path": row['graph_path'],
                "weights_checksum": row['weights_checksum'],
                "weights_path": row['weights_path']
            },
            "framework": {
                "id": row['framework_id'],
                "name": row['framework_name'],
                "version": row['framework_version'],
                "architectures": [
                    {
                        "name": row['architecture_name']
                    }
                ]
            },
            "input": {
                "description": row['input_description'],
                "type": row['input_type']
            },
            "license": row['license'],
            "name": row['model_name'],
            "output": {
                "description": row['output_description'],
                "type": row['output_type']
            },
            "url": {
                "github": row['url_github'],
                "citation": row['url_citation'],
                "link1": row['url_link1'],
                "link2": row['url_link2']
            },
            "version": "1.0"  # Assuming version is always 1.0 for this example
        }
    }

    return result







