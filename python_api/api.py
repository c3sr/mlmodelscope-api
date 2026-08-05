
from fastapi import FastAPI, Depends, HTTPException, Query, Request, UploadFile, File
from typing import List, Literal, Optional
from time import perf_counter
import psycopg2
import psycopg2.extras
import os
import mimetypes
import re
import shutil
# from pydantic import BaseModel
import uvicorn
import json
import pika
import os
from db import *
from pathlib import Path
from fastapi.responses import JSONResponse, FileResponse
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
logger = logging.getLogger("mlmodelscope.api")

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/tmp/mlmodelscope_uploads"))
UPLOAD_URL_BASE = os.environ.get("UPLOAD_URL_BASE", "").rstrip("/")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://local.mlmodelscope.org",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_request(request: Request, call_next):
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "%s %s failed",
            request.method,
            request.url.path,
        )
        raise

    if request.url.path != "/health":
        logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started_at) * 1000,
        )
    return response

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
    try:
        ensure_local_gpt2_model(cur, conn)
    except Exception as e:
        logger.warning("Unable to ensure local GPT-2 model metadata: %s", e)
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

    try:
        cur.execute(sql_query, params)
        rows = cur.fetchall()
    except Exception as e:
        logging.error(f"An error occurred: {e} while executing query: {sql_query} in function get_models")
        return JSONResponse(
            status_code=500,
            content={"message": "An internal server error occurred."},
        )
    # cur.execute(sql_query, params)
    # rows = cur.fetchall()

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
    try:
        cur.execute(query, (model_id,))
        row_dict = cur.fetchone()
    except Exception as e:
        logging.error(f"An error occurred: {e} while executing query: {query} in function get_model")
        return JSONResponse(
            status_code=500,
            content={"message": "An internal server error occurred."},
        )

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

    query = """ SELECT f.id as framework_id, f.name as framework_name, f.version,
                   a.name as architecture_name
            FROM frameworks f
            LEFT JOIN architectures a ON a.framework_id = f.id
    """
    try:
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
    except Exception as e:
        logging.error(f"An error occurred: {e} while executing query: {query} in function get_frameworks")
        return JSONResponse(
            status_code=500,
            content={"message": "An internal server error occurred."},
        )

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
    try:
        cur.execute(f"SELECT * FROM frameworks WHERE id={framework_id}")
        framework = cur.fetchone()
    except Exception as e:
        logging.error(f"An error occurred: {e} while executing query: {query} in function get_framework")
        return JSONResponse(
            status_code=500,
            content={"message": "An internal server error occurred."},
        )
    # print(model)
    json_framework = Framework(*framework).to_dict()
    return{"framework": json_framework}
    cur.close()
    # return models

@app.get("/")
async def version():
    return {"version": "0.1.0"}

@app.get("/health")
async def health():
    return {"status": "ok"}


def safe_upload_name(filename: Optional[str]) -> str:
    name = Path(filename or "upload").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name or "upload"


def upload_public_url(request: Request, upload_id: str) -> str:
    base_url = UPLOAD_URL_BASE or str(request.base_url).rstrip("/")
    return f"{base_url}/uploads/{upload_id}"


@app.post("/uploads")
async def upload_input_file(request: Request, file: UploadFile = File(...)):
    original_name = safe_upload_name(file.filename)
    extension = Path(original_name).suffix
    upload_id = f"{uuid.uuid4().hex}{extension}"
    upload_path = UPLOAD_DIR / upload_id

    try:
        with upload_path.open("wb") as output_file:
            shutil.copyfileobj(file.file, output_file)
    except Exception:
        logger.exception("Failed to store uploaded file %s", original_name)
        raise HTTPException(status_code=500, detail="Failed to store uploaded file.")
    finally:
        await file.close()

    content_type = (
        file.content_type
        or mimetypes.guess_type(original_name)[0]
        or "application/octet-stream"
    )
    return {
        "url": upload_public_url(request, upload_id),
        "filename": original_name,
        "contentType": content_type,
    }


@app.get("/uploads/{upload_id}")
async def get_uploaded_input(upload_id: str):
    safe_id = safe_upload_name(upload_id)
    if safe_id != upload_id:
        raise HTTPException(status_code=404, detail="Uploaded file not found.")

    upload_path = UPLOAD_DIR / safe_id
    if not upload_path.exists() or not upload_path.is_file():
        raise HTTPException(status_code=404, detail="Uploaded file not found.")

    media_type = mimetypes.guess_type(safe_id)[0] or "application/octet-stream"
    return FileResponse(upload_path, media_type=media_type)


@app.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    query = """
                SELECT e.id AS experiment_id,
                       t.id AS trial_id,
                       t.created_at,
                       t.completed_at,
                       t.source_trial_id
                FROM experiments e
                JOIN trials t ON e.id = t.experiment_id
                WHERE e.id = %s
            """
    cur,conn=get_db_cur_con()
    try:
        cur.execute(query, (experiment_id,))

                # Fetch all results
        rows = cur.fetchall()
    except Exception as e:
        logging.error(f"An error occurred: {e} while executing query: {query} in function get_experiment")
        return JSONResponse(
            status_code=500,
            content={"message": "An internal server error occurred."},
        )
    if not rows:
        #raise Exception(f"No experiment found with ID {experiment_id}") # this crashes the whole program
        return JSONResponse(
            status_code=404,
            content={"message": f"No experiment found with ID {experiment_id}"},
        )

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



