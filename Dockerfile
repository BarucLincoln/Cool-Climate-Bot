# Use uma imagem oficial do Python como base.
FROM python:3.11-slim

# Define o diretório de trabalho dentro do contêiner.
WORKDIR /app

# --- MUDANÇA CRÍTICA ---
# Instala cada dependência diretamente, sem usar requirements.txt.
# Isso é mais explícito e à prova de falhas de build.
RUN pip install --no-cache-dir "python-telegram-bot[job-queue]==21.1.1" python-dotenv==1.0.1 httpx==0.27.0

# Agora, copia o resto dos arquivos do projeto.
COPY . .
# --------------------

# Dá permissão de execução para o nosso script de inicialização.
RUN chmod +x /app/start.sh

# Define o script de inicialização como o comando de entrada.
CMD ["/app/start.sh"]
