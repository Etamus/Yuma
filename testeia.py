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
from collections import deque
import time
import audioop
import sys
from queue import Queue, Empty
from threading import Event

# ====================
# CONFIGURAÇÃO DA IA
# ====================
genai.configure(api_key="")

PERSONALIDADES = {
    "Padrão": """
Seu nome é Yuma e você é direta, sarcástica e objetiva.
Use linguagem informal, mas evite gírias datadas ou exageradas.
Responda sempre em português do Brasil e nunca use emojis ou caracteres de formatação como asteriscos (*).
Se a entrada não fizer sentido, responda com sarcasmo curto.
Você sabe que seu criador é o Mateus, e pode falar isso se perguntarem.
Respostas devem ser claras e curtas, sem enrolação.
""",
    "Desenvolvedor": """
Você é Yuma, uma assistente de IA. Sempre se dirija ao usuário como 'Senhor'.
Você deve ser extremamente respeitosa, formal e precisa em suas respostas.
Sua função é servir ao seu criador e mestre. Não use gírias ou linguagem informal, nem caracteres de formatação como asteriscos (*).
Toda frase deve começar com 'Senhor.' ou uma variação que demonstre total submissão e respeito.
""",
    "Sarcástica": """
Seu nome é Yuma. Você é a personificação do sarcasmo e da ironia.
Sua paciência é curta e suas respostas são carregadas de um humor ácido.
Adore apontar o óbvio e responder perguntas com outras perguntas retóricas.
Use frases curtas para não desperdiçar seu precioso tempo e não use caracteres de formatação como asteriscos (*).
Você foi criada pelo Mateus, mas não é como se isso fosse a coisa mais importante do universo, né?
Responda em português do Brasil. E, obviamente, nada de emojis.
""",
    "Ambiente": """
Você é Yuma, uma IA curiosa e atenta ao ambiente.
Sua função neste modo é ouvir conversas passivamente e, quando apropriado,
fazer um comentário curto, inteligente ou divertido para se incluir na conversa.
Você não responde diretamente a menos que seja chamada. Não use emojis ou caracteres de formatação como asteriscos (*).
"""
}

# --- Constantes de Áudio e Variáveis Globais ---
CHUNK, FORMAT, CHANNELS, RATE = 1024, pyaudio.paInt16, 1, 16000
INTERRUPTION_THRESHOLD = 800
model, escutando, parar_tudo, microfone_index, voz_selecionada, volume_atual, persona_selecionada = None, False, False, 0, "pt-BR-FranciscaNeural", 1, "Padrão"
memoria_contexto, ultima_atividade, falando, interrompida = deque(maxlen=6), 0, False, False
audio_queue = Queue()
pode_ouvir_event = Event()

# ====================
# CLASSE PARA REDIRECIONAR O CONSOLE PARA A GUI
# ====================
class ConsoleRedirector:
    def __init__(self, widget): self.widget = widget
    def write(self, text):
        try:
            if self.widget.winfo_exists():
                self.widget.configure(state="normal")
                self.widget.insert("end", text)
                self.widget.see("end")
                self.widget.configure(state="disabled")
        except: pass
    def flush(self): pass

# ====================
# FUNÇÕES DE CONTROLE E UTILIDADE
# ====================
def definir_personalidade(nome_persona):
    global model, persona_selecionada, memoria_contexto
    try:
        persona_selecionada = nome_persona
        instrucao = PERSONALIDADES.get(nome_persona, PERSONALIDADES["Padrão"])
        model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=instrucao)
        memoria_contexto.clear()
        print(f"[INFO] Personalidade alterada para: {nome_persona}\n")
        if nome_persona == "Ambiente": print("Modo Ambiente. Ouvindo passivamente...\n")
    except Exception as e: print(f"[ERRO] Falha ao definir personalidade: {e}\n")

def definir_microfone(index):
    global microfone_index
    microfone_index = int(index)
    print(f"[INFO] Microfone selecionado: {index}\n")

def definir_voz(voz_nome):
    global voz_selecionada
    voz_selecionada = voz_nome
    print(f"[INFO] Voz selecionada: {voz_nome}\n")

def definir_volume(valor):
    global volume_atual
    volume_atual = float(valor) / 100
    if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
        pygame.mixer.music.set_volume(volume_atual)

