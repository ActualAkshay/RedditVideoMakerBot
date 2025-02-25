#!/usr/bin/env python3
import multiprocessing
import time
import os
import re
import pickle
from typing import Tuple, Any
import imgkit
import math
from os.path import exists
from moviepy.audio.AudioClip import concatenate_audioclips, CompositeAudioClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.video.fx import mask_color
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from rich.console import Console

from utils.cleanup import cleanup
from utils.console import print_step, print_substep
from utils.videos import save_data
from utils import settings

console = Console()
W, H = 1080, 1920


def name_normalize(name: str) -> str:
    name = re.sub(r'[?\\"%*:|<>]', "", name)
    name = re.sub(r"( [w,W]\s?\/\s?[o,O,0])", r" without", name)
    name = re.sub(r"( [w,W]\s?\/)", r" with", name)
    name = re.sub(r"(\d+)\s?\/\s?(\d+)", r"\1 of \2", name)
    name = re.sub(r"(\w+)\s?\/\s?(\w+)", r"\1 or \2", name)
    name = re.sub(r"\/", r"", name)
    name[:30]

    lang = settings.config["reddit"]["thread"]["post_lang"]
    if lang:
        import translators as ts

        print_substep("Translating filename...")
        translated_name = ts.google(name, to_language=lang)
        return translated_name

    else:
        return name


