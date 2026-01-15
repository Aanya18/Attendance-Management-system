import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_or_create_folder(folder_name="Student_Attendance_Images"):
    """
    Get or create a folder in Google Drive
    
    Args:
        folder_name (str): Name of the folder to get or create
        
    Returns:
        str: ID of the folder
    """
    try:
        # Get the credentials file path
        credentials_file = 'sams-457718-15d12ee30281.json'
            
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
            
            # Share with the specific email if not already shared
            try:
                drive_service.permissions().create(
                    fileId=folder_id,
                    body={
                        'type': 'user',
                        'role': 'writer',
                        'emailAddress': 'ananya.robostaan@gmail.com'
                    },
                    sendNotificationEmail=True
                ).execute()
                print(f"Folder shared with ananya.robostaan@gmail.com")
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
            
            # Share with the specific email
            try:
                drive_service.permissions().create(
                    fileId=folder_id,
                    body={
                        'type': 'user',
                        'role': 'writer',
                        'emailAddress': 'ananya.robostaan@gmail.com'
                    },
                    sendNotificationEmail=True
                ).execute()
                print(f"Folder shared with ananya.robostaan@gmail.com")
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

if __name__ == "__main__":
    print("Testing Google Drive folder creation...")
    folder_id = get_or_create_folder("Student_Attendance_Images")
    if folder_id:
        print("Success!")
    else:
        print("Failed to create or find folder.")
