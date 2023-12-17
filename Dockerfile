# Usa una imagen oficial de Python como imagen base
FROM python:3.9

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Copia los archivos requeridos en el contenedor
COPY requirements.txt ./
COPY main.py ./

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Comando para ejecutar el script
CMD ["python", "./main.py"]
