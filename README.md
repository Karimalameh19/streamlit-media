# Streamlit Media Setup

## Change Directory
cd path/to/tpjecy

## Create and Activate Virtual Environment
python -m venv venv
venv/Scripts/activate

## Install Requirements
pip install -r requirements.txt
pip install -r packages.txt

## Download and Run ChromeDriver
download and run https://storage.googleapis.com/chrome-for-testing-public/128.0.6613.137/win64/chromedriver-win64.zip

## Download and Run GStreamer
download and run https://gstreamer.freedesktop.org/data/pkg/windows/1.24.7/msvc/gstreamer-1.0-msvc-x86_64-1.24.7.msi

## Add to Environment Variables
1. Set system variable:
    set system variable new GSTREAMER_1_0_ROOT_MSVC_X86_64= C:\gstreamer\1.0\msvc_x86_64
2. Add to PATH system variable:
    add C:\gstreamer\1.0\msvc_x86_64 to the PATH system variable

## Run Streamlit App
streamlit run streamlit_app.py
