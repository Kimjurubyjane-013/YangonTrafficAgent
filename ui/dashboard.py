import customtkinter as ctk
from ui.control_panel import ControlPanel
from ui.map_panel import MapPanel
from ui.ai_panel import AIPanel


# Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class Dashboard(ctk.CTk):


    def find_route(self, request):
        print("Analyzing traffic...")


    def __init__(self):

        super().__init__()

        # Window Settings
        self.title("Yangon Smart Traffic Management Agent")
        self.geometry("1400x800")


        # Header
        header = ctk.CTkFrame(
            self,
            height=70
        )

        header.pack(fill="x")


        title = ctk.CTkLabel(
            header,
            text="🚦 Yangon Smart Traffic Management Agent",
            font=("Arial", 28, "bold")
        )

        title.pack(pady=20)



        # Main Area
        main_frame = ctk.CTkFrame(self)

        main_frame.pack(
            fill="both",
            expand=True
        )


        # Control Panel
        left_panel = ControlPanel(
            main_frame,
            self.find_route
        )

        left_panel.pack(
            side="left",
            fill="y",
            padx=10,
            pady=10
        )


        # Map Panel
        map_panel = MapPanel(main_frame)

        map_panel.pack(
            side="right",
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )


        # AI Panel
        bottom = ctk.CTkFrame(
            self,
            height=200
        )

        bottom.pack(
            fill="x",
            padx=10,
            pady=10
        )


        ai_panel = AIPanel(bottom)

        ai_panel.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )