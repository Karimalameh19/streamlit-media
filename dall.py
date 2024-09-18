import moviepy.config as mpc

# Set ImageMagick path
mpc.IMAGEMAGICK_BINARY = r'C:\Program Files\ImageMagick-7.1.1-Q16\magick.exe'
import streamlit as st
import azure.cognitiveservices.speech as speechsdk
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os
import time
# Azure Speech Service credentials
SUBSCRIPTION_KEY = "2c97990594c3481ebfa0782416fc3eb1"
SERVICE_REGION = "eastus"

# Function to extract audio from video
def extract_audio(video_path):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
        audio_path = temp_audio_file.name
    video = VideoFileClip(video_path)
    audio = video.audio
    audio.write_audiofile(audio_path)
    video.close()
    print(f"Audio extracted to: {audio_path}")
    return audio_path


# Function to transcribe audio using Azure Speech-to-Text
def transcribe_audio(audio_path):
    speech_config = speechsdk.SpeechConfig(subscription=SUBSCRIPTION_KEY, region=SERVICE_REGION)
    audio_input = speechsdk.AudioConfig(filename=audio_path)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)
    
    result = speech_recognizer.recognize_once()
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return "No speech could be recognized"
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speechsdk.CancellationDetails.from_result(result)
        return f"Speech Recognition canceled: {cancellation_details.reason}"

# Function to add subtitles to a video
def add_subtitles_to_video(video_path, captions):
    video = VideoFileClip(video_path)

    # Create a TextClip for subtitles
    subtitle_clip = TextClip(captions, fontsize=24, color='white', bg_color='black', size=video.size)
    subtitle_clip = subtitle_clip.set_duration(video.duration).set_position(('center', 'bottom'))

    # Overlay the subtitles on the original video
    video_with_subtitles = CompositeVideoClip([video, subtitle_clip])

    # Write the result to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video_file:
        final_video_path = temp_video_file.name

    video_with_subtitles.write_videofile(final_video_path, codec='libx264', audio_codec='aac')

    video.close()  # Close the video file
    return final_video_path

# Streamlit app
def main():
    st.title("Video Captioning App")

    uploaded_file = st.file_uploader("Choose a video file", type="mp4")
    
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
            temp_video_path = temp_video_file.name
            temp_video_file.write(uploaded_file.read())

        st.video(temp_video_path)
        
        # Extract audio from the uploaded video
        audio_path = extract_audio(temp_video_path)
        
        # Transcribe the extracted audio
        captions = transcribe_audio(audio_path)
        
        # Create video with subtitles
        video_with_subtitles_path = add_subtitles_to_video(temp_video_path, captions)
        
        st.write("Captions:")
        st.write(captions)
        st.video(video_with_subtitles_path)

        # Skipping file deletion
        # os.remove(temp_video_path)
        # os.remove(audio_path)
        # os.remove(video_with_subtitles_path)

if __name__ == "__main__":
    main()