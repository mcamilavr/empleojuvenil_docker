FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema para GDAL y Fiona
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar variables de entorno para GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copiar requirements.txt primero
COPY requirements.txt .

# Instalar dependencias con límites de memoria
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la aplicación
COPY . .

# Reducir tamaño de la imagen
RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configurar Gunicorn para uso de memoria optimizado
ENV GUNICORN_CMD_ARGS="--workers=1 --threads=2 --timeout=120 --bind=0.0.0.0:8050 --log-level=info"

# Exponer el puerto
EXPOSE 8050

# Comando para ejecutar con límite de memoria
CMD ["gunicorn", "app:server"]