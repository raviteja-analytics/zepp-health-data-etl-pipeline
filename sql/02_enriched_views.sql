CREATE VIEW `zepp-health-data.my_health_database.vw_marathon_training_enriched`
AS SELECT 
    z.*,
    w.temperature_celsius,
    w.humidity_percentage,
    w.weather_condition
FROM `zepp-health-data.my_health_database.vw_marathon_training_baseline` z
LEFT JOIN `zepp-health-data.my_health_database.raw_weather_data` w
ON DATE(z.local_start_time) = DATE(TIMESTAMP(w.local_start_time, 'UTC'), 'Asia/Kolkata');



CREATE VIEW `zepp-health-data.my_health_database.vw_marathon_training_baseline`
AS WITH PreparedSport AS (
    SELECT 
        -- startTime is already a TIMESTAMP, so it can be passed directly to DATETIME
        DATETIME(startTime, 'Asia/Kolkata') AS local_start_time,
        DATETIME_ADD(DATETIME(startTime, 'Asia/Kolkata'), INTERVAL CAST(sportTime_s_ AS INT64) SECOND) AS local_end_time,
        CASE 
            WHEN type = 52 THEN 'Strength Training'
            WHEN type IN (1, 8) THEN 'Running'
            WHEN type = 6 THEN 'Walking'
            WHEN type IN (53, 50, 21) THEN 'Warm-up / Stretching'
            ELSE 'Home Workout'
        END AS workout_name,
        
        -- FIXED: Microscopic fractional adjustment (jitter) using the timestamp so X-axis coordinates never collide
        ROUND((distance_m_ / 1000) + (MOD(CAST(UNIX_SECONDS(startTime) AS INT64), 100) * 0.0001), 4) AS distance_km,
        
        CASE 
            WHEN type IN (1, 8, 6) AND avgPace__meter_ > 0 THEN 
                FORMAT('%d:%02d', 
                    CAST(FLOOR((avgPace__meter_ * 1000) / 60) AS INT64), 
                    MOD(CAST((avgPace__meter_ * 1000) AS INT64), 60)
                )
            ELSE 'N/A'
        END AS avg_pace_per_km
    -- FIXED: Now points to the automated pipeline view
    FROM `zepp-health-data.my_health_database.vw_latest_sport`
    WHERE type IN (1, 8, 52)
),

PreparedHR AS (
    SELECT 
        PARSE_DATETIME('%Y-%m-%d %H:%M', CONCAT(date, ' ', time)) AS hr_timestamp,
        heartRate
    -- FIXED: Now points to the automated external table
    FROM `zepp-health-data.my_health_database.ext_heartrate_auto`
)

SELECT 
    s.workout_name,
    s.local_start_time,
    s.distance_km,
    s.avg_pace_per_km,
    ROUND(AVG(h.heartRate), 1) AS avg_workout_hr,
    MAX(h.heartRate) AS max_workout_hr
FROM PreparedSport s
LEFT JOIN PreparedHR h    
    ON h.hr_timestamp >= s.local_start_time 
    AND h.hr_timestamp <= s.local_end_time
GROUP BY 
    s.workout_name, 
    s.local_start_time, 
    s.distance_km,
    s.avg_pace_per_km;


CREATE VIEW `zepp-health-data.my_health_database.vw_latest_sport`
AS SELECT * EXCEPT(row_num)
FROM (
  SELECT 
    *,
    ROW_NUMBER() OVER(PARTITION BY startTime ORDER BY startTime DESC) as row_num
  FROM `zepp-health-data.my_health_database.ext_sport`
)
WHERE row_num = 1

  
CREATE VIEW `zepp-health-data.my_health_database.vw_race_predictions`
AS WITH RawPace AS (
    SELECT 
        DATE(local_start_time) AS run_date,
        distance_km,
        (CAST(SPLIT(avg_pace_per_km, ':')[OFFSET(0)] AS INT64) * 60) + 
         CAST(SPLIT(avg_pace_per_km, ':')[OFFSET(1)] AS INT64) AS pace_in_seconds
    FROM `zepp-health-data.my_health_database.vw_marathon_training_baseline`
    -- Because type 1 and 8 are both 'Running' now, this filter captures everything automatically
    WHERE workout_name = 'Running' AND distance_km >= 4.0 AND avg_pace_per_km != 'N/A'
),
Predictions AS (
    SELECT 
        run_date,
        distance_km,
        pace_in_seconds,
        pace_in_seconds - 408 AS gap_to_68min_10k_sec,
        pace_in_seconds - 390 AS gap_to_65min_10k_sec,
        pace_in_seconds - 469 AS gap_to_2h45m_hm_sec,
        pace_in_seconds - 426 AS gap_to_2h30m_hm_sec,
        CAST((pace_in_seconds * distance_km) * POWER(21.1 / distance_km, 1.06) AS INT64) AS predicted_hm_sec
    FROM RawPace
)
SELECT 
    run_date,
    distance_km,
    FORMAT('%d:%02d', CAST(FLOOR(pace_in_seconds / 60) AS INT64), MOD(CAST(pace_in_seconds AS INT64), 60)) AS avg_pace,
    CASE WHEN gap_to_68min_10k_sec <= 0 THEN 'Target Pace Hit' ELSE CONCAT('Needs -', CAST(gap_to_68min_10k_sec AS STRING), ' sec/km') END AS deficit_to_68min_10K,
    CASE WHEN gap_to_65min_10k_sec <= 0 THEN 'Target Pace Hit' ELSE CONCAT('Needs -', CAST(gap_to_65min_10k_sec AS STRING), ' sec/km') END AS deficit_to_65min_10K,
    CASE WHEN gap_to_2h45m_hm_sec <= 0 THEN 'Target Pace Hit' ELSE CONCAT('Needs -', CAST(gap_to_2h45m_hm_sec AS STRING), ' sec/km') END AS deficit_to_2h45m_HM,
    CASE WHEN gap_to_2h30m_hm_sec <= 0 THEN 'Target Pace Hit' ELSE CONCAT('Needs -', CAST(gap_to_2h30m_hm_sec AS STRING), ' sec/km') END AS deficit_to_2h30m_HM,
    FORMAT('%d:%02d', CAST(FLOOR(predicted_hm_sec / 3600) AS INT64), CAST(FLOOR(MOD(predicted_hm_sec, 3600) / 60) AS INT64)) AS predicted_goa_hm_time
FROM Predictions;
