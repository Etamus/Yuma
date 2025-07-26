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


# ====================
# CONFIGURAÇÃO DA IA
# ====================
genai.configure(api_key="")

model = genai.GenerativeModel(
    model_name="models/gemini-2.5-flash",
    system_instruction="""
Seu nome é Yuma e você é bem-humorada, direta e sarcástica.
Fala de forma informal, como se fosse um amigo zoando.
Responda sempre em português do Brasil. Nunca use emojis nas respostas.
Se a entrada não fizer sentido, responda com sarcasmo como se não tivesse entendido"
"""
)

pygame.mixer.init()
escutando = False
parar_tudo = False
microfone_index = 0


# ====================
# FALA
# ====================
async def speak(texto):
    global parar_tudo
    nome_arquivo = f"resposta_{uuid.uuid4()}.mp3"
    communicate = edge_tts.Communicate(texto, voice="pt-BR-FranciscaNeural")
    await communicate.save(nome_arquivo)
    if parar_tudo:
        os.remove(nome_arquivo)
        return
    pygame.mixer.music.load(nome_arquivo)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        if parar_tudo:
            pygame.mixer.music.stop()
            break
        await asyncio.sleep(0.1)
    pygame.mixer.music.unload()
    if os.path.exists(nome_arquivo):
        os.remove(nome_arquivo)


# ====================
# MICROFONE
# ====================
def listar_microfones():
    pa = pyaudio.PyAudio()
    dispositivos = []
    try:
        default_info = pa.get_default_input_device_info()
        default_index = default_info.get('index', None)
    except:
        default_index = None

    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)

        nome = info["name"].lower()
        entrada = info["maxInputChannels"]
        saida = info["maxOutputChannels"]

        # Critérios para aceitar como microfone:
        if entrada > 0:
            if (
                ("mic" in nome) or 
                ("microfone" in nome) or 
                ("input" in nome) or 
                ("capture" in nome) or
                (saida == 0) or  # Se não tem saída, é bem provável ser microfone
                (entrada >= 1 and saida <= 1)  # Entrada bem maior que saída
            ):
                dispositivos.append((i, info["name"]))

    pa.terminate()

    if not dispositivos:
        print("[AVISO] Nenhum microfone encontrado!")

    if default_index is None and dispositivos:
        default_index = dispositivos[0][0]

    return dispositivos, default_index


def definir_microfone(index):
    global microfone_index
    microfone_index = int(index)
    print(f"[INFO] Microfone selecionado: {index}")


# ====================
# OUVIR
# ====================
def ouvir_microfone():
    recognizer = sr.Recognizer()

    try:
        with sr.Microphone(device_index=microfone_index) as source:
            print(f"[INFO] Ouvindo pelo microfone: {source.device_index}")
            recognizer.adjust_for_ambient_noise(source, duration=0.8)
            audio = recognizer.listen(source, timeout=None, phrase_time_limit=None)
    except Exception as e:
        print(f"[ERRO] Problema ao acessar o microfone: {e}")
        resposta_label.configure(text=f"Erro no microfone: {e}")
        return None

    try:
        frase = recognizer.recognize_google(audio, language='pt-BR')
        print(f"[USUÁRIO] {frase}")
        return frase
    except sr.UnknownValueError:
        print("[ERRO] Não entendi o que você disse (UnknownValueError).")
        resposta_label.configure(text="Não foi possível entender. Fale novamente.")
        return None
    except sr.RequestError as e:
        print(f"[ERRO] Erro no serviço de reconhecimento de voz: {e}")
        resposta_label.configure(text="Erro na API de reconhecimento.")
        return None
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {e}")
        resposta_label.configure(text=f"Erro inesperado: {e}")
        return None


# ====================
# FRASE PROATIVA
# ====================
def gerar_frase_proativa():
    try:
        prompt = """
Gere uma frase divertida, sarcástica ou curiosa para puxar papo, como se fosse uma inteligência artificial que percebe que o usuário está em silêncio. Fale de forma informal, como se fosse um amigo zoando. Não use emojis. Seja direto, criativo e espontâneo. Apenas responda a frase, sem explicações.
"""
        resposta = model.generate_content(prompt).text.strip()
        print(f"[YUMA - Proativa] {resposta}")
        return resposta
    except Exception as e:
        print(f"[ERROR] Erro ao gerar frase proativa: {e}")
        return "Tá muito silêncio aí... Fala comigo pô!"


