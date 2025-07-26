# Yuma
IA com interface moderna em Python (CustomTkinter), respostas por voz, personalidade customizável e memória a longo prazo.

## 🔧 Funcionalidades

### 🎨 Interface Gráfica (CustomTkinter)
- Interface moderna e responsiva.
- Botão único (Start/Stop) para controle da IA.
- Animação circular pulsante durante escuta.
- Campo de resposta para exibir texto retornado.
- Redimensionamento de janela com ajuste dinâmico de todos os elementos.

### ⚙️ Menus de Configuração
- **Microfone**: Dropdown com filtro avançado (somente dispositivos válidos com entrada).
- **Voz da IA**: Escolha entre vozes pt-BR "Animada" (Francisca) e "Neutra" (Thalita).
- **Volume**: Slider de 0 a 100%, com controle direto via `pygame`.

### 🎤 Captura e Processamento de Áudio
- Reconhecimento de voz com `speech_recognition`.
- Filtro por nome (mic, input, capture) e canais de entrada reais.
- Ajuste automático de ruído ambiente (`adjust_for_ambient_noise`).
- Detecção de sobreposição de fala (interrupção).

### 🧠 Comportamento da IA
- Respostas geradas com Gemini (Google).
- Interações sarcásticas quando o input não faz sentido.
- Frases proativas em períodos de silêncio, com controle de frequência.
- IA sempre responde, mesmo com entradas desconexas.

### 👤 Personas Customizáveis
- Modos disponíveis: `Padrão`, `Desenvolvedor`, `Sarcástica`, `Alma`.
- A persona `Alma` é carregada por arquivo `.json` externo.
- Personalidade dinâmica, configurável sem alterar o código.

### 💾 Memória e Persistência
- Memória de conversa entre interações.
- Reset automático ao parar a IA.
- A `Alma` salva resumos da conversa no `.json`, criando memória evolutiva.

### 🧵 Execução Paralela (Threads)
- Threads separadas para: escuta, resposta e TTS.
- Fila (`Queue`) para comunicação entre threads.
- Prevenção de travamentos, deadlocks e eco de comandos.

### 🛠️ Tratamento de Erros
- Feedback visual na interface para erros críticos.
- Logs detalhados no terminal (microfone usado, texto reconhecido, falhas).
- Limpeza automática de arquivos temporários (`resposta_*.mp3`).

---

## 🆕 Atualizações Recentes

### 📌 Persona "Alma"
- Comportamento carregado dinamicamente via `.json`.
- Memória persistente com resumo da conversa salvo entre sessões.
- Botão “Carregar Memória” aparece apenas quando Alma é selecionada.

### 💡 Melhorias de UX/UI
- Elementos reestilizados e mais intuitivos.
- Botões desativados automaticamente em estados inválidos.
- Console limpo e sem mensagens desnecessárias.

### 🧱 Correções de Bugs Críticos
- Duplicação de respostas e voz eliminada.
- Crash em sobreposição de fala proativa resolvido.
- Verificação inicial de microfone evita erros de execução.

---

## 📦 Requisitos

- Python 3.10+
- `customtkinter`
- `pyaudio`
- `pygame`
- `speechrecognition`
- `edge-tts`
- Gemini API key (Google)

---
