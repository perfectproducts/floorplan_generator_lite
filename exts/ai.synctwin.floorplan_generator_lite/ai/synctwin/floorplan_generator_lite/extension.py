import omni.ext
import omni.ui as ui
import os 
from omni.kit.window.filepicker import FilePickerDialog
from omni.kit.widget.filebrowser import FileBrowserItem
from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Tf
from .floorplan_semantics import FloorPlanSemantics, FloorPlanImagePointSemantics
from .floorplan_model import FloorPlanModel, FloorPlanImagePoint
from .floorplan_simpleviz import FloorPlanSimpleViz
from .utils.geo_utils import GeoUtils
from omni.kit.pipapi import install
import tempfile
import gc
from pdf2image import convert_from_path
import tempfile 

# Python code to read image

class FloorPlanGeneratorLite(omni.ext.IExt):
    
    def on_startup(self, ext_id):      
        # get script path 
        
        
        self._window = ui.Window("SyncTwin Floor Plan Generator Lite", width=400, height=700)
        
        self._usd_context = omni.usd.get_context()

        self._model = FloorPlanModel()                
        self._selected_points = []
        self._ref_edited = False
        self._in_create = False 
        self._stage_listener = None 
        # local script pah 
        ext_manager = omni.kit.app.get_app().get_extension_manager()         
        self._local_extension_path = f"{ext_manager.get_extension_path(ext_id)}/ai/synctwin/floorplan_generator_lite"
        
        # subscribe to selection change 
        self._selection = self._usd_context.get_selection()
        self._sub_stage_event = self._usd_context.get_stage_event_stream().create_subscription_to_pop(
                self._on_stage_event
            )
        self.create_ui()
        self.clear()

    def create_ui(self):
        with self._window.frame:
            with ui.VStack():
                
                self._img = ui.Image(f"{self._local_extension_path}/bitmaps/select_image.png")
                
                with ui.VStack():
                    self._create_button = ui.Button("create...", clicked_fn=lambda :self.create(), enabled=False)
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
                        self._res_field = ui.MultiIntField(*args, h_spacing=5, enabled=False, height=25,min=1) 
                    

                    with ui.HStack(spacing=5, height=30):
                        ui.Label("Scale", width=70)
                        args = [1.0,1.0]
                        self._scale_field = ui.MultiFloatDragField(*args, h_spacing=5, height=25,min=0.0001) 
                        self.add_multifield_edit_cb(self._scale_field, 
                            lambda m:self.set_scale_x(m.get_value_as_float()),
                            lambda m:self.set_scale_y(m.get_value_as_float()))
                        

                    with ui.HStack(spacing=5, height=30):
                        ui.Label("Size", width=70)
                        args = [1.0,1.0]
                        self._size_field = ui.MultiFloatDragField(*args, h_spacing=5, height=25,min=0.0001)                        
                        self.add_multifield_edit_cb(self._size_field, 
                            lambda m:self.set_size_x(m.get_value_as_float()),
                            lambda m:self.set_size_y(m.get_value_as_float()))
                        

                    
                    with ui.HStack(height=30):
                        ui.Spacer()
                        with ui.VStack(style={"margin_width": 0}, height=30, width=30):
                            ui.Spacer()
                            self._keep_ratio_check  = ui.CheckBox( height=0 )
                            self._keep_ratio_check.model.set_value(True)
                            ui.Spacer()
                        ui.Label("keep aspect ratio",  height=30)

                    with ui.CollapsableFrame("Selected References"):
                        with ui.VStack():
                            self._selection_info_label = ui.Label("[nothing selected]", height=25)
                            with ui.HStack(spacing=5, height=30):
                                ui.Label("Distance", width=70)                                
                                self._ref_dist_field = ui.FloatField(height=25)                        
                                self._ref_dist_field.model.add_end_edit_fn(lambda m:self.set_ref_dist(m.get_value_as_float()))
                                
                                
                    ui.Spacer()    
        
    def set_image_url(self, url):
        self._model.set_image_url(url)
        self.refresh()

    def on_image_file_selected(self, dialog, dirname:str, filename: str):        
        print(f"selected {filename}")
        filepath = f"{dirname}/{filename}"
        if filename.endswith(".pdf"):
            is_remote = dirname.startswith("omniverse://")
            if is_remote:
                temp_dir = "c:/temp"                
                temp_name= f"{temp_dir}/{filename}"
                r = omni.client.copy(filepath, temp_name, behavior=omni.client.CopyBehavior.OVERWRITE)
                print(f"copy tmp {temp_name} {r}")
                if r != omni.client.Result.OK:
                    print("## could not copy file")
                    return 
                filepath = temp_name 

            print("convert pdf...")
            path = f"{self._local_extension_path}/poppler-0.68.0/bin"
            if not path in os.environ["PATH"]:
                os.environ["PATH"] += os.pathsep + path
            
            basename = os.path.splitext(filename)[0].replace(".","_")

            if is_remote:
                output_folder = temp_dir
            else:
                output_folder = dirname

            outfile = f"{output_folder}/{basename}.png"
            images_from_path = convert_from_path(filepath, output_folder=output_folder)

            images_from_path[0].save(outfile)
            print(f"written to {outfile}")    
            if is_remote: 
                upload_file = f"{dirname}/{basename}.png"
                r = omni.client.copy(outfile, upload_file,  behavior=omni.client.CopyBehavior.OVERWRITE)
                print(f"upload {r}")
                filepath = upload_file 
            else:
                filepath = outfile 
             
        self._image_file = filename
        self.set_image_url(filepath)
        dialog.hide()            
        # we'd like to create the map immediately after image selection 
        self.create()
        
    def show_image_selection_dialog(self):
        heading = "Select File..."
        dialog = FilePickerDialog(
            heading,
            allow_multi_selection=False,
            apply_button_label="select file",
            click_apply_handler=lambda filename, dirname: self.on_image_file_selected(dialog, dirname, filename),
            file_extension_options = [("*.png", "Images"), ("*.jpg", "Images"), ("*.pdf", "PDF documents")]
            
        )            
        dialog.show()
    
    def is_keep_ar_checked(self):
        return self._keep_ratio_check.model.get_value_as_bool()

    def set_scale_x(self, v):  
        if v <= 0:
            return       
        self._model.set_scale(v, v if self.is_keep_ar_checked() else self._model.scale_y)
        self.refresh()

    def set_scale_y(self, v):        
        if v <= 0:
            return       
        self._model.set_scale(v if self.is_keep_ar_checked() else self._model.scale_x, v)
        self.refresh()

    def set_size_x(self, v):     
        if v <= 0:
            return          
        self._model.set_size(v, v/self._model.aspect_ratio() if self.is_keep_ar_checked() else self._model.size_x)
        self.refresh()

    def set_size_y(self, v):        
        if v <= 0:
            return       
        self._model.set_size( v*self._model.aspect_ratio() if self.is_keep_ar_checked() else self._model.size_y, v)
        self.refresh()

    def set_ref_dist(self, v):        
        if v <= 0:
            return       
        self._ref_edited = True
        self.update_scale_from_selected_references()

    def set_selected_points(self, refs):
        
        if len(refs) != 2:
            self._selected_points = []
        else:        
            self._selected_points = refs
        self._ref_edited = False
        self.refresh()

    def update_scale_from_selected_references(self):
        dx = self._selected_points[0].distance_to(self._selected_points[1]) # these are image space points (-> pixels) 
        x = self._ref_dist_field.model.get_value_as_float()
        sx = x/dx
        
        if sx != self._model.scale_x or sx != self._model.scale_y:
            self._model.set_scale(sx,sx) 
            self.refresh()

    def _on_stage_event(self, event):
        #print(f'STAGE EVENT : stage event type int: {event.type}')
        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            selection = self._selection.get_selected_prim_paths()
            stage = self._usd_context.get_stage()
            #print(f'== selection changed with {len(selection)} items')
            if selection and stage:
                sel_refs = []
                for selected_path in selection:
                    #print(f' item {selected_path}:')
                    point = FloorPlanImagePointSemantics().read(stage, selected_path)
                    if point:
                        sel_refs.append(point)                                            
                self.set_selected_points(sel_refs)

        elif event.type == int(omni.usd.StageEventType.CLOSED):            
            if not self._in_create: 
                self.clear()

        elif event.type == int(omni.usd.StageEventType.OPENED):            
            if not self._in_create: 
                context = omni.usd.get_context()
                # check 
                stage = context.get_stage()
                model = FloorPlanSemantics().read(stage)
                if model:
                    self._model = model
                    self._stage_listener = Tf.Notice.Register(
                        Usd.Notice.ObjectsChanged, self._notice_changed, stage)
                self.refresh() 
                self.clear_dirty()     

    def _notice_changed(self, notice, stage):        
        for p in notice.GetChangedInfoOnlyPaths():            
            if FloorPlanImagePointSemantics.DEFAULT_ROOT_PATH in str(p.GetPrimPath()):                
                self.set_dirty()
                break            

        

    def get_multifield_floats(self, field):
        m =field.model
        v1 = m.get_item_value_model(m.get_item_children()[0]).get_value_as_float()
        v2 = m.get_item_value_model(m.get_item_children()[1]).get_value_as_float()
        return (v1,v2)

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

    def add_multifield_edit_cb(self, field, cb_a, cb_b):
        m = field.model
        m.get_item_value_model(m.get_item_children()[0]).add_end_edit_fn(cb_a)
        m.get_item_value_model(m.get_item_children()[1]).add_end_edit_fn(cb_b)                        

    def clear(self):
        self._model = FloorPlanModel()
        self._selected_points = []
        self._ref_edited = False
        self._in_create = False 
        self._stage_listener = None 
        self.clear_dirty()
        self.refresh()        
        
    def refresh(self):
        
        if self._model.image_url:
            self._img.source_url = self._model.image_url  
            self._has_image = True
        else:
            self._img.source_url = f"{self._local_extension_path}/bitmaps/select_image.png"
            self._has_image = False
        
        self._image_label.text = os.path.basename(self._model.image_url) 
        self._image_label.tooltip = self._model.image_url
        changed = False 
        changed |= self.set_multifield(self._res_field, self._model.resolution_x, self._model.resolution_y)
        changed |= self.set_multifield(self._scale_field, self._model.scale_x, self._model.scale_y)
        changed |= self.set_multifield(self._size_field, self._model.size_x, self._model.size_y)
        
        if changed and self._has_image:
            self.set_dirty()
        if not self._ref_edited:
            if len(self._selected_points) == 2:
                dx = self._selected_points[0].distance_to(self._selected_points[1])
                self._ref_dist_field.model.set_value( dx*self._model.scale_x)
                self._selection_info_label.text = f"{self._selected_points[0].name}, {self._selected_points[1].name}"
            else:
                self._selection_info_label.text = "[select two reference points]"
                self._ref_dist_field.model.set_value(0)
        self._res_field.enabled = self._has_image
        self._scale_field.enabled = self._has_image
        self._size_field.enabled = self._has_image
        self._ref_dist_field.enabled = self._has_image

    def set_dirty(self):
        self._create_button.text = "create..."
        self._create_button.enabled = True 

    def clear_dirty(self):
        self._create_button.text = "up to date"
        self._create_button.enabled = False 

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

    def update_poi_from_usd(self):
        context = omni.usd.get_context()        
        stage = context.get_stage()
        model = FloorPlanSemantics().read(stage)
        if model:
            self._model.points_of_interest = model.points_of_interest

    def create(self):        
        self._in_create = True
        self.update_poi_from_usd()

        context = omni.usd.get_context()        
        context.new_stage()

        stage = context.get_stage()
        gb = GeoUtils(stage)
        gb.create_lighting()
        self._stage_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._notice_changed, stage)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)        
        # get scale 
        root_prim = FloorPlanSemantics().write(stage, self._model)         
        floor_path = FloorPlanSimpleViz().write(stage, self._model, root_prim)        
        stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))
        omni.kit.commands.execute(
            "SelectPrimsCommand", old_selected_paths=[], new_selected_paths=[floor_path], expand_in_stage=True
        )
        
        self.focus_selection()
        self._in_create = False
        self.clear_dirty()        

    def on_shutdown(self):        
        self._window = None
        gc.collect()


    