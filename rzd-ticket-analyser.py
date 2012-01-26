# -*- coding: UTF-8 -*-

__author__  = 'Andrew ks1v Kiselev'
__email__   = "mail@andrewkiselev.com"
__year__    = "2012"
__title__   = "Simple RZD tickets analyser"
__version__ = 1.0
__new__     = '+ License;\n\
               + All functions commented;\n\
               + Script renamed;\n\
               + Code clean-up.'


import httplib2                 # Downloading
from urllib import urlencode    # Downloading
import datetime                 # Parsing, Statistic
import re                       # Parsing
import string                   # Parsing
import hashlib                  # Serialization
import pickle                   # Serialization
import os                       # DeSerialization
import numpy                    # Statistic
from scipy import *             # Statistic
import sys                      # Commands parsing



# == Release ==
# TODO [done] Command interface
# TODO [done] Testing - Command interface
# TODO [done] Licence verification
# TODO [done] Help verification
# TODO [done] Code clean-up
# TODO [done]- Comment all the functions
# TODO [done]- +|-|:
# TODO [done] - Help and Lic in external file

# == Next ==
# TODO Config file for all constats 
# TODO Pickel replacement
# TODO Import optimization
# TODO Exceptions
# TODO Testing - Accounts

# SITE

def rzdAuth(login, password) :
    """
    rzdAuth(login, password)
        returns [http, headers]
            http - http object
            headers - headers with cookies
    """
    host = "http://ticket.rzd.ru"
    auth_page  = host + "/isvp/public/j_security_check"
    error_page = host + "/pass/public/logonErr"
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    auth_form = { "j_username" : login,
                  "j_password" : password,
                  "action.x"   : "53",
                  "action.y"   : "10",
                  "action"     : "Вход"}

    # HTTP object creation
    http = httplib2.Http(disable_ssl_certificate_validation = True)

    # Authentication
    print "Login as " + login + '.'
    response, content = http.request(auth_page, "POST", headers = headers, body = urlencode(auth_form))

    if response['location'] == error_page :
        print "\tAuthentication Failed."
        sys.exit()
    else :
        print "\tAuthentication OK."
        headers['Cookie'] = response['set-cookie']


    return http, headers

def nextCabinetPageURLPosition(cabinet_page) :
    """
    nextCabinetPageURLPosition(cabinet_page)
        returns numerical position of the next cabinet page or -1 o/w
    """
    current_page_mark = 'curPage'
    next_page_url_mark = '/pass/secure/ticket/cabinet?STRUCTURE_ID=14&page'

    mark_position = string.find(cabinet_page, current_page_mark)
    next_page_position = string.find(cabinet_page, next_page_url_mark, mark_position)
    return next_page_position

def nextCabinetPageURLExtraction(cabinet_page, next_page_url_position) :
    """
    nextCabinetPageURLExtraction(cabinet_page, next_page_url_position)
        returns URL of the next cabinet page
    """
    HOST = "http://ticket.rzd.ru"

    start_pos = next_page_url_position
    end_pos = start_pos + string.find(cabinet_page[start_pos : start_pos + 200], '">')
    next_page_url = cabinet_page[start_pos : end_pos]

    # httplib2 understands only absolute URLs
    if not next_page_url.startswith('http') :
        next_page_url = HOST + next_page_url


    return next_page_url

