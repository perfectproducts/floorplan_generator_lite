from .floorplan_model import FloorPlanImagePoint, FloorPlanModel
from pxr import Usd, Kind, UsdGeom, Sdf, Gf, Tf

class FloorPlanImagePointSemantics():
    SCHEMA = "PointOfInterest"
    SCHEMA_VERSION = "1.0.0"
    DEFAULT_ROOT_PATH = "PointsOfInterest"
    def write(self, stage, poi:FloorPlanImagePoint, prim_path) :
        poi_path = prim_path if prim_path!="" else f"{FloorPlanImagePointSemantics.DEFAULT_ROOT_PATH}/{Tf.MakeValidIdentifier(poi.name)}"
        poi_prim = stage.DefinePrim(poi_path,'Xform') 
        poi_prim.CreateAttribute("mfgstd:schema", Sdf.ValueTypeNames.String).Set(f"{FloorPlanImagePointSemantics.SCHEMA}#{FloorPlanImagePointSemantics.SCHEMA_VERSION}")
        poi_prim.CreateAttribute("mfgstd:properties:name", Sdf.ValueTypeNames.String).Set(poi.name)
        poi_prim.CreateAttribute("mfgstd:properties:point_type", Sdf.ValueTypeNames.String).Set(poi.point_type)
        xf = UsdGeom.Xformable(poi_prim)
        xf.AddTranslateOp().Set(Gf.Vec3f(poi.x, poi.y, 0))         
        
        return poi_path 

    def read(self, stage : Usd.Stage, poi_path : str)->FloorPlanImagePoint:
        poi_prim = stage.GetPrimAtPath(poi_path)
        schema = str(poi_prim.GetAttribute("mfgstd:schema").Get())
        if not schema.startswith(FloorPlanImagePointSemantics.SCHEMA):
            print("error reading schema")
            return None

        xf = UsdGeom.Xformable(poi_prim)    
        mat = Gf.Transform(xf.GetLocalTransformation())
        t = mat.GetTranslation()
        name = str(poi_prim.GetAttribute("mfgstd:properties:name").Get())
        point_type = str(poi_prim.GetAttribute("mfgstd:properties:point_type").Get())        
        poi = FloorPlanImagePoint(name=name, point_type=point_type, x=t[0], y=t[1])
        return poi 

class FloorPlanSemantics:
    SCHEMA = "Floorplan"
    SCHEMA_VERSION = "1.0.0"
    DEFAULT_ROOT_PATH = "/World/FloorPlan"

    
    def write(self, stage:Usd.Stage, model:FloorPlanModel, prim_path:str=""):
        root_path = FloorPlanSemantics.DEFAULT_ROOT_PATH if prim_path == "" else prim_path 
        root_prim = stage.DefinePrim(root_path, "Xform")           
        Usd.ModelAPI(root_prim).SetKind(Kind.Tokens.component)

        smantics_prim = root_prim  #semantics prim might go to /semantics, for now root prim
        smantics_prim.CreateAttribute("mfgstd:schema", Sdf.ValueTypeNames.String).Set(f"{FloorPlanSemantics.SCHEMA}#{FloorPlanSemantics.SCHEMA_VERSION}") 
        smantics_prim.CreateAttribute("mfgstd:properties:resolution_x", Sdf.ValueTypeNames.Int).Set(model.resolution_x) 
        smantics_prim.CreateAttribute("mfgstd:properties:resolution_y", Sdf.ValueTypeNames.Int).Set(model.resolution_y) 
        smantics_prim.CreateAttribute("mfgstd:properties:image_url", Sdf.ValueTypeNames.String).Set(model.image_url) 
        
         
        xf = UsdGeom.Xformable(root_prim)
        xf.ClearXformOpOrder () 
        origin = model.reference_origin()        
        
        xf.AddTranslateOp().Set(Gf.Vec3f(-origin.x*model.scale_x, -origin.y*model.scale_y,0) )
        xf.AddScaleOp().Set(Gf.Vec3f(model.scale_x, model.scale_y, min(model.scale_x, model.scale_y)) )
        
        poi_path = f"{root_path}/{FloorPlanImagePointSemantics.DEFAULT_ROOT_PATH}"
        stage.DefinePrim(poi_path, "Scope")
        for key, poi in model.points_of_interest.items():            
            FloorPlanImagePointSemantics().write(stage, poi,f"{poi_path}/{Tf.MakeValidIdentifier(key)}")
        return root_path 

    def read(self, stage:Usd.Stage, prim_path:str="")->FloorPlanModel:
        if not stage:
            return None 
        root_path = FloorPlanSemantics.DEFAULT_ROOT_PATH if prim_path == "" else prim_path 
        root_prim = stage.GetPrimAtPath(root_path)
        if not root_prim:
            return None         
        schema = str(root_prim.GetAttribute("mfgstd:schema").Get())
        if not schema.startswith(FloorPlanSemantics.SCHEMA):
            print("error reading schema")
            return None
        model = FloorPlanModel()
        model.resolution_x = int(root_prim.GetAttribute("mfgstd:properties:resolution_x").Get() )
        model.resolution_y = int(root_prim.GetAttribute("mfgstd:properties:resolution_y").Get() )
        model.image_url = str(root_prim.GetAttribute("mfgstd:properties:image_url").Get() )
        
        xf = UsdGeom.Xformable(root_prim)
        xf = Gf.Transform(xf.GetLocalTransformation())
        t = xf.GetTranslation()
        s = xf.GetScale()
        model.set_scale(s[0], s[1])
        o = model.reference_origin()
        o.set(-t[0], -t[1])
        pois_path = f"{root_path}/{FloorPlanImagePointSemantics.DEFAULT_ROOT_PATH}"
        pois_prim = stage.GetPrimAtPath(pois_path)        
        for poi_prim in pois_prim.GetChildren():
            point = FloorPlanImagePointSemantics().read(stage, poi_prim.GetPath())
            if point:
                model.add_poi(point)
        
        return model