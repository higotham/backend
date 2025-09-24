from fastapi import APIRouter, Depends
from pydantic import BaseModel
from config.db import getConn
from config.token import get_current
import mariadb
import json

route = APIRouter(tags=["스토리 보드"])

class StoryboardQuery(BaseModel):
  q: str

class StoryboardDelete(BaseModel):
  storyboards: str

class Storyboard(BaseModel):
  title: str
  tag: str
  
class StoryboardDetail(BaseModel):
  storyBoardNo: int
  order: int
  fileNo: int
  caption: str
  
class StoryboardDetails(BaseModel):
  storyboards: str

class StoryboardDetailDelete(BaseModel):
  no: int
  storyboards: str

@route.post("/storyboard")
def findAll(sbq: StoryboardQuery, payload = Depends(get_current)):
  try:
    conn = getConn()
    cur = conn.cursor()
    sql = f'''
          SELECT `no`, `title`, `tag`
            FROM gotham.`story_board`
          WHERE useYn = 'Y'
          AND `regUserNo` = {payload["userNo"]}
          AND `tag` like '%{sbq.q}%'
          ORDER BY `no` DESC
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
    
@route.post("/storyboard/{no}")
def findByOne(no: int, payload = Depends(get_current)):
  try:
    conn = getConn()
    cur = conn.cursor()
    
    sql = f'''
          SELECT `no`, `title`, `tag`
            FROM gotham.`story_board`
          WHERE useYn = 'Y'
            AND `regUserNo` = {payload["userNo"]}
            AND `no` = {no}
          ORDER BY `no` DESC
    '''
    cur.execute(sql)
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    result1 = dict(zip(columns, row)) if row else None
    
    sql = f'''
        SELECT sbd.`no`, sbd.`storyBoardNo`, sbd.`order`, sbd.`caption`, sbd.`useYn`, sbd.`regUserNo`,
            sbd.`fileNo`, f.attachPath		 
          FROM gotham.`story_board_detail` AS sbd
        LEFT JOIN auth.`file` AS f
            ON (sbd.fileNo = f.`no` AND f.useYn = 'Y')
        WHERE sbd.useYn = 'Y'
          AND sbd.`storyBoardNo` = {no}
        ORDER BY sbd.`order`
    '''
    cur.execute(sql)
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result2 = [dict(zip(columns, row)) for row in rows]
    result = {"story_board": result1, "story_board_detail": result2}
    return {"status": True, "result" : result}
  except mariadb.Error as e:
    print(f"MariaDB 오류 발생: {e}")
    return {"status": False}

@route.put("/storyboard")
def makeStoryBoard(sb: Storyboard, payload = Depends(get_current)):
  try:
    conn = getConn()
    cur = conn.cursor()
    sql = f'''
        INSERT INTO gotham.`story_board`
        (`title`, `tag`, `useYn`, `regUserNo`)
        VALUE 
        ('{sb.title}', '{sb.tag}', 'Y', {payload["userNo"]})
    '''
    cur.execute(sql)
    conn.commit()
    storyBoardNo = cur.lastrowid
    
    for order in range(1,7):
      sql = f'''
            INSERT INTO gotham.`story_board_detail` 
            (`storyBoardNo`, `order`, `fileNo`, `caption`, `useYn`, `regUserNo`)
            VALUE 
            ({storyBoardNo}, {order}, 0, null, 'Y', {payload["userNo"]})
      '''
      cur.execute(sql)
      conn.commit()
    
    cur.close()
    conn.close()
    return {"status": True}
  except mariadb.Error as e:
    print(f"MariaDB 오류 발생: {e}")
    return {"status": False}
  
@route.delete("/storyboard")
def deleteStoryBoard(sbd: StoryboardDelete, payload = Depends(get_current)):
  try:
    conn = getConn()
    cur = conn.cursor()
    
    storyBoardNos = sbd.storyboards.split(",")
    for no in storyBoardNos:
      sql = f'''
            UPDATE gotham.`story_board` SET useYn = 'N', modUserNo = {payload["userNo"]} WHERE `no` = {no}
      '''
      cur.execute(sql)
      conn.commit()
      
      sql = f'''
            UPDATE gotham.`story_board_detail` SET useYn = 'N', modUserNo = {payload["userNo"]} WHERE `storyBoardNo` = {no}
      '''
      cur.execute(sql)
      conn.commit()
    
    cur.close()
    conn.close()
    return {"status": True}
  except mariadb.Error as e:
    print(f"MariaDB 오류 발생: {e}")
    return {"status": False}
  
@route.put("/storyboard/detail")
def editDetail(sbd: StoryboardDetails, payload = Depends(get_current)):
  try:
    conn = getConn()
    cur = conn.cursor()
    
    storyBoards = json.loads(sbd.storyboards)
    for detail in storyBoards:
      caption = f"caption = '{detail["caption"]}'," if detail["caption"] != None else 'caption = null,'
      sql = f'''
            UPDATE gotham.`story_board_detail` 
              SET fileNo = {detail["fileNo"]},
                  {caption}
                  modUserNo = {payload["userNo"]}
            WHERE `storyBoardNo` = {detail["storyBoardNo"]}
              AND `no` = {detail["no"]}
      '''
      cur.execute(sql)
      conn.commit()
    
    cur.close()
    conn.close()
    return {"status": True}
  except mariadb.Error as e:
    print(f"MariaDB 오류 발생: {e}")
    return {"status": False}
  
@route.delete("/storyboard/detail")
def deleteDetail(sbd: StoryboardDetailDelete, payload = Depends(get_current)):
  try:
    conn = getConn()
    cur = conn.cursor()

    storyBoardNos = sbd.storyboards.split(",")
    for no in storyBoardNos:
      sql = f'''
          UPDATE gotham.`story_board_detail` 
            SET fileNo = 0,
                caption = null,
                modUserNo = {payload["userNo"]}
          WHERE `no` = {no}
      '''
      cur.execute(sql)
      conn.commit()
    cur.close()
    conn.close()
    
    return {"status": True}
  except mariadb.Error as e:
    print(f"MariaDB 오류 발생: {e}")
    return {"status": False}