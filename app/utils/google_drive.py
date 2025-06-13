import os
from datetime import datetime
from flask import current_app

# Try to import Google Drive API libraries
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    print("Google Drive API libraries not available. Image upload to Drive will be disabled.")
    GOOGLE_DRIVE_AVAILABLE = False

def get_or_create_folder(folder_name="Student_Attendance_Images"):
    # Check if Google Drive API is available
    if not globals().get('GOOGLE_DRIVE_AVAILABLE', False):
        print("Google Drive API libraries not available. Cannot get or create folder.")
        return None

    try:
        # Get the credentials file path from the app config
        credentials_file = current_app.config.get('GOOGLE_CREDENTIALS_FILE')
        if not credentials_file:
            credentials_file = 'sams-457718-15d12ee30281.json'  # Default credentials file

        # Set up credentials
        scopes = ['https://www.googleapis.com/auth/drive.file']
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=scopes)

        # Build the Drive service
        drive_service = build('drive', 'v3', credentials=credentials)

        # Check if folder already exists
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])

        if items:
            # Folder exists, return its ID
            folder_id = items[0]['id']
            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
            print(f"Found existing folder: {folder_name}")
            print(f"Folder URL: {folder_url}")
            print(f"Folder ID: {folder_id}")

            # Share with the admin email if not already shared
            admin_email = current_app.config.get('MAIL_USERNAME')
            if admin_email:
                try:
                    drive_service.permissions().create(
                        fileId=folder_id,
                        body={
                            'type': 'user',
                            'role': 'writer',
                            'emailAddress': admin_email
                        },
                        sendNotificationEmail=True
                    ).execute()
                    print(f"Folder shared with {admin_email}")
                except Exception as e:
                    print(f"Note: {str(e)}")

            return folder_id
        else:
            # Create the folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            folder = drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            folder_id = folder.get('id')

            # Make the folder accessible to anyone with the link
            drive_service.permissions().create(
                fileId=folder_id,
                body={
                    'type': 'anyone',
                    'role': 'reader'
                }
            ).execute()

            # Share with the admin email
            admin_email = current_app.config.get('MAIL_USERNAME')
            if admin_email:
                try:
                    drive_service.permissions().create(
                        fileId=folder_id,
                        body={
                            'type': 'user',
                            'role': 'writer',
                            'emailAddress': admin_email
                        },
                        sendNotificationEmail=True
                    ).execute()
                    print(f"Folder shared with {admin_email}")
                except Exception as e:
                    print(f"Error sharing folder with email: {str(e)}")

            # Get the folder URL
            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
            print(f"Created new folder: {folder_name}")
            print(f"Folder URL: {folder_url}")
            print(f"Folder ID: {folder_id}")
            return folder_id

    except Exception as e:
        print(f"Error getting or creating folder in Google Drive: {str(e)}")
        return None

def upload_file_to_drive(file_path, file_name=None, folder_id=None):
    # Check if Google Drive API is available
    if not globals().get('GOOGLE_DRIVE_AVAILABLE', False):
        print("Google Drive API libraries not available. Image will be stored locally only.")
        return None

    try:
        # Get the credentials file path from the app config
        credentials_file = current_app.config.get('GOOGLE_CREDENTIALS_FILE')
        if not credentials_file:
            credentials_file = 'sams-457718-15d12ee30281.json'  # Default credentials file

        # Check if the file exists
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None

        # If no file name is provided, use the original file name
        if not file_name:
            file_name = os.path.basename(file_path)

        # Add date to the file name
        date_str = datetime.now().strftime('%Y-%m-%d')
        file_name = f"{date_str}_{file_name}"

        # Set up credentials
        scopes = ['https://www.googleapis.com/auth/drive.file']
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=scopes)

        # Build the Drive service
        drive_service = build('drive', 'v3', credentials=credentials)

        # If no folder ID is provided, get or create the default folder
        if not folder_id:
            folder_id = get_or_create_folder("Student_Attendance_Images")

        # File metadata
        file_metadata = {
            'name': file_name,
        }

        # If a folder ID is provided, add it to the metadata
        if folder_id:
            file_metadata['parents'] = [folder_id]

        # Create a media object
        media = MediaFileUpload(file_path, resumable=True)

        # Upload the file
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,webViewLink'
        ).execute()

        # Make the file accessible to anyone with the link
        drive_service.permissions().create(
            fileId=file.get('id'),
            body={
                'type': 'anyone',
                'role': 'reader'
            }
        ).execute()

        print(f"File uploaded to Google Drive folder 'Student_Attendance_Images': {file.get('webViewLink')}")
        return file

    except Exception as e:
        print(f"Error uploading file to Google Drive: {str(e)}")
        return None

def create_drive_folder(folder_name):
    # Check if Google Drive API is available
    if not globals().get('GOOGLE_DRIVE_AVAILABLE', False):
        print("Google Drive API libraries not available. Cannot create folder.")
        return None

    try:
        # Get the credentials file path from the app config
        credentials_file = current_app.config.get('GOOGLE_CREDENTIALS_FILE')
        if not credentials_file:
            credentials_file = 'sams-457718-15d12ee30281.json'  # Default credentials file

        # Set up credentials
        scopes = ['https://www.googleapis.com/auth/drive.file']
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=scopes)

        # Build the Drive service
        drive_service = build('drive', 'v3', credentials=credentials)

        # Folder metadata
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        # Create the folder
        folder = drive_service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()

        # Make the folder accessible to anyone with the link
        drive_service.permissions().create(
            fileId=folder.get('id'),
            body={
                'type': 'anyone',
                'role': 'reader'
            }
        ).execute()

        print(f"Folder created in Google Drive: {folder.get('id')}")
        return folder.get('id')

    except Exception as e:
        print(f"Error creating folder in Google Drive: {str(e)}")
        return None
