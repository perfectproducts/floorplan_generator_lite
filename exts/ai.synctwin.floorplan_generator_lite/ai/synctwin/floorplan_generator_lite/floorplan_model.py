from __future__ import annotations
from weakref import ref
from pydantic import BaseModel, Field
from typing import List, Dict , Optional
from pxr import Usd, Kind,Gf
from PIL import Image
import carb
import omni.client 
import io 

class FloorPlanImagePoint(BaseModel):
    x : int = 0
    y : int = 0     
    name:str= ""
    point_type : str = ""
    
    def set(self, x,y):
        self.x = x
        self.y = y 
    def distance_to(self, point:FloorPlanImagePoint):
        return (Gf.Vec2f(point.x, point.y)-Gf.Vec2f(self.x,self.y)).GetLength()
    def component_distance_to(self, point:FloorPlanImagePoint):
        return (abs(point.x-self.x),abs(point.y-self.y))

class FloorPlanModel(BaseModel):
    size_y: float = 0
    size_x: float = 0
    resolution_x : int = 0
    resolution_y : int = 0 
    image_url: str = ""
    scale_x: float = 1.0
    scale_y: float = 1.0     
    points_of_interest : Dict[str, FloorPlanImagePoint] = dict()
    
    def poi(self, name, point_type) -> FloorPlanImagePoint:
        if not name: 
            return None 
        if not name in self.points_of_interest:
            self.points_of_interest[name] = FloorPlanImagePoint(name = name, point_type=point_type)
        return self.points_of_interest.get(name) 

    def add_poi(self, point:FloorPlanImagePoint):
        if not point.name: 
            print("no name")
            return  
        self.points_of_interest[point.name] = point 

    def reference_diff_x(self):
        return abs(self.reference_b().x-self.reference_a().x)

    def reference_diff_y(self):
        return abs(self.reference_b().y-self.reference_a().y)

    def reference_a(self):
        return self.poi("Reference_A", "Reference")
    def reference_origin(self):
        return self.poi("Origin", "Reference")

    def reference_b(self):
        return self.poi("Reference_B", "Reference") 

    def set_image_url(self, url):
        result, _, content = omni.client.read_file(url)
        if result != omni.client.Result.OK:
            carb.log_error(f"Can't read image file {url}, error code: {result}")
            return


        img = Image.open(io.BytesIO(memoryview(content).tobytes()))
        sx, sy = img.size
        if sx == 0 or sy == 0:
            print("# invalid image")
            return 

        self.image_url = url
        
        self.resolution_x = sx 
        self.resolution_y = sy
        self.scale_x = 1.0
        self.scale_y = 1.0 
        self.reference_a().set(0,0)
        self.reference_b().set(self.resolution_x, self.resolution_y)
        self.reference_origin().set(self.resolution_x/2, self.resolution_y/2)

        self._update_size()

    def set_scale(self, x, y):
        self.scale_x = x
        self.scale_y = y 
        self._update_size()

    def set_size(self, x, y): 
        self.size_x = x
        self.size_y= y
        self.aspect_ratio = self.size_x / self.size_y
        self.scale_x = self.size_x / self.resolution_x 
        self.scale_y = self.size_y / self.resolution_y


    def _update_size(self):
        self.size_x = self.resolution_x * self.scale_x
        self.size_y = self.resolution_y * self.scale_y
    def aspect_ratio(self)->float:
        return self.size_x / self.size_y
        