def getTicketURLs(http, headers) :
    """
    getTicketURLs(http, headers)
        returns list of URLs of tickets from pre-authorized account ('http', 'headers')
    """

    ticket_urls = []
    cabinet_url = "https://ticket.rzd.ru/pass/secure/ticket/cabinet?STRUCTURE_ID=14"
    ticket_url_mark = "/pass/secure/ticket/cabinet?STRUCTURE_ID=14&layer_id=5020"

    while True :

        print "\nCabinet page is found at ", cabinet_url

        # Fetch new cabinet page
        response, cabinet_page = http.request(cabinet_url, "GET", headers = headers)
        print "\tRequest... " + response['status'] + '.'

        # Tickets existence check
        urls_tickets_positions = findAll(cabinet_page, ticket_url_mark)

        if len(urls_tickets_positions) == 0 :
            print "\tThere are no tickets here :("
            break
        else :
            print "\tFound "+str(len(urls_tickets_positions))+" tickets."

            # Extraction tickets' URLs
            ticket_urls.extend(ticketURLsExtraction(cabinet_page, urls_tickets_positions))

            # Next cabinet page url searching

            next_page_url_position = nextCabinetPageURLPosition(cabinet_page)

            if next_page_url_position == -1 :
                print "\nThere's no more cabinet pages ;)"
                break
            else :
                # Next cabinet page url extraction
                cabinet_url = nextCabinetPageURLExtraction(cabinet_page, next_page_url_position)

    print "\nFound " + str(len(ticket_urls)) + " ticket URLs."
    return ticket_urls

def ticketURLsExtraction(page, ticket_urls_positions) :
    """
    ticketURLsExtraction(page, ticket_urls_positions)
        extracts tickets' URLs from the 'page' using its positions 'ticket_urls_positions'
        returns list of ticket URLs
    """
    ticket_urls = []
    for start_pos in ticket_urls_positions :
        end_pos = start_pos + string.find(page[start_pos : start_pos + 300], "target") - 2
        ticket_url = page[start_pos : end_pos]
        ticket_urls.append(ticket_url)

    return ticket_urls

def getTicketPagesByURL(http, headers, ticket_urls) :
    """
    getTicketPages(http, headers, ticket_urls)
        returns list of pages with ticket data inside
        using list of ticket URLs ('ticket_urls') from pre-authorized account ('http', 'headers')
    """
    HOST = "http://ticket.rzd.ru"

    print "\nTickets fetching started.\n"

    ticket_pages = []

    for url in ticket_urls :

        # httplib2 understands only absolute URLs
        if not url.startswith('http') :
            url = HOST + url

        # Fetching ticket page
        response, ticket_page = http.request(url, "GET", headers = headers)

        print "\tFetched ticket at " + url + " with status " + response['status'] + "."

        # if page really fetched => store it
        if response['status'] == '200' :
            ticket_pages.append(ticket_page)
            
    print "\nFetched " + str(len(ticket_pages)) + " tickets from " + str(len(ticket_urls)) + " URLs"
    return ticket_pages

def getTicketsPagesFromSite(login, password) :
    """
    getTicketsFromSite(login, password)
        returns list of pages with tickets from given account ('login', 'password')
    """

    # Account authentication
    http, headers = rzdAuth(login, password)

    # Get URLs of all tickets in account
    ticket_urls = getTicketURLs(http, headers)

    # Get tickets' pages ('raw_tickets')
    ticket_pages = getTicketPagesByURL(http, headers, ticket_urls)
    return ticket_pages

# TOOLS

def findAll(S, substring) :
    """
    Returns positions of 'substring' in 'S' as list of ints

    NB! finditer() won't find overlapping strings.
    The regular expression methods, including finditer(), find non-overlapping matches.
    To find overlapping matches you need a loop.
    """
    return [match.start() for match in re.finditer(re.escape(substring), S)]

def getList(tickets, field) :
    """
    getList(tickets, field)
        forms list of 'field' elements from list of dicts 'tickets'
        (extracts a vector from vector of dicts).
    """
    out = []
    for ticket in tickets :
        out.append(ticket[field])
    return out

def getHist(data) :
    """
    getHist(data)
        returns a histogramm of 'data' in the form of two-column table,
        sorted in descending order (1st column - quantity of each element, 
        2nd - element name). This is not a binned histogramm, 
        function only counts a quantity of each unique element.
        So, this function isn't very useful for numeric vector 
        and designed for vectors of strings.
    """
    values = []
    hist = []
    for value in data :
        if not value in values :
            values.append(value)
            hist.append(1)
        else :
            hist[values.index(value)] += 1
    out = zip(hist, values)
    out.sort(reverse = True)
    return out

