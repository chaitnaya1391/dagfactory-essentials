import dagfactory
from airflow import DAG
from datetime import datetime, timedelta

dag_factory = dagfactory.DagFactory("/path/to/dags/dags.yaml")

dag_factory.generate_dags(globals())