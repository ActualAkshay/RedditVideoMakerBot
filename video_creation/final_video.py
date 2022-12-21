#!/usr/bin/env python3
import multiprocessing
import os
import re
import pickle
import imgkit
import math
from os.path import exists
from typing import Tuple, Any
from moviepy.audio.AudioClip import concatenate_audioclips, CompositeAudioClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.video.fx import mask_color
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
import moviepy as mp
from rich.console import Console

from utils.cleanup import cleanup
from utils.console import print_step, print_substep
from utils.video import Video
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
    # audio_clips = [AudioFileClip(f"assets/temp/{id}/mp3/{i}.mp3") for i in range(number_of_clips)] # get comment clips and insert them in audio_clips object array
    audio_clips = []
    audio_clips.insert(0, AudioFileClip(f"assets/temp/{id}/mp3/title.mp3")) # add title tts mp3 at index 0

    # START Gather and Insert split post tts mp3 files
    post_tts_list = [f for f in os.listdir(f"assets/temp/{id}/mp3") if re.match(r'post\.part[0-9]+.*\.mp3', f)]
    post_tts_list.sort()

    for index in range(len(post_tts_list)):
        audio_clips.insert(index+1, AudioFileClip(f"assets/temp/{id}/mp3/{post_tts_list[index]}")) # add post tts parts at relevant indexes
    #END ather and Insert split post tts mp3 files

    audio_concat = concatenate_audioclips(audio_clips)
    audio_composite = CompositeAudioClip([audio_concat])
    
    
    console.log(f"[bold green] Video Will Be: {math.ceil(length)} Seconds Long")


    # add title to video
    image_clips = []
    # Gather all images
    new_opacity = 1 if opacity is None or float(opacity) >= 1 else float(opacity)
    new_transition = 0 if transition is None or float(transition) > 2 else float(transition)
    image_clips.insert(
        0,
        ImageClip(f"assets/temp/{id}/png/title.png")
        .set_duration(audio_clips[0].duration)
        .resize(width=W - 100)
        .set_opacity(new_opacity)
        .crossfadein(new_transition)
        .crossfadeout(new_transition),
    )

    #START Insert post text captions
        # getting post captions text into an array to use as captions
    post_captions = pickle.load(open(f"assets/temp/{id}/mp3/post.pickle", "rb"))    
    #print(post_captions)  # debug
    
    # CSS to choose for text to image conversion
    if settings.config["settings"]["theme"] == "dark":
        css = 'assets/css/dark.css'
    else:
        css = 'assets/css/light.css'
    
    options = {
    'format': 'png',
    'crop-w':  480,
    'quiet': ''
    }
    for idy, post_line in enumerate(post_captions):
        imgkit.from_string(f"<span>{post_line}</span>", f"assets/temp/{id}/png/post.part{idy}.png", css=css, options=options)

        image_clips.append(
                ImageClip(f"assets/temp/{id}/png/post.part{idy}.png")
                .resize(width=W - 100)
                .set_duration(audio_clips[idy + 1].duration)
                .set_opacity(new_opacity)
                .crossfadein(new_transition)
                .crossfadeout(new_transition)
        )
        
    #END Insert post text captions
    
    for i in range(0, number_of_clips):
        image_clips.append(
            ImageClip(f"assets/temp/{id}/png/comment_{i}.png")
            .set_duration(audio_clips[i + 1].duration)
            .resize(width=W - 100)
            .set_opacity(new_opacity)
            .crossfadein(new_transition)
            .crossfadeout(new_transition)
        )
    # if os.path.exists("assets/mp3/posttext.mp3"):
    #    image_clips.insert(
    #        0,
    #        ImageClip("assets/png/title.png")
    #        .set_duration(audio_clips[0].duration + audio_clips[1].duration)
    #        .set_position("center")
    #        .resize(width=W - 100)
    #        .set_opacity(float(opacity)),
    #    )
    # else: story mode stuff
    total_duration = sum([i.duration for i in image_clips])

    logo = (ImageClip(logo_path)
            .set_duration(total_duration)
            .resize(height=400)  # if you need to resize...
            .margin(top=300, opacity=0)  # (optional) logo-border padding
            .set_pos(("center", "top")))
    animation_clip = VideoFileClip(animation_path)

    masked_clip = mask_color.mask_color(animation_clip, color=[64, 222, 0], thr=150, s=5)

    masked_clip = masked_clip.set_start(total_duration - animation_clip.duration).margin(bottom=300, opacity=0).set_pos(
        ('center', 'bottom'))
    img_clip_pos = 'center'  # background_config[3]
    image_concat = concatenate_videoclips(image_clips).set_position(
        img_clip_pos
    )  # note transition kwarg for delay in imgs

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
    )
    ffmpeg_extract_subclip(
        f"assets/temp/{id}/temp.mp4",
        0,
        length,
        targetname=f"results/{subreddit}/{filename}",
    )
    save_data(subreddit, filename, title, idx, background_config[1])
    print_step("Removing temporary files 🗑")
    cleanups = cleanup(id)
    print_substep(f"Removed {cleanups} temporary files 🗑")
    print_substep("See result in the results folder!")

    print_step(
        f'Reddit title: {reddit_obj["thread_title"]} \n Background Credit: {background_config[1]}'
    )
