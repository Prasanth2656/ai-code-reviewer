import uuid

scan_jobs = {}

def create_scan_job():
    job_id = str(uuid.uuid4())

    scan_jobs[job_id] = {
        "status": "processing",
        "result": None
    }

    return job_id

def update_scan_job(job_id, result):
    scan_jobs[job_id]["status"] = "completed"
    scan_jobs[job_id]["result"] = result

def get_scan_job(job_id):
    return scan_jobs.get(job_id)