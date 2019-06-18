from flask import request


def get_var(request, var_name):
    if request.method == 'GET':
        return request.args.get(var_name)
    elif request.method == 'POST':
        return request.form.get(var_name)

