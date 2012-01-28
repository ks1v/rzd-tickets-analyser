# -*- coding: UTF-8 -*-
# Testing

import os

import ConfigParser


#пароль сериализуй в файл настроек и дергай извне

#test_commands = []]
#test_commands.append(['-l tickets ./../tickets/tickets.pkl -n Киселев -d stats'])
#test_commands.append(['-l tickets ./../tickets/tickets.pkl -n Киселев -d stats'])

#for it in range(0,len(test_commands)) :
    #print 'Test #'+str(it)
    #os.system('python ./rzd-ticket-analyser.py '+test_commands[it])

    
    
    
def getOptions(path) :
    """
    getOptions(path)   
        reads options from config file using ConfigParser module
        returns dict of options
    """ 
    options = {}
    cp = ConfigParser.ConfigParser()
    cp.read(path)
    for section in cp.sections() :
        for option in cp.options(section) :
            options[option] = cp.get(section, option)
    return options

op = getOptions('./config')

for it in op.keys() :
    print it,'=',op[it]