# SERIALIZATION

def saveTicketPages(ticket_pages, path = './ticket_pages') :
    """
    saveTicketPages(ticket_pages)
        write pages with ticket data inside on disk
        files format - html
        files name - md5 hash of file body
    """

    if not os.path.isdir(path) :
        os.makedirs(path)

    if not path[len(path) - 1] == '/' :
        path += '/'

    for item in ticket_pages :
        fd = open(path + str(hashlib.md5(item).hexdigest()) + '.html', 'w')
        fd.write(item)
        fd.close()

    print '\nTicket pages are saved in ' + path

def loadTicketPages(path = './ticket_pages') :
    """
    getTicketPages(path)
        load html ticket pages from 'path' directory
        returns list of strings
    """
    ticket_pages = []
    print 'Loading ticket pages from ' + path

    for file in os.listdir(path) :
        fd = open(path + '/' + file, 'r')
        ticket_pages.append(fd.read())
        fd.close()
        print '\t' + path + '/' + file

    print '\t---------------------\n\t' + str(len(ticket_pages)) + ' / ' + str(len(os.listdir(path))) + " files loaded."
    return ticket_pages

def saveTickets(tickets, path = './tickets.pkl') :
    """
    saveTickets(tickets, path = './tickets.pkl')
        serialize tickets to the 'path' file
        nothing to return
    """
    fd = open(path, 'w')
    pickle.dump(tickets, fd)
    fd.close()
    print "\nTickets are saved as a file in" + path

def loadTickets(path = './tickets.pkl') :
    """
    loadTickets(path = './tickets.pkl')
        deserialize (read) tickets from the 'path' file
        returns tickets as a list of dicts
    """
    fd = open(path, 'r')
    tickets = pickle.load(fd)
    fd.close()
    print '\nTickets loaded from ' + path
    return tickets

def saveCSVTable(tickets, path = './tickets_table.csv') :
    """
    saveCSVTable(table, path)
        write CSV formatted 'table' on disk as 'path' file
    """

    # Write table into CSV file
    fd = open(path, 'w')
    fd.write(formTable(tickets))
    fd.close()
    print "\nTickets are saved as a table in" + path

# PARSING

def treatTextFields(tickets) :
    """
    treatTextFields(tickets) 
        treat text fields in tickets:
            - converts all string to utf8
            - makes it start with a capital letter
            - replace ugly RZD spelling of cities and stations 
                with its real ones
        returns treated tickets
    """

    # Capitalization
    fields_to_convert = ['departureCity', 'arrivalCity', 'carType', 'passenger']

    for ticket in tickets :
        for field in fields_to_convert :
            s = unicode(ticket[field], 'utf-8')
            ticket[field] = s.capitalize()

    # Cities and Stations
    #                       Original        City                    Station
    substitutions_dict = {u'Горький м'   : [u'Нижний Новогород', u'Московский вокзал)'],
                          u'Н.новгород м': [u'Нижний Новогород', u'Московский вокзал'],
                          u'Москва яр'   : [u'Москва',           u'Ярославский вокзал'],
                          u'Москва кур'  : [u'Москва',           u'Курский вокзал'],
                          u'Москва каз'  : [u'Москва',           u'Казанский вокзал']}

    substitutions_fields = [['departureCity', 'departureStation'],['arrivalCity', 'arrivalStation']]

    for ticket in tickets :
        for field in substitutions_fields :
            ticket[field[1]] = u'Вокзал'
            for item in substitutions_dict.keys() :
                if ticket[field[0]] == item :
                    ticket[field[0]] = substitutions_dict[item][0]
                    ticket[field[1]] = substitutions_dict[item][1]

    return tickets

