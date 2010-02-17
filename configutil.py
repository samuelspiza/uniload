def getIndexedOptions(config, section, values):
    arr = []
    i = 0
    temp = getOptionsById(config, section, values, i)
    while 0 < len(temp):
        arr.append(temp)
        i = i + 1
        temp = getOptionsById(config, section, values, i)
    return arr

def getOptionsById(config, section, values, i):
    values = [v.format(i) for v in ["{0:02}" + v for v in values]]
    return dict([(v[2:], config.get(section, v))
                 for v in values if config.has_option(section, v)])

