# chatapp/style.py
import reflex as rx

# Common styles
shadow = "rgba(0, 0, 0, 0.15) 0px 2px 8px"
chat_margin = "20%"

# Message styles
message_style = dict(
    padding="1em",
    border_radius="5px",
    display="inline-block",
    color="black",
)

question_style = message_style | dict(
    width="100%",
    border="1px solid #E9E9E9",
    box_shadow="none",
)

answer_style = message_style | dict(
    margin_right=chat_margin,
    background_color="#F9F9F9",
    border="1px solid #E9E9E9",
    box_shadow="none",
    width="100%",
)

# Input container style
input_container_style = dict(
    border="1px solid #E9E9E9",
    border_radius="15px",
    padding="1em",
    width="100%",
    background_color="white",
    box_shadow=shadow,
)

# Form style
form_style = dict(
    width="100%",
    border="none",
    outline="none",
    box_shadow="none",
    _focus={"border": "none", "outline": "none", "box_shadow": "none"},
)

# Input field style
input_style = dict(
    border="none",
    border_width="0",
    padding="0.5em",
    width="100%",
    _placeholder={"color": "#A3A3A3"},
    color="black",
    background_color="transparent",
    outline="none",
    box_shadow="none",
    font_size="1em",
    min_height="6em",
    overflow_y="hidden",  # Changed from auto to hidden
    _focus={
        "border": "none",
        "outline": "none",
        "ring": "0",
        "box_shadow": "none",
    },
    _hover={
        "border": "none",
        "outline": "none",
        "box_shadow": "none",
    },
    # Remove webkit appearance and shadow
    _webkit_appearance="none",
    _webkit_box_shadow="none",
)

# Controls container style
controls_style = dict(
    padding_top="0.5em",
    gap="2",
    width="100%",
)

# Model select style
select_style = dict(
    border="1px solid #E9E9E9",
    padding="0.5em",
    border_radius="8px",
    background_color="#F5F5F5",
    color="black",
    width="auto",
    min_width="150px",
)

# Submit button style
button_style = dict(
    background_color="#FFFFFF",
    border="1px solid #E9E9E9",
    border_radius="50%",
    padding="0.5em",
    aspect_ratio="1",
    color="black",
)