def parseTicketPages(ticket_pages) :
    """
    parseTicketPages(ticket_pages)
        'ticket_pages' - list of string with ticket pages
        returns tickets as the list of dicts 
        according to the 'marks' settings below.
    """
    # Marks and other stuff for parsing fucking RZD html
    # List of lists
    #              Mark,                      Start Shift,   End Shift,  Type,    Corresponding Fields of Dict
    marks = [["Ваш номер заказа",                '78', '92',       'str',   'orderNumber'],                    # 0
             ["Дата и время заказа",             '58', '79',       'date',  'orderDatetime'],                  # 1
             ["Номер поезда",                    '46', '49',       'int',   'trainNumber'],                    # 2
             ["Маршрут следования пассажира",    '77', "</td>",    'str',   ['departureCity', 'arrivalCity']], # 3
             ["Дата и время отправления поезда", '81', '102',      'date',  'departureDatetime'],              # 4
             ["Дата и время прибытия поезда",    '75', '96',       'date',  'arrivalDatetime'],                # 5
             ["Номер вагона",                    '46', '48',       'int',   'carNumber'],                      # 6
             ["Тип вагона",                      '80', "&nbsp;",   'str',   'carType'],                        # 7
             ["Номера мест",                     '61', '63',       'int',   'seatNumber'],                     # 8
             ["Стоимость заказа",                '41', "руб.",     'int',   'price'],                          # 9
             ["ФИО",                             '  ', "&nbsp;",   'str',   'passenger']]                      # 10

    print '\nParsing ticket pages'

    # Set of orderNumbers of unique tickets
    order_numbers_set = set()

    # Parsing raw tickets
    tickets = []    # List of dicts

    #   for ticket_page in ticket_pages :
    #       ticket_page = unicode(ticket_page, 'utf-8')

    for ticket_page in ticket_pages :

        ticket = {}     # Empty Dict for coming ticket

        for mark in marks :
            # Searching for special mark that corresponds to desired data
            # Position of the mark/label
            mark_pos = string.find(ticket_page, mark[0])

            # Fixed length data
            if str.isdigit(mark[1]) and str.isdigit(mark[2]) :

                start_pos = mark_pos + int(mark[1])
                end_pos   = mark_pos + int(mark[2])
                chunk = ticket_page[start_pos : end_pos]

                # Converting data to non-string types
                if mark[3] == 'date' :
                    chunk = datetime.datetime.strptime(chunk,"%d.%m.%Y&nbsp;%H:%M")   # to datetime object
                    #chunk = time.strptime(chunk,"%d.%m.%Y&nbsp;%H:%M")  # time object doesnt support subtracting
                    #chunk = datetime.datetime.strftime("%Y.%m.%d %H:%M", chunk)       # to string
                elif mark[3] == 'int' :
                    chunk = int(chunk)

                ticket[mark[4]] = chunk

            # Variable length data
            elif mark[0] == marks[3][0] :   # Route
                start_pos = mark_pos + int(mark[1])
                end_pos = start_pos + string.find( ticket_page[mark_pos + int(mark[1]) : mark_pos + 200], mark[2])
                chunk = ticket_page[start_pos : end_pos]

                middle_pos = string.find(chunk, "&nbsp;-&nbsp;")
                ticket[mark[4][0]] = chunk[0 : middle_pos]                                 #departureCity
                ticket[mark[4][1]] = chunk[middle_pos + len("&nbsp;-&nbsp;") : len(chunk)] #arrivalCity

            elif mark[0] == marks[7][0] :     # Car Type
                start_pos = mark_pos + int(mark[1])
                end_pos = start_pos + string.find(ticket_page[mark_pos + int(mark[1]) : mark_pos + 150], mark[2])
                chunk = ticket_page[start_pos : end_pos]
                ticket[mark[4]] = chunk

            elif mark[0] == marks[9][0] :    # Price
                start_pos = mark_pos + int(mark[1])
                end_pos = start_pos + string.find(ticket_page[mark_pos + int(mark[1]) : mark_pos + 100], mark[2] ) - 9
                chunk = ticket_page[start_pos : end_pos]
                # Replacing of decimal comma with point
                # Cannot cast string '565.54' directly to int
                ticket[mark[4]] = int(float(chunk.replace(',','.')))

            elif mark[0] == marks[10][0] :    # Passenger
                # Position of the passenger's name depends on ticket price's position
                price = str(ticket['price'])
                price_pos = string.find(ticket_page, price)     # Too weak, price - just a three or four digit number
                start_pos = string.find(ticket_page[price_pos : price_pos + 20], "<td>") + price_pos + len("<td>")
                end_pos = start_pos + string.find(ticket_page[start_pos : start_pos + 50], mark[2])
                chunk = ticket_page[start_pos : end_pos]
                ticket[mark[4]] = chunk

            else :
                # Non-listed above field doesn't acceptable
                print "Parsing warning. Unknown field mark."

        # Uniqueness testing
        # Store only unique tickets
        if not ticket['orderNumber'] in order_numbers_set :
            order_numbers_set.add(ticket['orderNumber'])
            tickets.append(ticket)
            print "\tTicket #" + ticket['orderNumber'] + " processed"

    print '\t--------------------------------------\n\t' + str(len(tickets)) + ' unique out of ' + str(len(ticket_pages)) + " tickets processed."

    return  tickets

