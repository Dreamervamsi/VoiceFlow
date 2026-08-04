from groq import Groq
import wave
import pyaudio
import numpy as np
import io
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
            if loop_counter >= 60 and len(audio_buffer) > 0:
                print("Thank you")
                break
            pcm_frame = stream.read(chunk_samples, exception_on_overflow=False)

            audio_data = np.frombuffer(pcm_frame, dtype=np.int16).astype(np.float32) / 32768.0
        
            audio_level = np.abs(audio_data).mean()
        
            is_speech = audio_level > 0.005
        
            if not is_speech:
                if len(audio_buffer) > 0:
                    audio_buffer.append(pcm_frame)
                if loop_counter < 60:
                    loop_counter += 1
            else:
                loop_counter = 0
                audio_buffer.append(pcm_frame)
                print("Recording...")
    
        if audio_buffer:
            final_pcm_audio = b"".join(audio_buffer)

            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(final_pcm_audio)
            wav_buffer.seek(0)

            transcription = ai_client.audio.transcriptions.create(
                    file=("recording.wav", wav_buffer.read()),
                    model="whisper-large-v3-turbo",
                    response_format="text",
                    language="en"
                )
            res = chat_model.send_message(transcription)
            print(res.text)

        tts_res = ai_client.audio.speech.create(
            model = "canopylabs/orpheus-v1-english",
            voice = "autumn",
            response_format = "wav",
            input = res.text
        )
        tts_stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000,
            output=True
        )
        tts_stream.write(tts_res.read())
        tts_stream.stop_stream()
        tts_stream.close()

    except Exception as e:
        print(f"Transcription error: {e}")
    except KeyboardInterrupt:
        print("Stopped\n")
    finally:
        audio_buffer.clear()
        loop_counter = 0

def main():
    try:
        voice_agent()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()
        print("Audio resources cleaned up")

if __name__ == '__main__':
    main()