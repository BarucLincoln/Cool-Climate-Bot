# Use uma imagem oficial do Python como base.
# A versão 3.11-slim é leve e eficiente.
FROM python:3.11-slim

# Define o diretório de trabalho dentro do contêiner.
# Todos os comandos a seguir serão executados a partir daqui.
WORKDIR /app

# Copia o arquivo de dependências para dentro do contêiner.
COPY requirements.txt .

# Instala as dependências listadas no requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto dos arquivos do seu projeto (main.py, usuarios.json) para o contêiner.
COPY . .

# Define o comando que será executado quando o bot iniciar.
CMD ["python", "main.py"]
