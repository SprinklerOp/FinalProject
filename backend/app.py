from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
import pyttsx3
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
import requests
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import cast, POINTER
import pythoncom

app = Flask(__name__)
CORS(app)


IPINFO_API_KEY = '1e02c8d80f1695'



def send_email(subject, body, to_email):
    from_email = 'your_email@example.com'
    password = 'your_email_password'
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
            return 'Email sent successfully'
    except Exception as e:
        return f'Error sending email: {str(e)}'

def send_sms(account_sid, auth_token, body, from_number, to_number):
    client = Client(account_sid, auth_token)
    try:
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
        return f'SMS sent: {message.sid}'
    except Exception as e:
        return f'Error sending SMS: {str(e)}'

def scrape_google(query):
    search_url = f'https://www.google.com/search?q={query}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    results = []

    for item in soup.find_all('h3'):  # Example: Extracting titles from search results
        results.append(item.get_text())

    return results

def get_ip_location():
    try:
        response = requests.get(f'http://ipinfo.io?token={IPINFO_API_KEY}')
        data = response.json()
        loc = data.get('loc', '0,0').split(',')
        return {
            'latitude': float(loc[0]),
            'longitude': float(loc[1]),
            'address': f"{data.get('city', 'Unknown')}, {data.get('region', 'Unknown')}, {data.get('country', 'Unknown')}"
        }
    except Exception as e:
        return {'error': str(e)}

def get_location_from_coords(lat, lon):
    try:
        response = requests.get(f'https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}')
        data = response.json()
        address = data.get('display_name', 'Unknown location')
        return {'latitude': lat, 'longitude': lon, 'address': address}
    except Exception as e:
        return {'error': str(e)}


def text_to_audio(text):
    engine = pyttsx3.init()
    audio_file = 'output.mp3'
    engine.save_to_file(text, audio_file)
    engine.runAndWait()
    return audio_file

def control_volume(volume_level):
    try:
        # Ensure volume_level is an integer and within range
        volume_level = int(volume_level)
        if volume_level < 0 or volume_level > 100:
            return {'result': 'Volume level must be between 0 and 100.'}

        # Initialize COM library
        pythoncom.CoInitialize()

        # Get the default audio endpoint
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_,
            23,  # CLSCTX_ALL
            None
        )
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        # Convert volume level to a range from 0.0 to 1.0
        normalized_volume_level = volume_level / 100.0
        volume.SetMasterVolumeLevelScalar(normalized_volume_level, None)
        return {'result': 'Volume adjusted successfully'}
    except Exception as e:
        return {'result': f'Error adjusting volume: {str(e)}'}
    finally:
        pythoncom.CoUninitialize()

    
@app.route('/send_email', methods=['POST'])
def api_send_email():
    data = request.json
    result = send_email(data['subject'], data['body'], data['to_email'])
    return jsonify({'result': result})

@app.route('/send_sms', methods=['POST'])
def api_send_sms():
    data = request.json
    result = send_sms(data['account_sid'], data['auth_token'], data['message_body'], data['from_number'], data['to_number'])
    return jsonify({'result': result})

@app.route('/scrape_google', methods=['POST'])
def api_scrape_google():
    data = request.json
    results = scrape_google(data['query'])
    return jsonify({'results': results})

@app.route('/get_location', methods=['GET'])
def api_get_location():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    if lat and lon:
        location = get_location_from_coords(lat, lon)
    else:
        location = get_ip_location()
    return jsonify(location)
@app.route('/text_to_audio', methods=['POST'])
def api_text_to_audio():
    data = request.json
    audio_file = text_to_audio(data['text'])
    return jsonify({'audio_file': audio_file})


@app.route('/control_volume', methods=['POST'])
def api_control_volume():
    data = request.json
    volume_level = data.get('volume_level')
    if volume_level is None:
        return jsonify({'result': 'Volume level not provided'}), 400
    
    result = control_volume(volume_level)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
