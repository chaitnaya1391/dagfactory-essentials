"""Module contains code for generating tasks and constructing a DAG"""
from datetime import datetime
from typing import Any, Callable, Dict, List, Union

from airflow import DAG, configuration
from airflow.models import BaseOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.module_loading import import_string

import utils

# these are params only used in the DAG factory, not in the tasks
SYSTEM_PARAMS: List[str] = ["operator", "dependencies"]


class DagBuilder:
    """
    Generates tasks and a DAG from a config.

    :param dag_name: the name of the DAG
    :param dag_config: a dictionary containing configuration for the DAG
    :param default_config: a dictitionary containing defaults for all DAGs
        in the YAML file
    """

    # pylint: disable=bad-continuation
    def __init__(
        self, dag_name: str, dag_config: Dict[str, Any], default_config: Dict[str, Any]
    ) -> None:
        self.dag_name: str = dag_name
        self.dag_config: Dict[str, Any] = dag_config
        self.default_config: Dict[str, Any] = default_config

    def get_dag_params(self) -> Dict[str, Any]:
        """
        Merges default config with dag config, sets dag_id, and extropolates dag_start_date

        :returns: dict of dag parameters
        """
        try:
            dag_params: Dict[str, Any] = utils.merge_configs(
                self.dag_config, self.default_config
            )
        except Exception as err:
            raise Exception(f"Failed to merge config with default config, err: {err}")
        dag_params["dag_id"]: str = self.dag_name
        try:
            # ensure that default_args dictionary contains key "start_date"
            # with "datetime" value in specified timezone
            dag_params["default_args"]["start_date"]: datetime = utils.get_start_date(
                date_value=dag_params["default_args"]["start_date"],
                timezone=dag_params["default_args"].get("timezone", "UTC"),
            )
        except KeyError as err:
            raise Exception(f"{self.dag_name} config is missing start_date, err: {err}")
        return dag_params

    @staticmethod
    def make_task(operator: str, task_params: Dict[str, Any]) -> BaseOperator:
        """
        Takes an operator and params and creates an instance of that operator.

        :returns: instance of operator object
        """
        try:
            # class is a Callable https://stackoverflow.com/a/34578836/3679900
            operator_obj: Callable[..., BaseOperator] = import_string(operator)
        except Exception as err:
            raise Exception(f"Failed to import operator: {operator}. err: {err}")
        try:
            if operator_obj == PythonOperator:
                if not task_params.get("python_callable_name") and not task_params.get(
                    "python_callable_file"
                ):
                    raise Exception(
                        "Failed to create task. PythonOperator requires `python_callable_name` \
                        and `python_callable_file` parameters."
                    )
                task_params["python_callable"]: Callable = utils.get_python_callable(
                    task_params["python_callable_name"],
                    task_params["python_callable_file"],
                )
            task: BaseOperator = operator_obj(**task_params)
        except Exception as err:
            raise Exception(f"Failed to create {operator_obj} task. err: {err}")
        return task

    def build(self) -> Dict[str, Union[str, DAG]]:
        """
        Generates a DAG from the DAG parameters.

        :returns: dict with dag_id and DAG object
        :type: Dict[str, Union[str, DAG]]
        """
        dag_params: Dict[str, Any] = self.get_dag_params()
        dag: DAG = DAG(
            dag_id=dag_params["dag_id"],
            schedule_interval=dag_params["schedule_interval"],
            description=dag_params.get("description", ""),
            max_active_runs=dag_params.get(
                "max_active_runs",
                configuration.conf.getint("core", "max_active_runs_per_dag"),
            ),
            default_args=dag_params.get("default_args", {}),
        )
        tasks: Dict[str, Dict[str, Any]] = dag_params["tasks"]

        # create dictionary to track tasks and set dependencies
        tasks_dict: Dict[str, BaseOperator] = {}
        for task_name, task_conf in tasks.items():
            task_conf["task_id"]: str = task_name
            operator: str = task_conf["operator"]
            task_conf["dag"]: DAG = dag
            params: Dict[str, Any] = {
                k: v for k, v in task_conf.items() if k not in SYSTEM_PARAMS
            }
            task: BaseOperator = DagBuilder.make_task(
                operator=operator, task_params=params
            )
            tasks_dict[task.task_id]: BaseOperator = task

        # set task dependencies after creating tasks
        for task_name, task_conf in tasks.items():
            if task_conf.get("dependencies"):
                source_task: BaseOperator = tasks_dict[task_name]
                for dep in task_conf["dependencies"]:
                    dep_task: BaseOperator = tasks_dict[dep]
                    source_task.set_upstream(dep_task)

        return {"dag_id": dag_params["dag_id"], "dag": dag}