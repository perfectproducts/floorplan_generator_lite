from .floorplan_model import FloorPlanModel
from pxr import Usd
from pxr import Kind

class FloorPlanCustomData:
    ROOT_PATH = "/World/FloorPlan"
    def __init__(self, model:FloorPlanModel) -> None:
        self._model = model 

    def write(self, stage:Usd.Stage)->bool:
        root = stage.DefinePrim(FloorPlanCustomData.ROOT_PATH)                
        Usd.ModelAPI(root).SetKind(Kind.Tokens.component)        
        root.SetCustomDataByKey("mfgstd:schema", "FloorPlan#1.0.0")
        d = self._model.dict()
        for k in d:
            root.SetCustomDataByKey(f"mfgstd:properties:{k}", d[k]) 
        return True 

    def read(self, stage:Usd.Stage)->bool:
        root = stage.GetPrimAtPath("/World/FloorPlan")
        if not root:
            return False         
        schema = root.GetCustomDataByKey("mfgstd:schema")

        return True 





