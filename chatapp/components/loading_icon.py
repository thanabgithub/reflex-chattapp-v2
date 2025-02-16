"""Loading icon component."""

import reflex as rx


class LoadingIcon(rx.Component):
    """A loading spinner component."""

    library = "react-loading-icons"
    tag = "SpinningCircles"

    # Define attributes that can be passed to the component
    stroke: rx.Var[str]
    stroke_opacity: rx.Var[str]
    fill: rx.Var[str]
    fill_opacity: rx.Var[str]
    stroke_width: rx.Var[str]
    speed: rx.Var[str]
    height: rx.Var[str]


loading_icon = LoadingIcon.create
