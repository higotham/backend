from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from config.db import getConn
from config.token import get_current
import json
from urllib import request
import asyncio
import uuid
import base64
import random
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

COMFYUI_URL = os.getenv('COMFYUI_URL')
route = APIRouter(tags=["이미지 생성"])

class Prompt(BaseModel):
  prompt : str
  init_image: str
  model: int
  aspect: int
  seed: Optional[int] = Field(default=None)
  controlAfterGenerate: Optional[str] = Field(default="randomize")
  step: Optional[int] = Field(default=20, ge=1, le=100)
  cfg: Optional[int] = Field(default=7, ge=1, le=30)
  samplerName: Optional[str] = Field(default="dpmpp_2m")
  scheduler: Optional[str] = Field(default="normal")
  denoise: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)

  
models = [
  "theSixthSenseRealistic_v10.safetensors",
  "anim8drawIllustriousXL_v10.safetensors",
  "ghostmix_v20Bakedvae.safetensors",
  "3dfeelingColdPony_v10BakedVae.safetensors"
]
aspects = [
  {'width_ratio': 1, 'height_ratio': 1},
  {'width_ratio': 4, 'height_ratio': 3},
  {'width_ratio': 3, 'height_ratio': 4},
  {'width_ratio': 16, 'height_ratio': 9},
  {'width_ratio': 9, 'height_ratio': 16},
]

@route.post("/gen")
async def comfyUI(prompt : Prompt, payload = Depends(get_current)):
  try:  
    # p = "a majestic lion with a crown of stars, photorealistic"
    with open("flow/1.json", "r", encoding="utf-8") as f:
      workflow = json.load(f)
      
    # 1. 긍정 프롬프트
    workflow["6"]["inputs"]["text"] = prompt.prompt

    # 2. 입력 이미지
    startIndex = prompt.init_image.find(",") + 1
    image_data = base64.b64decode(prompt.init_image[startIndex:])
    base64_data = base64.b64encode(image_data).decode("utf-8")
    workflow["25"]["inputs"]["data"] = base64_data
    workflow["25"]["class_type"] = "LoadImageFromBase64"
    
    # 3. 생성형 AI 모델
    workflow["14"]["inputs"]["ckpt_name"] = models[prompt.model]
    
    # 4. 이미지 비율
    aspect = aspects[prompt.aspect]
    workflow["23"]["inputs"]["width_ratio"] = aspect["width_ratio"]
    workflow["23"]["inputs"]["height_ratio"] = aspect["height_ratio"]
    
    # 5) ★ KSampler 옵션(노드 3)
    ks = workflow["3"]["inputs"]
    # seed
    if (prompt.controlAfterGenerate or "randomize").lower() == "randomize" or prompt.seed is None:
        ks["seed"] = random.randint(10**14, 10**15 - 1)
    else:
        ks["seed"] = int(prompt.seed)
    # 나머지
    ks["steps"]        = int(prompt.step if prompt.step is not None else 20)
    ks["cfg"]          = int(prompt.cfg  if prompt.cfg  is not None else 7)
    ks["sampler_name"] = (prompt.samplerName or "dpmpp_2m")
    ks["scheduler"]    = (prompt.scheduler  or "normal")
    ks["denoise"]      = float(prompt.denoise if prompt.denoise is not None else 0.5)
    workflow["3"]["inputs"] = ks

    # 6) ComfyUI 큐잉 & 진행 조회
    prompt_id = queue_prompt(workflow)
    result = await check_progress(prompt_id)
    
    # 7) 결과 저장 (/images/YYYYMMDD/랜덤.png) + DB 기록
    final_image_url, origin_name, file_name, file_path = None, None, None, None
    now = datetime.now()
    path = f"images/{now.strftime('%Y%m%d')}"
    if not os.path.exists(path):
      os.makedirs(path)
    
    for node_id, node_output in result['outputs'].items():
      if 'images' in node_output:
        for image in node_output['images']:
          final_image_url = f"http://{COMFYUI_URL}/api/view?filename={image['filename']}&type=output&subfolder="
          origin_name = image['filename'].replace(".png", "")
          file_name = uuid.uuid1().hex
          file_path = f"{path}/{file_name}.png"
          request.urlretrieve(final_image_url, file_path)
    
    if final_image_url:
      if file_name:
        conn = getConn()
        cur = conn.cursor()
        sql = f'''
              INSERT INTO auth.file 
              (`service`, `origin`, `name`, `ext`, `mediaType`, `attachPath`, `useYn`, `regUserNo`) 
              VALUE 
              (3, '{origin_name}', '{file_name}', '.png', 'image/png', '{file_path}', 'Y', {payload["userNo"]})
        '''
        cur.execute(sql)
        conn.commit()
        last_id = cur.lastrowid
        
        p = prompt.prompt.replace("\'", "\"")
        
        sql = f'''
              INSERT INTO gotham.`gallery`
              (`model`, `ratio`, `prompt`, `fileNo`, `useYn`, `regUserNo`) 
              VALUE 
              ({prompt.model}, {prompt.aspect}, '{p}', {last_id}, 'Y', {payload["userNo"]})
        '''
        cur.execute(sql)
        
        conn.commit()
        cur.close()
        conn.close()
        return {"status": True, "url": file_path}
    else:
      return {"status": False}
  except HTTPException as e:
    raise e
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

def queue_prompt(prompt_workflow):
  p = {"prompt": prompt_workflow}
  data = json.dumps(p).encode('utf-8')
  req = request.Request(f"http://{COMFYUI_URL}/prompt", data=data)
  try:
    res = request.urlopen(req)
    if res.code != 200:
      raise Exception(f"Error: {res.code} {res.reason}")
    return json.loads(res.read().decode('utf-8'))['prompt_id']
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

async def check_progress(prompt_id: str):
  while True:
    try:
      req = request.Request(f"http://{COMFYUI_URL}/history/{prompt_id}")
      res = request.urlopen(req)
      if res.code == 200:
        history = json.loads(res.read().decode('utf-8'))
        if prompt_id in history:
          return history[prompt_id]
    except Exception as e:
      print(f"Error checking progress: {str(e)}")
    await asyncio.sleep(1)

# class PromptTest(BaseModel):
#   prompt: str
#   init_image: str
#   model: int
#   aspect: int

# @route.post("/gentest")
# def test(promptTest: PromptTest): 
#   now = datetime.now()
#   formatted_date = now.strftime("%Y%m%d")
#   path = f"images/{formatted_date}"
#   if not os.path.exists(path):
#     os.makedirs(path)
#   image_data = base64.b64decode(promptTest.init_image.replace("data:image/png;base64,", ""))
#   file_name = uuid.uuid1().hex
#   file_path = f"{path}/{file_name}.png"
#   with open(file_path, "wb") as f:
#     f.write(image_data)
#   return {"status": True}
