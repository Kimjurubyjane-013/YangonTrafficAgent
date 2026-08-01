import customtkinter as ctk

from ui.control_panel import ControlPanel
from ui.map_panel import MapPanel
from ui.result_panel import ResultPanel
from ui.ai_recommendation import AIRecommendation

from agent.traffic_agent import run_traffic_agent



class YangonTrafficApp(ctk.CTk):

    def __init__(self):

        super().__init__()


        self.title(
            "Yangon Traffic Agent"
        )

        self.geometry(
            "1400x800"
        )


        # Grid
        # Map column widened (1 : 3 : 1) so there's room for
        # the planned 3D car animation

        self.grid_columnconfigure(
            0,
            weight=1
        )

        self.grid_columnconfigure(
            1,
            weight=3
        )

        self.grid_columnconfigure(
            2,
            weight=1
        )


        self.grid_rowconfigure(
            0,
            weight=1
        )


        # Map

        self.map_panel = MapPanel(
            self
        )

        self.map_panel.grid(
            row=0,
            column=1,
            padx=15,
            pady=15,
            sticky="nsew"
        )


        # Control

        self.control_panel = ControlPanel(
            self,
            self.find_route
        )

        self.control_panel.grid(
            row=0,
            column=0,
            padx=15,
            pady=15,
            sticky="nsew"
        )


        # Result

        self.result_panel = ResultPanel(
            self
        )

        self.result_panel.grid(
            row=0,
            column=2,
            padx=15,
            pady=15,
            sticky="nsew"
        )


        # AI

        self.ai_panel = AIRecommendation(
            self
        )

        self.ai_panel.grid(
            row=1,
            column=0,
            columnspan=3,
            padx=20,
            pady=10,
            sticky="ew"
        )



    def find_route(self, request):

        if request.get("reset"):

            self.map_panel.update_route([])
            self.result_panel.reset()
            self.ai_panel.reset()

            return


        vehicle = request["vehicle"]

        start = request["start"]

        destination = request["destination"]



        self.ai_panel.update_text(
            "🔍 Finding optimal route..."
        )



        result = run_traffic_agent(
            start,
            destination,
            vehicle
        )


        if "error" in result:

            self.ai_panel.update_text(
                result["error"]
            )

            return



        # Update Map

        self.map_panel.update_route(
            result["route"]
        )


        # Update Result

        self.result_panel.update_result(
            result["route"],
            result["distance"],
            result["time"],
            result.get(
                "traffic",
                "Unknown"
            )
        )


        # Update AI

        self.ai_panel.update_text(
            result.get(
                "ai_message",
                "No recommendation"
            )
        )



if __name__ == "__main__":

    app = YangonTrafficApp()

    app.mainloop()