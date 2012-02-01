# -*- coding: UTF-8 -*-
# Testing

import os

#os.system('rm -rf ./../tickets')  

test_commands = []
test_commands.append('-l pages -s table') 
#test_commands.append('-l pages') # Display table and stats
#test_commands.append('-l tickets -d table') 




for it in range(0, len(test_commands)) :
    print '\n\nTest #' + str(it) + '\n'
    os.system('python ./rzd-ticket-analyser.py ' + test_commands[it])
    print '\n\n'


    
  
    









