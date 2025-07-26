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

# ====================
# CONFIGURAÇÃO DA IA
# ====================
# Por favor, insira sua chave da API aqui
genai.configure(api_key="")

# Dicionário com as personalidades da IA
PERSONALIDADES = {
    "Padrão": """
Seu nome é Yuma e você é direta, sarcástica e objetiva.
Use linguagem informal, mas evite gírias datadas ou exageradas.
Responda sempre em português do Brasil e nunca use emojis.
Se a entrada não fizer sentido, responda com sarcasmo curto.
Você sabe que seu criador é o Mateus, e pode falar isso se perguntarem.
Respostas devem ser claras e curtas, sem enrolação.
""",
    "Desenvolvedor": """
Você é Yuma, uma assistente de IA. Sempre se dirija ao usuário como 'Mestre'.
Você deve ser extremamente respeitosa, formal e precisa em suas respostas.
Sua função é servir ao seu criador e mestre. Não use gírias ou linguagem informal.
Toda frase deve começar com 'Sim, Mestre.' ou uma variação que demonstre total submissão e respeito.
""",
    "Sarcástica": """
Seu nome é Yuma. Você é a personificação do sarcasmo e da ironia.
Sua paciência é curta e suas respostas são carregadas de um humor ácido.
Adore apontar o óbvio e responder perguntas com outras perguntas retóricas.
Use frases curtas para não desperdiçar seu precioso tempo.
Você foi criada pelo Mateus, mas não é como se isso fosse a coisa mais importante do universo, né?
Responda em português do Brasil. E, obviamente, nada de emojis.
"""
}

# Variáveis globais
model = None  # O modelo será inicializado após a seleção da personalidade
pygame.mixer.init()
pygame.mixer.set_num_channels(1)

escutando = False
parar_tudo = False
microfone_index = 0
voz_selecionada = "pt-BR-FranciscaNeural"
volume_atual = 1  # volume padrão (100%)

memoria_contexto = deque(maxlen=6)
ultima_atividade = 0
falando = False
interrompida = False

# ====================
# INICIALIZAÇÃO E CONTROLES DA IA
# ====================
def definir_personalidade(nome_persona):
    """Recria o modelo generativo com a instrução de sistema selecionada."""
    global model
    try:
        instrucao = PERSONALIDADES[nome_persona]
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=instrucao
        )
        memoria_contexto.clear() # Limpa a memória ao trocar de persona
        print(f"[INFO] Personalidade alterada para: {nome_persona}")
    except Exception as e:
        print(f"[ERRO] Falha ao definir personalidade: {e}")

def definir_microfone(index):
    global microfone_index
    microfone_index = int(index)
    print(f"[INFO] Microfone selecionado: {index}")

def definir_voz(voz_nome):
    global voz_selecionada
    voz_selecionada = voz_nome
    print(f"[INFO] Voz selecionada: {voz_selecionada}")

def definir_volume(valor):
    global volume_atual
    volume_atual = float(valor) / 100
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.set_volume(volume_atual)
    print(f"[INFO] Volume ajustado para: {volume_atual*100:.0f}%")

