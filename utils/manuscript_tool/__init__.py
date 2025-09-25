from pyramid.config import Configurator

def main(global_config, **settings):
    """
    Devuelve la aplicacion de Pyramid.
    """
    with Configurator(settings=settings) as config:
        # Definimos las rutas: 
        # Para crear repositorios (POST /repo)
        config.add_route('repo_collection', '/repo')
        
        # Para eliminar un repositorio específico (DELETE /repo/{repo_name})
        config.add_route('repo_resource', '/repo/{repo_name}')
        
        # Para sincronizar todo el contenido 
        config.add_route('repo_content', '/repo/{repo_name}/content')
        
        # Para editar un solo archivo
        config.add_route('repo_content_file', '/repo/{repo_name}/content/{filename}')
        
        # Para importar un manuscrito completo
        config.add_route('repo_import', '/repo/{repo_name}/import')

        # Para agregar uno o mas autores
        config.add_route('add_author', '/repo/{repo_name}/authors')

        # Para actualizar los metadatos 
        config.add_route('update_metadata', '/repo/{repo_name}/metadata')

        # Para agregar una o mas referencias
        config.add_route('add_references', '/repo/{repo_name}/references')
        
        config.add_route('repo_deployment', '/repo/{repo_name}/deploy')

        config.scan('.views')
        
    return config.make_wsgi_app()
