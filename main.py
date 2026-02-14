"""
Wallpaper Splitter - Split wallpapers across multiple screens with different resolutions
A GUI application to crop wallpapers for multi-monitor setups with custom aspect ratios.
"""

import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageTk
import logging
import os


def setup_logging(level=logging.INFO):
    """Configure the logging system for the application."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


logger = logging.getLogger(__name__)


class ScreenConfig:
    """Represents the configuration of a screen with aspect ratio and position."""
    
    def __init__(self, screen_id, ratio_w=16, ratio_h=9, x=0, y=0):
        self.id = screen_id
        self.ratio_w = ratio_w
        self.ratio_h = ratio_h
        self.x = x
        self.y = y
        self.width = 1920
        self.height = 1080
        self.color = self.generate_color(screen_id)
    
    def generate_color(self, screen_id):
        """Generates a unique color for each screen."""
        colors = ["#CC9709", "#C74405", "#CC0058", "#692ECC", "#2F6ECC", "#080E24"]
        return colors[screen_id % len(colors)]
    
    def get_ratio_string(self):
        """Returns the ratio as a string (e.g., '16:9')."""
        return f"{self.ratio_w}:{self.ratio_h}"
    
    def get_box(self):
        """Returns coordinates for PIL crop (left, top, right, bottom)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    def calculate_resolution(self, ref_width, ref_height, scale_percent):
        """
        Calculates resolution based on reference and scale.
        
        Args:
            ref_width: Reference width
            ref_height: Reference height
            scale_percent: Scale percentage (0-100)
                          0% = ×0.5, 50% = ×1.0, 100% = ×2.0
        """
        scale_factor = 0.5 + (scale_percent / 100) * 1.5
        max_ref_side = max(ref_width, ref_height)
        scaled_max_side = max_ref_side * scale_factor
        
        if self.ratio_w >= self.ratio_h:
            self.width = round(scaled_max_side)
            self.height = round(scaled_max_side * (self.ratio_h / self.ratio_w))
        else:
            self.height = round(scaled_max_side)
            self.width = round(scaled_max_side * (self.ratio_w / self.ratio_h))
        
        logger.debug(
            f"Screen {self.id+1} ({self.ratio_w}:{self.ratio_h}): "
            f"{self.width}x{self.height} (scale {scale_percent}%, factor {scale_factor:.2f})"
        )


