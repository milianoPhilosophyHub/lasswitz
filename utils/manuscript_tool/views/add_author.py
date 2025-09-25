import os
import logging
import tempfile
import shutil
import subprocess
import yaml
from pyramid.view import view_config
from ..helpers import json_response, run_command

@view_config(route_name='add_author', request_method='POST', renderer='json')
def add_author(request):
    """
    Agrega uno o mas autores a la lista en content/metadata.yaml.
    Verifica que el archivo 00.front-matter.md exista antes de proceder.
    """
    try:
        owner, token = os.getenv('OWNER'), os.getenv('TOKEN')
        if not owner or not token:
            return json_response({'error': 'Configuracion del servidor incompleta'}, status=500)

        repo_name = request.matchdict['repo_name']
        data = request.json_body

        authors_to_add = []
        if isinstance(data, list):
            authors_to_add = data
        elif isinstance(data, dict):
            authors_to_add = [data]
        else:
            return json_response({'error': 'La entrada debe ser un objeto JSON o una lista de objetos.'}, status=400)
        
        for author in authors_to_add:
            if 'name' not in author:
                return json_response({'error': 'Cada autor en la lista debe tener una clave "name".'}, status=400)
        
        commit_message = f"Add {len(authors_to_add)} author(s) to metadata"

        temp_dir = tempfile.mkdtemp()
        try:
            repo_path = os.path.join(temp_dir, repo_name)
            secure_url = f"https://{token}@github.com/{owner}/{repo_name}.git"

            run_command(['git', 'clone', secure_url, repo_name], cwd=temp_dir)
            
            content_dir = os.path.join(repo_path, 'content')
            metadata_path = os.path.join(content_dir, 'metadata.yaml')
            front_matter_path = os.path.join(content_dir, '00.front-matter.md')

            if not os.path.exists(front_matter_path):
                logging.error(f"El archivo critico {front_matter_path} no fue encontrado.")
                return json_response({
                    'error': "El archivo de plantilla 'content/00.front-matter.md' es requerido y no fue encontrado."
                }, status=409) 

            if not os.path.exists(metadata_path):
                return json_response({'error': 'El archivo content/metadata.yaml no fue encontrado.'}, status=404)

            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = yaml.safe_load(f)

            if 'authors' not in metadata or not isinstance(metadata['authors'], list):
                metadata['authors'] = []
            
            metadata['authors'].extend(authors_to_add)

            with open(metadata_path, 'w', encoding='utf-8') as f:
                yaml.dump(metadata, f, sort_keys=False, allow_unicode=True)

            run_command(['git', 'add', metadata_path], cwd=repo_path)
            
            status_result = run_command(['git', 'status', '--porcelain'], cwd=repo_path)
            if not status_result.stdout:
                return {'status': 'no_changes', 'message': 'No se detectaron cambios en el archivo.'}

            run_command(['git', 'commit', '-m', commit_message], cwd=repo_path)
            run_command(['git', 'push', secure_url, 'main'], cwd=repo_path)

            logging.info(f"{len(authors_to_add)} autor(es) anadido(s) a {repo_name}.")
            return {
                'status': 'success',
                'message': f"{len(authors_to_add)} autor(es) anadido(s) a {repo_name}.",
                'updated_authors': metadata['authors']
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return json_response({'error': 'Verifica que el repositorio exista.'}, status=500)
    except Exception as e:
        logging.error(f"Error interno al agregar autor: {e}", exc_info=True)
        return json_response({'error': 'Error interno en el servidor.'}, status=500)