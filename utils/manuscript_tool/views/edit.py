import os
import logging
import tempfile
import shutil
import subprocess
from pyramid.view import view_config
from ..helpers import json_response, run_command

@view_config(route_name='repo_content_file', request_method='PUT', renderer='json')
def edit_manuscript(request):
    """
    Modifica el contenido de un solo archivo .md especificado en la URL.
    No afecta a los demas archivos de la carpeta.
    """
    try:
        owner, token = os.getenv('OWNER'), os.getenv('TOKEN')
        if not owner or not token:
            return json_response({'error': 'Configuracion del servidor incompleta'}, status=500)

        repo_name = request.matchdict['repo_name']
        filename = request.matchdict['filename']
        
        data = request.json_body
        new_content = data.get('content')
        commit_message = data.get('commit_message', f'Update {filename} via API')

        if new_content is None:
            return json_response({'error': 'El cuerpo debe contener el "content" del archivo.'}, status=400)
        
        if '..' in filename or not filename.endswith('.md'):
            return json_response({'error': 'Nombre de archivo invalido.'}, status=400)

        temp_dir = tempfile.mkdtemp()
        try:
            repo_path = os.path.join(temp_dir, repo_name)
            secure_url = f"https://{token}@github.com/{owner}/{repo_name}.git"

            run_command(['git', 'clone', secure_url, repo_name], cwd=temp_dir)

            file_path = os.path.join(repo_path, 'content', filename)
            
            if not os.path.exists(file_path):
                return json_response({'error': f'El archivo "{filename}" no fue encontrado.'}, status=404)

            # Guarda el contenido en el archivo específico
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Comprueba si realmente hubo un cambio
            status_result = subprocess.run(['git', 'status', '--porcelain', file_path], cwd=repo_path, capture_output=True, text=True)
            if not status_result.stdout:
                return {'status': 'no_changes', 'message': 'El contenido es identico al existente.'}

            # Agrega solo el archivo modificado
            run_command(['git', 'add', file_path], cwd=repo_path)
            run_command(['git', 'commit', '-m', commit_message], cwd=repo_path)
            run_command(['git', 'push', secure_url, 'main'], cwd=repo_path)
            
            logging.info(f"Archivo actualizado.")
            return {'status': 'success', 'message': f'Archivo {filename} actualizado en {repo_name}.'}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return json_response({'error': 'Verifica que el repositorio y el archivo existan.'}, status=500)
    except Exception as e:
        logging.error(f"Error interno en EDIT: {e}", exc_info=True)
        return json_response({'error': 'Error interno.'}, status=500)