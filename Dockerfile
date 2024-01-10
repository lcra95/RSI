# Utilizar la imagen base que incluye Python y TA-Lib
FROM rezaq/ta-lib-python-3.8.10-slim

# Instalar GCC y otras herramientas de compilación
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libffi-dev \
    libssl-dev

# Establecer el directorio de trabajo en el contenedor
WORKDIR /usr/src/app

# Copiar el archivo de requerimientos y instalar las dependencias de Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código fuente del proyecto al directorio de trabajo
COPY . .

# Comando para ejecutar la aplicación
CMD [ "python", "./main.py" ]