# OUTPUT

def formTable(tickets) :
    """
    formTable(tickets)
        returns printable CSV table
        'tickets' - list of dicts
    """

    # Strong order of the fields for dictionary printing
    # List
    fields = ['orderNumber',       # 0
              'orderDatetime',     # 1
              'trainNumber',       # 2
              'departureCity',     # 3
              'departureStation',   # 4
              'arrivalCity',       # 5
              'arrivalStation',     # 6
              'departureDatetime', # 7
              'arrivalDatetime',   # 8
              'carNumber',         # 9
              'carType',           # 10
              'seatNumber',        # 11
              'price',             # 12
              'passenger']         # 13

    # Form CSV table
    delimiter = ', '
    table = ''
    line = ''

    # Write titles
    for field in fields :
        line = line + str(field) + delimiter

    table = table + line + '\n'

    # Write each ticket in line
    for ticket in tickets :
        line = ''
        for field in fields :  # Sorting in specific order
            chunk = ticket[field]
            if str(type(ticket[field])) == "<type 'unicode'>" :
                chunk = ticket[field].encode('utf-8', 'ignore')

            if field.endswith('Datetime') :
                chunk = datetime.datetime.strftime(ticket[field], "%Y.%m.%d %H:%M")
                
            line = line + str(chunk) + delimiter

        table = table + line + '\n'


    return table

def dispTable(tickets) :
    print '\n' + formTable(tickets)

def selectPassenger(tickets, name) :
    """
    selectPassenger(tickets, name) 
        returns 'tickets' filtered by passenger last 'name'
    """

    name = unicode(name, 'utf-8')
    tickets_quantity = len(tickets)
    selected_tickets = []

    print '\nPassenger selection: ' + name
    for ticket in tickets :
        if ticket['passenger'] == name :
            selected_tickets.append(ticket)

    print '\tRemoved ' + str(tickets_quantity - len(selected_tickets)) + ' out of ' + str(tickets_quantity) + ' tickets.'

    return selected_tickets