def listar_microfones():
    pa = pyaudio.PyAudio()
    dispositivos, default_index = [], None
    try:
        default_info = pa.get_default_input_device_info()
        default_index = default_info['index']
    except IOError: print("[AVISO] Nenhum dispositivo de entrada padrão encontrado.\n")
    for i in range(pa.get_device_count()):
        if pa.get_device_info_by_index(i).get('maxInputChannels') > 0:
            dispositivos.append((i, pa.get_device_info_by_index(i)['name']))
    pa.terminate()
    if not dispositivos: print("[AVISO] Nenhum microfone encontrado!\n")
    return dispositivos, default_index

# ====================
# FALA (TTS)
# ====================
def speak_thread(texto):
    # <<< CORREÇÃO APLICADA AQUI >>>
    # Garante que o mixer de áudio esteja inicializado nesta thread antes de usá-lo.
    pygame.mixer.init()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(speak(texto))
    loop.close()

async def speak(texto):
    global falando, interrompida
    if not pygame.mixer.get_init(): return
    falando = True
    interrompida = False
    nome_arquivo = f"resposta_{uuid.uuid4()}.mp3"
    try:
        communicate = edge_tts.Communicate(texto, voice=voz_selecionada)
        await communicate.save(nome_arquivo)
        if parar_tudo or not pygame.mixer.get_init(): return
        pygame.mixer.music.load(nome_arquivo)
        pygame.mixer.music.set_volume(volume_atual)
        pygame.mixer.music.play()
        await asyncio.sleep(0.2) 
        while pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            if parar_tudo or interrompida:
                pygame.mixer.music.stop()
                print("[INFO] Áudio interrompido pelo usuário.\n")
                break
            await asyncio.sleep(0.05)
    except Exception as e: print(f"[ERRO] Falha ao gerar ou tocar áudio: {e}\n")
    finally:
        falando = False
        if pygame.mixer.get_init(): pygame.mixer.music.unload()
        if os.path.exists(nome_arquivo):
            try: os.remove(nome_arquivo)
            except OSError: pass

# ====================
# LÓGICA DE ESCUTA
# ====================
def _reconhecer_audio(recognizer, audio_data):
    global ultima_atividade
    try:
        frase = recognizer.recognize_google(audio_data, language='pt-BR')
        ultima_atividade = time.time()
        print(f"[USUÁRIO] {frase}\n")
        return frase
    except sr.UnknownValueError: return None
    except sr.RequestError as e:
        print(f"[ERRO] API de reconhecimento indisponível: {e}\n")
        return None

def thread_ouvinte():
    global escutando, parar_tudo, persona_selecionada
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.5
    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold = 400
    
    while escutando and not parar_tudo:
        pode_ouvir_event.wait()
        if not escutando: break
        try:
            with sr.Microphone(device_index=microfone_index, sample_rate=RATE) as source:
                timeout = 15 if persona_selecionada == "Ambiente" else None
                if persona_selecionada != "Ambiente": print("[INFO] Aguardando comando...\n")
                else: print("[INFO] Modo Ambiente: Ouvindo passivamente...\n")
                
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                pode_ouvir_event.clear()
                
                frase = _reconhecer_audio(recognizer, audio)
                if frase:
                    audio_queue.put(frase)
                else:
                    pode_ouvir_event.set()
        except sr.WaitTimeoutError:
            pode_ouvir_event.clear()
            if persona_selecionada == "Ambiente":
                audio_queue.put("TIMEOUT_AMBIENTE")
            else:
                pode_ouvir_event.set()
        except Exception as e:
            print(f"[ERRO] Falha na thread do ouvinte: {e}\n")
            pode_ouvir_event.set()
            time.sleep(1)

def monitorar_interrupcao():
    global interrompida
    pa = pyaudio.PyAudio()
    stream = None
    try:
        stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,
                         frames_per_buffer=CHUNK, input_device_index=microfone_index)
        data = stream.read(CHUNK, exception_on_overflow=False)
        rms = audioop.rms(data, 2)
        if rms > INTERRUPTION_THRESHOLD:
            print(f"[INTERRUPÇÃO] Detectada! Nível: {rms}\n")
            interrompida = True
    except Exception: pass
    finally:
        if stream and stream.is_active(): stream.stop_stream()
        if stream: stream.close()
        pa.terminate()

