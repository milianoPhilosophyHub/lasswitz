import os, re, tempfile, shutil, logging, requests, subprocess, yaml
from pyramid.view import view_config
from ..helpers import json_response, run_command

@view_config(route_name='repo_collection', request_method='POST', renderer='json')
def create_manuscript(request):
    """
    Maneja la CREACION de un nuevo repositorio y limpia los metadatos y referencias iniciales.
    """
    try:
        owner, token = os.getenv('OWNER'), os.getenv('TOKEN')
        if not owner or not token: return json_response({'error': 'Configuracion del servidor incompleta'}, status=500)
        
        repo = request.json_body.get('repo')
        if not repo: return json_response({'error': 'Falta el parametro "repo"'}, status=400)
        if not re.match(r'^[a-zA-Z0-9_.-]+$', repo): return json_response({'error': 'Formato de "repo" invalido'}, status=400)

        headers = {"Authorization": f"token {token}"}
        repo_data = {"name": repo, "description": "Manuscrito generado con Manubot"}
        response = requests.post("https://api.github.com/user/repos", headers=headers, json=repo_data)
        if response.status_code != 201:
            return json_response({'error': 'Error al crear el repositorio. Puede que ya exista.'}, status=response.status_code)

        temp_dir = tempfile.mkdtemp()
        try:
            repo_path = os.path.join(temp_dir, repo)
            secure_push_url = f"https://{token}@github.com/{owner}/{repo}.git"

            logging.info(f"Clonando historial completo de rootstock en {repo_path}...")
            run_command(['git', 'clone', 'https://github.com/manubot/rootstock.git', repo], cwd=temp_dir)

            logging.info(f"Subiendo contenido inicial a https://github.com/{owner}/{repo}.git")
            run_command(['git', 'push', secure_push_url, '--all'], cwd=repo_path)

            logging.info("Personalizando el repositorio y limpiando metadatos...")
            run_command(['git', 'rm', '.appveyor.yml'], cwd=repo_path)
            run_command(['git', 'rm', 'ci/install.sh'], cwd=repo_path)
            
            # Modifica README
            readme_path = os.path.join(repo_path, "README.md")
            if os.path.exists(readme_path):
                with open(readme_path, 'r', encoding='utf-8') as f: content = f.read()
                content = content.replace('manubot/rootstock', f'{owner}/{repo}')
                content = content.replace('manubot.github.io/rootstock', f'{owner}.github.io/{repo}')
                with open(readme_path, 'w', encoding='utf-8') as f: f.write(content)
            
            # Modifica metadata.yaml para vaciar autores y pone un titulo
            metadata_path = os.path.join(repo_path, 'content', 'metadata.yaml')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = yaml.safe_load(f)
                
                metadata['title'] = f"Titulo para el manuscrito: {repo}"
                metadata['authors'] = [] # Vaciamos la lista de autores
                
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    yaml.dump(metadata, f, sort_keys=False, allow_unicode=True)

            # Limpia el archivo de referencias manuales
            references_path = os.path.join(repo_path, 'content', 'manual-references.json')
            if os.path.exists(references_path):
                with open(references_path, 'w', encoding='utf-8') as f:
                    f.write('[]\n')
            
            logging.info("Guardando personalizacion...")
            run_command(['git', 'add', '--all'], cwd=repo_path)
            run_command(['git', 'commit', '-m', f"Brand repo and clean metadata for {owner}/{repo}"], cwd=repo_path)
            run_command(['git', 'push', secure_push_url, 'main'], cwd=repo_path)
            
            return {'status': 'success', 'message': f'Repositorio {owner}/{repo} creado y limpiado exitosamente.'}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return json_response({'error': 'Error en un paso de la configuracion de Git.'}, status=500)
    except Exception as e:
        logging.error(f"Error interno en CREATE: {e}", exc_info=True)
        return json_response({'error': 'Error interno.'}, status=500)