def dispStatistics(tickets) :
    """
    dispStatistics(tickets) 
        form and display some useful descriptive statistics of ''tickets''
    """
    tickets_quantity = len(tickets) 

    if len(tickets) == 0 :
        print "ERROR! There are no tickets with given passenger's name.\nExit."
        sys.exit()

    # Numbers

    print '\n\n\t┏━━━━━━━━━━━━━━━━━━━┓'
    print     '\t┃ Ticket statistics ┃'
    print     '\t┗━━━━━━━━━━━━━━━━━━━┛\n'


    print '\tTotal number of tickets: ' + str(tickets_quantity)
    print '\tYour tickets: ' + str(len(tickets)) + ' (' + str( len(tickets) * 100 / tickets_quantity ) + '%)'

    # Times

    diff_ord_dep = []
    diff_dep_arr = []

    for ticket in tickets :
        diff_ord_dep.append((ticket['departureDatetime'] - ticket['orderDatetime']).total_seconds())
        diff_dep_arr.append((ticket['arrivalDatetime'] - ticket['departureDatetime']).total_seconds())

    round_coeff = 0
    print '\n\t\tTime differences'
    print '\t\tArr-Dep\t\tDep-Arr'
    print '----------------------------------'
    print 'Median\t' + str(datetime.timedelta(seconds = median(diff_dep_arr),)) +'\t\t' + str(datetime.timedelta(seconds=median(diff_ord_dep)))
    print 'Mean\t'   + str(datetime.timedelta(seconds = round(mean(diff_dep_arr),round_coeff)))   +'\t\t' + str(datetime.timedelta(seconds=round(mean(diff_ord_dep),round_coeff)))
    print 'Std\t'  + str(datetime.timedelta(seconds = round(std(diff_dep_arr),round_coeff)))    +'\t\t' + str(datetime.timedelta(seconds=round(std(diff_ord_dep),round_coeff)))
    print 'Min\t'  + str(datetime.timedelta(seconds = min(diff_dep_arr)))    +'\t\t' + str(datetime.timedelta(seconds=min(diff_ord_dep)))
    print 'Max\t'  + str(datetime.timedelta(seconds = max(diff_dep_arr)))    +'\t\t' + str(datetime.timedelta(seconds=max(diff_ord_dep)))


    # Car type
    print '\n\tCar types'
    print '-------------'
    car_types = getList(tickets, 'carType')
    car_types_zip = getHist(car_types)
    car_types_set = []
    
    for h, t in car_types_zip :
        car_types_set.append(t)
        print str(h) + '\t' + t


    # Price
    price = getList(tickets, 'price')

    # Price by car types

    # Data preparation
    price_by_car_types = {}

    for t in car_types_set :
        price_by_car_types[t] = []
        for car_type, p in zip(car_types, price) :
            if car_type == t :
                price_by_car_types[t].append(p)
    price_by_car_types['All'] = price
    car_types_set.insert(0, 'All')




    # Show table
    # Some helpful for table formatting function
    def addTabs(string) :
        if len(string) < 4 :
            return '\t\t'
        elif len(string) > 7 :
            return '\t'
        else :
            return '\t\t'

    # Build Titles
    title = '\nPrices\t\t'
    for item in car_types_set :
        title += item + addTabs(item)
    title += '\n-----------------------------------------------------'



    # Build Table
    metric_function = ['median','mean','std','min','max','sum']
    table = title
    for metric in metric_function :
        line = metric + addTabs(metric)
        for type in car_types_set :
            m = str(round(getattr(numpy, metric)(price_by_car_types[type]), round_coeff))
            line += m + addTabs(m)
        table += '\n' + line
    print table



    
    
    # Route

    routes = []
    arr_city = getList(tickets, 'arrivalCity')
    dep_city = getList(tickets, 'departureCity')


    for it in range(0, len(arr_city)) :
        routes.append(dep_city[it] + ' -> ' + arr_city[it])

    route_hist_zip = getHist(routes)
    h, routes_set = zip(*route_hist_zip)

    price_by_route = {}
    for route in routes_set :
        price_by_route[route] = []
        for r, p in zip(routes, price) :
            if r == route :
                price_by_route[route].append(p)

    print '\n\tMedian price\tRoutes'
    print '-------------------------------'
    for h, route in route_hist_zip :
        print str(h) + '\t' + str(round(median(price_by_route[route]), round_coeff)) + '\t\t\t' + route

    arr_stations = []
    dep_stations = []

    # Stations
    for ticket in tickets :
        if ticket['arrivalCity'] == u'Москва' :
            arr_stations.append(ticket['arrivalStation'])
        if ticket['departureCity'] == u'Москва' :
            dep_stations.append(ticket['departureStation'])

    dep_stations_zip = getHist(dep_stations)
    arr_stations_zip = getHist(arr_stations)

    print '\n\tArrival Stations'
    print '------------------------'
    for h, v in arr_stations_zip :
        print str(h) + '\t' + v

    print '\n\tDeparture Stations'
    print '------------------------'
    for h, v in dep_stations_zip :
        print str(h) + '\t' + v

