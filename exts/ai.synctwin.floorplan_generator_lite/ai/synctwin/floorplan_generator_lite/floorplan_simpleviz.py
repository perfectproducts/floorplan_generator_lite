from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade,Tf
from .floorplan_model import FloorPlanModel
from .utils.geo_utils import GeoUtils
from .floorplan_semantics import FloorPlanImagePointSemantics
# simple viz assumes known structure from semantics 

class FloorPlanSimpleViz:
    
    def __init__(self) -> None:
        self.point_radius  = 2

    def write(self, stage : Usd.Stage, model : FloorPlanModel, root_path:str):
        self._model = model 
        
        map_root = stage.GetPrimAtPath(root_path)        
        sx = self._model.resolution_x 
        sy = self._model.resolution_y
        gb = GeoUtils(stage =stage)
        point_mat = gb.create_material(root_path, "point_material", (0, 0, 1))
        gb.create_textured_rect_mesh(root_path, sx, sy, model.image_url) 
       
        #--- create reference points 
        poi_path = f"{root_path}/{FloorPlanImagePointSemantics.DEFAULT_ROOT_PATH}"
        for key, poi in model.points_of_interest.items():            
            prim_path = f"{poi_path}/{Tf.MakeValidIdentifier(key)}"
            xf = stage.GetPrimAtPath(prim_path) 
            mesh_prim = stage.DefinePrim(f"{prim_path}/mesh", "Sphere")
            mesh_prim.GetAttribute("radius").Set(self.point_radius)
            UsdShade.MaterialBindingAPI(mesh_prim).Bind(point_mat)            
        
        return root_path
