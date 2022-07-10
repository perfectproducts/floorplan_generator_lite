import omni.ext
import omni.ui as ui
import os 
from omni.kit.window.filepicker import FilePickerDialog
from omni.kit.widget.filebrowser import FileBrowserItem
from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade
from .floorplan_customdata import FloorPlanCustomData
from .floorplan_model import FloorPlanModel
from .floorplan_builder import FloorPlanBuilder

# Python code to read image


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class FloorPlanGeneratorLite(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def set_image_url(self, url):
        self._model.set_image_url(url)
        self.refresh(True)

    def on_image_file_selected(self, dialog, dirname, filename: str):        
        self._image_file = filename 
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
    
    def keep_ar(self):
        return self._keep_ratio_check.model.get_value_as_bool()

    def set_scale_x(self, v):        
        self._model.set_scale(v, v if self.keep_ar() else self._model.scale_y)
        self.refresh(create=True)

    def set_scale_y(self, v):        
        self._model.set_scale(v if self.keep_ar() else self._model.scale_x, v)
        self.refresh(create=True)

    def set_size_x(self, v):        
        self._model.set_size(v, v/self._model.aspect_ratio if self.keep_ar() else self._model.depth)
        self.refresh(create=True)

    def set_size_y(self, v):        
        self._model.set_size( v*self._model.aspect_ratio if self.keep_ar() else self._model.width, v)
        self.refresh(create=True)        

    def on_startup(self, ext_id):        
        self._SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))
        self._window = ui.Window("Floor Plan Generator Lite", width=400, height=400)
        
        self._model = FloorPlanModel()

        with self._window.frame:
            with ui.VStack():
                
                self._img = ui.Image(f"{self._SCRIPT_ROOT}/bitmaps/select_image.png")
                with ui.VStack():
                    with ui.HStack():
                        ui.Label("Source", height=30, width=75)
                        self._image_label = ui.Label("[select an image]", height=30)
                        
                        ui.Button(
                                "...",
                                height=30,
                                width=30,
                                tooltip="select plan image...",
                                clicked_fn=lambda: self.show_image_selection_dialog()
                            )

                    
                    with ui.HStack(spacing=5):
                        ui.Label("Resolution", width=70, height=30)
                        args = [0,0]
                        self._res_field = ui.MultiIntField(*args, h_spacing=5, enabled=False, height=25) 
                    with ui.HStack(spacing=5, height=30):
                        ui.Label("Scale", width=70)
                        args = [1.0,1.0]
                        self._scale_field = ui.MultiFloatDragField(*args, h_spacing=5, height=25) 
                        
                        m = self._scale_field.model
                        m.get_item_value_model(m.get_item_children()[0]).add_end_edit_fn(lambda m:self.set_scale_x(m.get_value_as_float()))
                        m.get_item_value_model(m.get_item_children()[1]).add_end_edit_fn(lambda m:self.set_scale_y(m.get_value_as_float()))

                    with ui.HStack(spacing=5, height=30):
                        ui.Label("Size", width=70)
                        args = [1.0,1.0]
                        self._size_field = ui.MultiFloatDragField(*args, h_spacing=5, height=25)
                        m = self._size_field.model
                        m.get_item_value_model(m.get_item_children()[0]).add_end_edit_fn(lambda m:self.set_size_x(m.get_value_as_float()))
                        m.get_item_value_model(m.get_item_children()[1]).add_end_edit_fn(lambda m:self.set_size_y(m.get_value_as_float()))


                    with ui.HStack(height=30):
                        ui.Spacer()
                        with ui.VStack(style={"margin_width": 0}, height=30, width=30):
                            ui.Spacer()
                            self._keep_ratio_check  = ui.CheckBox( height=0 )
                            self._keep_ratio_check.model.set_value(True)
                            ui.Spacer()
                        ui.Label("keep aspect ratio",  height=30)
                    ui.Spacer()    
                
                #self._create_button = ui.Button("create", height=30, clicked_fn=lambda : self.create())
                #self.set_image_url("E:/_STASH/SyncTwinFloorMaps/floormaps/exts/ai.synctwin.floormaps/ai/synctwin/floormaps/bitmaps/samplemap.png")

    def set_multifield(self, field, a, b)->bool:
        changed = False
        m =field.model
        v1 = m.get_item_value_model(m.get_item_children()[0])
        if v1.get_value_as_float() != float(a):
            v1.set_value(a)
            changed = True 
        v2 = m.get_item_value_model(m.get_item_children()[1])            
        if v2.get_value_as_float() != float(b):            
            v2.set_value(b)
            changed = True 
        return changed 
        
    def refresh(self, create=False):
        self._img.source_url =  self._model.image_url                
        self._image_label.text = os.path.basename(self._model.image_url) 
        self._image_label.tooltip = self._model.image_url
        changed = False 
        changed |= self.set_multifield(self._res_field, self._model.resolution_x, self._model.resolution_y)
        changed |= self.set_multifield(self._scale_field, self._model.scale_x, self._model.scale_y)
        changed |= self.set_multifield(self._size_field, self._model.width, self._model.depth)
        if create and changed:
            self.create()

    def set_dirty(self):
        self._create_button.text = "create..."
        self._create_button.enabled = True 

    def focus_selection(self):
        # omni.kit.viewport_legacy is optional dependancy
        try:
            import omni.kit.viewport_legacy
            viewport = omni.kit.viewport_legacy.get_viewport_interface()
            if viewport:
                window = viewport.get_viewport_window()
                window.focus_on_selected()
        except:
            pass

    def create(self):
        context = omni.usd.get_context()       
        context.new_stage()
        stage = context.get_stage()

        floor_path = FloorPlanBuilder().build(stage, self._model)
        omni.kit.commands.execute(
            "SelectPrimsCommand", old_selected_paths=[], new_selected_paths=[floor_path], expand_in_stage=True
        )
        self.focus_selection()


    def on_shutdown(self):        
        self._window = None


    