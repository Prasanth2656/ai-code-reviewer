import os
import shutil
import uuid

BASE_TEMP_DIR = "temp_scans"


def create_scan_directory():
    """
    Creates isolated directory per scan job.
    """
    if not os.path.exists(BASE_TEMP_DIR):
        os.makedirs(BASE_TEMP_DIR)

    scan_id = str(uuid.uuid4())
    scan_path = os.path.join(BASE_TEMP_DIR, scan_id)

    os.makedirs(scan_path)

    return scan_path


def delete_scan_directory(path: str):
    """
    Deletes scan directory after processing.
    """
    if os.path.exists(path):
        shutil.rmtree(path)