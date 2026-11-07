from airflow import DAG
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocCreateClusterOperator,
    DataprocSubmitJobOperator,
    DataprocDeleteClusterOperator,
)
from airflow.utils.dates import days_ago

# ---------------------------------------------------------
# CONFIGURATION
# Replace with your actual project ID and bucket name
# ---------------------------------------------------------
PROJECT_ID = "zepp-health-data"
REGION = "us-central1" # Or whichever region your bucket is in
CLUSTER_NAME = "zepp-spark-cluster"
BUCKET_NAME = "ravi-health-data-12345"

# Dataproc cluster configuration (n1-standard-2 is lightweight and cheap)
CLUSTER_CONFIG = {
    "master_config": {
        "num_instances": 1,
        "machine_type_uri": "n1-standard-2",
        "disk_config": {"boot_disk_type": "pd-standard", "boot_disk_size_gb": 50},
    },
    "worker_config": {
        "num_instances": 2,
        "machine_type_uri": "n1-standard-2",
        "disk_config": {"boot_disk_type": "pd-standard", "boot_disk_size_gb": 50},
    },
}

# The PySpark job configuration pointing to your GCS bucket
PYSPARK_JOB = {
    "reference": {"project_id": PROJECT_ID},
    "placement": {"cluster_name": CLUSTER_NAME},
    "pyspark_job": {
        "main_python_file_uri": f"gs://{BUCKET_NAME}/scripts_zepp/heartrate_transform.py",
        # Adding the BigQuery connector so Spark can write to BQ
        "jar_file_uris": ["gs://spark-lib/bigquery/spark-bigquery-with-dependencies_2.13-0.34.0.jar"],
    },
}

default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "retries": 0,
}

with DAG(
    "zepp_heartrate_dataproc_pipeline",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
    tags=["portfolio", "dataproc", "pyspark"],
) as dag:

    create_cluster = DataprocCreateClusterOperator(
        task_id="create_cluster",
        project_id=PROJECT_ID,
        cluster_config=CLUSTER_CONFIG,
        region=REGION,
        cluster_name=CLUSTER_NAME,
    )

    submit_pyspark_job = DataprocSubmitJobOperator(
        task_id="submit_pyspark_job",
        job=PYSPARK_JOB,
        region=REGION,
        project_id=PROJECT_ID,
    )

    delete_cluster = DataprocDeleteClusterOperator(
        task_id="delete_cluster",
        project_id=PROJECT_ID,
        cluster_name=CLUSTER_NAME,
        region=REGION,
        trigger_rule="all_done", # CRITICAL: Deletes cluster even if the Spark job fails
    )

    # Set the dependencies
    create_cluster >> submit_pyspark_job >> delete_cluster