# Usa la imagen oficial de Python como imagen base
FROM python:3.9-slim

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo requirements.txt al contenedor
COPY requirements.txt .

# Instala las dependencias especificadas en el archivo requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código de la aplicación al contenedor
COPY . .

# # Ejecuta la aplicación cuando se inicie el contenedor
# CMD ["uvicorn", "apiGateway:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["uvicorn", "apiGateway:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
