import os
import logging
import tempfile
import shutil
import subprocess
import glob
from pyramid.view import view_config
from ..helpers import json_response, run_command

SECTION_KEYWORDS = {
    'abstract': ['Abstract', 'Resumen'],
    'introduction': ['Introduction', 'Introduccion'],
    'background': ['Background', 'Antecedentes'],
    'methods': ['Methods', 'Materials and Methods', 'Metodologia', 'Materiales y Metodos'],
    'results': ['Results', 'Resultados'],
    'discussion': ['Discussion', 'Discusion'],
    'conclusion': ['Conclusion', 'Conclusiones'],
    'acknowledgments': ['Acknowledgments', 'Agradecimientos'],
    'references': ['References', 'Referencias', 'Bibliografia']
}
SECTION_ORDER = [
    'abstract', 'introduction', 'background', 'methods', 'results',
    'discussion', 'conclusion', 'acknowledgments', 'references'
]

def _parse_text_to_sections(manuscrit_text: str) -> dict:
    title_to_key_map = {}
    for key, titles in SECTION_KEYWORDS.items():
        for title in titles:
            title_to_key_map[title.lower()] = key

    parsed_sections = {}
    current_section_key = None
    current_content = []
    
    for line in manuscrit_text.splitlines():
        cleaned_line = line.strip()
        if cleaned_line.lower() in title_to_key_map:
            if current_section_key:
                parsed_sections[current_section_key] = '\n'.join(current_content).strip()
            
            current_section_key = title_to_key_map[cleaned_line.lower()]
            current_content = [f"## {cleaned_line}\n"]
            
        elif current_section_key:
            current_content.append(line)

    if current_section_key and current_content:
        parsed_sections[current_section_key] = '\n'.join(current_content).strip()
        
    return parsed_sections

@view_config(route_name='repo_import', request_method='POST', renderer='json')
def import_manuscript(request):
    """
    Recibe un manuscrito completo, lo procesa y lo sube a un
    repositorio de Manubot, reemplazando los archivos .md existentes
    y protegiendo archivos de plantilla como 00.front-matter.md.
    """
    try:
        owner, token = os.getenv('OWNER'), os.getenv('TOKEN')
        if not owner or not token:
            return json_response({'error': 'Configuracion del servidor incompleta'}, status=500)

        repo_name = request.matchdict['repo_name']
        data = request.json_body
        manuscript_content = data.get('content')
        commit_message = data.get('commit_message', 'Import full manuscript via API')

        if not manuscript_content:
            return json_response({'error': 'El cuerpo debe contener el "content" del manuscrito.'}, status=400)
        
        parsed_sections = _parse_text_to_sections(manuscript_content)
        if not parsed_sections:
            return json_response({'error': 'No se encontraron secciones validas en el texto.'}, status=400)

        temp_dir = tempfile.mkdtemp()
        try:
            repo_path = os.path.join(temp_dir, repo_name)
            secure_url = f"https://{token}@github.com/{owner}/{repo_name}.git"

            run_command(['git', 'clone', secure_url, repo_name], cwd=temp_dir)
            content_dir = os.path.join(repo_path, 'content')
            os.makedirs(content_dir, exist_ok=True)

            logging.info("Limpiando archivos .md existentes, excepto plantillas...")
            for md_file in glob.glob(os.path.join(content_dir, '*.md')):
                # Condicion para saltar y proteger el archivo de plantilla
                if os.path.basename(md_file) == '00.front-matter.md':
                    logging.info(f"Protegiendo el archivo de plantilla: {md_file}")
                    continue
                os.remove(md_file)

            files_created = []
            for index, section_key in enumerate(SECTION_ORDER):
                if section_key in parsed_sections:
                    content = parsed_sections[section_key]
                    if not content:
                        continue
                    
                    file_number = str(index + 1).zfill(2)
                    filename = f"{file_number}.{section_key}.md"
                    filepath = os.path.join(content_dir, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    files_created.append(filename)
            
            run_command(['git', 'add', 'content/'], cwd=repo_path)
            
            status_result = run_command(['git', 'status', '--porcelain'], cwd=repo_path)
            if not status_result.stdout:
                return {'status': 'no_changes', 'message': 'El contenido es identico al existente.'}

            run_command(['git', 'commit', '-m', commit_message], cwd=repo_path)
            run_command(['git', 'push', secure_url, 'main'], cwd=repo_path)

            logging.info(f"Manuscrito importado a {repo_name}.")
            return {
                'status': 'success',
                'message': f'Manuscrito importado a {repo_name}.',
                'files_created': files_created
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return json_response({'error': 'Verifica que el repositorio exista.'}, status=500)
    except Exception as e:
        logging.error(f"Error interno en IMPORT: {e}", exc_info=True)
        return json_response({'error': 'Error interno en el servidor.'}, status=500)