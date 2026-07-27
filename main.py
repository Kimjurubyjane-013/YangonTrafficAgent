import customtkinter as ctk

from ui.control_panel import ControlPanel
from ui.map_panel import MapPanel


class YangonTrafficApp(ctk.CTk):

    def __init__(self):

        super().__init__()

        self.title(
            "Yangon Traffic Agent"
        )

        self.geometry(
            "1200x700"
        )


        # Main layout

        self.grid_columnconfigure(
            0,
            weight=0
        )

        self.grid_columnconfigure(
            1,
            weight=1
        )

        self.grid_rowconfigure(
            0,
            weight=1
        )


        # Map panel first
        self.map_panel = MapPanel(
            self
        )

        self.map_panel.grid(
            row=0,
            column=1,
            padx=20,
            pady=20,
            sticky="nsew"
        )


        # Control panel

        self.control_panel = ControlPanel(
            self,
            self.update_map
        )

        self.control_panel.grid(
            row=0,
            column=0,
            padx=20,
            pady=20,
            sticky="ns"
        )



    def update_map(self, result):

        self.map_panel.update_route(
            result
        )



if __name__ == "__main__":

    app = YangonTrafficApp()

    app.mainloop()