from groq import Groq
import wave
import pyaudio
import torch
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()



ai_client = Groq(api_key = os.getenv('GROQ_API_KEY'))
gemini_client = genai.Client(api_key = os.getenv('GEMINI_API_KEY'))

chat_model = gemini_client.chats.create(
            model = 'gemini-2.5-flash',
      )

sample_rate = 16000
frame_duration_ms = 30
chunk_samples = int(sample_rate * frame_duration_ms / 1000)

audio = pyaudio.PyAudio()

stream = audio.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=sample_rate,
    input=True,
    frames_per_buffer=chunk_samples
)

def voice_agent():
    audio_buffer = []
    loop_counter = 0

    print("Listening...")
    try:
        while True:
            if loop_counter >= 100 and len(audio_buffer) > 0:
                print("Thank you")
                break
            pcm_frame = stream.read(chunk_samples, exception_on_overflow=False)

            audio_data = torch.frombuffer(pcm_frame, dtype=torch.int16).float() / 32768.0
        
            audio_level = torch.abs(audio_data).mean().item()
        
            is_speech = audio_level > 0.005
        
            if not is_speech:
                if len(audio_buffer) > 0:
                    audio_buffer.append(pcm_frame)
                if loop_counter < 100:
                    loop_counter += 1
            else:
                loop_counter = 0
                audio_buffer.append(pcm_frame)
                print("Recording...")
    
        if audio_buffer:
            final_pcm_audio = b"".join(audio_buffer)
            with wave.open("recording.wav", "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(sample_rate)
                f.writeframes(final_pcm_audio)
            print("Saved as recording.wav")

            try:
                with open('recording.wav', 'rb') as f:
                    transcription = ai_client.audio.transcriptions.create(
                        file=f,
                        model="whisper-large-v3-turbo",
                        response_format="text",
                        language="en"
                    )
                res = chat_model.send_message(transcription)
                print(res.text)
            except Exception as e:
                print(f"Transcription error: {e}")

    except KeyboardInterrupt:
        print("Stopped\n")
    finally:
        audio_buffer.clear()
        loop_counter = 0

try:
    while True:
        voice_agent()
except KeyboardInterrupt:
    print("\nShutting down...")
finally:
    stream.stop_stream()
    stream.close()
    audio.terminate()
    print("Audio resources cleaned up")