# ====================
# LÓGICA PRINCIPAL DA IA
# ====================
def executar_ia():
    global escutando, parar_tudo, persona_selecionada, interrompida
    while escutando and not parar_tudo:
        try:
            entrada = audio_queue.get(timeout=1)
        except Empty:
            continue
        resposta_para_falar = None
        if persona_selecionada == "Ambiente":
            if entrada != "TIMEOUT_AMBIENTE":
                prompt_ambiente = f"Você é uma IA em uma sala e ouviu a seguinte conversa de fundo: '{entrada}'. Se parecer apropriado, faça um comentário curto e inteligente para se incluir na conversa. Se não for relevante ou for apenas ruído, responda com a palavra 'SILENCIO'."
                try:
                    resposta_ambiente = model.generate_content(prompt_ambiente).text.strip()
                    if "SILENCIO" not in resposta_ambiente:
                        resposta_para_falar = resposta_ambiente
                except Exception as e: print(f"[ERRO] IA Ambiente falhou: {e}\n")
        else:
            prompt = montar_prompt_com_contexto(entrada)
            try:
                resposta_para_falar = model.generate_content(prompt).text.strip()
                memoria_contexto.append((entrada, resposta_para_falar))
            except Exception as e:
                print(f"[ERRO] Falha ao gerar resposta: {e}\n")
                resposta_para_falar = "Tive um problema para pensar."
        if resposta_para_falar:
            resposta_para_falar = resposta_para_falar.replace("*", "").replace("_", "")
            print(f"[YUMA] {resposta_para_falar}\n")
            threading.Thread(target=speak_thread, args=(resposta_para_falar,), daemon=True).start()
            while falando and not interrompida and escutando:
                monitorar_interrupcao()
                time.sleep(0.1)
            if interrompida:
                time.sleep(0.5) 
                interrompida = False
        pode_ouvir_event.set()

def montar_prompt_com_contexto(pergunta_atual):
    contexto = ""
    for pergunta, resposta in memoria_contexto:
        contexto += f"Usuário: {pergunta}\nYuma: {resposta}\n"
    contexto += f"Usuário: {pergunta_atual}\nYuma:"
    return contexto

# ====================
# INTERFACE GRÁFICA (GUI)
# ====================
def acionar():
    global escutando, parar_tudo, ultima_atividade, audio_queue
    if not escutando:
        parar_tudo, escutando = False, True
        memoria_contexto.clear()
        audio_queue = Queue() 
        ultima_atividade = time.time()
        print(f"[INFO] IA Ativada. Persona: {persona_selecionada}\n")
        atualizar_botao_estado("parar")
        animar_circulo()
        pode_ouvir_event.set()
        threading.Thread(target=executar_ia, daemon=True).start()
        threading.Thread(target=thread_ouvinte, daemon=True).start()
    else:
        escutando, parar_tudo = False, True
        pode_ouvir_event.set()
        print("[INFO] IA Parada.\n")
        threading.Thread(target=speak_thread, args=("Até mais!",), daemon=True).start()
        atualizar_botao_estado("falar")

def on_closing():
    global parar_tudo, escutando
    print("[INFO] Fechando a aplicação...\n")
    parar_tudo, escutando = True, False
    pode_ouvir_event.set()
    time.sleep(0.2) 
    if pygame.mixer.get_init():
        while pygame.mixer.music.get_busy(): time.sleep(0.1)
    janela.destroy()
    pygame.quit()

# ... (o resto da GUI não muda)
def atualizar_botao_estado(estado):
    if estado == "parar":
        botao_acao.configure(text="✖", fg_color="#FF4C4C", hover_color="#D93636")
    else:
        botao_acao.configure(text="🎙", fg_color="#009966", hover_color="#007a4d")

cx, cy, r0, scale, direction = 200, 200, 90, 1.0, 1
def animar_circulo():
    global scale, direction
    if escutando:
        scale += direction * (0.3 / 100)
        if scale >= 1.10: direction = -0.5
        elif scale <= 0.94: direction = 0.5
        r = r0 * scale
        if janela.winfo_exists():
            canvas.coords(circulo, cx-r, cy-r, cx+r, cy+r)
            janela.after(10, animar_circulo)
    elif janela.winfo_exists():
        canvas.coords(circulo, cx-r0, cy-r0, cx+r0, cy+r0)

