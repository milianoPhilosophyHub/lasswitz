# Uso 

Primero, clona la plantilla, la cual debe estar en el mismo lugar que `app.py`.
```console
git clone https://github.com/manubot/rootstock.git rootstock_template
```

El archivo environment.yml de la plantilla contiene todas las dependencias necesarias. 
```Bash
# Crear el entorno
conda env create --file rootstock_template/build/environment.yml

# Activar el entorno
conda activate manubot
```
Una vez hecho lo anterior, puedes iniciar el servidor con `python app.py` y hacer lo siguiente.

1. **Crear un nuevo manuscrito:**
```console
curl -X POST http://localhost:6543/manuscripts -H "Content-Type: application/json" -d '{"name": "mi-primer-articulo"}'
```

2. **Mostrar todos los manuscritos:**
```console
curl http://localhost:6543/manuscripts
```

3. **Compilar el manuscrito:**
```console
curl -X POST http://localhost:6543/manuscripts/mi-primer-articulo/build -H "Content-Type: application/json" -d '{"build_pdf": true, "build_docx": true}'
```

4. **Descargar el PDF generado:**
```console
curl -o mi_articulo.pdf http://localhost:6543/manuscripts/mi-primer-articulo/output/manuscript.pdf
```