def make_final_video(
    number_of_clips: int,
    length: int,
    reddit_obj: dict,
    background_config: Tuple[str, str, str, Any],
    logo_path: str,
    animation_path: str,
):
    """Gathers audio clips, gathers all screenshots, stitches them together and saves the final video to assets/temp
    Args:
        number_of_clips (int): Index to end at when going through the screenshots'
        length (int): Length of the video
        reddit_obj (dict): The reddit object that contains the posts to read.
        background_config (Tuple[str, str, str, Any]): The background config to use.
    """
    # try:  # if it isn't found (i.e you just updated and copied over config.toml) it will throw an error
    #    VOLUME_MULTIPLIER = settings.config["settings"]['background']["background_audio_volume"]
    # except (TypeError, KeyError):
    #    print('No background audio volume found in config.toml. Using default value of 1.')
    #    VOLUME_MULTIPLIER = 1
    number_of_clips = number_of_clips or 0
    id = re.sub(r"[^\w\s-]", "", reddit_obj["thread_id"])
    print_step("Creating the final video 🎥")
    VideoFileClip.reW = lambda clip: clip.resize(width=W)
    VideoFileClip.reH = lambda clip: clip.resize(width=H)
    opacity = settings.config["settings"]["opacity"]
    transition = settings.config["settings"]["transition"]
    background_clip = (
        VideoFileClip(f"assets/temp/{id}/background.mp4")
        .without_audio()
        .resize(height=H)
        .crop(x1=1166.6, y1=0, x2=2246.6, y2=1920)
    )

    # Gather all audio clips
    
    audio_clips = []
    audio_clips.insert(0, AudioFileClip(f"assets/temp/{id}/mp3/title.mp3")) # add title tts mp3 at index 0

    # START Gather and Insert split post tts mp3 files
    audio_list_len= len(pickle.load(open(f"assets/temp/{id}/mp3/post.pickle", "rb")))
    for index in range(audio_list_len):
        audio_clips.insert(index+1, AudioFileClip(f"assets/temp/{id}/mp3/post.part{index}.mp3")) # add post tts parts at relevant indexes
    #END ather and Insert split post tts mp3 files

    audio_concat = concatenate_audioclips(audio_clips)
    audio_composite = CompositeAudioClip([audio_concat])
    
    
    console.log(f"[bold green] Video Will Be: {math.ceil(length)} Seconds Long")


    # BEGIN: Title Stuff
    image_clips = []
    # Gather all images
    new_opacity = 1 if opacity is None or float(opacity) >= 1 else float(opacity)
    new_transition = 0 if transition is None or float(transition) > 2 else float(transition)
    image_clips.insert(
        0,
        ImageClip(f"assets/temp/{id}/png/title.png")
        .set_duration(audio_clips[0].duration)
        .resize(width=W - 100)
        .margin(bottom=300, opacity=0) # for pulling Title image up towards logo
        .set_opacity(new_opacity)
        .crossfadein(new_transition)
        .crossfadeout(new_transition)
    )
    # END: Title Stuff

    #BEGIN: Post Text Captions Stuff
    # getting post captions text into an array to use as captions
    post_captions = pickle.load(open(f"assets/temp/{id}/mp3/post.pickle", "rb"))    
    # print(len(post_captions))  # debug
    
    # CSS to choose for text to image conversion
        
    css = settings.config["captions"]["theme"]
    render_width_config = settings.config["captions"]["render_width"]
    render_width=480 if render_width_config is None else render_width_config
    max_width_config = settings.config["captions"]["width_on_video"]
    max_width=980 if max_width_config is None else max_width_config
    cap_margin_right_config = settings.config["captions"]["margin_right"]
    cap_margin_right=0 if cap_margin_right_config is None else cap_margin_right_config
    
    if not exists(css):
        if settings.config["settings"]["theme"] == "dark":
            print_substep("Using Dark theme for captions...")
            css = 'assets/css/captions/dark.css' # Default theme for dark mode
        else:
            print_substep("Using Light theme for captions...")
            css = 'assets/css/captions/light.css' # Default theme for dark mode
    else:
        print_substep(f"Using custom theme for captions... {css}")
    
    options = {
    'format': 'png',
    'crop-w':  render_width,
    'quiet': ''
    }
    for idy, post_line in enumerate(post_captions):
        imgkit.from_string(f"<span>{post_line}</span>", f"assets/temp/{id}/png/post.part{idy}.png", css=css, options=options)

        image_clips.append(
                ImageClip(f"assets/temp/{id}/png/post.part{idy}.png")
                .resize(width=max_width)
                .margin(right=cap_margin_right, opacity=0)
                .set_duration(audio_clips[idy + 1].duration)
                .set_opacity(new_opacity)
                .crossfadein(new_transition)
                .crossfadeout(new_transition)
        )
    #END: Post Text Caption stuff

    
        # for i in range(0, number_of_clips):
        #     image_clips.append(
        #         ImageClip(f"assets/temp/{id}/png/comment_{i}.png")
        #         .set_duration(audio_clips[i + 1].duration)
        #         .resize(width=W - 100)
        #         .set_opacity(new_opacity)
        #         .crossfadein(new_transition)
        #         .crossfadeout(new_transition)
        #     )
    
    # BEGIN: Logo stuff
    total_duration = sum([i.duration for i in image_clips])
    logo_transition_config = settings.config["settings"]["background"]["logo_fadein_duration"]
    if logo_transition_config is None:
        logo_transition = 0
    elif logo_transition_config > 2:
        logo_transition = 2 
    else:
        logo_transition = float(logo_transition_config)

    logo = (ImageClip(logo_path)
            .set_duration(total_duration)
            .resize(height=400)  # if you need to resize...
            .margin(top=300, opacity=0)  # (optional) logo-border padding
            .crossfadein(logo_transition)
            .set_pos(("center", "top")))
    #END: Logo stuff

    #BEGIN: Animation STuff

    animation_clip = VideoFileClip(animation_path)

    animation_width_config = settings.config["settings"]["background"]["animation_width"]
    animation_width= animation_clip.w if animation_width_config is None else animation_width_config
    animation_margin_r_config = settings.config["settings"]["background"]["animation_margin_right"]
    animation_margin_right=0 if animation_margin_r_config is None else animation_margin_r_config
    
    showat_con=settings.config["settings"]["background"]["animation_show_at"]
    showat = "end" if showat_con == "start" or showat_con == "middle" else showat_con
    
    showat_time = (total_duration - animation_clip.duration)/2
    showat_time=0 if showat_con == "start" else total_duration - animation_clip.duration
        
    masked_clip = mask_color.mask_color(animation_clip, color=[64, 222, 0], thr=150, s=5)
    masked_clip = (masked_clip
                    .resize(width=animation_width)
                    .set_start(showat_time)
                    .margin(bottom=300,right=animation_margin_right, opacity=0)
                    .set_pos(('center', 'bottom')))
    img_clip_pos = 'center'  # background_config[3]
    image_concat = concatenate_videoclips(image_clips).set_position(
        img_clip_pos
    )  # note transition kwarg for delay in imgs
    #END: Animation stuff


    image_concat.audio = audio_composite
    final = CompositeVideoClip([background_clip, image_concat, logo, masked_clip])
    title = re.sub(r"[^\w\s-]", "", reddit_obj["thread_title"])
    idx = re.sub(r"[^\w\s-]", "", reddit_obj["thread_id"])

    filename = f"{name_normalize(title)[:251]}.mp4"
    subreddit = settings.config["reddit"]["thread"]["subreddit"]

    if not exists(f"./results/{subreddit}"):
        print_substep("The results folder didn't exist so I made it")
        os.makedirs(f"./results/{subreddit}")

    # if settings.config["settings"]['background']["background_audio"] and exists(f"assets/backgrounds/background.mp3"):
    #    audioclip = mpe.AudioFileClip(f"assets/backgrounds/background.mp3").set_duration(final.duration)
    #    audioclip = audioclip.fx( volumex, 0.2)
    #    final_audio = mpe.CompositeAudioClip([final.audio, audioclip])
    #    # lowered_audio = audio_background.multiply_volume( # todo get this to work
    #    #    VOLUME_MULTIPLIER)  # lower volume by background_audio_volume, use with fx
    #    final.set_audio(final_audio)
    # final = Video(final).add_watermark(
    #     text=f"Background credit: {background_config[2]}", opacity=0.4, redditid=reddit_obj
    # )

    # final = CompositeVideoClip([final, logo])
    final.write_videofile(
        f"assets/temp/{id}/temp.mp4",
        fps=30,
        audio_codec="aac",
        audio_bitrate="192k",
        verbose=False,
        threads=multiprocessing.cpu_count(),
        temp_audiofile=f"assets/temp/{id}/audio.mp4"
    )
    ffmpeg_extract_subclip(
        f"assets/temp/{id}/temp.mp4",
        0,
        length,
        targetname=f"results/{subreddit}/{filename}",
    )
    save_data(subreddit, filename, title, idx, background_config[1])
    cleanup()
    print_substep("See result in the results folder!")
    print_step(
        f'Reddit title: {reddit_obj["thread_title"]} \nBackground Credit: {background_config[1]}'
    )
