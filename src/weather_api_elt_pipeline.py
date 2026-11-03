from google.colab import auth
from google.cloud import bigquery
import requests
import pandas as pd

# 1. Authenticate and connect
auth.authenticate_user()
client = bigquery.Client(project='zepp-health-data')
table_id = 'zepp-health-data.my_health_database.raw_weather_data'
API_KEY = "HT8W6YXQRQQ8B3FHM5GCMG4YN"

print("Identifying missing weather records in BigQuery...")

# 2. Find Zepp runs from April to November without weather data
query = """
SELECT z.local_start_time
FROM `zepp-health-data.my_health_database.vw_marathon_training_baseline` z
LEFT JOIN `zepp-health-data.my_health_database.raw_weather_data` w
ON DATE(z.local_start_time) = DATE(TIMESTAMP(w.local_start_time, 'UTC'), 'Asia/Kolkata')
WHERE w.local_start_time IS NULL
"""
df_missing = client.query(query).to_dataframe()
print(f"Found {len(df_missing)} runs requiring weather data.\n")

# Default coordinates for Brookefield, Bengaluru
lat, lon = 12.969, 77.712
rows_to_insert = []

for index, row in df_missing.iterrows():
    # Zepp data is in IST. We format it directly for the API call.
    ist_time = row['local_start_time']
    api_time_str = ist_time.strftime('%Y-%m-%dT%H:%M:%S')

    api_url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{lat},{lon}/{api_time_str}?key={API_KEY}&include=current&unitGroup=metric"
    response = requests.get(api_url)

    if response.status_code == 200:
        weather_data = response.json()
        temp = weather_data['days'][0]['temp']
        humidity = weather_data['days'][0]['humidity']
        conditions = weather_data['days'][0]['conditions']

        # Convert IST back to UTC before inserting to match the existing Strava schema logic
        utc_time = ist_time - pd.Timedelta(hours=5, minutes=30)
        bq_time = utc_time.strftime('%Y-%m-%d %H:%M:%S')

        rows_to_insert.append({
            "local_start_time": bq_time,
            "latitude": lat,
            "longitude": lon,
            "temperature_celsius": temp,
            "humidity_percentage": int(humidity),
            "weather_condition": conditions
        })
        print(f"✅ Fetched Brookefield weather for {api_time_str}")

# 3. Load the missing data into BigQuery
if rows_to_insert:
    errors = client.insert_rows_json(table_id, rows_to_insert)
    if not errors:
        print(f"\n🚀 SUCCESS: {len(rows_to_insert)} new weather rows added to BigQuery.")
    else:
        print(f"\n❌ Encountered errors: {errors}")
else:
    print("No data required processing.")
