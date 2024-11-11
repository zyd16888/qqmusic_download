import flet as ft

from src.ui.app import MusicDownloaderApp


def main():
    def init(page: ft.Page):
        app = MusicDownloaderApp(page)

    ft.app(target=init)


if __name__ == "__main__":
    main()