# MAIN

def main(args) :
    """
    main(args)
        realizes command line UI. 
        to display help message use '-h'
    """

    argn = len(args)
    keys_help = ['-h', '--help']
    keys_acc = ['-a', '--acc']
    keys_load = ['-l', '--load']
    keys_save = ['-s', '--save']
    keys_disp = ['-d', '--disp']
    keys_name = ['-n', '--name']
    keys_lic  = ['--lic']

    def strKeys(k) :
        return k[0] + ' ( or ' + k[1] + ')'

    command_name = args[0][2 : len(args[0])]

    help_text = '\nNAME' \
                '\n\t' + command_name + ' provides an overview and useful statistics of your travels by Russian Railways.' \
                \
                '\n\nSYNOPSIS ' \
                '\n\t' + command_name + ' {source} [{filter}] [{output}]' \
                \
                '\n\nDESCRIPTION' \
                '\n\n\tSource of the ticket data.'\
                '\n\t\t{source}:'\
                '\n\t\t\t' + strKeys(keys_acc)  + '\t{login}' + '\t{password}' + '\t- your RZD account;' \
                '\n\t\t\t' + strKeys(keys_load) + '\tpages'   + '\t{path}'     + '\t\t- pre-saved html-pages of tickets from your account;' \
                '\n\t\t\t' + strKeys(keys_load) + '\ttickets' + '\t{path}'     + '\t\t- per-serialized tickets data;' \
                "\n\n\tFilter tickets by passenger's last name. Optional (default: any passenger ( = --name any))."\
                '\n\t\t{filter}:'\
                '\n\t\t\t' + strKeys(keys_name) + '\t{last name}' + '\t\t- {last name} must start with a capital letter;' \
                '\n\n\tWay of output. Optional (default: display table and statistics ( = --disp all)).'\
                '\n\t\t{output}:'\
                '\n\t\t\t' + strKeys(keys_disp) + '\tstats'   + '\t\t- display ticket statistics;' \
                '\n\t\t\t' + strKeys(keys_disp) + '\ttable'   + '\t\t- display table of tickets;' \
                '\n\t\t\t' + strKeys(keys_disp) + '\tall'     + '\t\t- display table of ticket and statistics;' \
                '\n\t\t\t' + strKeys(keys_save) + '\tpages'   + '\t{path}' + '\t- save ticket pages from your account one by one in {path} folder;' \
                '\n\t\t\t' + strKeys(keys_save) + '\ttickets' + '\t{path}' + '\t- save tickets in pickle file by given path;' \
                '\n\t\t\t' + strKeys(keys_save) + '\ttable'   + '\t{path}' + '\t- save table of tickets as CSV file.' \
                \
                '\n\nEXAMPLES' \
                "\n\t" + command_name + " --account {username} {password} " \
                "\n\t\t\t- gets tickets from your RZD account and shows you tickets' table and statistics; \n" \
                "\n\t" + command_name + " --load tickets ./tickets.pkl --name Smith --disp table --save table ./tickets.csv " \
                "\n\t\t\t- gets tickets from pre-saved file of tickets' data, shows you tickets' table and save the table as CSV file. " \
                \
                '\n\nAUTHOR' \
                '\n\tAndrew «ks1v» Kiselev' \
                '\n\tmail@andrewkiselev.com' \
                '\n\thttp://andrewkiselev.com' \
                '\n\thttp://twitter.com/ks1v'\
                \
                '\n\nREPORTING BUGS' \
                '\n\tSubmit new issue: \thttps://bitbucket.org/ks1v/rzd-tickets-analyser/issues/new' \
                '\n\tProject repo: \t\thttps://bitbucket.org/ks1v/rzd-tickets-analyser' \
                '\n\tProject page: \t\thttp://andrewkiselev.com/rzd-tickets-analyser'
                 






    if argn == 1 :
        print 'Use -h or --help to show help.'
        sys.exit()
    
    if args[1] in keys_help :
        print help_text
        sys.exit()
        
    if args[1] in keys_lic :
        fd = open('./LICENSE', 'r')
        print fd.read()
        fd.close()
        sys.exit()

    if argn < 4 :
        print '\nERROR! Insufficient number of arguments.'
        sys.exit()

    if args[1] in keys_acc :
        login = args[2]
        password = args[3]
        ticket_pages = getTicketsPagesFromSite(login, password)
        tickets = parseTicketPages(ticket_pages)
        tickets = treatTextFields(tickets)
        current_arg = 4


    elif args[1] in keys_load :
        content = args[2]
        path = args[3]
        current_arg = 4

        if content == 'pages' :
            if not os.path.isdir(path) :
                print '\nERROR! There is no such directory.'
                sys.exit()
            ticket_pages = loadTicketPages(path)
            tickets = parseTicketPages(ticket_pages)
            tickets = treatTextFields(tickets)

        elif content == 'tickets' :
            if not os.path.isfile(path) :
                print '\nERROR! There is no such file.'
                sys.exit()
            tickets = loadTickets(path)

        else :
            print '\nERROR! Unexpected content to load'
            sys.exit()
    else :
        print '\nERROR! Unexpected input action'
        sys.exit()


    if current_arg + 1 <= argn :
        if args[current_arg] in keys_name :
            name = args[current_arg + 1]
            if not name == 'any' :
                tickets = selectPassenger(tickets, name)
                current_arg += 2


    if argn == current_arg :
        dispTable(tickets)
        dispStatistics(tickets)
        sys.exit()

    else :

        while current_arg < argn :

            if ( args[current_arg] in keys_save ) and ( current_arg + 2 <= argn ) :
                content = args[current_arg + 1]
                path = args[current_arg + 2]

                if content == 'pages' :
                    if args[2] == 'tickets' :
                        print "\nWARNING! Cannot save ticket pages, I don't have it."
                    else :
                        saveTicketPages(ticket_pages, path)
                        current_arg += 3
                        continue

                elif content == 'tickets' :
                    saveTickets(tickets, path)
                    current_arg += 3
                    continue

                elif content == 'table' :
                    saveCSVTable(tickets, path)
                    current_arg += 3
                    continue

                else :
                    print '\nERROR! Unexpected content to save'
                    sys.exit()

            elif ( args[current_arg] in keys_disp ) and ( current_arg + 2 <= argn ) :
                if args[current_arg + 1] == 'stats' :
                    dispStatistics(tickets)
                    current_arg += 2
                    continue

                elif args[current_arg + 1] == 'table' :
                    dispTable(tickets)
                    current_arg += 2
                    continue

                elif args[current_arg + 1] == 'all' :
                    dispTable(tickets)
                    dispStatistics(tickets)
                    current_arg += 2
                    continue

                else :
                    print '\nERROR! Unexpected content to display'
                    sys.exit()

            else :
                print '\nERROR! Unexpected output action'
                sys.exit()

main(sys.argv)

