from fastapi import APIRouter

route = APIRouter(tags=["기본"])

@route.get("/")
def home():
  return {"service": "GOTHAM"}


@route.get('/health')
def health():
  return {'ok': True}
