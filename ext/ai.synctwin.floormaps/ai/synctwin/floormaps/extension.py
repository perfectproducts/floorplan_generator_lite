from ai.synctwin.floormaps.mfgstd_floorplan_model import MfgStdFloorPlanModel
import omni.ext
import omni.ui as ui
import os 
from omni.kit.window.filepicker import FilePickerDialog
from omni.kit.widget.filebrowser import FileBrowserItem
from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade
from .mfgstd_floorplan_model import MfgStdFloorPlanCustomData

# Python code to read image


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class MyExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def set_image_url(self, url):
        self._model.set_image_url(url)
        self.refresh()

    def on_image_file_selected(self, dialog, dirname, filename: str):        
        self._image_file = filename 
        print(f"-> image select {filename}")
        
        self.set_image_url(f"{dirname}/{filename}")
        dialog.hide()            
        self.create()
        

    def show_image_selection_dialog(self):
        heading = "Select Folder..."
        dialog = FilePickerDialog(
            heading,
            allow_multi_selection=False,
            apply_button_label="select file",
            click_apply_handler=lambda filename, dirname: self.on_image_file_selected(dialog, dirname, filename),
            file_extension_options = [("*.png", "Images"), ("*.jpg", "Images")]
            
        )            
        dialog.show()

    def on_startup(self, ext_id):
        print("[ai.synctwin.floormaps] MyExtension startup")
        self._SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))
        self._window = ui.Window("Floor Plan Helper", width=300, height=300)
        
        self._model = MfgStdFloorPlanModel()

        with self._window.frame:
            with ui.VStack():
                
                self._img = ui.Image(f"{self._SCRIPT_ROOT}/bitmaps/select_image.png" )
                self._image_label = ui.Label("-", height=30)
                self._resolution_label = ui.Label("-", height=30)

                def on_click():
                    print("clicked!")
                    self.set_image_url(f"{self._SCRIPT_ROOT}/bitmaps/samplemap2.PNG") 
                    self.create()

                #ui.Button("test", clicked_fn=lambda: on_click())

                ui.Button(
                        "select image...",
                        height=30,
                        tooltip="select plan image...",
                        clicked_fn=lambda: self.show_image_selection_dialog()
                    )
    def refresh(self):
        self._img.source_url =  self._model.image_url
        self._resolution_label.text = f"Resolution: {self._model.resolution_x}x{self._model.resolution_y}"
        self._image_label.text = f"Image: {os.path.basename(self._model.image_url)}"


    def on_shutdown(self):
        print("[ai.synctwin.floormaps] MyExtension shutdown")
        self._window = None


    def create(self):
        context = omni.usd.get_context()       
        context.new_stage()
        stage = context.get_stage()
        cd = MfgStdFloorPlanCustomData(self._model)
        cd.write(stage)

        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

        modelRoot = UsdGeom.Xform.Define(stage, "/floorplan")
        Usd.ModelAPI(modelRoot).SetKind(Kind.Tokens.component)
        billboard = UsdGeom.Mesh.Define(stage, "/floorplan/card")
        sx = self._model.width 
        sy = self._model.depth
        left = -sx/2
        right = sx/2
        top = -sy/2 
        bottom = sy/2
        billboard.CreatePointsAttr([(left, top, 0), (right, top, 0), (right, bottom, 0), (left, bottom, 0)])
        billboard.CreateFaceVertexCountsAttr([4])
        billboard.CreateFaceVertexIndicesAttr([0,1,2,3])
        billboard.CreateExtentAttr([(-430, -145, 0), (430, 145, 0)])
        texCoords = billboard.CreatePrimvar("st",
                                            Sdf.ValueTypeNames.TexCoord2fArray,
                                            UsdGeom.Tokens.varying)
        texCoords.Set([(0, 0), (1, 0), (1,1), (0, 1)])
        #--
        material = UsdShade.Material.Define(stage, '/floorplan/boardMat')
        pbrShader = UsdShade.Shader.Define(stage, '/floorplan/boardMat/PBRShader')
        pbrShader.CreateIdAttr("UsdPreviewSurface")
        pbrShader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
        pbrShader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)

        material.CreateSurfaceOutput().ConnectToSource(pbrShader.ConnectableAPI(), "surface")
        #-
        stReader = UsdShade.Shader.Define(stage, '/floorplan/boardMat/stReader')
        stReader.CreateIdAttr('UsdPrimvarReader_float2')

        diffuseTextureSampler = UsdShade.Shader.Define(stage,'/floorplan/boardMat/diffuseTexture')
        diffuseTextureSampler.CreateIdAttr('UsdUVTexture')
        diffuseTextureSampler.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(self._model.image_url)
        diffuseTextureSampler.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(stReader.ConnectableAPI(), 'result')
        diffuseTextureSampler.CreateOutput('rgb', Sdf.ValueTypeNames.Float3)
        pbrShader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(diffuseTextureSampler.ConnectableAPI(), 'rgb')
        #-
        stInput = material.CreateInput('frame:stPrimvarName', Sdf.ValueTypeNames.Token)
        stInput.Set('st')

        stReader.CreateInput('varname',Sdf.ValueTypeNames.Token).ConnectToSource(stInput)
        UsdShade.MaterialBindingAPI(billboard).Bind(material)
