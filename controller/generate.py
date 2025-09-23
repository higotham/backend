from fastapi import APIRouter
import uuid, time

route = APIRouter(tags=["생성 스텁"])

@route.post("/generate")
def generate_stub():
    job_id = str(uuid.uuid4())
    return {"status": True, "jobId": job_id, "queuedAt": int(time.time()), "message": "stub queued"}
