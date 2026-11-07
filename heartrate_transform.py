from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, round

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("ZeppHeartRateAggregation") \
    .getOrCreate()

# ---------------------------------------------------------
# CONFIGURATION
# Replace 'YOUR_BUCKET_NAME' with your actual bucket name
# ---------------------------------------------------------
gcs_bucket = "ravi-health-data-12345"
input_path = f"gs://{gcs_bucket}/raw_data_zepp/HEARTRATE_AUTO_1793081717167.csv"
bq_destination = "my_health_database.heartrate_auto_clean_spark"
bq_temp_bucket = f"{gcs_bucket}/spark_logs_zepp"

# 1. EXTRACT: Read the continuous heart rate log from the GCS Landing Zone
print(f"Reading raw data from {input_path}...")
df = spark.read.csv(input_path, header=True, inferSchema=True)

# 2. TRANSFORM: Group by date and calculate the rounded daily average
print("Applying aggregation transformations...")
transformed_df = df.groupBy("date") \
    .agg(round(avg(col("heartRate")), 0).alias("avg_daily_heartrate")) \
    .orderBy(col("date").desc())

# 3. LOAD: Write the aggregated DataFrame directly to BigQuery
# The 'overwrite' mode ensures idempotent execution (rerunning the DAG won't duplicate data)
print(f"Writing transformed data to BigQuery table: {bq_destination}...")
transformed_df.write \
    .format("bigquery") \
    .option("table", bq_destination) \
    .option("temporaryGcsBucket", bq_temp_bucket) \
    .mode("overwrite") \
    .save()

print("Pipeline execution completed successfully.")
spark.stop()