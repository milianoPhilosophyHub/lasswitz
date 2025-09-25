## Uso
Tras iniciar el servidor con `python run.py`, podemos hacer lo siguiente.

1. **Crear un manuscrito:**
```console
curl -X POST http://localhost:5000/repo \
  -H "Content-Type: application/json" \
  -d '{"repo": "mi-nuevo-manuscrito"}'
```
Nos hemos basdado en este [este script](https://github.com/manubot/rootstock/blob/main/setup.bash) para crear uno,
sin embargo, al crearse, el manuscrito tendrá un título genérico, con la lista de referencias y la de autores vacías.

2. **Importar un Manuscrito:**
```console
curl -X POST http://localhost:5000/repo/mi-nuevo-manuscrito/import \
-H "Content-Type: application/json" \
-d '{
  "commit_message": "Importa desde texto plano",
  "content": "Abstract\nEste es el resumen del estudio...\n\nIntroduction\nEsta es la introduccion...\n\nMethods\nEstos son los metodos..."
}'
```
Toma un texto largo y lo divide automáticamente en la estructura de archivos que Manubot necesita (`01.abstract.md`, `02.introduction.md`, etc.). 

3. **Eliminar un manuscrito:**
```console
curl -X DELETE http://localhost:5000/repo/mi-nuevo-manuscrito
```

4. **Editar una sola parte del manuscrito:**
```console
curl -X PUT http://localhost:5000/repo/mi-nuevo-manuscrito/content/01.introduction.md \
-H "Content-Type: application/json" \
-d '{
  "commit_message": "Corrijo un error en la introducción",
  "content": "Este es el nuevo contenido solo para la introducción."
}'
```

5. **Sincronizar todo el manuscrito (con archivos ya separados):**
```console
curl -X PUT http://localhost:5000/repo/mi-nuevo-manuscrito/content \
-H "Content-Type: application/json" \
-d '{
  "commit_message": "Primera version del manuscrito",
  "files": {
    "01.introduction.md": "Esto es el texto de la intro...",
    "02.abstract.md": "Este es el contenido del abstract...",
    "03.background.md": "Este es un capítulo sobre los antecedentes..."
  }
}'
```

6. **Actualizar Metadatos (Título, Palabras Clave, etc.):**
```console
curl -X PATCH http://localhost:5000/repo/mi-nuevo-manuscrito/metadata \
-H "Content-Type: application/json" \
-d '{
  "title": "Un Titulo Para Mi Manuscrito",
  "keywords": ["ciencia", "api", "manubot"]
}'
```
Permite modificar campos en `content/metadata.yaml`

7. **Añadir Autores:**
```console
curl -X POST http://localhost:5000/repo/mi-nuevo-manuscrito/authors \
-H "Content-Type: application/json" \
-d '[
  {
    "name": "Autor Uno",
    "github": "autor1",
    "orcid": "YYYY-YYYY-YYYY-YYYY"
  },
  {
    "name": "Autor Dos",
    "github": "autor2",
    "affiliations": ["Universidad de Ejemplo"]
  }
]'
```
Añade uno o más autores a la lista en `content/metadata.yaml` sin borrar los existentes.

9. **Añadir Referencias:**
```console
curl -X POST http://localhost:5000/repo/mi-nuevo-manuscrito/references \
-H "Content-Type: application/json" \
-d '[
  {
    "id": "mi-referencia",
    "type": "webpage",
    "title": "Un Blog Interesante",
    "URL": "https://example.com/blog-post"
  }
]'
```
Añade una o más referencias al archivo `content/manual-references.json`. Cada referencia debe tener un id.

10. **Verificar el despliegue y obtener URLs::**
```console
curl -X POST http://localhost:5000/repo/mi-nuevo-manuscrito/deploy
```

### Requisitos
Necesitas un token de GitHub con los permisos `repo`, `workflow` y `delete_repo`.  

Dentro de `.env`, coloca tus variables:
```bash
OWNER="tu-usuario-de-github"
TOKEN="ghp_tu_token"

