from pydantic import BaseModel


class Location3d(BaseModel):
    x : float = 0.0
    y : float = 0.0
    z : float = 0.0


class RGBColor(BaseModel):
    red_value : float 
    green_value : float 
    blue_value : float 
