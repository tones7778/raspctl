#!/usr/bin/env python

from bottle import route, run, template, request, static_file, redirect, post, get
import config
import helpers
import storage

config.load_config()

# STATIC ROUTES
@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root=config.ROOT+"/static")  # Maybe os.path.join()?

@route('/favicon.ico')
def get_favicon():
    return static_file('favicon.ico', root=config.ROOT+"/static/img")

## HTTP HANDLERS
@route('/execute')
def execute():
    try:
        _class = request.params['class']
        action = request.params['action']
    except:
        return "Invalid request. 'class' and 'action' parameters must be present."

    return helpers.execute_command(_class, action)

@route('/commands')
def commands():
    helpers.current_tab("commands")
    rows = map(helpers.Dummy, storage.read('commands'))
    return template('commands', rows=rows)

@route('/command/edit/:id_')
def command_edit(id_=None):
    id_ = "" if id_ == "new" else int(id_)

    data = helpers.Dummy(storage.get_by_id('commands', id_))

    return template('edit', data=data)

@post('/command/save')
def command_save():
    id_ = request.POST.get('id')
    class_ = request.POST.get('class')
    action = request.POST.get('action')
    command = request.POST.get('command', '')

    if not class_ or not action:
        return "Invalid data. CLASS and ACTION are required fields."

    if id_:
        new_command = {"id_": int(id_), "class_": class_, "action": action, "command": command}
        commands = storage.replace('commands', new_command)
        print commands
        storage.save_table('commands', commands)
    else:
        data = storage.read()
        ids = map(lambda x: x['id_'], data['commands'])
        id_ = max(ids)+1 if ids else 1

        new_command = {"id_": int(id_), "class_": class_, "action": action, "command": command}
        data['commands'].append(new_command)
        storage.save(data)

    redirect("/command/edit/%s" % id_)

@route('/command/delete/:id_')
def command_delete(id_=None):
    storage.delete('commands', int(id_))
    return "ok"

@route('/config')
def config_edit(config_saved=False):
    helpers.current_tab("config")
    return template('config', config=config, config_saved=config_saved)

@post('/save_configuration')
def config_save():
    def bool_eval(name):
        return request.POST.get(name) == "True"

    conf = {
        'SHOW_DETAILED_INFO': bool_eval('SHOW_DETAILED_INFO'),
        'SHOW_TODO': bool_eval('SHOW_TODO'),
        'COMMAND_EXECUTION': bool_eval('COMMAND_EXECUTION'),
        'SERVICE_EXECUTION': bool_eval('SERVICE_EXECUTION'),
    }

    config.save_configuration(conf)
    return config_edit(config_saved=True)

@route('/webcam')
def webcam():
    helpers.current_tab("webcam")
    fswebcam_is_installed = helpers.check_program_is_installed("fswebcam")
    return template('webcam', fswebcam_is_installed=fswebcam_is_installed)

@get('/take_picture')
def take_picture():
    if not helpers.check_program_is_installed("fswebcam"):
        return "Is seems you don't have fswebcam installed in your system. Install it using apt-get or aptitude and add your user to VIDEO group."

    command = "fswebcam -r 640x480 -S 3 %s/static/img/webcam_last.jpg" % config.ROOT
    subprocess.call(command, shell=True)
    return "done"

@get('/services')
def services():
    filter_favorites = request.params.get('filter_favorites') == "true"
    helpers.current_tab("services")
    if config.SERVICE_EXECUTION:
        services = helpers._execute("ls /etc/init.d/")
        services = filter(bool, services.split('\n'))
        favorite_services = config.SERVICES_FAVORITES
        if filter_favorites:
            services = favorite_services
    else:
        services, favorite_services = [], []
    return template('services', services=services, favorite_services=favorite_services,
                                filter_favorites=filter_favorites)

def _service_favorite(name):
    # Just mark a service (daemon) as favorite
    if name in config.SERVICES_FAVORITES:
        config.SERVICES_FAVORITES.remove(name)
    else:
        config.SERVICES_FAVORITES.append(name)
    new_config = {"SERVICES_FAVORITES": config.SERVICES_FAVORITES}

    config.save_configuration(new_config)
    return "Toggled favorite"

@get('/service/:name/:action')
def service_action(name=None, action=None):

    if action == "favorite":
        return _service_favorite(name)

    if action not in config.SERVICE_VALID_ACTIONS:
        return "Error! Invalid action!"

    if name not in helpers._execute("ls /etc/init.d/"):
        return "Error! Service not found!"

    result = helpers._execute("sudo %s/scripts/exec.sh service %s %s" % (config.ROOT, name, action))
    return result if result else "No information returned"

@get('/about')
def about():
    helpers.current_tab("about")
    return template('about')

@get('/system_info')
def system_info():
    system_info = helpers.execute_system_information_script()
    return template("system_info", info=system_info)

@get('/')
def index():
    helpers.current_tab("index")
    return template("index")

if __name__ == '__main__':
    import sys
    reloader = '--debug' in sys.argv
    run(host='0.0.0.0', port=8086, reloader=reloader)
