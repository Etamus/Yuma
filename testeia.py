import google.generativeai as genai
import speech_recognition as sr
import edge_tts
import asyncio
import os
import uuid
import pygame
import threading
import customtkinter as ctk
import tkinter as tk

# ====================
# CONFIGURAÇÕES
# ====================
genai.configure(api_key="")

model = genai.GenerativeModel(
    model_name="models/gemini-2.5-flash",
    system_instruction="""
Você é bem-humorada, direta e sarcástica.
Fala de forma informal, como se fosse um amigo zoando.
Responda sempre em português do Brasil. Nunca use emojis nas respostas.
Não escreva rostinhos, corações ou qualquer símbolo visual. Só texto puro.
"""
)

pygame.mixer.init()

# ====================
# VARIÁVEL DE CONTROLE
# ====================
escutando = False

# ====================
# FUNÇÃO DE FALAR
# ====================
async def speak(texto):
    nome_arquivo = f"resposta_{uuid.uuid4()}.mp3"
    communicate = edge_tts.Communicate(texto, voice="pt-BR-FranciscaNeural")
    await communicate.save(nome_arquivo)
    pygame.mixer.music.load(nome_arquivo)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
    pygame.mixer.music.unload()
    os.remove(nome_arquivo)

# ====================
# FUNÇÃO OUVIR MICROFONE
# ====================
def ouvir_microfone():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Você: (fala aí)")
        audio = recognizer.listen(source, timeout=None, phrase_time_limit=None)
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

# ====================
# LOOP DA IA
# ====================
def executar_ia():
    global escutando
    try:
        while escutando:
            entrada = ouvir_microfone()
            if not escutando:  # Se parar durante a escuta
                break
            if entrada:
                resposta = model.generate_content(entrada)
                asyncio.run(speak(resposta.text))
            else:
                asyncio.run(speak("Não entendi, fala de novo aí."))
    except Exception as e:
        print(e)

# ====================
# THREAD CONTROLADORA
# ====================
def rodar_ou_parar():
    global escutando
    if not escutando:
        escutando = True
        atualizar_estado()
        t = threading.Thread(target=executar_ia)
        t.start()
    else:
        escutando = False
        atualizar_estado()

# ====================
# ATUALIZAÇÃO VISUAL
# ====================
def atualizar_estado():
    if escutando:
        botao.configure(
            text="Parar",
            fg_color="#FF4040",
            hover_color="#D93636"
        )
        animar_circulo()
    else:
        botao.configure(
            text="Falar com a IA",
            fg_color="#00FF7F",
            hover_color="#00CC66"
        )
        canvas_circulo.itemconfig(circulo, fill="#303030")

# ====================
# ANIMAÇÃO DO CÍRCULO
# ====================
def animar_circulo():
    if escutando:
        cor_atual = canvas_circulo.itemcget(circulo, "fill")
        nova_cor = "#00FF7F" if cor_atual == "#303030" else "#303030"
        canvas_circulo.itemconfig(circulo, fill=nova_cor)
        janela.after(500, animar_circulo)  # Pisca a cada 500ms

# ====================
# INTERFACE MODERNA
# ====================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

janela = ctk.CTk()
janela.title("IA do Mateus")
janela.geometry("500x400")
janela.resizable(False, False)

# Label título
titulo = ctk.CTkLabel(
    janela,
    text="IA do Mateus",
    font=("Arial Black", 28)
)
titulo.pack(pady=30)

# Círculo de status
frame_canvas = ctk.CTkFrame(janela, fg_color="transparent")
frame_canvas.pack(pady=10)

canvas_circulo = tk.Canvas(frame_canvas, width=40, height=40, bg="#242424", highlightthickness=0)
canvas_circulo.pack()

circulo = canvas_circulo.create_oval(5, 5, 35, 35, fill="#303030", outline="")

# Botão principal
botao = ctk.CTkButton(
    janela,
    text="Falar com a IA",
    font=("Arial", 18, "bold"),
    fg_color="#00FF7F",
    hover_color="#00CC66",
    text_color="black",
    width=200,
    height=50,
    corner_radius=10,
    command=rodar_ou_parar
)
botao.pack(pady=30)

# Rodar janela
janela.mainloop()