class ScreenConfigWidget(ctk.CTkFrame):
    """Widget for configuring an individual screen."""
    
    def __init__(self, parent, screen_config, on_update, on_delete):
        super().__init__(parent)
        self.screen_config = screen_config
        self.on_update = on_update
        self.on_delete = on_delete
        self.create_widgets()
    
    def create_widgets(self):
        """Creates the screen configuration interface."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color=self.screen_config.color)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(
            header_frame,
            text=f"Screen {self.screen_config.id + 1}",
            font=("Arial", 14, "bold")
        ).pack(side="left", padx=10, pady=5)
        
        self.ratio_label = ctk.CTkLabel(
            header_frame,
            text=f"{self.screen_config.get_ratio_string()} • "
                 f"{self.screen_config.width}x{self.screen_config.height}",
            font=("Arial", 12)
        )
        self.ratio_label.pack(side="left", padx=10)
        
        delete_btn = ctk.CTkButton(
            header_frame,
            text="Delete",
            width=100,
            command=self.delete_screen,
            fg_color="red",
            hover_color="darkred"
        )
        delete_btn.pack(side="right", padx=5)
        
        # Screen ratio configuration
        ratio_frame = ctk.CTkFrame(self)
        ratio_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            ratio_frame, 
            text="Screen Ratio:",
            font=("Arial", 12, "bold")
        ).pack(side="left", padx=5)
        
        ctk.CTkLabel(ratio_frame, text="Width:").pack(side="left", padx=5)
        self.ratio_w_entry = ctk.CTkEntry(ratio_frame, width=60)
        self.ratio_w_entry.insert(0, str(self.screen_config.ratio_w))
        self.ratio_w_entry.pack(side="left", padx=5)
        self.ratio_w_entry.bind("<KeyRelease>", lambda e: self.update_config())
        
        ctk.CTkLabel(ratio_frame, text=":").pack(side="left", padx=5)
        
        ctk.CTkLabel(ratio_frame, text="Height:").pack(side="left", padx=5)
        self.ratio_h_entry = ctk.CTkEntry(ratio_frame, width=60)
        self.ratio_h_entry.insert(0, str(self.screen_config.ratio_h))
        self.ratio_h_entry.pack(side="left", padx=5)
        self.ratio_h_entry.bind("<KeyRelease>", lambda e: self.update_config())
        
        # Position configuration
        position_frame = ctk.CTkFrame(self)
        position_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            position_frame, 
            text="Position:",
            font=("Arial", 12, "bold")
        ).pack(side="left", padx=5)
        
        ctk.CTkLabel(position_frame, text="X:").pack(side="left", padx=5)
        self.x_entry = ctk.CTkEntry(position_frame, width=100)
        self.x_entry.insert(0, str(self.screen_config.x))
        self.x_entry.pack(side="left", padx=5)
        self.x_entry.bind("<KeyRelease>", lambda e: self.update_config())
        
        ctk.CTkLabel(position_frame, text="Y:").pack(side="left", padx=5)
        self.y_entry = ctk.CTkEntry(position_frame, width=100)
        self.y_entry.insert(0, str(self.screen_config.y))
        self.y_entry.pack(side="left", padx=5)
        self.y_entry.bind("<KeyRelease>", lambda e: self.update_config())
        
        # Separator
        ctk.CTkFrame(self, height=2, fg_color="gray").pack(fill="x", padx=5, pady=10)
    
    def update_config(self):
        """Updates the screen configuration based on user input."""
        try:
            ratio_w = int(self.ratio_w_entry.get())
            ratio_h = int(self.ratio_h_entry.get())
            x = int(self.x_entry.get())
            y = int(self.y_entry.get())
            
            if ratio_w <= 0 or ratio_h <= 0:
                logger.error(f"Invalid ratio: {ratio_w}:{ratio_h}")
                return
            
            self.screen_config.ratio_w = ratio_w
            self.screen_config.ratio_h = ratio_h
            self.screen_config.x = x
            self.screen_config.y = y
            
            self.ratio_label.configure(
                text=f"{self.screen_config.get_ratio_string()} • "
                     f"{self.screen_config.width}x{self.screen_config.height}"
            )
            
            self.on_update()
            logger.info(f"Screen {self.screen_config.id + 1} updated automatically")
            
        except ValueError:
            pass
    
    def delete_screen(self):
        """Deletes this screen."""
        logger.info(f"Deleting screen {self.screen_config.id + 1}")
        self.on_delete(self.screen_config)
    
    def refresh_display(self):
        """Refreshes the calculated resolution display."""
        self.ratio_label.configure(
            text=f"{self.screen_config.get_ratio_string()} • "
                 f"{self.screen_config.width}x{self.screen_config.height}"
        )


class GlobalConfigWidget(ctk.CTkFrame):
    """Widget for global configuration (reference resolution + scale)."""
    
    def __init__(self, parent, on_change):
        super().__init__(parent)
        self.on_change = on_change
        self.ref_width = 2560
        self.ref_height = 1440
        self.scale_percent = 50
        self.create_widgets()
    
    def create_widgets(self):
        """Creates the global configuration interface."""
        title_label = ctk.CTkLabel(
            self,
            text="Global Settings",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(10, 5))
        
        # Reference resolution
        ref_frame = ctk.CTkFrame(self, fg_color="transparent")
        ref_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            ref_frame,
            text="Reference Resolution",
            font=("Arial", 11),
            text_color="gray"
        ).pack()
        
        input_frame = ctk.CTkFrame(ref_frame, fg_color="transparent")
        input_frame.pack(pady=5)
        
        self.ref_width_entry = ctk.CTkEntry(input_frame, width=80, height=30)
        self.ref_width_entry.insert(0, str(self.ref_width))
        self.ref_width_entry.pack(side="left", padx=2)
        self.ref_width_entry.bind("<KeyRelease>", lambda e: self.apply_reference())
        
        ctk.CTkLabel(input_frame, text="×", font=("Arial", 14)).pack(side="left", padx=5)
        
        self.ref_height_entry = ctk.CTkEntry(input_frame, width=80, height=30)
        self.ref_height_entry.insert(0, str(self.ref_height))
        self.ref_height_entry.pack(side="left", padx=2)
        self.ref_height_entry.bind("<KeyRelease>", lambda e: self.apply_reference())
        
        # Scale slider
        scale_frame = ctk.CTkFrame(self, fg_color="transparent")
        scale_frame.pack(fill="x", padx=10, pady=10)
        
        header = ctk.CTkFrame(scale_frame, fg_color="transparent")
        header.pack(fill="x")
        
        ctk.CTkLabel(
            header,
            text="Scale",
            font=("Arial", 11),
            text_color="gray"
        ).pack(side="left")
        
        self.scale_info_label = ctk.CTkLabel(
            header,
            text=f"{self.scale_percent}% (×1.0)",
            font=("Arial", 11, "bold"),
            text_color="gray"
        )
        self.scale_info_label.pack(side="right")
        
        self.scale_slider = ctk.CTkSlider(
            scale_frame,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self.on_slider_change,
            height=16
        )
        self.scale_slider.set(self.scale_percent)
        self.scale_slider.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            scale_frame,
            text="0% = ×0.5  •  50% = ×1.0  •  100% = ×2.0",
            font=("Arial", 9),
            text_color="gray"
        ).pack()
    
    def apply_reference(self):
        """Applies the new reference resolution."""
        try:
            new_width = int(self.ref_width_entry.get())
            new_height = int(self.ref_height_entry.get())
            
            if new_width <= 0 or new_height <= 0:
                logger.error("Invalid reference resolution")
                return
            
            self.ref_width = new_width
            self.ref_height = new_height
            
            logger.info(f"New reference resolution: {self.ref_width}x{self.ref_height}")
            self.on_change()
            
        except ValueError:
            logger.error("Invalid values for reference resolution")
    
    def on_slider_change(self, value):
        """Called when slider moves."""
        self.scale_percent = int(value)
        scale_factor = 0.5 + (self.scale_percent / 100) * 1.5
        
        self.scale_info_label.configure(
            text=f"{self.scale_percent}% (×{scale_factor:.2f})"
        )
        
        self.on_change()


class WallpaperSplitterApp:
    """Main application for splitting wallpapers across multiple screens."""
    
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Wallpaper Splitter")
        self.root.geometry("1400x900")
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.image = None
        self.image_path = None
        self.screens = []
        self.screen_widgets = []
        
        self.background_image = None
        self.canvas_bg_image = None
        self.scale_factor = 1.0
        
        self.create_widgets()
        logger.info("Application started")
    
    def create_widgets(self):
        """Creates all interface widgets."""
        header = ctk.CTkLabel(
            self.root, 
            text="Wallpaper Splitter", 
            font=("Arial", 24, "bold")
        )
        header.pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Left column: Configuration
        left_frame = ctk.CTkFrame(main_frame, width=500)
        left_frame.pack(side="left", fill="both", padx=10, pady=10)
        left_frame.pack_propagate(False)
        
        # Image section
        image_section = ctk.CTkFrame(left_frame, fg_color="transparent")
        image_section.pack(fill="x", padx=10, pady=10)
        
        load_button = ctk.CTkButton(
            image_section,
            text="Load Image",
            command=self.load_image,
            height=35,
            font=("Arial", 13)
        )
        load_button.pack(pady=5)
        
        self.image_info_label = ctk.CTkLabel(
            image_section,
            text="No image loaded",
            font=("Arial", 11),
            text_color="gray"
        )
        self.image_info_label.pack(pady=5)
        
        # Screens section
        screens_section = ctk.CTkFrame(left_frame, fg_color="transparent")
        screens_section.pack(fill="both", expand=True, padx=10, pady=10)
        
        screens_header = ctk.CTkFrame(screens_section, fg_color="transparent")
        screens_header.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(
            screens_header,
            text="Screens",
            font=("Arial", 14, "bold")
        ).pack(side="left")
        
        add_screen_btn = ctk.CTkButton(
            screens_header,
            text="+ Add",
            command=self.add_screen,
            width=80,
            height=28,
            font=("Arial", 12)
        )
        add_screen_btn.pack(side="right")
        
        self.screens_container = ctk.CTkScrollableFrame(screens_section, height=200)
        self.screens_container.pack(fill="both", expand=True)
        
        # Global configuration
        self.global_config = GlobalConfigWidget(
            left_frame,
            on_change=self.on_global_config_change
        )
        self.global_config.pack(fill="x", padx=10, pady=10)
        
        # Right column: Preview
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        preview_header = ctk.CTkFrame(right_frame, fg_color="transparent")
        preview_header.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            preview_header,
            text="Preview",
            font=("Arial", 14, "bold")
        ).pack(side="left", padx=10)
        
        extract_button = ctk.CTkButton(
            preview_header,
            text="EXTRACT ALL",
            command=self.extract_all,
            height=32,
            font=("Arial", 13, "bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        extract_button.pack(side="right", padx=10)
        
        self.preview_canvas = ctk.CTkCanvas(
            right_frame,
            bg="#2b2b2b",
            highlightthickness=0
        )
        self.preview_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.help_text = self.preview_canvas.create_text(
            400, 300,
            text="Load an image to start",
            fill="gray",
            font=("Arial", 16),
            anchor="center"
        )
    
    def load_image(self):
        """Loads an image file."""
        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            self.image = Image.open(file_path)
            self.image_path = file_path
            
            width, height = self.image.size
            filename = os.path.basename(file_path)
            
            info_text = f"{filename}\n{width} × {height} pixels"
            self.image_info_label.configure(text=info_text)
            
            self.update_preview_full()
            logger.info(f"Image loaded: {filename} ({width}x{height})")
            
        except Exception as e:
            self.image_info_label.configure(text="Loading error")
            logger.error(f"Error loading image: {e}")
    
    def add_screen(self):
        """Adds a new screen configuration."""
        screen_id = len(self.screens)
        screen_config = ScreenConfig(screen_id)
        self.screens.append(screen_config)
        
        widget = ScreenConfigWidget(
            self.screens_container,
            screen_config,
            on_update=self.on_screen_update,
            on_delete=self.delete_screen
        )
        widget.pack(fill="x", pady=10)
        self.screen_widgets.append(widget)
        
        self.recalculate_all_resolutions()
        logger.info(f"Screen {screen_id + 1} added")
    
    def delete_screen(self, screen_config):
        """Deletes a screen configuration."""
        try:
            index = self.screens.index(screen_config)
            
            self.screens.pop(index)
            widget = self.screen_widgets.pop(index)
            widget.destroy()
            
            # Reorganize IDs and colors
            for i, screen in enumerate(self.screens):
                screen.id = i
                screen.color = screen.generate_color(i)
            
            # Recreate widgets
            for widget in self.screen_widgets:
                widget.destroy()
            self.screen_widgets.clear()
            
            for screen in self.screens:
                widget = ScreenConfigWidget(
                    self.screens_container,
                    screen,
                    on_update=self.on_screen_update,
                    on_delete=self.delete_screen
                )
                widget.pack(fill="x", pady=10)
                self.screen_widgets.append(widget)
            
            self.recalculate_all_resolutions()
            logger.info("Screen deleted")
            
        except Exception as e:
            logger.error(f"Deletion error: {e}")
    
    def on_screen_update(self):
        """Called when a screen configuration is modified."""
        self.recalculate_all_resolutions()
    
    def on_global_config_change(self):
        """Called when global configuration changes."""
        self.recalculate_all_resolutions()
    
    def recalculate_all_resolutions(self):
        """Recalculates resolutions for all screens."""
        ref_width = self.global_config.ref_width
        ref_height = self.global_config.ref_height
        scale_percent = self.global_config.scale_percent
        
        logger.debug(
            f"Recalculating with ref={ref_width}x{ref_height}, scale={scale_percent}%"
        )
        
        for screen in self.screens:
            screen.calculate_resolution(ref_width, ref_height, scale_percent)
        
        for widget in self.screen_widgets:
            widget.refresh_display()
        
        self.update_preview_rectangles()
    
    def update_preview_full(self):
        """Completely updates preview (background image + rectangles)."""
        logger.debug("Complete preview update...")
        
        if self.image is None:
            logger.debug("No image")
            return
        
        self.preview_canvas.delete("all")
        self.preview_canvas.update()
        
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.root.after(100, self.update_preview_full)
            return
        
        # Calculate scale
        img_width, img_height = self.image.size
        scale_w = canvas_width / img_width
        scale_h = canvas_height / img_height
        self.scale_factor = min(scale_w, scale_h) * 0.9
        
        new_width = int(img_width * self.scale_factor)
        new_height = int(img_height * self.scale_factor)
        
        # Create background image
        self.background_image = self.image.resize(
            (new_width, new_height), 
            Image.Resampling.LANCZOS
        )
        self.canvas_bg_image = ImageTk.PhotoImage(self.background_image)
        
        # Center image
        self.x_offset = (canvas_width - new_width) // 2
        self.y_offset = (canvas_height - new_height) // 2
        
        # Display background
        self.preview_canvas.create_image(
            self.x_offset, self.y_offset,
            anchor="nw",
            image=self.canvas_bg_image,
            tags="background"
        )
        
        self.draw_rectangles()
        logger.debug("Complete preview updated")
    
    def update_preview_rectangles(self):
        """Updates only rectangles (keeps background image)."""
        if self.image is None or self.background_image is None:
            return
        
        logger.debug("Updating rectangles only...")
        
        self.preview_canvas.delete("rectangles")
        self.preview_canvas.delete("labels")
        
        self.draw_rectangles()
        logger.debug("Rectangles updated")
    
    def draw_rectangles(self):
        """Draws rectangles for all configured screens."""
        if not hasattr(self, 'x_offset') or not hasattr(self, 'y_offset'):
            return
        
        for screen in self.screens:
            x1 = int(screen.x * self.scale_factor) + self.x_offset
            y1 = int(screen.y * self.scale_factor) + self.y_offset
            x2 = int((screen.x + screen.width) * self.scale_factor) + self.x_offset
            y2 = int((screen.y + screen.height) * self.scale_factor) + self.y_offset
            
            self.preview_canvas.create_rectangle(
                x1, y1, x2, y2,
                outline=screen.color,
                width=3,
                tags="rectangles"
            )
            
            label_text = (
                f"Screen {screen.id + 1}\n"
                f"{screen.ratio_w}:{screen.ratio_h}\n"
                f"{screen.width}x{screen.height}\n"
                f"({screen.x}, {screen.y})"
            )
            self.preview_canvas.create_text(
                x1 + 5, y1 + 5,
                text=label_text,
                anchor="nw",
                fill=screen.color,
                font=("Arial", 10, "bold"),
                tags="labels"
            )
    
    def get_unique_filename(self, base_path):
        """Generates a unique filename by appending a number if needed."""
        if not os.path.exists(base_path):
            return base_path
        
        name, ext = os.path.splitext(base_path)
        counter = 2
        
        while True:
            new_path = f"{name}_{counter}{ext}"
            if not os.path.exists(new_path):
                return new_path
            counter += 1
    
    def extract_all(self):
        """Extracts all configured screen zones from the wallpaper."""
        if self.image is None:
            logger.warning("No image loaded")
            return
        
        if len(self.screens) == 0:
            logger.warning("No screens configured")
            return
        
        output_folder = filedialog.askdirectory(
            title="Select output folder",
            initialdir=os.path.expanduser("~")
        )
        
        if not output_folder:
            logger.info("Extraction cancelled by user")
            return
        
        extracted_count = 0
        errors = []
        
        for screen in self.screens:
            try:
                img_width, img_height = self.image.size
                
                if (screen.x < 0 or screen.y < 0 or 
                    screen.x + screen.width > img_width or 
                    screen.y + screen.height > img_height):
                    error_msg = f"Screen {screen.id + 1} exceeds image boundaries"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    continue
                
                cropped = self.image.crop(screen.get_box())
                
                ext = os.path.splitext(self.image_path)[1]
                filename = f"wallpaper_screen_{screen.ratio_w}-{screen.ratio_h}{ext}"
                filepath = os.path.join(output_folder, filename)
                filepath = self.get_unique_filename(filepath)
                
                cropped.save(filepath)
                extracted_count += 1
                
                logger.info(f"Screen {screen.id + 1} extracted: {filepath}")
                
            except Exception as e:
                error_msg = f"Error screen {screen.id + 1}: {e}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
        
        # Show result dialog
        result_window = ctk.CTkToplevel(self.root)
        result_window.title("Extraction Result")
        result_window.geometry("500x300")
        
        if extracted_count > 0:
            msg = (
                f"{extracted_count} screen(s) extracted!\n\n"
                f"Files saved in:\n{output_folder}"
            )
            if errors:
                msg += f"\n\n{len(errors)} error(s) occurred"
        else:
            msg = "No extraction succeeded"
        
        ctk.CTkLabel(
            result_window,
            text=msg,
            font=("Arial", 14),
            justify="center"
        ).pack(pady=30)
        
        if errors:
            error_text = "\n".join(errors[:3])
            ctk.CTkLabel(
                result_window,
                text=error_text,
                font=("Arial", 10),
                text_color="orange"
            ).pack(pady=10)
        
        ctk.CTkButton(
            result_window,
            text="OK",
            command=result_window.destroy,
            width=200,
            height=40
        ).pack(pady=20)
    
    def run(self):
        """Runs the application main loop."""
        self.root.mainloop()


def main():
    """Main entry point of the application."""
    setup_logging(level=logging.INFO)
    app = WallpaperSplitterApp()
    app.run()


if __name__ == "__main__":
    main()