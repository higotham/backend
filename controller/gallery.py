from fastapi import APIRouter
import os, time

route = APIRouter(tags=["갤러리"])

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "images")
IMAGES_DIR = os.path.abspath(IMAGES_DIR)

@route.get("/gallery")
def list_gallery():
    try:
        if not os.path.exists(IMAGES_DIR):
            return {"status": True, "items": []}
        items = []
        for fn in os.listdir(IMAGES_DIR):
            p = os.path.join(IMAGES_DIR, fn)
            if not os.path.isfile(p): continue
            if not (fn.lower().endswith(".png") or fn.lower().endswith(".jpg") or fn.lower().endswith(".jpeg")):
                continue
            st = os.stat(p)
            items.append({
                "name": fn,
                "size": st.st_size,
                "mtime": int(st.st_mtime),
                "url": f"/images/{fn}"
            })
        items.sort(key=lambda x: x["mtime"], reverse=True)
        return {"status": True, "items": items}
    except Exception as e:
        return {"status": False, "items": [], "error": str(e)}
