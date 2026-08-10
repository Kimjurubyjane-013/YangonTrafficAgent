import customtkinter as ctk
import os
import json
import webbrowser


class MapPanel(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(
            parent,
            corner_radius=15
        )


        title = ctk.CTkLabel(
            self,
            text="🗺 Yangon Route Map",
            font=("Arial",22,"bold")
        )

        title.pack(
            pady=10
        )


        self.route = []
        self.vehicle = "Car"


        self.open_button = ctk.CTkButton(
            self,
            text="🌐 Open Yangon Map",
            width=250,
            height=40,
            command=self.open_map
        )

        self.open_button.pack(
            pady=10
        )



        self.status = ctk.CTkLabel(
            self,
            text="Waiting for route...",
            font=("Arial",14)
        )

        self.status.pack(
            pady=10
        )



    # ==========================
    # Receive route from agent
    # ==========================

    def update_route(
            self,
            route,
            vehicle="Car"
    ):

        self.route = route
        self.vehicle = vehicle


        if route:

            self.status.configure(
                text=
                "Route Loaded:\n"
                +
                " → ".join(route)
            )

            self.create_map_file()


        else:

            self.status.configure(
                text="Waiting for route..."
            )



    # ==========================
    # Create HTML map
    # ==========================

    def create_map_file(self):


        data = {

            "route": self.route,

            "vehicle": self.vehicle

        }


        path = os.path.abspath(
            "web/map.html"
        )


        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            html = f.read()



        inject = f"""

<script>

window.routeData =
{json.dumps(data)};

</script>

"""


        html = html.replace(
            "</body>",
            inject + "</body>"
        )



        temp = os.path.abspath(
            "web/generated_map.html"
        )


        with open(
            temp,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(html)



    # ==========================
    # Open browser map
    # ==========================

    def open_map(self):

        file_path = os.path.abspath(
            "web/generated_map.html"
        )


        if os.path.exists(file_path):

            webbrowser.open(
                "file:///" + file_path
            )

        else:

            self.create_map_file()

            webbrowser.open(
                "file:///" + file_path
            )