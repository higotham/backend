from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from config.db import getConn
from config.token import get_current
import mariadb

route = APIRouter(tags=["캔버스 드로잉"])

class Canvas(BaseModel):
  name: str
  draft: str

@route.post("/canvas")
def findAll(payload = Depends(get_current)):
  try:
    conn = getConn()
    cur = conn.cursor()
    
    sql = f'''
          SELECT `no`, `name`, `draft`, `regDate`
            FROM gotham.`canvas`
          WHERE useYn = 'Y'
            AND regUserNo = {payload["userNo"]}
          Order By 1 desc
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
  
@route.put("/canvas")
def insert(canvas: Canvas, payload = Depends(get_current)):
  try:
    conn = getConn()
    cur = conn.cursor()
    
    sql = f'''
          INSERT INTO gotham.`canvas`
            (`name`, `draft`, `useYn`, `regUserNo`)
          VALUE 
            ('{canvas.name}', '{canvas.draft}', 'Y', {payload["userNo"]})  
    '''
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    return {"status": True}
  except mariadb.Error as e:
    print(f"MariaDB 오류 발생: {e}")
    return {"status": False}