class ExplanationRequest(BaseModel):
    enabled: bool = False
    method: Literal["grad_cam", "token_probability"] = "grad_cam"
    topK: int = Field(default=2, ge=2, le=10)
    userLevel: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    detailLevel: Optional[Literal["concise", "standard", "detailed"]] = None
    terminology: Optional[Literal["plain", "balanced", "technical"]] = None
    evidenceView: Optional[Literal["focus", "intensity", "both"]] = None
    includePipeline: Optional[bool] = None
    includeTechnicalDetails: Optional[bool] = None
    includeLimitations: Optional[bool] = None


EXPLANATION_PROFILE_DEFAULTS = {
    "beginner": {
        "detailLevel": "concise",
        "terminology": "plain",
        "evidenceView": "focus",
        "includePipeline": True,
        "includeTechnicalDetails": False,
        "includeLimitations": True,
    },
    "intermediate": {
        "detailLevel": "standard",
        "terminology": "balanced",
        "evidenceView": "both",
        "includePipeline": True,
        "includeTechnicalDetails": True,
        "includeLimitations": True,
    },
    "advanced": {
        "detailLevel": "detailed",
        "terminology": "technical",
        "evidenceView": "both",
        "includePipeline": True,
        "includeTechnicalDetails": True,
        "includeLimitations": True,
    },
}


def normalize_explanation_settings(explanation_request):
    explanation = (
        explanation_request.model_dump()
        if hasattr(explanation_request, "model_dump")
        else explanation_request.dict()
    )
    user_level = explanation.get("userLevel", "intermediate")
    profile = EXPLANATION_PROFILE_DEFAULTS[user_level]

    audience = {"userLevel": user_level}
    for key, default_value in profile.items():
        audience[key] = (
            explanation[key]
            if explanation.get(key) is not None
            else default_value
        )

    return {
        "enabled": explanation["enabled"],
        "method": explanation["method"],
        "topK": explanation["topK"],
        "audience": audience,
    }


@app.get("/explanation/profiles")
async def get_explanation_profiles():
    return {
        "levels": [
            {
                "userLevel": "beginner",
                "description": "Plain-language explanation with the main evidence view first.",
                "defaults": EXPLANATION_PROFILE_DEFAULTS["beginner"],
            },
            {
                "userLevel": "intermediate",
                "description": "Balanced explanation with pipeline context and technical terms introduced carefully.",
                "defaults": EXPLANATION_PROFILE_DEFAULTS["intermediate"],
            },
            {
                "userLevel": "advanced",
                "description": "Technical explanation retaining raw logits, method details, and limitations.",
                "defaults": EXPLANATION_PROFILE_DEFAULTS["advanced"],
            },
        ],
        "supportedMethods": ["grad_cam", "token_probability"],
    }


