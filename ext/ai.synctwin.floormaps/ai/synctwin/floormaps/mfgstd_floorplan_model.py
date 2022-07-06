from pydantic import BaseModel, Field
from typing import List 
from pxr import Usd, Kind 
from PIL import Image

class MfgStdFloorPlanModel(BaseModel):
    width: float = 0
    depth: float = 0
    resolution_x : int = 0
    resolution_y : int = 0 
    image_url: str = ""
    scale_x: float = 1
    scale_y: float = 1  
    def set_image_url(self, url):
        self.image_url = url 
        img = Image.open(url)
        self.resolution_x, self.resolution_y = img.size
        self.width = self.resolution_x * self.scale_x
        self.depth = self.resolution_y * self.scale_y
        



class MfgStdFloorPlanCustomData:
    def __init__(self, model:MfgStdFloorPlanModel) -> None:
        self._model = model 

    def write(self, stage:Usd.Stage)->bool:
        root = stage.DefinePrim("/World/floorplan")                
        Usd.ModelAPI(root).SetKind(Kind.Tokens.component)        
        root.SetCustomDataByKey("mfgstd:schema", "FloorPlan#1.0.0")
        d = self._model.dict()
        for k in d:
            root.SetCustomDataByKey(f"mfgstd:properties:{k}", d[k]) 
        return True 

    def read(self, stage:Usd.Stage)->bool:
        root = stage.GetPrimAtPath("/World/floorplan")
        if not root:
            return False         
        schema = root.GetCustomDataByKey("mfgstd:schema")

        return True 





