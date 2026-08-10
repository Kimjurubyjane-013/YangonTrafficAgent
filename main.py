import webview

from api import Api


if __name__ == "__main__":

    api = Api()

    webview.create_window(
        "Yangon Traffic Agent",
        "web/app.html",
        js_api=api,
        width=1400,
        height=900
    )

    webview.start()