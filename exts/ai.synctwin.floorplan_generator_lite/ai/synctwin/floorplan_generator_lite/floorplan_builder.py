from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade
from .floorplan_customdata import FloorPlanCustomData
from .floorplan_model import FloorPlanModel

class FloorPlanBuilder:

    def build(self, stage : Usd.Stage, model : FloorPlanModel):
        self._model = model 
        cd = FloorPlanCustomData(self._model)
        cd.write(stage)
        root_path = FloorPlanCustomData.ROOT_PATH
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

        modelRoot = UsdGeom.Xform.Define(stage, root_path)
        Usd.ModelAPI(modelRoot).SetKind(Kind.Tokens.component)
        map_path = f"{root_path}/map"
        billboard = UsdGeom.Mesh.Define(stage, map_path)
        sx = self._model.width 
        sy = self._model.depth
        left = -sx/2
        right = sx/2
        top = -sy/2 
        bottom = sy/2
        billboard.CreatePointsAttr([(left, top, 0), (right, top, 0), (right, bottom, 0), (left, bottom, 0)])
        billboard.CreateFaceVertexCountsAttr([4])
        billboard.CreateFaceVertexIndicesAttr([0,1,2,3])
        billboard.CreateExtentAttr([(left, top, 0), (right, bottom, 0)])
        texCoords = billboard.CreatePrimvar("st",
                                            Sdf.ValueTypeNames.TexCoord2fArray,
                                            UsdGeom.Tokens.varying)
        texCoords.Set([(0, 0), (1, 0), (1,1), (0, 1)])
        #--
        material_path = f"{root_path}/map_material"
        material = UsdShade.Material.Define(stage, material_path)
        pbrShader = UsdShade.Shader.Define(stage, f'{material_path}/PBRShader')
        pbrShader.CreateIdAttr("UsdPreviewSurface")
        pbrShader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
        pbrShader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)

        material.CreateSurfaceOutput().ConnectToSource(pbrShader.ConnectableAPI(), "surface")
        #-
        stReader = UsdShade.Shader.Define(stage, f'{material_path}/stReader')
        stReader.CreateIdAttr('UsdPrimvarReader_float2')

        diffuseTextureSampler = UsdShade.Shader.Define(stage,f'{material_path}/diffuseTexture')
        diffuseTextureSampler.CreateIdAttr('UsdUVTexture')
        diffuseTextureSampler.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(self._model.image_url)
        diffuseTextureSampler.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(stReader.ConnectableAPI(), 'result')
        diffuseTextureSampler.CreateOutput('rgb', Sdf.ValueTypeNames.Float3)
        pbrShader.CreateInput("diffuseColor", 
                              Sdf.ValueTypeNames.Color3f).ConnectToSource(diffuseTextureSampler.ConnectableAPI()
                              , 'rgb')
        #-
        stInput = material.CreateInput('frame:stPrimvarName', Sdf.ValueTypeNames.Token)
        stInput.Set('st')

        stReader.CreateInput('varname',Sdf.ValueTypeNames.Token).ConnectToSource(stInput)
        UsdShade.MaterialBindingAPI(billboard).Bind(material)
        return root_path
