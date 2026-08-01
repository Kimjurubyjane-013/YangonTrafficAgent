import customtkinter as ctk


class MapPanel(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(
            parent,
            corner_radius=15
        )


        self.title = ctk.CTkLabel(
            self,
            text="🗺 Yangon Map",
            font=("Arial",22,"bold")
        )

        self.title.pack(
            pady=10
        )


        self.route_display = ctk.CTkTextbox(
            self,
            width=400,
            height=400,
            font=("Arial",16)
        )

        self.route_display.pack(
            padx=20,
            pady=20,
            fill="both",
            expand=True
        )


        self.route_display.insert(
            "0.0",
            "Waiting for route..."
        )

        self.route_display.configure(
            state="disabled"
        )



    def update_route(self, route):

        self.route_display.configure(
            state="normal"
        )


        self.route_display.delete(
            "0.0",
            "end"
        )


        if not route:

            self.route_display.insert(
                "0.0",
                "Waiting for route..."
            )


            self.route_display.configure(
                state="disabled"
            )

            return



        map_text = "🗺 Recommended Route\n\n"


        for index, place in enumerate(route):

            map_text += f"● {place}\n"


            if index != len(route)-1:

                map_text += "      |\n"
                map_text += "      ↓\n"



        self.route_display.insert(
            "0.0",
            map_text
        )


        self.route_display.configure(
            state="disabled"
        )