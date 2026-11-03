import io
import pyzipper
import pandas as pd
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import storage

# 1. Configuration
SERVICE_ACCOUNT_FILE = 'D:/Zepp_GCP/credentials.json'
FOLDER_ID = '1K-DM0zOyzVfu4tI1wnmeGyh_-Q3UYZw0'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
GCS_BUCKET_NAME = 'ravi-health-data-12345' # Replace with your actual GCP bucket name

# Define the ZIP password as bytes
ZIP_PASSWORD = b'gsRRPRsg' 

def get_latest_zepp_export():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)
    
    query = f"'{FOLDER_ID}' in parents and trashed=false"
    results = drive_service.files().list(q=query, orderBy="createdTime desc", pageSize=1, fields="files(id, name)").execute()
    files = results.get('files', [])

    if not files:
        print('No Zepp exports found.')
        return None, None
    
    return drive_service, files[0]['id']

def extract_zepp_data_in_memory(drive_service, file_id):
    print("Downloading ZIP file into memory...")
    request = drive_service.files().get_media(fileId=file_id)
    
    file_stream = io.BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request)
    
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}% complete.")
        
    print("Unzipping and decrypting...")
    file_stream.seek(0)
    
    target_folders = ['HEALTH_DATA', 'SPORT', 'HEARTRATE', 'HEARTRATE_AUTO']
    dataframes = {}

    with pyzipper.AESZipFile(file_stream) as z:
        z.setpassword(ZIP_PASSWORD)
        
        for folder in target_folders:
            target_file = None
            for file_path in z.namelist():
                if file_path.upper().startswith(f"{folder.upper()}/") and file_path.lower().endswith('.csv'):
                    target_file = file_path
                    break
            
            if target_file:
                print(f"Found {folder} dataset: {target_file}")
                with z.open(target_file) as csv_file:
                    dataframes[folder] = pd.read_csv(csv_file)
            else:
                print(f"Warning: No CSV found inside {folder}")

    return dataframes

def upload_dfs_to_gcs(dfs, bucket_name):
    print("\nInitiating partitioned Google Cloud Storage upload...")
    storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_FILE)
    bucket = storage_client.bucket(bucket_name)
    
    # Capture current time once for both folder and file naming
    now = datetime.datetime.now()
    date_folder = now.strftime("%Y-%m-%d")         # e.g., 2026-11-01
    timestamp = now.strftime("%Y%m%d_%H%M%S")      # e.g., 20261101_154000

    for dataset_name, df in dfs.items():
        # Injects the date_folder directly into the GCS path
        destination_blob_name = f"raw_data_zepp/{dataset_name}/{date_folder}/{dataset_name}_{timestamp}.csv"
        blob = bucket.blob(destination_blob_name)
        
        csv_data = df.to_csv(index=False)
        blob.upload_from_string(csv_data, content_type='text/csv')
        
        print(f"Success: Uploaded gs://{bucket_name}/{destination_blob_name}")

if __name__ == '__main__':
    service, target_file_id = get_latest_zepp_export()
    
    if target_file_id:
        dfs = extract_zepp_data_in_memory(service, target_file_id)
        
        if dfs:
            upload_dfs_to_gcs(dfs, GCS_BUCKET_NAME)
