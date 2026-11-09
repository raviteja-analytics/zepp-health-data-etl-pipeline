import io
import pyzipper
import pandas as pd
import datetime
import functions_framework
from google.auth import default
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import storage

FOLDER_ID = '1K-DM0zOyzVfu4tI1wnmeGyh_-Q3UYZw0'
GCS_BUCKET_NAME = 'ravi-health-data-12345' 

# The entry point for the Cloud Function
@functions_framework.http
def run_zepp_extraction(request):
    # 1. Capture the dynamic password from the Airflow/Webhook payload
    request_json = request.get_json(silent=True)
    if not request_json or 'zip_password' not in request_json:
        return 'Error: Missing zip_password in payload.', 400
        
    zip_password = request_json['zip_password'].encode('utf-8')

    # 2. Inherit the Cloud Function's attached service account credentials
    creds, project_id = default()
    drive_service = build('drive', 'v3', credentials=creds)
    storage_client = storage.Client(credentials=creds, project=project_id)

    # 3. Locate File
    query = f"'{FOLDER_ID}' in parents and trashed=false"
    results = drive_service.files().list(q=query, orderBy="createdTime desc", pageSize=1, fields="files(id)").execute()
    files = results.get('files', [])
    if not files:
        return 'No Zepp exports found.', 404
    file_id = files[0]['id']

    # 4. Download and Extract
    print("Downloading ZIP file into memory...")
    request_media = drive_service.files().get_media(fileId=file_id)
    file_stream = io.BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request_media)
    
    done = False
    while not done:
        status, done = downloader.next_chunk()
        
    file_stream.seek(0)
    target_folders = ['HEALTH_DATA', 'SPORT', 'HEARTRATE', 'HEARTRATE_AUTO']
    
    now = datetime.datetime.now()
    date_folder = now.strftime("%Y-%m-%d")         
    timestamp = now.strftime("%Y%m%d_%H%M%S")  
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    
    extracted_count = 0

    with pyzipper.AESZipFile(file_stream) as z:
        z.setpassword(zip_password)
        for folder in target_folders:
            target_file = next((f for f in z.namelist() if f.upper().startswith(f"{folder.upper()}/") and f.lower().endswith('.csv')), None)
            
            if target_file:
                with z.open(target_file) as csv_file:
                    df = pd.read_csv(csv_file)
                    
                    # 5. Upload straight to GCS Bronze Layer
                    destination = f"raw_data_zepp/{folder}/{date_folder}/{folder}_{timestamp}.csv"
                    blob = bucket.blob(destination)
                    blob.upload_from_string(df.to_csv(index=False), content_type='text/csv')
                    extracted_count += 1

    return f'Success: Extracted and uploaded {extracted_count} files.', 200