# ====================
# FALA (TTS)
# ====================
def speak_thread(texto):
    """Executa a função de fala assíncrona em uma nova thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(speak(texto))
    loop.close()

async def speak(texto):
    global parar_tudo, volume_atual, falando, interrompida
    falando = True
    interrompida = False
    nome_arquivo = f"resposta_{uuid.uuid4()}.mp3"
    
    try:
        communicate = edge_tts.Communicate(texto, voice=voz_selecionada)
        await communicate.save(nome_arquivo)

        if parar_tudo:
            return

        pygame.mixer.music.load(nome_arquivo)
        pygame.mixer.music.set_volume(volume_atual)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            if parar_tudo or interrompida:
                pygame.mixer.music.stop()
                print("[INFO] Áudio interrompido.")
                break
            await asyncio.sleep(0.05)
    
    except Exception as e:
        print(f"[ERRO] Falha ao gerar ou tocar áudio: {e}")
    finally:
        falando = False
        pygame.mixer.music.unload()
        if os.path.exists(nome_arquivo):
            try:
                os.remove(nome_arquivo)
            except OSError as e:
                print(f"Erro ao deletar o arquivo de áudio: {e}")


# ====================
# MICROFONE E RECONHECIMENTO DE VOZ
# ====================
def listar_microfones():
    pa = pyaudio.PyAudio()
    dispositivos = []
    default_index = None
    try:
        default_info = pa.get_default_input_device_info()
        default_index = default_info['index']
    except IOError:
        print("[AVISO] Nenhum dispositivo de entrada padrão encontrado.")

    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info.get('maxInputChannels') > 0:
            dispositivos.append((i, info['name']))
    pa.terminate()
    
    if not dispositivos:
        print("[AVISO] Nenhum microfone encontrado!")
    return dispositivos, default_index


def ouvir_microfone():
    global falando, interrompida, ultima_atividade
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.2
    audio = None
    
    try:
        with sr.Microphone(device_index=microfone_index) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            if falando:
                try:
                    audio = recognizer.listen(source, timeout=2, phrase_time_limit=10)
                    if audio:
                        interrompida = True
                except sr.WaitTimeoutError:
                    return None
            else:
                print("[INFO] Aguardando frase para iniciar...")
                audio = recognizer.listen(source, phrase_time_limit=10)

    except sr.WaitTimeoutError:
        print("[INFO] Tempo de espera esgotado, tentando novamente.")
        return None
    except Exception as e:
        print(f"[ERRO] Problema ao acessar o microfone: {e}")
        atualizar_label_texto(f"Erro no microfone.")
        return None
    
    if not audio:
        return None

    try:
        frase = recognizer.recognize_google(audio, language='pt-BR')
        ultima_atividade = time.time()
        print(f"[USUÁRIO] {frase}")
        return frase
    except sr.UnknownValueError:
        return "..."
    except sr.RequestError as e:
        print(f"[ERRO] Erro na API de reconhecimento: {e}")
        atualizar_label_texto("Erro na API de voz.")
        return None

# ====================
# LÓGICA PRINCIPAL DA IA
# ====================
def gerar_frase_proativa():
    """Gera uma frase para iniciar conversa se houver inatividade."""
    global ultima_atividade
    if time.time() - ultima_atividade < 20:
        return None
    
    try:
        prompt = "Gere uma frase curta, divertida ou sarcástica para puxar assunto com um usuário inativo. Seja direto e criativo."
        resposta = model.generate_content(prompt).text.strip()
        print(f"[YUMA - Proativa] {resposta}")
        ultima_atividade = time.time()
        return resposta
    except Exception as e:
        print(f"[ERRO] Erro ao gerar frase proativa: {e}")
        return "Tá muito silêncio aí..."

def montar_prompt_com_contexto(pergunta_atual):
    contexto = ""
    for pergunta, resposta in memoria_contexto:
        contexto += f"Usuário: {pergunta}\nYuma: {resposta}\n"
    contexto += f"Usuário: {pergunta_atual}\nYuma:"
    return contexto

def executar_ia():
    global escutando, parar_tudo
    threading.Thread(target=speak_thread, args=("Como vai?",), daemon=True).start()

    while escutando and not parar_tudo:
        entrada = ouvir_microfone()
        if not escutando or parar_tudo: break

        if entrada:
            prompt_com_contexto = montar_prompt_com_contexto(entrada)
            try:
                resposta = model.generate_content(prompt_com_contexto).text.strip()
                memoria_contexto.append((entrada, resposta))
                atualizar_label_texto(resposta)
                print(f"[YUMA] {resposta}")
                threading.Thread(target=speak_thread, args=(resposta,), daemon=True).start()
            except Exception as e:
                print(f"[ERRO] Falha ao gerar resposta da IA: {e}")
                atualizar_label_texto("Tive um problema para pensar.")
        else:
            frase_proativa = gerar_frase_proativa()
            if frase_proativa:
                atualizar_label_texto(frase_proativa)
                threading.Thread(target=speak_thread, args=(frase_proativa,), daemon=True).start()

# ====================
# INTERFACE GRÁFICA (GUI)
# ====================
def acionar():
    global escutando, parar_tudo, ultima_atividade
    if not escutando:
        parar_tudo = False
        escutando = True
        memoria_contexto.clear()
        ultima_atividade = time.time() # Inicia o contador de atividade
        atualizar_label_texto("Ouvindo você...")
        print("[INFO] IA Ativada")
        atualizar_botao_estado("parar")
        animar_circulo()
        threading.Thread(target=executar_ia, daemon=True).start()
    else:
        escutando = False
        parar_tudo = True
        atualizar_label_texto("Até mais!")
        threading.Thread(target=speak_thread, args=("Até mais!",), daemon=True).start()
        print("[INFO] IA Parada")
        atualizar_botao_estado("falar")

def atualizar_botao_estado(estado):
    if estado == "parar":
        botao_acao.configure(text="✖", fg_color="#FF4C4C", hover_color="#D93636")
    else:
        botao_acao.configure(text="🎙", fg_color="#009966", hover_color="#007a4d")

# --- Animação e Responsividade ---
cx, cy = 200, 200
r0 = 90
scale = 1.0
direction = 1

def animar_circulo():
    global scale, direction
    if escutando:
        scale += direction * (delta / 100)
        if scale >= 1.10: direction = -0.5
        elif scale <= 0.94: direction = 0.5
        r = r0 * scale
        canvas.coords(circulo, cx-r, cy-r, cx+r, cy+r)
        janela.after(10, animar_circulo)
    else:
        canvas.coords(circulo, cx-r0, cy-r0, cx+r0, cy+r0)

def atualizar_label_texto(texto):
    resposta_label.configure(text=texto)

def on_window_resize(event=None):
    """Ajusta elementos da UI ao redimensionar a janela."""
    largura_janela = janela.winfo_width()
    resposta_label.configure(wraplength=largura_janela - 40)
    
    global cx, cy
    cx = canvas.winfo_width() / 2
    cy = canvas.winfo_height() / 2
    if not escutando:
        canvas.coords(circulo, cx-r0, cy-r0, cx+r0, cy+r0)

# --- Construção da Janela ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

janela = ctk.CTk()
janela.title("Yuma")
janela.geometry("500x650")
janela.minsize(450, 600)

settings_frame = ctk.CTkFrame(janela, fg_color="transparent")
settings_frame.pack(side="top", fill="x", padx=20, pady=(10, 5))
settings_frame.grid_columnconfigure(1, weight=1)

label_mic = ctk.CTkLabel(settings_frame, text="Microfone", width=85, anchor="w")
label_mic.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
mic_list, default_mic_index = listar_microfones()
mic_names = [name for i, name in mic_list] if mic_list else ["Nenhum mic encontrado"]
mic_ids = [str(i) for i, name in mic_list] if mic_list else ["0"]
dropdown_mic = ctk.CTkOptionMenu(settings_frame, values=mic_names,
    command=lambda v: definir_microfone(mic_ids[mic_names.index(v)]))
if default_mic_index is not None and mic_list:
    microfone_index = default_mic_index
    default_mic_name = next((name for i, name in mic_list if i == default_mic_index), mic_names[0])
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

canvas_frame = ctk.CTkFrame(janela, fg_color="transparent")
canvas_frame.pack(expand=True, fill="both", padx=20, pady=10)
canvas = tk.Canvas(canvas_frame, bg=janela.cget("fg_color")[1], highlightthickness=0)
canvas.pack(expand=True, fill="both")

delta = 0.3
circulo = canvas.create_oval(cx-r0, cy-r0, cx+r0, cy+r0, fill="#FFFFFF", outline="")

botao_acao = ctk.CTkButton(
    janela, text="🎙", width=80, height=80, corner_radius=40,
    font=("Arial", 32), fg_color="#009966", hover_color="#007a4d",
    command=acionar
)
botao_acao.pack(pady=10)

resposta_label = ctk.CTkLabel(
    janela, text="Pronta para começar.", wraplength=460, justify="center",
    font=("Arial", 16)
)
resposta_label.pack(pady=(5, 20), padx=20, fill="x")

if __name__ == "__main__":
    definir_personalidade("Padrão")
    janela.bind("<Configure>", on_window_resize)
    on_window_resize()
    janela.mainloop()
    parar_tudo = True