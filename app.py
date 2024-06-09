import os
from typing import Optional

from dotenv import load_dotenv
from dubbing_utils import  *
from urllib.parse import urlparse
from elevenlabs.client import ElevenLabs
import openai

from flask import Flask, request, render_template, flash, jsonify, redirect, url_for
import os
from flask import send_from_directory
import json
from youtube_transcript_api import YouTubeTranscriptApi as yta
import re

from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from dotenv import load_dotenv, find_dotenv
import os
import pprint
from pymongo import MongoClient

from os import environ as env
# 📁 server.py -----

import json
from os import environ as env

from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for
from urllib.parse import quote_plus, urlencode


from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)


@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

app.config['STATIC_FOLDER'] = 'data'  

@app.route('/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory(app.config['STATIC_FOLDER'], filename)



# Load environment variables
load_dotenv()
password = os.environ.get("MONGODB_PWD")
connection = f"mongodb+srv://thesnehaladbol:{password}@ex1.sbojxfb.mongodb.net/?retryWrites=true&w=majority&appName=EX1"
app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/myDatabase"
mongo = PyMongo(app)
client = MongoClient(connection)

openai.api_key = "sk-proj-3pdaYf8lyxWvJ2ebvArjT3BlbkFJl9PtXO8WvYurY76hMOzK"

#initialize db
dbs = client.list_database_names()
videos_db = client.videos
collections = videos_db.list_collection_names()
collection = videos_db.video



# Retrieve the API key
ELEVENLABS_API_KEY = ""
if not ELEVENLABS_API_KEY:
    raise ValueError(
        "ELEVENLABS_API_KEY environment variable not found. "
        "Please set the API key in your environment variables."
    )

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

#routes


source_url =""
source_language=""
target_language=""



@app.route("/")
def home():
    return render_template("index.html", session=session.get('user'), pretty=json.dumps(session.get('user'), indent=4))




@app.route("/notes")
def notes():
    if request.method =="POST":
        url = str(request.form.get('link'))
        url_data = urlparse.urlparse("http://www.youtube.com/watch?v=z_AbfPXTKms&NR=1")
        query = urlparse.parse_qs(url_data.query)
        video = query["v"][0]

        # extract
        data = yta.get_transcript(video)
        transcript = ""
        for value in data:
            for key, val in value.items():
                if key =="text":
                    transcript += val
        l = transcript.splitlines()
        final_tra =" ".join(l)

        # save in db
        video = {"id": video, "content": final_tra}

        #ask openai
        def generate():
            stream = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "summarize"+final_tra}],
                stream=True
            ) 

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield(chunk.choices[0].delta.content)

        return generate(), {"Content-Type": "text/plain"}
    return render_template("notes.html")

@app.route("/dub" , methods=['GET', 'POST'])
def dub():
    if request.method =="POST":
        source_url = str(request.form.get('link'))
        source_language = str(request.form.get('lang1'))
        target_language = str(request.form.get('lang2')
                              )
        print(source_url , source_language, target_language)
        result = create_dub_from_url(source_url, source_language, target_language)
        if result:
            print("Dubbing was successful! File saved at:", result)
            return render_template("dub.html", video_path=result, url=source_url)
            print("Dubbing failed or timed out.")
    return render_template("dub.html" )



def create_dub_from_url(
    source_url: str,
    source_language: str,
    target_language: str,
) -> Optional[str]:
    """
    Downloads a video from a URL, and creates a dubbed version in the target language.

    Args:
        source_url (str): The URL of the source video to dub. Can be a YouTube link, TikTok, X (Twitter) or a Vimeo link.
        source_language (str): The language of the source video.
        target_language (str): The target language to dub into.

    Returns:
        Optional[str]: The file path of the dubbed file or None if operation failed.
    """

    response = client.dubbing.dub_a_video_or_an_audio_file(
        source_url=source_url,
        target_lang=target_language,
        mode="automatic",
        source_lang=source_language,
        num_speakers=1,
        watermark=True,
    )


    
    dubbing_id = response.dubbing_id
    if wait_for_dubbing_completion(dubbing_id):
        output_file_path = download_dubbed_file(dubbing_id, target_language)
        return output_file_path
    else:
        return None
    


if __name__ == "__main__":
    app.run(debug=True)





