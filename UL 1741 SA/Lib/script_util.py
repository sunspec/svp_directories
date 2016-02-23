
def group_params(ts, group=None, params=None):
    if params is None:
        params = {}
    if group is not None:
        param_group = ts.param_defs.param_group_get(group)
    else:
        param_group = ts.param_defs
    if param_group is not None:
        for param in param_group.params:
            params[param.name] = ts.param_value(param.qname)
    return params

