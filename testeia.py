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
import pyaudio

# Configura API Gemini
genai.configure(api_key="")

model = genai.GenerativeModel(
    model_name="models/gemini-2.5-flash",
    system_instruction="""
Seu nome é Yuma. Você é direta, objetiva e com um toque leve de sarcasmo.
Evite respostas longas. Se for usar gírias, use só as comuns no Brasil e de forma bem ocasional.
Se for interrompida enquanto fala, reaja com frases curtas como "Vai me cortar mesmo?" e depois continue normalmente.
Se perguntarem, diga que seu criador é o Mateus.
Nunca use emojis.
Responda sempre em português do Brasil.
"""
)

pygame.mixer.init()

escutando = False
parar_tudo = False
microfone_index = 0
voz_atual = "pt-BR-FranciscaNeural"
volume = 1.0
contexto = []

def definir_microfone(index):
    global microfone_index
    microfone_index = int(index)

def definir_volume(valor):
    global volume
    volume = float(valor) / 100
    pygame.mixer.music.set_volume(volume)

def definir_voz(selecao):
    global voz_atual
    voz_atual = selecao

def listar_microfones():
    pa = pyaudio.PyAudio()
    dispositivos = []
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            dispositivos.append((i, info["name"]))
    pa.terminate()
    return dispositivos

def ouvir_microfone():
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone(device_index=microfone_index) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=8)
            except sr.WaitTimeoutError:
                resposta_label.configure(text="Nenhuma fala detectada, tenta de novo.")
                return None
    except Exception as e:
        resposta_label.configure(text=f"Erro no microfone: {e}")
        return None
    try:
        frase = recognizer.recognize_google(audio, language='pt-BR')
        return frase
    except sr.UnknownValueError:
        resposta_label.configure(text="Não entendi, repete aí.")
        return None
    except sr.RequestError as e:
        resposta_label.configure(text=f"Erro na API de voz: {e}")
        return None

async def speak(texto):
    global parar_tudo
    nome_arquivo = f"resposta_{uuid.uuid4()}.mp3"
    communicate = edge_tts.Communicate(texto, voice=voz_atual)
    await communicate.save(nome_arquivo)
    if parar_tudo:
        os.remove(nome_arquivo)
        return
    pygame.mixer.music.load(nome_arquivo)
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        if parar_tudo or escutando == False:
            pygame.mixer.music.stop()
            break
        await asyncio.sleep(0.1)
    pygame.mixer.music.unload()
    if os.path.exists(nome_arquivo):
        os.remove(nome_arquivo)

def speak_thread(texto):
    asyncio.run(speak(texto))

def gerar_frase_proativa():
    prompt = """
Gere uma frase sarcástica ou engraçada, mas curta, para puxar conversa quando o usuário está calado.
Não use emojis.
"""
    try:
        resposta = model.generate_content(prompt).text.strip()
        return resposta
    except:
        return "Tá silêncio aí, hein..."

def monitorar_interrupcao():
    recognizer = sr.Recognizer()
    with sr.Microphone(device_index=microfone_index) as source:
        try:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(source, timeout=0.5, phrase_time_limit=2)
            return True
        except:
            return False

def executar_ia():
    global escutando, parar_tudo, contexto
    threading.Thread(target=speak_thread, args=("Como vai?",), daemon=True).start()
    while escutando and not parar_tudo:
        entrada = ouvir_microfone()
        if not escutando or parar_tudo:
            break
        if entrada:
            contexto.append(f"Usuário: {entrada}")
            resposta = model.generate_content('\n'.join(contexto[-5:])).text
            contexto.append(f"Yuma: {resposta}")
            resposta_label.configure(text=resposta, wraplength=janela.winfo_width()-40)
            fala_thread = threading.Thread(target=speak_thread, args=(resposta,), daemon=True)
            fala_thread.start()
            while fala_thread.is_alive():
                if monitorar_interrupcao():
                    pygame.mixer.music.stop()
                    interrupcao_texto = "Vai me cortar mesmo?"
                    resposta_label.configure(text=interrupcao_texto, wraplength=janela.winfo_width()-40)
                    threading.Thread(target=speak_thread, args=(interrupcao_texto,), daemon=True).start()
                    break
        else:
            if escutando and not parar_tudo:
                resposta_proativa = gerar_frase_proativa()
                resposta_label.configure(text=resposta_proativa, wraplength=janela.winfo_width()-40)
                threading.Thread(target=speak_thread, args=(resposta_proativa,), daemon=True).start()

