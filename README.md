# dagfactory-essentials
Fork of dag-factory==0.3.0 for using it on GCP Composer 

Link to original repository: https://github.com/ajbosco/dag-factory

Reason for doing this: 
1. GCP provides custom apache-airflow
2. dag-factory has default apache-airflow as required dependecies; hence that too gets installed
3. Composer cluster fails due to conflict in airflow versions