# ====================
# IA LOOP
# ====================
def executar_ia():
    global escutando, parar_tudo
    try:
        asyncio.run(speak("Como vai?."))
        while escutando and not parar_tudo:
            entrada = ouvir_microfone()
            if not escutando or parar_tudo:
                break
            if entrada:
                resposta = model.generate_content(entrada).text
                resposta_label.configure(text=resposta)
                print(f"[YUMA] {resposta}")
                asyncio.run(speak(resposta))
            else:
                resposta = gerar_frase_proativa()
                resposta_label.configure(text=resposta)
                print(f"[YUMA] {resposta}")
                asyncio.run(speak(resposta))
    except Exception as e:
        print(f"[ERROR] {e}")
        resposta_label.configure(text=f"Erro: {e}")


# ====================
# BOTÕES
# ====================
def acionar():
    global escutando, parar_tudo
    if not escutando:
        parar_tudo = False
        escutando = True
        resposta_label.configure(text="Ouvindo você...")
        print("[INFO] IA Ativada")
        atualizar_botao_estado("parar")
        animar_circulo()
        threading.Thread(target=executar_ia, daemon=True).start()
    else:
        escutando = False
        parar_tudo = True
        resposta_label.configure(text="Parado.")
        asyncio.run(speak("Beleza, parei de ouvir."))
        print("[INFO] IA Parada")
        canvas.coords(circulo, cx-r0, cy-r0, cx+r0, cy+r0)
        atualizar_botao_estado("falar")


def atualizar_botao_estado(estado):
    if estado == "parar":
        botao_acao.configure(
            text="✖",
            fg_color="#FF4C4C",
            hover_color="#D93636"
        )
    else:
        botao_acao.configure(
            text="🎙",
            fg_color="#009966",
            hover_color="#007a4d"
        )


# ====================
# CÍRCULO ANIMAÇÃO
# ====================
cx, cy = 200, 200
r0 = 90
delta = 0.3
scale = 1.0
direction = 1

def animar_circulo():
    global scale, direction
    if escutando:
        scale += direction * (delta / 100)
        if scale >= 1.04:
            direction = -1
        elif scale <= 0.96:
            direction = 1
        r = r0 * scale
        canvas.coords(circulo, cx-r, cy-r, cx+r, cy+r)
        janela.after(20, animar_circulo)


def atualizar_canvas_tamanho(event):
    global cx, cy
    cx = event.width / 2
    cy = event.height / 2
    r = r0 * scale
    canvas.coords(circulo, cx - r, cy - r, cx + r, cy + r)


# ====================
# INTERFACE
# ====================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

janela = ctk.CTk()
janela.title("Yuma")
janela.geometry("500x700")
janela.minsize(400, 600)
janela.resizable(True, True)

# Dropdown de microfone
mic_list, default_index = listar_microfones()
mic_names = [name for i, name in mic_list]
mic_ids = [str(i) for i, name in mic_list]

if default_index is not None:
    microfone_index = default_index
    default_index_name = next((name for i, name in mic_list if i == default_index), mic_names[0])
else:
    microfone_index = int(mic_ids[0])
    default_index_name = mic_names[0]

dropdown = ctk.CTkOptionMenu(
    janela,
    values=mic_names,
    command=lambda v: definir_microfone(mic_ids[mic_names.index(v)])
)
dropdown.set(default_index_name)
dropdown.pack(pady=10, fill="x", padx=20)

# Canvas frame
canvas_frame = ctk.CTkFrame(janela, fg_color="transparent")
canvas_frame.pack(expand=True, fill="both", padx=20, pady=10)

canvas = tk.Canvas(canvas_frame, bg="#1e1e1e", highlightthickness=0)
canvas.pack(expand=True, fill="both")
canvas.bind("<Configure>", atualizar_canvas_tamanho)

circulo = canvas.create_oval(cx-r0, cy-r0, cx+r0, cy+r0, fill="#FFFFFF", outline="")

# Botão único
botao_acao = ctk.CTkButton(
    janela, text="🎙", width=80, height=80, corner_radius=40,
    font=("Arial", 28), fg_color="#009966", hover_color="#007a4d",
    command=acionar
)
botao_acao.pack(pady=10)

# Label resposta
resposta_label = ctk.CTkLabel(
    janela, text="Parado.", wraplength=450, justify="center",
    font=("Arial", 16)
)
resposta_label.pack(pady=20, padx=20, fill="x")

janela.mainloop()
