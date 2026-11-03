CREATE EXTERNAL TABLE `zepp-health-data.my_health_database.ext_sport`
OPTIONS(
  skip_leading_rows=1,
  format="CSV",
  uris=["gs://ravi-health-data-12345/raw_data_zepp/SPORT/*"]
);

CREATE EXTERNAL TABLE `zepp-health-data.my_health_database.ext_heartrate_auto`
OPTIONS(
  skip_leading_rows=1,
  format="CSV",
  uris=["gs://ravi-health-data-12345/raw_data_zepp/HEARTRATE_AUTO/*"]
);

CREATE TABLE `zepp-health-data.my_health_database.raw_weather_data`
(
  local_start_time DATETIME,
  latitude FLOAT64,
  longitude FLOAT64,
  temperature_celsius FLOAT64,
  humidity_percentage INT64,
  weather_condition STRING
);
