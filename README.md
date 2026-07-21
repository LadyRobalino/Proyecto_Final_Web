# Proyecto Final Web - Isben Solution

Este proyecto está desarrollado con **Django**. A continuación, se detallan los pasos necesarios para levantar el proyecto localmente.

## Requisitos previos
- Tener instalado **Python 3** (se recomienda versión 3.8 o superior).

## Pasos para ejecutar el proyecto

**1. Navegar a la carpeta del proyecto**
Abre una terminal y dirígete a la carpeta donde se encuentra el archivo `manage.py`.


**2. Crear y activar un entorno virtual (Recomendado)**

```bash
# Crear el entorno virtual
python -m venv venv

# Activar en Windows:
venv\Scripts\activate
```

**3. Instalar las dependencias**
Con el entorno virtual activado, instala los paquetes necesarios usando el archivo `requirements.txt`:
```bash
pip install -r requirements.txt
```

**4. Aplicar las migraciones de la base de datos**
Este comando crea la estructura necesaria en la base de datos:
```bash
python manage.py migrate
```

**5. Cargar los datos iniciales**
El proyecto incluye datos base (como usuarios o registros de prueba) en el archivo `datos_iniciales.json`. Para cargarlos, ejecuta:
```bash
python manage.py loaddata datos_iniciales.json
```

**6. Levantar el servidor**
Finalmente levanta el servidor:
```bash
python manage.py runserver
```

**7. Acceder a la aplicación**
Abre tu navegador web con la siguiente dirección:
http://127.0.0.1:8000
