"""Styles for the chat app."""

# Common styles
shadow = "rgba(0, 0, 0, 0.15) 0px 2px 8px"
message_style = dict(
    padding_inline="1em",
    margin_block="0.25em",
    border_radius="1rem",
    display="inline-block",
    color="black",
)

question_style = message_style | dict(
    width="100%",
    border="1px solid #E9E9E9",
    box_shadow="none",
)

answer_style = message_style | dict(
    background_color="#F9F9F9",
    border="1px solid #E9E9E9",
    box_shadow="none",
    width="100%",
)

# Container styles
input_container_style = dict(
    border="1px solid #E9E9E9",
    border_radius="15px",
    padding="1em",
    width="100%",
    background_color="white",
    box_shadow=shadow,
)

form_style = dict(
    width="100%",
    border="none",
    outline="none",
    box_shadow="none",
    _focus={"border": "none", "outline": "none", "box_shadow": "none"},
)

input_style = dict(
    border="none",
    padding="0.5em",
    width="100%",
    color="black",
    background_color="transparent",
    outline="none",
    box_shadow="none",
    font_size="1em",
    min_height="6em",
    height="100%",
    max_height="60vh",  # Maximum height set to 60vh
    overflow_y="auto",  # Scrollable vertically when content exceeds 60vh
    resize="vertical",  # Allow user or auto growth in vertical direction
    _focus={"border": "none", "outline": "none", "box_shadow": "none"},
    _placeholder={"color": "#A3A3A3"},
)

controls_style = dict(
    padding_top="0.5em",
    gap="2",
    width="100%",
)

select_style = dict(
    border="1px solid #E9E9E9",
    padding="0.5em",
    border_radius="1em",
    background_color="#F5F5F5",
    color="black",
    width="auto",
    min_width="150px",
)

button_style = dict(
    background_color="#FFFFFF",
    border="1px solid #E9E9E9",
    border_radius="50%",
    padding="0.5em",
    aspect_ratio="1",
    color="black",
)

context_menu_style = dict(
    background_color="white",
    border="1px solid #E9E9E9",
    border_radius="8px",
    padding="0.5em",
    box_shadow=shadow,
    color="black",
)

# Update button_style to remove border-radius for regular buttons
button_style = dict(
    background_color="#FFFFFF",
    border="1px solid #E9E9E9",
    border_radius="8px",
    padding="0.5em",
    color="black",
)

# Add specific style for circular buttons (used in action bar)
circular_button_style = dict(
    background_color="#FFFFFF",
    border="1px solid #E9E9E9",
    border_radius="50%",
    padding="0.5em",
    aspect_ratio="1",
    color="black",
)

copy_button_style = dict(
    position="absolute",
    bottom="0.5em",
    right="0.5em",
    background_color="white",
    border="1px solid #E9E9E9",
    border_radius="4px",
    padding="0.3em",
    cursor="pointer",
    opacity="0",
    transition="opacity 0.2s",
    _hover={"opacity": 1},
)
