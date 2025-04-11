# Dockerfile (Completo y Corregido)

# 1. Usar una imagen base de Python oficial
FROM python:3.9-slim

# 2. Instalar dependencias del sistema operativo necesarias
# Incluye gdal, fiona y dependencias potenciales de geopandas/rtree
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    # build-essential # Descomentar si pip necesita compilar algo
    # python3-rtree # Descomentar si hay problemas con rtree vía pip
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 4. Configurar variables de entorno para GDAL (Ayuda a pip a encontrar GDAL)
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# 5. Copiar requirements.txt primero para aprovechar la caché de Docker
COPY requirements.txt .

# 6. Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copiar el resto de los archivos de la aplicación al directorio de trabajo
COPY . .

# 8. Exponer el puerto es informativo, Gunicorn usará $PORT que Render define
# EXPOSE 10000

# 9. Comando para ejecutar la aplicación (¡Forma SHELL para expansión de $PORT!)
#    - Usa $PORT para el binding.
#    - --workers 1 es adecuado para el plan gratuito de Render.
#    - --timeout 120 da más tiempo a las requests.
#    - app:server apunta al objeto 'server' en tu archivo 'app.py'.
CMD gunicorn --bind "0.0.0.0:$PORT" --workers 1 --timeout 120 app:server