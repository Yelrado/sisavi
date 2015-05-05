# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## This is a sample controller
## - index is the default action of any application
## - user is required for authentication and authorization
## - download is for downloading files uploaded in the db (does streaming)
## - call exposes all registered services (none by default)
#########################################################################


def index():
    """
    Pagina principal que muestra los avisos
    
    Recibe como parametros para ordenar:
    orderby=cron: Ordena los avisos por publicación de recientes a los antiguos
                  Por default.
    orderby=next: Ordena los avisos por caducidad, los que están próximos a caducar
                  se muestran primero.
                  
    Filtra los avisos:
    filter=notices: Sólo muestra avisos.
    filter=events: Sólo muestra eventos (los que tienen fecha de inicio de evento).
    Por defecto muestra todos.
    """
    avisos = db((db.notice.approved == True) & (db.notice.finish_on > request.now)).select(orderby=~db.notice.created_on)
    #Ordenar por cronología o por caducidad
    if request.vars['orderby'] == 'cron':
        avisos = avisos.sort(lambda r: r.created_on)
    elif request.vars['orderby'] == 'next':
        avisos = avisos.sort(lambda r: r.finish_on)
    #Filtrar por Avisos o por Eventos
    if request.vars['filter'] == 'notices':
        avisos = avisos.exclude(lambda r: r.event_start_date == None)
    elif request.vars['filter'] == 'events':
        avisos = avisos.find(lambda r: r.event_start_date != None)
    
    if request.vars['new'] == 'y':
        response.flash = 'Su aviso fue agregado con éxito'
    elif request.vars['new'] == 'requires':
        response.flash = 'Su aviso está esperando aprobación'
    return dict(avisos=avisos)

@auth.requires_login()
def nuevo():
    """"
    Muestra el formulario para publicar un nuevo aviso
    
    Requiere inicio de sesión.
    Le da permisos de modificar al usuario que creo el aviso.
    """
    requires_approval = db.auth_user[auth.user_id].requires_approval
    
    db.notice.approved.default = not requires_approval
    form = SQLFORM(db.notice, fields=['title','event_start_date','finish_on','description','image','link','priority'],
                   labels={'title':'Titulo',
                           'event_start_date':'Inicia el',
                           'finish_on':'Termina el',
                           'description':'Descripción',
                           'image':'Imagen',
                           'link':'Enlace externo',
                           'priority':'Prioridad'},
                   col3={'event_start_date':'Usado para eventos en vivo. Opcional.',
			 'description':'Puedes darle formato al texto como si usarás Wikipedia',
			 'image':'Opcional',
                         'link':'Opcional',
                         'priority':'Da un formato distinto a su Aviso o Evento'})
    if form.process().accepted:
        #Dar permisos sobre el registro
        auth.add_permission(0, 'Modificar', 'Aviso', form.vars.id)
        if requires_approval == True:
            redirect(URL('index',vars={'new':'requires'}))
        else:
            redirect(URL('index',vars={'new':'y'}))
        response.flash = 'Aviso agregado'
    elif form.errors:
        response.flash = 'Corrija los errores'
    else:
        response.flash = 'Llene todos los campos'

    return dict(form=form)


@auth.requires(lambda: __is_admin())
def admin_notices():
    """
    Administra los avisos, permite que se aprueben
    los avisos que necesitan revisión.
    
    Filtra los avisos por necesidad:
    filter=need_approval: Muestra sólo los avisos que requieren aprobación
    filter=next: Muestra sólo los avisos que están vigentes en fecha próxima
    Por defecto muestra todos los avisos.
    """
    if request.vars['filter'] == 'need_approval':
        grid = SQLFORM.grid((db.notice.approved == False) & (db.notice.finish_on > request.now),csv=False)
    elif request.vars['filter'] == 'next':
        grid = SQLFORM.grid((db.notice.finish_on > request.now),csv=False)
    else:
        grid = SQLFORM.grid(db.notice,csv=False)
    return dict(grid=grid)

@auth.requires(lambda: __is_admin())
def admin_users():
    """
    Administra a los usuarios.
    
    Permite aprobar las solicitudes de registro y definir si
    un usuario necesita que se le revisen sus avisos.
    """
    db.auth_user.registration_key.readable=True
    db.auth_user.registration_key.writable=True
    db.auth_user.requires_approval.readable=True
    db.auth_user.requires_approval.writable=True
    db.auth_user.is_admin.readable=True
    db.auth_user.is_admin.writable=True
    grid = SQLFORM.grid(db.auth_user,csv=False)
    return dict(grid=grid)

def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/manage_users (requires membership in
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    """
    return dict(form=auth())

@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


@auth.requires_signature()
def data():
    """
    http://..../[app]/default/data/tables
    http://..../[app]/default/data/create/[table]
    http://..../[app]/default/data/read/[table]/[id]
    http://..../[app]/default/data/update/[table]/[id]
    http://..../[app]/default/data/delete/[table]/[id]
    http://..../[app]/default/data/select/[table]
    http://..../[app]/default/data/search/[table]
    but URLs must be signed, i.e. linked with
      A('table',_href=URL('data/tables',user_signature=True))
    or with the signed load operator
      LOAD('default','data.load',args='tables',ajax=True,user_signature=True)
    """
    return dict(form=crud())
