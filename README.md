# Zepp Health Data ELT Pipeline

## 📌 Project Overview
An end-to-end Data Engineering ELT (Extract, Load, Transform) pipeline built on Google Cloud Platform (GCP). This project automates the extraction of biometric data from a Zepp smartwatch (Amazfit) and correlates it with historical weather data. The pipeline is designed to track Half Marathon training metrics, analyze heart rate zones, and generate race pace predictions.

## 🏗️ Architecture & Data Flow
1. **Extract:** Python scripts pull encrypted ZIP exports from Google Drive, decrypt them using `pyzipper`, and fetch corresponding local weather data via the Visual Crossing API.
2. **Load:** Raw CSV and JSON payloads are uploaded directly to Google Cloud Storage (GCS) data lakes.
3. **Transform:** BigQuery reads the GCS files via External Tables, loads them into Raw Tables, and processes the data through a series of SQL-based analytical views (DDL).
4. **Serve:** A Looker Studio dashboard connects to the enriched BigQuery views to visualize training performance.

## 🛠️ Tech Stack
* **Languages:** Python 3, Standard SQL
* **Cloud Infrastructure (GCP):** Google Cloud Storage, Google BigQuery
* **APIs & Libraries:** Google Drive API, Visual Crossing Weather API, `pandas`, `google-cloud-storage`, `pyzipper`
* **BI & Visualization:** Looker Studio
* **Version Control:** Git & GitHub

## 📂 Repository Structure
* `src/` - Contains all Python extraction and GCS upload scripts.
  * `weather_api_elt_pipeline.py`
  * `zepp_gcs_extraction.py`
* `sql/` - Contains BigQuery DDL for the transformation layer.
  * `01_external_and_raw_tables.sql` - Foundational data structures.
  * `02_enriched_views.sql` - Business logic and marathon training analytics.

## 📊 Dashboard Integration
The final transformed data is visualized in Looker Studio. 
* **[View the Looker Studio Dashboard Here](#)** *(https://datastudio.google.com/reporting/ef510912-7743-4a9e-acc5-be28170aa297/page/1qVCG)*
