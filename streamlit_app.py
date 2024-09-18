import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
import requests
import uuid
import json
from openai import AzureOpenAI
import os
import requests
from PIL import Image
import json
import PyPDF2
import docx
import subprocess
import cv2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access the environment variables
TEXT_ANALYTICS_KEY = os.getenv('AZURE_TEXT_ANALYTICS_KEY')
TEXT_ANALYTICS_ENDPOINT = os.getenv('AZURE_TEXT_ANALYTICS_ENDPOINT')
print(TEXT_ANALYTICS_KEY)
TRANSLATOR_KEY = os.getenv('AZURE_TRANSLATOR_KEY')
TRANSLATOR_ENDPOINT = os.getenv('AZURE_TRANSLATOR_ENDPOINT')
TRANSLATOR_REGION = os.getenv('AZURE_TRANSLATOR_LOCATION')

OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')

AZURE_SPEECH_KEY = os.getenv('AZURE_SPEECH_KEY')
AZURE_SPEECH_REGION = os.getenv('AZURE_SPEECH_REGION')




def format_time(seconds):
    """Convert seconds to SRT timestamp format."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"

def read_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def read_docx(file):
    doc = docx.Document(file)
    text = "\n".join([p.text for p in doc.paragraphs])
    return text

def read_txt(file):
    return file.read().decode("utf-8")


# Set up Azure Text Analytics client
def authenticate_client():
    key = TEXT_ANALYTICS_KEY
    endpoint = TEXT_ANALYTICS_ENDPOINT
    ta_credential = AzureKeyCredential(key)
    text_analytics_client = TextAnalyticsClient(endpoint=endpoint, credential=ta_credential)
    return text_analytics_client

# Extractive summarization method
def extractive_summarization(client, document):
    from azure.ai.textanalytics import ExtractiveSummaryAction

    poller = client.begin_analyze_actions(
        document,
        actions=[ExtractiveSummaryAction(max_sentence_count=4)],
    )
    document_results = poller.result()
    summary = ""
    for result in document_results:
        extract_summary_result = result[0]  # first document, first result
        if extract_summary_result.is_error:
            summary = f"Error: {extract_summary_result.message}"
        else:
            summary = " ".join([sentence.text for sentence in extract_summary_result.sentences])
    return summary

# Selenium scraping function
def scrape_website(url):
    # Set up Selenium options
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode for Streamlit
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')

    # Initialize Selenium WebDriver
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    
    # Open the URL
    driver.get(url)
    
    # Extract all text from the webpage's body
    body = driver.find_element(By.TAG_NAME, 'body')
    scraped_data = body.text
    
    # Close the driver
    driver.quit()
    
    return scraped_data

# Translation function
def translate_text(text, target_language):
    key = TRANSLATOR_KEY
    endpoint = TRANSLATOR_ENDPOINT
    location = TRANSLATOR_REGION
    path = '/translate'
    constructed_url = endpoint + path

    params = {
        'api-version': '3.0',
        'from': 'en',
        'to': target_language
    }

    headers = {
        'Ocp-Apim-Subscription-Key': key,
        'Ocp-Apim-Subscription-Region': location,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    body = [{'text': text}]
    response = requests.post(constructed_url, params=params, headers=headers, json=body)
    return response.json()


# Set up Azure OpenAI client for image generation
def authenticate_openai_client():
    client = AzureOpenAI(
        api_version="2024-02-01",  
        api_key=OPENAI_API_KEY,  
        azure_endpoint=OPENAI_ENDPOINT
    )
    return client

# Function to generate image using Azure OpenAI's DALL-E 3
def generate_image(client, prompt):
    result = client.images.generate(
        model="Dalle3",
        prompt=prompt,
        n=1
    )
    json_response = json.loads(result.model_dump_json())
    
    # Set the directory for the stored image
    image_dir = os.path.join(os.curdir, 'images')
    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)

    # Initialize the image path (the filetype should be png)
    image_path = os.path.join(image_dir, 'generated_image.png')

    # Retrieve the generated image
    image_url = json_response["data"][0]["url"]  # Extract image URL from response
    generated_image = requests.get(image_url).content  # Download the image
    with open(image_path, "wb") as image_file:
        image_file.write(generated_image)

    return image_path

# Streamlit app
def main():
    st.sidebar.title('Options')
    page = st.sidebar.selectbox(
        'Choose a page',
        ['Web Summarization and translation', 'Text Input Summarization and translation', 'Document Summarization and translation', 'News and media Text-to-Image Generation', 'Video Captioning'],
        help='Choose the task you want to perform using the app.'
    )

    if page == 'Web Summarization and translation':
        st.title('Web Scraping and Summarization with Azure AI in Streamlit')

        # Dropdown to select language for translation
        target_language = st.selectbox(
            'Select a language for translation',
            ['fr', 'de', 'es', 'it', 'pt', 'ar']
        )

        url = st.text_input('Enter the URL to scrape', 'https://www.aub.edu.lb/admissions/Pages/EnglishRequirements.aspx')

        if st.button('Scrape and Translate'):
            try:
                # Spinner for scraping
                with st.spinner('Scraping the website...'):
                    scraped_content = scrape_website(url)
                
                if scraped_content:
                    # Spinner for summarization
                    with st.spinner('Generating summary...'):
                        client = authenticate_client()
                        summary = extractive_summarization(client, [scraped_content])

                    st.write('Summary:')
                    st.write(summary)

                    # Spinner for translation
                    if target_language:
                        if summary:
                            with st.spinner('Translating summary...'):
                                translated_texts = translate_text(summary, target_language)
                                translation = translated_texts[0]['translations'][0]['text']

                            st.write(f'Translation in {target_language}:')
                            st.write(translation)
                        else:
                            st.write('No summary to translate.')
                else:
                    st.write('No content found.')
            except Exception as e:
                st.write(f'An error occurred: {e}')
        
    elif page == 'Text Input Summarization and translation':
        st.title('Text Input Summarization and Translation with Azure AI in Streamlit')

        # Text input for user to provide content
        user_input_text = st.text_area('Enter the text to summarize', '')

        # Dropdown to select language for translation
        target_language = st.selectbox(
            'Select a language for translation',
            ['fr', 'de', 'es', 'it', 'pt', 'ar']
        )

        if st.button('Summarize and Translate'):
            try:
                if user_input_text:
                    # Spinner for summarization
                    with st.spinner('Generating summary...'):
                        client = authenticate_client()
                        summary = extractive_summarization(client, [user_input_text])

                    st.write('Summary:')
                    st.write(summary)

                    # Spinner for translation
                    if target_language:
                        if summary:
                            with st.spinner('Translating summary...'):
                                translated_texts = translate_text(summary, target_language)
                                translation = translated_texts[0]['translations'][0]['text']

                            st.write(f'Translation in {target_language}:')
                            st.write(translation)
                        else:
                            st.write('No summary to translate.')
                else:
                    st.write('Please input some text to summarize.')
            except Exception as e:
                st.write(f'An error occurred: {e}')


    elif page == 'Document Summarization and translation':
        st.title('Document Summarization and Translation with Azure AI in Streamlit')

        uploaded_file = st.file_uploader("Choose a file (PDF, DOCX, TXT)", type=['pdf', 'docx', 'txt'])
        target_language = st.selectbox(
            'Select a language for translation',
            ['fr', 'de', 'es', 'it', 'pt', 'ar']
        )

        if st.button('Summarize and Translate'):
            try:
                if uploaded_file:
                    # Read the content based on file type
                    if uploaded_file.type == 'application/pdf':
                        file_text = read_pdf(uploaded_file)
                    elif uploaded_file.type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                        file_text = read_docx(uploaded_file)
                    elif uploaded_file.type == 'text/plain':
                        file_text = read_txt(uploaded_file)
                    else:
                        st.write('Unsupported file type.')
                        file_text = ""

                    if file_text:
                        # Spinner for summarization
                        with st.spinner('Generating summary...'):
                            client = authenticate_client()
                            summary = extractive_summarization(client, [file_text])

                        st.write('Summary:')
                        st.write(summary)

                        # Spinner for translation
                        if target_language:
                            if summary:
                                with st.spinner('Translating summary...'):
                                    translated_texts = translate_text(summary, target_language)
                                    translation = translated_texts[0]['translations'][0]['text']

                                st.write(f'Translation in {target_language}:')
                                st.write(translation)
                            else:
                                st.write('No summary to translate.')
                    else:
                        st.write('No content found.')
                else:
                    st.write('Please upload a file to process.')
            except Exception as e:
                st.write(f'An error occurred: {e}')


    elif page == 'News and media Text-to-Image Generation':
        st.title('Text-to-Image Generation with DALL-E 3')

        # Text input for image prompt
        prompt = st.text_input('Enter a prompt to generate an image', '')

        if st.button('Generate Image'):
            if prompt:
                # Spinner while generating the image
                with st.spinner('Generating image...'):
                    try:
                        client = authenticate_openai_client()
                        image_path = generate_image(client, prompt)
                        
                        # Display the generated image
                        st.image(image_path, caption='Generated Image', use_column_width=True)
                    except Exception as e:
                        st.write(f'An error occurred: {e}')
            else:
                st.write('Please enter a prompt to generate an image.')
    elif page == 'Video Captioning':
        st.title('Video Captioning with Real-Time Transcription')

        uploaded_file = st.file_uploader('Upload an MP4 video', type=['mp4'])

        if uploaded_file is not None:
            video_path = os.path.join(os.curdir, 'uploaded_video.mp4')
            with open(video_path, 'wb') as video_file:
                video_file.write(uploaded_file.read())

            st.video(video_path)

            if st.button('Generate Captions'):
                with st.spinner('Generating captions...'):
                    try:
                        output_caption_path = os.path.join(os.curdir, 'caption_output.srt')

                        # Load Speech service credentials from environment variables
                        SPEECH_KEY = AZURE_SPEECH_KEY  # Replace with your actual Speech resource key
                        SPEECH_REGION = AZURE_SPEECH_REGION # Replace with your actual Speech service region

                        # Path to the Python executable of the virtual environment
                        python_path = "./venv/Scripts/python.exe"  # Update this path

                        command = [
                            python_path, 'captioning.py',
                            '--input', video_path,
                            '--format', 'any',
                            '--output', output_caption_path,
                            '--srt', '--offline',
                            '--threshold', '5',
                            '--delay', '0',
                            '--profanity', 'mask',
                            '--phrases', 'Contoso;Jessie;Rehaan',
                            '--key', SPEECH_KEY,
                            '--region', SPEECH_REGION
                        ]

                        subprocess.run(command, check=True)

                        # Check if the SRT file was created
                        if os.path.exists(output_caption_path):
                            st.write('Generated Captions:')
                            with open(output_caption_path, 'r') as caption_file:
                                captions = [line.strip() for line in caption_file if line.strip()]
                                st.text_area('Captions', ''.join(captions), height=200)

                            st.success(f'SRT file saved as: {output_caption_path}')

                            # Display the video with subtitles
                            st.video(video_path, subtitles={"English": output_caption_path})
                        else:
                            st.warning("Subtitles file not found.")
                    
                    except subprocess.CalledProcessError as e:
                        st.write(f'An error occurred while generating captions: {e}')
                    except Exception as e:
                        st.write(f'An unexpected error occurred: {e}')

if __name__ == '__main__':
    main()
