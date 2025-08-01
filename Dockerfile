# Use uma imagem oficial do Python como base.
FROM python:3.11-slim

# Define o diretório de trabalho dentro do contêiner.
WORKDIR /app

# Copia o arquivo de dependências para dentro do contêiner.
COPY requirements.txt .

# Instala as dependências listadas no requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto dos arquivos do seu projeto.
COPY . .

# --- NOVAS LINHAS ---
# Dá permissão de execução para o nosso script de inicialização.
RUN chmod +x /app/start.sh

# Define o script de inicialização como o comando de entrada.
CMD ["/app/start.sh"]
