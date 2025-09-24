from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from config.db import getConn
from config.token import get_current
import mariadb
import os

route = APIRouter(tags=["이미지 갤러리"])

class Gallery(BaseModel):
  q: str
  qBy: int
  aspect: int
  sort: str
  limit: int

class BulkDelete(BaseModel):
  ids: str

@route.get("/download/{no}")
def download(no: int):
  try:
    conn = getConn()
    cur = conn.cursor()
    sql = f'''
          SELECT `no`, `mediaType`, `origin`, `attachPath`
            FROM auth.`file`
          WHERE useYn = 'Y'
            AND `no` = {no}
    '''
    cur.execute(sql)
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    cur.close()
    conn.close()
    result = dict(zip(columns, row)) if row else None
    
    if os.path.exists(result["attachPath"]):
      return FileResponse(
          path=result["attachPath"],
          media_type=result["mediaType"],
          filename=f"gotham-{no}.png",
      )
    return {"error": "File not found"}
  except mariadb.Error as e:
    print(f"MariaDB 오류 발생: {e}")
    return {"status": False, "message": "File not found"}

@route.post("/gallery")
def findAll(gallery: Gallery, payload = Depends(get_current)):
  try:
    conn = getConn()
    cur = conn.cursor()
    
    q = ''
    model = ''
    aspect = gallery.aspect if gallery.aspect >= 0 else ''
    sort = 'DESC' if gallery.sort == 'newest' else 'ASC'
    
    if gallery.qBy == 0:
      q = gallery.q
    elif gallery.qBy == 1:
      model = gallery.q
    
    sql = f'''
          SELECT g.`no`, g.`model`, g.`ratio`, g.`prompt`, g.`regUserNo`, g.`fileNo`, f.attachPath
            FROM gotham.`gallery` AS g
          INNER JOIN auth.`file` AS f
              ON (g.fileNo = f.`no` AND f.useYn = 'Y')
          WHERE g.useYn = 'Y'
            AND g.`regUserNo` = {payload["userNo"]}
            AND g.`prompt` LIKE '%{q}%'
            AND g.`ratio` LIKE '%{aspect}%'
            AND g.`model` LIKE '%{model}%'
          ORDER BY g.`no` {sort}
    '''
    cur.execute(sql)
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = None
    if rows:
      result = [dict(zip(columns, row)) for row in rows]
    else :
      result = []
    return {"status": True, "result" : result}
  except mariadb.Error as e:
    print(f"MariaDB 오류 발생: {e}")
    return {"status": False}
  
@route.delete("/gallery")
def findAll(bulkDelete: BulkDelete, payload = Depends(get_current)):
  try:
    gallerys = bulkDelete.ids.split(",")
    conn = getConn()
    cur = conn.cursor()
    for no in gallerys:
      sql = f'''
            UPDATE gotham.`gallery` SET useYn = 'N', modUserNo = {payload["userNo"]} WHERE `no` = {no}
      '''
      print(sql)
      cur.execute(sql)
      conn.commit()
    cur.close()
    conn.close()
    return {"status": True}
  except mariadb.Error as e:
    print(f"MariaDB 오류 발생: {e}")
    return {"status": False}