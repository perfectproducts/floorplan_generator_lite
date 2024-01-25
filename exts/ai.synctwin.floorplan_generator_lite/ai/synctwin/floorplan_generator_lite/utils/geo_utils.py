from pxr import Gf, UsdGeom, Usd, Sdf, UsdShade
import omni.usd as ou
import unicodedata
from .common import Location3d
import re
import omni.kit.actions.core


class GeoUtils:
    
    def __init__(self, stage = None) -> None:
        self._stage = stage

    
    def open_or_create_stage(self, path, clear_exist=True) -> Usd.Stage:
        layer = Sdf.Layer.FindOrOpen(path)
        if not layer:
            layer = Sdf.Layer.CreateNew(path)
        elif clear_exist:
            layer.Clear()
            
        if layer:
            self._stage = Usd.Stage.Open(layer)
            return self._stage
        else:
            return None
        
    def create_lighting(self):
        # add lighting
        ar = omni.kit.actions.core.get_action_registry()
        set_lighting_mode_rig = ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_rig")
        set_lighting_mode_rig.execute(2)

    def create_material(self, material_path, name, diffuse_color) -> UsdShade.Material:
        material_path = ou.get_stage_next_free_path(self._stage, material_path, False)
        material = UsdShade.Material.Define(self._stage, material_path)

        shader_path = material_path + "/Shader"
        shader = UsdShade.Shader.Define(self._stage, shader_path)
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(diffuse_color)
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        

        return material

    def create_textured_rect_mesh(self, root_path, sx,sy, image_url):        
        stage = self._stage
        billboard = UsdGeom.Mesh.Define(stage, f"{root_path}/mesh")
        left = 0
        right = sx
        top = 0 
        bottom = sy
        billboard.CreatePointsAttr([(left, top, 0), (right, top, 0), (right, bottom, 0), (left, bottom, 0)])
        billboard.CreateFaceVertexCountsAttr([4])
        billboard.CreateFaceVertexIndicesAttr([0,1,2,3])
        billboard.CreateExtentAttr([(left, top, 0), (right, bottom, 0)])
        primvars_api = UsdGeom.PrimvarsAPI(billboard)
        texCoords = primvars_api.CreatePrimvar("primvars:st",
                                            Sdf.ValueTypeNames.TexCoord2fArray,
                                            UsdGeom.Tokens.faceVarying)
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
        diffuseTextureSampler.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(image_url)
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

    def location_to_vec3f(pos3d:Location3d)->Gf.Vec3f:
        return Gf.Vec3f(pos3d.x, pos3d.y, pos3d.z)
