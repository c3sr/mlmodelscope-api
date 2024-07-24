import datetime
import json
from typing import Optional, List

class Migration:
    def __init__(self, migration: int, migrated_at: datetime.datetime):
        self.migration = migration
        self.migrated_at = migrated_at
    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=4, default=str)
    
class Experiment:
    def __init__(self, id: str, created_at: datetime.datetime, updated_at: datetime.datetime,
                 deleted_at: Optional[datetime.datetime], user_id: str):
        self.id = id
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at
        self.user_id = user_id
    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=4, default=str)
    def to_dict(self) -> dict:
        return self.__dict__
    
class TrialInput:
    def __init__(self, id: int, created_at: datetime.datetime, updated_at: datetime.datetime,
                 deleted_at: Optional[datetime.datetime], trial_id: str, url: str, user_id: str):
        self.id = id
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at
        self.trial_id = trial_id
        self.url = url
        self.user_id = user_id
    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=4, default=str)
    def to_dict(self) -> dict:
        return self.__dict__

class Trial:
    def __init__(self, id: str, created_at: datetime.datetime, updated_at: datetime.datetime,
                 deleted_at: Optional[datetime.datetime], model_id: int, completed_at: Optional[datetime.datetime],
                 result: str, experiment_id: str, source_trial_id: Optional[str]):
        self.id = id
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at
        self.model_id = model_id
        self.completed_at = completed_at
        self.result = result
        self.experiment_id = experiment_id
        self.source_trial_id = source_trial_id
    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=4, default=str)
    def to_dict(self) -> dict:
        return self.__dict__

class Architecture:
    def __init__(self, id: int, created_at: datetime.datetime, updated_at: datetime.datetime,
                 deleted_at: Optional[datetime.datetime], name: str, framework_id: int):
        self.id = id
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at
        self.name = name
        self.framework_id = framework_id
    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=4, default=str)
    def to_dict(self) -> dict:
        return self.__dict__

class Framework:
    def __init__(self, id: int, created_at: datetime.datetime, updated_at: datetime.datetime,
                 deleted_at: Optional[datetime.datetime], name: str, version: str):
        self.id = id
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at
        self.name = name
        self.version = version
    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=4, default=str)
    def to_dict(self) -> dict:
        return self.__dict__
    


class User:
    def __init__(self, id: str, created_at: datetime.datetime, updated_at: datetime.datetime,
                 deleted_at: Optional[datetime.datetime]):
        self.id = id
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at
    def to_json(self) -> str:
        #return as a json object
        # return 
        return json.dumps(self.__dict__, indent=4, default=str)
    def to_dict(self) -> dict:
        return self.__dict__


class Model:
    """
    Represents a machine learning model.

    Attributes:
        id (int): The ID of the model.
        created_at (datetime.datetime): The timestamp when the model was created.
        updated_at (datetime.datetime): The timestamp when the model was last updated.
        deleted_at (Optional[datetime.datetime]): The timestamp when the model was deleted (if applicable).
        attribute_top1 (Optional[str]): The top1 attribute of the model.
        attribute_top5 (Optional[str]): The top5 attribute of the model.
        attribute_kind (str): The kind attribute of the model.
        attribute_manifest_author (str): The manifest author attribute of the model.
        attribute_training_dataset (str): The training dataset attribute of the model.
        description (str): The description of the model.
        detail_graph_checksum (str): The checksum of the model's graph.
        detail_graph_path (str): The path to the model's graph.
        detail_weights_checksum (str): The checksum of the model's weights.
        detail_weights_path (str): The path to the model's weights.
        framework_id (Framework): The ID of the framework used by the model.
        input_description (str): The description of the model's input.
        input_type (str): The type of the model's input.
        license (str): The license of the model.
        name (str): The name of the model.
        output_description (str): The description of the model's output.
        output_type (str): The type of the model's output.
        version (str): The version of the model.
        short_description (str): The short description of the model.
        url_github (str): The GitHub URL of the model.
        url_citation (str): The citation URL of the model.
        url_link1 (str): The first additional URL of the model.
        url_link2 (str): The second additional URL of the model.
    """

    def __init__(self, id: int, created_at: datetime.datetime, updated_at: datetime.datetime,
                 deleted_at: Optional[datetime.datetime], attribute_top1: Optional[str], attribute_top5: Optional[str],
                 attribute_kind: str, attribute_manifest_author: str, attribute_training_dataset: str, description: str,
                 detail_graph_checksum: str, detail_graph_path: str, detail_weights_checksum: str, detail_weights_path: str,
                 framework_id: Framework, input_description: str, input_type: str, license: str, name: str,
                 output_description: str, output_type: str, version: str, short_description: str,
                 url_github: str, url_citation: str, url_link1: str, url_link2: str):
        self.id = id
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at
        self.attributes = {
            "Top1": attribute_top1,
            "Top5": attribute_top5,
            "kind": attribute_kind,
            "manifest_author": attribute_manifest_author,
            "training_dataset": attribute_training_dataset
        }
        self.description = description
        self.short_description = short_description
        self.model = {
            "graph_checksum": detail_graph_checksum,
            "graph_path": detail_graph_path,
            "weights_checksum": detail_weights_checksum,
            "weights_path": detail_weights_path
        }
        self.framework_id = framework_id
        self.input = {
            "description": input_description,
            "type": input_type
        }
        self.license = license
        self.name = name
        self.output = {
            "description": output_description,
            "type": output_type
        }
        self.url = {
            "github": url_github,
            "citation": url_citation,
            "link1": url_link1,
            "link2": url_link2
        }
        self.version = version

    def to_json(self) -> str:
        """
        Convert the model object to a JSON string.

        Returns:
            str: The JSON representation of the model object.
        """
        return json.dumps(self.__dict__, default=str)

    def to_dict(self) -> dict:
        """
        Convert the model object to a dictionary.

        Returns:
            dict: The dictionary representation of the model object.
        """
        return self.__dict__
