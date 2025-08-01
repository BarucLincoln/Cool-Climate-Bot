# Use uma imagem oficial do Python como base.
FROM python:3.11-slim

# Define o diretório de trabalho dentro do contêiner.
WORKDIR /app

# --- MUDANÇA CRÍTICA ---
# Copia APENAS o arquivo de dependências primeiro.
COPY requirements.txt .

# Instala as dependências. Se esta etapa falhar, saberemos imediatamente.
RUN pip install --no-cache-dir -r requirements.txt

# Agora, copia o resto dos arquivos do projeto.
COPY . .
# --------------------

# Dá permissão de execução para o nosso script de inicialização.
RUN chmod +x /app/start.sh

# Define o script de inicialização como o comando de entrada.
CMD ["/app/start.sh"]
