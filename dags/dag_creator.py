import yaml
import copy

yaml.Dumper.ignore_aliases = lambda *args: True #This avoids YAML referencing; making DAGs YAML more readable


with open("bash_jobs.yaml", "r") as stream:
    data = yaml.safe_load(stream)

dags = data["dags"]
tasks = data["tasks"]
dag_default_args = data["dag-default-args"]

#Adding default task details to the custom parameters provided
for dag_name in list(dags.keys()):
    for task in list(dags[dag_name]['tasks'].keys()):
        if(task=='task-one'):
            dags[dag_name]['tasks'][task].update(tasks['task-one'])
        elif(task=='task-two'):
            dags[dag_name]['tasks'][task].update(tasks['task-two'])
        else:
            pass
    dags[dag_name]['default_args'] = dag_default_args

with open("bash_dags.yaml", "w") as file:
    yaml.dump(dags, file)