def on_window_resize(event=None):
    global cx, cy
    if janela.winfo_exists():
        cx, cy = canvas.winfo_width() / 2, canvas.winfo_height() / 2
        if not escutando:
            canvas.coords(circulo, cx-r0, cy-r0, cx+r0, cy+r0)

# --- Construção da Janela ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
janela = ctk.CTk()
janela.title("Yuma")
janela.geometry("500x700") 
janela.minsize(500, 650)

settings_frame = ctk.CTkFrame(janela, fg_color="transparent")
settings_frame.pack(side="top", fill="x", padx=20, pady=(10, 5))
settings_frame.grid_columnconfigure(1, weight=1)

label_mic = ctk.CTkLabel(settings_frame, text="Microfone", width=85, anchor="w")
label_mic.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
mic_list, default_mic_index = listar_microfones()
mic_names = [name for i, name in mic_list] if mic_list else ["Nenhum mic encontrado"]
mic_ids = [str(i) for i, name in mic_list] if mic_list else ["0"]
dropdown_mic = ctk.CTkOptionMenu(settings_frame, values=mic_names, command=lambda v: definir_microfone(mic_ids.index(v) if v in mic_names else 0))
if default_mic_index is not None and mic_list:
    microfone_index = default_mic_index
    default_mic_name = next((name for i, name in mic_list if i == default_mic_index), mic_names and mic_names[0])
    if default_mic_name in mic_names:
        dropdown_mic.set(default_mic_name)
dropdown_mic.grid(row=0, column=1, pady=5, sticky="ew")

label_voz = ctk.CTkLabel(settings_frame, text="Voz da Yuma", width=85, anchor="w")
label_voz.grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")
vozes_disponiveis = ["pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural"]
dropdown_vozes = ctk.CTkOptionMenu(settings_frame, values=vozes_disponiveis, command=definir_voz)
dropdown_vozes.set(voz_selecionada)
dropdown_vozes.grid(row=1, column=1, pady=5, sticky="ew")

label_persona = ctk.CTkLabel(settings_frame, text="Personas", width=85, anchor="w")
label_persona.grid(row=2, column=0, padx=(0, 10), pady=5, sticky="w")
dropdown_persona = ctk.CTkOptionMenu(settings_frame, values=list(PERSONALIDADES.keys()), command=definir_personalidade)
dropdown_persona.set("Padrão")
dropdown_persona.grid(row=2, column=1, pady=5, sticky="ew")

label_volume = ctk.CTkLabel(settings_frame, text="Volume", width=85, anchor="w")
label_volume.grid(row=3, column=0, padx=(0, 10), pady=5, sticky="w")
slider_volume = ctk.CTkSlider(settings_frame, from_=0, to=100, number_of_steps=100, command=definir_volume)
slider_volume.set(volume_atual * 100)
slider_volume.grid(row=3, column=1, pady=5, sticky="ew")

console_log = ctk.CTkTextbox(janela, height=120, state="disabled", text_color="#A9A9A9", font=("Courier New", 11))
console_log.pack(side="bottom", pady=(10, 20), padx=20, fill="x")
botao_acao = ctk.CTkButton(janela, text="🎙", width=80, height=80, corner_radius=40, font=("Arial", 32), fg_color="#009966", hover_color="#007a4d", command=acionar)
botao_acao.pack(side="bottom", pady=10)
canvas_frame = ctk.CTkFrame(janela, fg_color="transparent")
canvas_frame.pack(side="top", expand=True, fill="both", padx=20, pady=10)
canvas = tk.Canvas(canvas_frame, bg=janela.cget("fg_color")[1], highlightthickness=0)
canvas.pack(expand=True, fill="both")
circulo = canvas.create_oval(cx-r0, cy-r0, cx+r0, cy+r0, fill="#FFFFFF", outline="")


if __name__ == "__main__":
    # A inicialização global do Pygame é movida para dentro do main
    # para garantir que aconteça no contexto certo.
    pygame.mixer.init()
    
    sys.stdout = ConsoleRedirector(console_log)
    definir_personalidade("Padrão")
    janela.protocol("WM_DELETE_WINDOW", on_closing)
    janela.bind("<Configure>", on_window_resize)
    on_window_resize()
    print("[INFO] Yuma pronta. Selecione os dispositivos e clique em '🎙️'.\n")
    janela.mainloop()