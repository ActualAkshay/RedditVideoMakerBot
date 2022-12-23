# Supported Background. Can add/remove background video here....
# <key>-<value> : key -> used as keyword for TOML file. value -> background configuration
# Format (value):
# 1. Youtube URI
# 2. filename
# 3. Citation (owner of the video)
# 4. Position of image clips in the background. See moviepy reference for more information. (https://zulko.github.io/moviepy/ref/VideoClip/VideoClip.html#moviepy.video.VideoClip.VideoClip.set_position)
background_options = {
    "origminecraft": (  # Minecraft
        "https://www.youtube.com/watch?v=Pt5_GSKIWQM",
        "ItsIpsn.mp4",
        "ItsIpsn",
        lambda t: ("center", 480 + t)
    ),
    "motor-gta": (  # Motor-GTA Racing
        "https://www.youtube.com/watch?v=vw5L4xCPy9Q",
        "bike-parkour-gta.mp4",
        "Achy Gaming",
        lambda t: ("center", 480 + t)
    ),
    "rocket-league": (  # Rocket League
        "https://www.youtube.com/watch?v=2X9QGY__0II",
        "rocket_league.mp4",
        "Orbital Gameplay",
        lambda t: ("center", 200 + t)
    ),
    "minecraft": (  # Minecraft parkour
        "https://www.youtube.com/watch?v=n_Dv4JMiwK8",
        "parkour.mp4",
        "bbswitzer",
        "center"
    )

}