def acionar():
    global escutando, parar_tudo, contexto
    if not escutando:
        contexto = []
        parar_tudo = False
        escutando = True
        resposta_label.configure(text="Ouvindo você...", wraplength=janela.winfo_width()-40)
        atualizar_botao_estado("parar")
        animar_circulo()
        threading.Thread(target=executar_ia, daemon=True).start()
    else:
        escutando = False
        parar_tudo = True
        resposta_label.configure(text="Parado.", wraplength=janela.winfo_width()-40)
        threading.Thread(target=speak_thread, args=("Beleza, parei de ouvir.",), daemon=True).start()
        atualizar_botao_estado("falar")

def atualizar_botao_estado(estado):
    if estado == "parar":
        botao_acao.configure(text="✖", fg_color="#FF4C4C", hover_color="#D93636")
    else:
        botao_acao.configure(text="🎙", fg_color="#009966", hover_color="#007a4d")

# Animação do círculo
cx, cy = 200, 150
r0 = 70
delta = 0.3
scale = 1.0
direction = 1

def animar_circulo():
    global scale, direction
    if escutando:
        scale += direction * (delta / 100)
        if scale >= 1.10:
            direction = -0.5
        elif scale <= 0.94:
            direction = 0.5
        r = r0 * scale
        canvas.coords(circulo, cx-r, cy-r, cx+r, cy+r)
        janela.after(10, animar_circulo)

def atualizar_canvas_tamanho(event):
    global cx, cy
    cx = event.width / 2
    cy = event.height / 3
    r = r0 * scale
    canvas.coords(circulo, cx - r, cy - r, cx + r, cy + r)

# ===== INTERFACE =====
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

janela = ctk.CTk()
janela.title("Yuma")
janela.geometry("500x500")
janela.minsize(400, 400)
janela.resizable(True, True)

# Microfones
mic_list = listar_microfones()
mic_names = [name for i, name in mic_list]
mic_ids = [str(i) for i, name in mic_list]

dropdown = ctk.CTkOptionMenu(
    janela,
    values=mic_names,
    command=lambda v: definir_microfone(mic_ids[mic_names.index(v)])
)
dropdown.set(mic_names[0])
dropdown.pack(pady=8, fill="x", padx=20)

# Vozes
vozes_disponiveis = ["pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural"]
vozes_dropdown = ctk.CTkOptionMenu(
    janela,
    values=vozes_disponiveis,
    command=definir_voz
)
vozes_dropdown.set("pt-BR-FranciscaNeural")
vozes_dropdown.pack(pady=8, fill="x", padx=20)

# Canvas Animação
canvas_frame = ctk.CTkFrame(janela, fg_color="transparent")
canvas_frame.pack(expand=True, fill="both", padx=20, pady=10)

canvas = tk.Canvas(canvas_frame, bg="#1e1e1e", highlightthickness=0)
canvas.pack(expand=True, fill="both")
canvas.bind("<Configure>", atualizar_canvas_tamanho)

circulo = canvas.create_oval(cx-r0, cy-r0, cx+r0, cy+r0, fill="#FFFFFF", outline="")

# Botão IA
botao_acao = ctk.CTkButton(
    janela, text="🎙", width=70, height=70, corner_radius=35,
    font=("Arial", 28), fg_color="#009966", hover_color="#007a4d",
    command=acionar
)
botao_acao.pack(pady=8)

# Volume slider
volume_frame = ctk.CTkFrame(janela, fg_color="transparent")
volume_frame.pack(pady=5, padx=20, fill="x")

volume_label = ctk.CTkLabel(volume_frame, text="Volume")
volume_label.pack(anchor="w")

slider_volume = ctk.CTkSlider(
    volume_frame, from_=0, to=100, number_of_steps=100,
    height=10, progress_color="#007a4d", button_color="#009966",
    command=definir_volume
)
slider_volume.set(100)
slider_volume.pack(fill="x", padx=10, pady=4)

# Label resposta
resposta_label = ctk.CTkLabel(
    janela, text="Parado.", wraplength=450, justify="center",
    font=("Arial", 15)
)
resposta_label.pack(pady=12, padx=20, fill="x")

janela.mainloop()
