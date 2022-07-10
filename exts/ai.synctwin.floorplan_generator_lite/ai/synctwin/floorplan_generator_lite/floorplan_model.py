# (C) synctwin GmbH 2022 
# license: GPL3 

from pydantic import BaseModel, Field
from typing import List 
from pxr import Usd, Kind 
from PIL import Image

class FloorPlanModel(BaseModel):
    width: float = 0
    depth: float = 0
    resolution_x : int = 0
    resolution_y : int = 0 
    image_url: str = ""
    scale_x: float = 1
    scale_y: float = 1  
    aspect_ratio : float = 1 

    def set_image_url(self, url):
        self.image_url = url 
        img = Image.open(url)
        self.resolution_x, self.resolution_y = img.size
        self._update_size()

    def set_scale(self, x, y):
        self.scale_x = x
        self.scale_y = y 
        self._update_size()

    def set_size(self, w,h): 
        self.width = w
        self.depth = h
        self.aspect_ratio = self.width / self.depth
        self.scale_x = self.width / self.resolution_x 
        self.scale_y = self.depth / self.resolution_y


    def _update_size(self):
        self.width = self.resolution_x * self.scale_x
        self.depth = self.resolution_y * self.scale_y
        self.aspect_ratio = self.width / self.depth


