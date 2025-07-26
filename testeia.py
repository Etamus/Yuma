import google.generativeai as genai
import speech_recognition as sr
import edge_tts
import asyncio
import os
import uuid
import pygame

# Configura a API do Gemini
genai.configure(api_key="")  # <--- coloca tua chave aqui

# Usa o modelo Gemini 1.5 Flash
model = genai.GenerativeModel(
    model_name="models/gemini-2.0-flash",
    system_instruction="""
Você é bem-humorada, direta e sarcástica.
Fala de forma informal, como se fosse um amigo zoando.
Responda sempre em português do Brasil. Nunca use emojis nas respostas.
Não escreva rostinhos, corações ou qualquer símbolo visual. Só texto puro.
"""
)

# Inicializa o pygame
pygame.mixer.init()

# Fala com voz neural (sem abrir player)
async def speak(texto):
    nome_arquivo = f"resposta_{uuid.uuid4()}.mp3"
    communicate = edge_tts.Communicate(texto, voice="pt-BR-FranciscaNeural")
    await communicate.save(nome_arquivo)
    pygame.mixer.music.load(nome_arquivo)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
    pygame.mixer.music.unload()  # <- libera o arquivo
    os.remove(nome_arquivo)

# Ouve o microfone
def ouvir_microfone():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Você: (fala aí)")
        audio = recognizer.listen(source)
    try:
        frase = recognizer.recognize_google(audio, language='pt-BR')
        print("Você disse:", frase)
        return frase
    except sr.UnknownValueError:
        print("Não entendi :(")
        return None
    except sr.RequestError:
        print("Erro na API de reconhecimento")
        return None

# Loop principal
while True:
    entrada = ouvir_microfone()
    if entrada:
        if entrada.lower() in ["sair", "tchau", "fechar"]:
            asyncio.run(speak("Até logo! Foi bom falar com você."))
            break
        resposta = model.generate_content(entrada)
        asyncio.run(speak(resposta.text))