class PredictRequest(BaseModel):
    architecture: str
    batchSize: int
    desiredResultModality: str
    gpu: bool
    inputs: Optional[List[dict]] = Field(default=None)
    # input_url: Optional[str] = Field(default=None)
    context: Optional[List[str]] = Field(default_factory=list)
    model: int
    traceLevel: str
    config : Optional[dict] = Field(default_factory=dict)
    experiment : Optional[str] = Field(default=None)
    explanation: ExplanationRequest = Field(default_factory=ExplanationRequest)

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
    explanation = normalize_explanation_settings(request.explanation)
    if explanation["enabled"]:
        if explanation["method"] == "grad_cam" and desired_result_modality != "image_classification":
            raise HTTPException(
                status_code=422,
                detail="Grad-CAM explanations support image classification only.",
            )
        if explanation["method"] == "grad_cam" and explanation["topK"] != 2:
            raise HTTPException(
                status_code=422,
                detail="Grad-CAM explanations support topK 2 only.",
            )
        if explanation["method"] == "token_probability" and desired_result_modality != "text_to_text":
            raise HTTPException(
                status_code=422,
                detail="Token probability explanations support text-to-text generation only.",
            )
        if desired_result_modality == "image_classification" and explanation["method"] != "grad_cam":
            raise HTTPException(
                status_code=422,
                detail="Image classification explanations require method grad_cam.",
            )
        if desired_result_modality == "text_to_text" and explanation["method"] != "token_probability":
            raise HTTPException(
                status_code=422,
                detail="Text-to-text explanations require method token_probability.",
            )
        if batch_size != 1 or not inputs or len(inputs) != 1:
            raise HTTPException(
                status_code=422,
                detail="Explanations require exactly one input and batch size one.",
            )
    # print(inputs[0])
    
    experiment_id=request.experiment
    # print(experiment_id)
   
     
    # experiment_id=create_expriement( cur, conn)

    if desired_result_modality == "text_to_text":
        cur, conn = get_db_cur_con()
        try:
            ensure_local_gpt2_model(cur, conn)
        finally:
            close_db_cur_con(cur, conn)

    trial= get_trial_by_model_and_input(model_id, inputs, explanation)
    print("-"*20,experiment_id,"-"*20)
    if not experiment_id:
        print("+"*20,"ENTERED IF","+"*20)
        cur,conn=get_db_cur_con()
        experiment_id=create_expriement(cur, conn)
        close_db_cur_con(cur, conn)
        print("+"*20,"ENTERED IF", experiment_id,"+"*20)


    # print(trail)
    # if trail[2]
    # print("trial")
    if trial: #existing trial
        # print(trail[2])
        
        cur,conn=get_db_cur_con()
        source_trial = trial
        
        model=get_model_by_id(model_id,cur,conn)
        new_trial_id=create_trial( model_id, experiment_id, cur, conn,source_trial)
        close_db_cur_con(cur, conn)
        # if not experiment_id:
        #     experiment_id=create_expriement(cur, conn)
        print("*"*20,"RETURNING IF TRIAL", experiment_id,"*"*20)
        return {"experimentId": experiment_id, "trialId": new_trial_id, "model_id": model["name"], "input_url": inputs, "explanation": explanation if explanation["enabled"] else None}
    else:
        cur,conn=get_db_cur_con()

        # create a new trial and generate a new uuid experiment
        # cur,conn=get_db_cur_con()
        

        

        trial_id=create_trial( model_id, experiment_id, cur, conn)
        create_trial_inputs(trial_id, inputs, cur, conn)
        # print(trial_id)


        model=get_model_by_id(model_id,cur,conn)
        framework = get_framework_by_id(model['framework_id'],cur,conn)
        close_db_cur_con(cur, conn)


        context={}
        queue_name=f"agent-{framework['name']}-amd64".lower()

        

        message= makePredictMessage(
            architecture,
            batch_size,
            desired_result_modality,
            gpu,
            inputs,
            has_multi_input,
            context,
            config,
            model["name"],
            trace_level,
            0,
            "localhost:6831",
            explanation if explanation["enabled"] else None,
        )

        sendPredictMessage(message,queue_name,trial_id)
        print("*"*20,"RETURNING ELSE TRIAL", experiment_id,"*"*20)
        return {"experimentId": experiment_id, "trialId": trial_id, "model_id": model["name"],"input_url": inputs, "explanation": explanation if explanation["enabled"] else None}



    # print(trail)
    

@app.delete("/trial/{trial_id}")
async def delete_trial(trial_id: str):
    pass

@app.get("/trial/{trial_id}/status")
async def get_trial_status(trial_id: str):
    query = """
        SELECT requested.id,
               COALESCE(source.completed_at, requested.completed_at) AS completed_at,
               COALESCE(source.result, requested.result) AS result
        FROM trials requested
        LEFT JOIN trials source ON source.id = requested.source_trial_id
        WHERE requested.id = %s
    """
    cur, conn = get_db_cur_con()
    try:
        cur.execute(query, (trial_id,))
        row = cur.fetchone()
    except Exception as e:
        logging.error(
            f"An error occurred: {e} while executing query in get_trial_status"
        )
        return JSONResponse(
            status_code=500,
            content={"message": "An internal server error occurred."},
        )
    finally:
        cur.close()
        conn.close()

    if not row:
        return JSONResponse(
            status_code=404,
            content={"message": f"No trial found with ID {trial_id}"},
        )

    result = row["result"]
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            result = None
    status = "pending"
    if row["completed_at"]:
        status = "failed" if (result or {}).get("error") else "completed"

    return {
        "id": row["id"],
        "completed_at": row["completed_at"],
        "status": status,
    }

@app.get("/trial/{trial_id}")
async def get_trial(trial_id: str):
    cur,conn=get_db_cur_con()
    query="""
                SELECT * FROM trials t
                WHERE t.id = %s
            """
    # check if trial has a source trial 
    try:
        cur.execute(query, (trial_id,))
        row = cur.fetchone()
    except Exception as e:
        logging.error(f"An error occurred: {e} while executing query: {query} in function get_trial")
        return JSONResponse(
            status_code=500,
            content={"message": "An internal server error occurred."},
        )
    if row["source_trial_id"] is not None:
        # print("\n\n\n\n\n\n\n\n\n\n")
        # print(row["source_trial_id"])
        source_trial= await get_trial(row["source_trial_id"])
        return source_trial
    print(row)
    # else
                
    cur.close()
    cur,conn=get_db_cur_con()
    query = """
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
            """
    try:
        cur.execute(query, (trial_id,))

            # Fetch the result
        row = cur.fetchone()
    except Exception as e:
        logging.error(f"An error occurred: {e} while executing query: {query} in function get_trial")
        return JSONResponse(
            status_code=500,
            content={"message": "An internal server error occurred."},
        ) 

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
